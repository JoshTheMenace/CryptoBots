#!/usr/bin/env python3
"""
Live Momentum Bot Using API Endpoints for Trading

This bot:
  • Polls a market data endpoint every minute (e.g., http://localhost:3000/api/market-data)
  • Maintains a price history to compute a momentum indicator over a specified period.
  • Computes momentum as: current_price - price from MOMENTUM_PERIOD minutes ago.
  • Generates trade signals based on the momentum:
      - If no open position and momentum > THRESHOLD → send a BUY order.
      - If no open position and momentum < -THRESHOLD → send a SELL order.
      - If in a long position (buy) and momentum becomes negative → exit (SELL).
      - If in a short position (sell) and momentum becomes positive → exit (BUY).
  • Sends trade orders via your API endpoint (e.g., http://localhost:3000/api/bots/{BOT_ID}/trades).
  
Adjust the configuration parameters below as needed.
"""

import time
import datetime
import requests

# ------------------------------
# CONFIGURATION
# ------------------------------

# Bot & User Info (ensure these match what your API expects)
BOT_ID = "-OI-3FJjbLGuY7QiKlBp"      # Unique bot identifier
USER_ID = "6xDYg9OrqaRlkLecm4CFG2G1rq93"  # Your user id in the system
SYMBOL = "BTC"                      # Trading symbol (e.g. "BTC" or "ETH")
ORDER_TYPE = "market"               # Order type ("market" in our case)
TRADE_AMOUNT = 0.01                # Amount of BTC per trade (adjust as needed)

# https://crypto-bots-mu.vercel.app
# https://cryptobots-7ae5a.web.app
# API Endpoints (adjust host/port if necessary)
# TRADE_API_URL = f"http://localhost:3000/api/bots/{BOT_ID}/trades"
# MARKET_DATA_API_URL = "http://localhost:3000/api/market-data"
TRADE_API_URL = f"https://crypto-bots-mu.vercel.app/api/bots/{BOT_ID}/trades"
MARKET_DATA_API_URL = "https://crypto-bots-mu.vercel.app/api/market-data"

# Momentum Strategy Parameters
MOMENTUM_PERIOD = 10   # Number of minutes (data points) to look back
THRESHOLD = 50         # Momentum threshold (in USD) to trigger an entry

# Evaluation interval (in seconds) – here, we poll every minute
EVALUATION_INTERVAL = 60

# ------------------------------
# GLOBAL STATE
# ------------------------------

# Price history will store tuples of (timestamp, price)
price_history = []  # one data point per minute
# Position flag: 0 means no open position; 1 means long; -1 means short.
position = 0
# The price at which the current position was entered.
entry_price = None
# Cumulative profit (for logging purposes)
profit = 0.0

# ------------------------------
# FUNCTIONS
# ------------------------------

def fetch_market_data():
    """
    Retrieves the latest market prices from the market-data endpoint.
    Expected JSON format: { "BTC": <price>, "ETH": <price> }
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
        "side": side,       # "buy" or "sell"
        "amount": amount,   # e.g., 0.001 BTC
        "price": price,     # current market price
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
    Computes the momentum indicator from the price history and determines if a trade signal is generated.
    
    Momentum is defined as:
        momentum = current_price - price from MOMENTUM_PERIOD minutes ago.
    
    Trading logic:
      - If no position and momentum > THRESHOLD → send BUY order.
      - If no position and momentum < -THRESHOLD → send SELL order.
      - If in a long position (position == 1) and momentum < 0 → exit by selling.
      - If in a short position (position == -1) and momentum > 0 → exit by buying.
    """
    global position, entry_price, profit, price_history
    
    if len(price_history) < MOMENTUM_PERIOD:
        print(f"[{datetime.datetime.now().isoformat()}] ⏳ Waiting for at least {MOMENTUM_PERIOD} data points...")
        return
    
    # Current price is the last recorded price; price from MOMENTUM_PERIOD minutes ago:
    current_price = price_history[-1][1]
    past_price = price_history[-MOMENTUM_PERIOD][1]
    momentum = current_price - past_price
    
    now_str = datetime.datetime.now().isoformat()
    print(f"[{now_str}] Momentum: {momentum:.2f} (Current: {current_price:.2f}, {MOMENTUM_PERIOD} minutes ago: {past_price:.2f})")
    
    if position == 0:
        # No open position: enter based on strong momentum.
        if momentum > THRESHOLD:
            print(f"[{now_str}] 📈 Buy signal detected.")
            if send_trade_order("buy", TRADE_AMOUNT, current_price):
                position = 1
                entry_price = current_price
        elif momentum < -THRESHOLD:
            print(f"[{now_str}] 📉 Sell signal detected.")
            if send_trade_order("sell", TRADE_AMOUNT, current_price):
                position = -1
                entry_price = current_price
    else:
        # Exit conditions: exit when momentum reverses sign relative to your open position.
        if position == 1 and momentum < 0:
            print(f"[{now_str}] Exiting long position.")
            if send_trade_order("sell", TRADE_AMOUNT, current_price):
                profit += current_price - entry_price
                position = 0
                entry_price = None
        elif position == -1 and momentum > 0:
            print(f"[{now_str}] Exiting short position.")
            if send_trade_order("buy", TRADE_AMOUNT, current_price):
                profit += entry_price - current_price
                position = 0
                entry_price = None

def main():
    """
    Main loop:
      - Every minute, fetch the latest market data.
      - Append the current price with its timestamp to price_history.
      - Keep the history to a reasonable size.
      - Evaluate the momentum indicator and send trade orders if signals are generated.
    """
    global price_history

    print("🚀 Starting Live Momentum Bot...")
    while True:
        market_data = fetch_market_data()
        if market_data is not None:
            current_price = market_data.get(SYMBOL)
            if current_price is not None:
                now = datetime.datetime.now()
                price_history.append((now, current_price))
                # Optionally, limit the history size (e.g., keep the last 100 data points)
                if len(price_history) > 100:
                    price_history = price_history[-100:]
                evaluate_trading_signal()
            else:
                print(f"[{datetime.datetime.now().isoformat()}] ⚠️ {SYMBOL} price not found in market data.")
        else:
            print(f"[{datetime.datetime.now().isoformat()}] ⚠️ No market data received.")
        
        time.sleep(EVALUATION_INTERVAL)

if __name__ == '__main__':
    main()
