from flask import Flask, request, jsonify
import requests
import base64
import time

app = Flask(__name__)
from dotenv import load_dotenv
import os

load_dotenv()

CLIENT_ID = os.getenv("EBAY_CLIENT_ID")
CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET")

CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"

cached_token = None
token_expiry = 0


# ---------- TOKEN ----------
def get_token():
    global cached_token, token_expiry

    if cached_token and time.time() < token_expiry:
        return cached_token

    auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

    res = requests.post(
        TOKEN_URL,
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data={
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope"
        }
    )

    data = res.json()

    cached_token = data["access_token"]
    token_expiry = time.time() + 3500

    return cached_token


# ---------- EBAY SEARCH ----------
def search(query):
    token = get_token()

    res = requests.get(
        SEARCH_URL,
        headers={"Authorization": f"Bearer {token}"},
        params={"q": query, "limit": 20}
    )

    return res.json().get("itemSummaries", [])


# ---------- ANALYTICS ----------
def analyze(isbn):

    active = search(isbn)

    active_prices = []
    for item in active:
        try:
            active_prices.append(float(item["price"]["value"]))
        except:
            pass

    if not active_prices:
        return None

    avg_price = sum(active_prices) / len(active_prices)

    # SELL THROUGH ESTIMATE (proxy model)
    sell_through = min(len(active_prices) / 20, 1.0)

    # pricing logic
    buy_price = 2
    fee = avg_price * 0.13
    shipping = 3.5

    profit = avg_price - buy_price - fee - shipping

    recommendation_price = avg_price * 0.85

    return {
        "avg_price": round(avg_price, 2),
        "sell_through": round(sell_through, 2),
        "profit": round(profit, 2),
        "recommended_price": round(recommendation_price, 2),
        "decision": "BUY" if profit > 5 and sell_through > 0.3 else "SKIP"
    }


# ---------- API ----------
@app.route("/scan", methods=["POST"])
def scan():
    data = request.json
    isbn = data.get("isbn")

    result = analyze(isbn)

    if not result:
        return jsonify({"error": "no data"})

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)