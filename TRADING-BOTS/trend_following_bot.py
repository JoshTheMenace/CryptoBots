#!/usr/bin/env python3
"""
Trend-Following Bot Using Real Market Data and Your Node.js API

This bot:
  • Polls a market data endpoint every minute (e.g. http://localhost:3000/api/market-data)
  • Maintains a price history to compute moving averages (fast: 10 minutes, slow: 50 minutes)
  • Generates buy/sell signals based on a moving average crossover strategy
  • Sends trade orders to your API (which simulates trades and updates balances)
  
Configuration:
  • The bot trades a given symbol (e.g. "BTC")
  • Trade orders are sent as market orders.
  • Each trade is for a fixed amount.
  
Adjust the parameters below as needed.
"""

import time
import datetime
import requests

# ------------------------------
# CONFIGURATION
# ------------------------------

# Bot & User Info (ensure these match what your API expects)
BOT_ID = "-OHzvwendj9Ttjoh0Df-"  # Unique bot identifier
USER_ID = "6xDYg9OrqaRlkLecm4CFG2G1rq93"  # Your user id in the system
SYMBOL = "BTC"               # Trading symbol (e.g. "BTC" or "ETH")
ORDER_TYPE = "market"        # Order type ("market" in our case)
TRADE_AMOUNT = 0.01        # Reduced trade amount: amount of BTC per trade

# API Endpoints (adjust host/port if necessary)
# https://crypto-bots-mu.vercel.app
# https://cryptobots-7ae5a.web.app
TRADE_API_URL = f"https://crypto-bots-mu.vercel.app/api/bots/{BOT_ID}/trades"
MARKET_DATA_API_URL = "https://crypto-bots-mu.vercel.app/api/market-data"
# TRADE_API_URL = f"http://localhost:3000/api/bots/{BOT_ID}/trades"
# MARKET_DATA_API_URL = "http://localhost:3000/api/market-data"

# Moving Average Parameters (in minutes)
FAST_WINDOW = 10  # Fast moving average window (e.g. 10 minutes)
SLOW_WINDOW = 50  # Slow moving average window (e.g. 50 minutes)

# Evaluation interval (in seconds)
EVALUATION_INTERVAL = 60  # Evaluate every 60 seconds

# Cooldown period (in seconds) between successful trades to reduce overtrading
COOLDOWN = 60  # 1 minutes

# ------------------------------
# GLOBAL STATE
# ------------------------------

# We'll store the latest minute prices in a list of tuples: (timestamp, price)
price_history = []  # will store up to SLOW_WINDOW values

# Position flag: 0 means no open position, 1 means currently long
current_position = 0

# Timestamp (in seconds since epoch) of the last successful trade
last_trade_time = None

# ------------------------------
# FUNCTIONS
# ------------------------------

def fetch_market_data():
    """
    Retrieves the latest market prices from the market-data endpoint.
    Expects a JSON response with keys such as "BTC" and "ETH".
    """
    try:
        response = requests.get(MARKET_DATA_API_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        print(f"[{datetime.datetime.now().isoformat()}] ❌ Error fetching market data: {e}")
        return None

def send_trade_order(side, amount, price):
    """
    Sends a trade order to your API.
    The payload includes:
      - side: "buy" or "sell"
      - amount: amount of asset to trade
      - price: the execution price (for market orders, this is the current market price)
      - userId, symbol, and orderType
    Returns True if the order was executed successfully, False otherwise.
    """
    payload = {
        "side": side,
        "amount": amount,
        "price": price,
        "userId": USER_ID,
        "symbol": SYMBOL,
        "orderType": ORDER_TYPE
    }
    try:
        response = requests.post(TRADE_API_URL, json=payload, timeout=5)
        response.raise_for_status()
        result = response.json()
        print(f"[{datetime.datetime.now().isoformat()}] ✅ Trade executed: {side} {amount} {SYMBOL} at ${price:.2f}")
        print("Updated balances:", result.get("balances"))
        return True
    except Exception as e:
        if hasattr(e, 'response') and e.response is not None:
            print(f"[{datetime.datetime.now().isoformat()}] ❌ Trade order error: {e.response.text}")
        else:
            print(f"[{datetime.datetime.now().isoformat()}] ❌ Error sending trade order: {e}")
        return False

def evaluate_trading_signal():
    """
    Computes the fast and slow moving averages from the price history and decides if a trade signal is generated.
    Trading logic (trend following):
      - If not in a position and fast MA > slow MA, send a buy order.
      - If in a long position and fast MA < slow MA, send a sell order.
    A cooldown is enforced between trades.
    """
    global current_position, price_history, last_trade_time

    if len(price_history) < FAST_WINDOW:
        print(f"[{datetime.datetime.now().isoformat()}] ⏳ Waiting for at least {FAST_WINDOW} data points...")
        return

    # Enforce cooldown: if a trade was executed recently, skip evaluation.
    now_ts = time.time()
    if last_trade_time is not None and (now_ts - last_trade_time) < COOLDOWN:
        remaining = COOLDOWN - (now_ts - last_trade_time)
        print(f"[{datetime.datetime.now().isoformat()}] ⏳ Cooldown active. Waiting {remaining:.0f} more seconds before next trade.")
        return

    # Compute fast moving average from the last FAST_WINDOW price points
    fast_prices = [price for (_, price) in price_history[-FAST_WINDOW:]]
    fast_ma = sum(fast_prices) / len(fast_prices)

    # Compute slow moving average from the last SLOW_WINDOW price points (or fewer if not available)
    current_window = min(len(price_history), SLOW_WINDOW)
    slow_prices = [price for (_, price) in price_history[-current_window:]]
    slow_ma = sum(slow_prices) / len(slow_prices)

    current_price = price_history[-1][1]
    now_str = datetime.datetime.now().isoformat()
    print(f"[{now_str}] Fast MA: ${fast_ma:.2f}, Slow MA: ${slow_ma:.2f}, Current {SYMBOL} Price: ${current_price:.2f}")

    # Trading logic:
    if current_position == 0 and fast_ma > slow_ma:
        print(f"[{now_str}] 📈 Buy signal detected. Attempting to send BUY order.")
        if send_trade_order("buy", TRADE_AMOUNT, current_price):
            current_position = 1
            last_trade_time = time.time()
    elif current_position == 1 and fast_ma < slow_ma:
        print(f"[{now_str}] 📉 Sell signal detected. Attempting to send SELL order.")
        if send_trade_order("sell", TRADE_AMOUNT, current_price):
            current_position = 0
            last_trade_time = time.time()
    else:
        print(f"[{now_str}] 🔎 No trade signal generated.")

def main():
    """
    Main loop:
      - Every minute, fetch the latest market data.
      - Record the price as the current minute's closing price.
      - Update the price history (keeping at most SLOW_WINDOW data points).
      - Evaluate the trading signal and send trade orders if conditions are met.
    """
    global price_history

    print("🚀 Starting Trend-Following Bot...")
    while True:
        market_data = fetch_market_data()
        if market_data is not None:
            print("Market data:", market_data)
            current_price = market_data.get(SYMBOL)
            if current_price is not None:
                now = datetime.datetime.now()
                price_history.append((now, current_price))
                if len(price_history) > SLOW_WINDOW:
                    price_history = price_history[-SLOW_WINDOW:]
                evaluate_trading_signal()
            else:
                print(f"[{datetime.datetime.now().isoformat()}] ⚠️ Current price for {SYMBOL} not found in market data.")
        else:
            print(f"[{datetime.datetime.now().isoformat()}] ⚠️ No market data received.")
        time.sleep(EVALUATION_INTERVAL)

if __name__ == "__main__":
    main()
