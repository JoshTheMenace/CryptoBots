#!/usr/bin/env python3
"""
Moving Average Bot with API Integration

This bot:
  • Polls your market data API every minute for the current price.
  • Constructs a candle (with open, high, low, and close all equal to the fetched price) per interval.
  • Maintains a history of the most recent 50 candles.
  • Computes a 50–bar moving average of the close prices.
  • Trading logic:
      - If not in a position, it enters a long position if current price > MA, or a short position if current price < MA.
      - If already in a position but the desired position (based on current price vs. MA) changes, it exits the current position (realizing profit or loss) and immediately flips to the new position.
  • Sends trade orders to your API and prints logs detailing actions and cumulative profit.

Configuration:
  • Update BOT_ID, USER_ID, SYMBOL, TRADE_AMOUNT, API endpoints, and EVALUATION_INTERVAL as needed.
  • No chart displays are provided.
"""

import time
import datetime
import requests

# ------------------------------
# CONFIGURATION
# ------------------------------
BOT_ID = "-OI04wNtjGRkfiEa3gO5"         # Unique bot identifier
USER_ID = "6xDYg9OrqaRlkLecm4CFG2G1rq93"  # Your user id
SYMBOL = "BTC"                           # Trading symbol
ORDER_TYPE = "market"                    # Order type ("market")
TRADE_AMOUNT = 0.01                      # Amount to trade per order

# API endpoints (adjust host/port if necessary)
TRADE_API_URL = f"https://crypto-bots-mu.vercel.app/api/bots/{BOT_ID}/trades"
MARKET_DATA_API_URL = "https://crypto-bots-mu.vercel.app/api/market-data"
# For local testing, you might use:
# TRADE_API_URL = f"http://localhost:3000/api/bots/{BOT_ID}/trades"
# MARKET_DATA_API_URL = "http://localhost:3000/api/market-data"

# Moving Average Parameters
WINDOW = 50  # Number of candles used to compute the moving average

# Evaluation interval (in seconds)
EVALUATION_INTERVAL = 60

# ------------------------------
# GLOBAL STATE
# ------------------------------
position = 0       # 0: no position, 1: long, -1: short
entry_price = None # Price at which the current position was entered
profit = 0.0       # Cumulative profit
candles = []       # List to store recent candles (each is a dict with open, high, low, close)

# ------------------------------
# FUNCTIONS
# ------------------------------
def fetch_market_price():
    """
    Fetches the current market price for SYMBOL from the market data API.
    Expects a JSON response like: { "BTC": 12345.67, ... }.
    """
    try:
        response = requests.get(MARKET_DATA_API_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        price = data.get(SYMBOL)
        if price is None:
            print(f"[{datetime.datetime.now().isoformat()}] ⚠️ {SYMBOL} not found in market data response.")
        return price
    except Exception as e:
        print(f"[{datetime.datetime.now().isoformat()}] ❌ Error fetching market data: {e}")
        return None

def send_trade_order(side, amount, price):
    """
    Sends a trade order to your API.
    The payload includes:
      - side: "buy" or "sell"
      - amount: the trade amount
      - price: the current market price
      - userId, symbol, and orderType
    Returns True if the order is executed successfully.
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

def evaluate_moving_average():
    """
    Evaluates the moving average strategy using the last WINDOW candles.
      - Computes the 50–bar moving average of the close prices.
      - Determines the desired position:
            * LONG (1) if current price > moving average.
            * SHORT (-1) if current price < moving average.
      - If not in a position, enters the desired position.
      - If already in a position but the desired position changes, exits the current position (realizing profit or loss)
        and immediately flips to the new position.
    """
    global position, entry_price, profit, candles

    if len(candles) < WINDOW:
        print(f"[{datetime.datetime.now().isoformat()}] ⏳ Not enough data to evaluate strategy ({len(candles)}/{WINDOW}).")
        return

    # Calculate the moving average from the last WINDOW candles' close prices.
    recent_candles = candles[-WINDOW:]
    moving_average = sum(candle['close'] for candle in recent_candles) / WINDOW

    current_candle = candles[-1]
    current_price = current_candle['close']
    now_str = datetime.datetime.now().isoformat()

    print(f"[{now_str}] Current Price: ${current_price:.2f}, MA: ${moving_average:.2f}")

    # Determine desired position based on current price relative to moving average.
    desired_position = 1 if current_price > moving_average else -1

    if position == 0:
        # Enter the desired position.
        position = desired_position
        entry_price = current_price
        if position == 1:
            print(f"[{now_str}] Entering LONG at ${current_price:.2f}")
            send_trade_order("buy", TRADE_AMOUNT, current_price)
        else:
            print(f"[{now_str}] Entering SHORT at ${current_price:.2f}")
            send_trade_order("sell", TRADE_AMOUNT, current_price)
    elif position != desired_position:
        # Exit the existing position.
        if position == 1:
            profit_change = current_price - entry_price
            profit += profit_change
            print(f"[{now_str}] Exiting LONG at ${current_price:.2f} (Profit: ${profit_change:.2f}). Cumulative Profit: ${profit:.2f}")
            send_trade_order("sell", TRADE_AMOUNT, current_price)
        else:
            profit_change = entry_price - current_price
            profit += profit_change
            print(f"[{now_str}] Exiting SHORT at ${current_price:.2f} (Profit: ${profit_change:.2f}). Cumulative Profit: ${profit:.2f}")
            send_trade_order("buy", TRADE_AMOUNT, current_price)
        # Immediately flip to the desired position.
        position = desired_position
        entry_price = current_price
        if position == 1:
            print(f"[{now_str}] Entering LONG at ${current_price:.2f}")
            send_trade_order("buy", TRADE_AMOUNT, current_price)
        else:
            print(f"[{now_str}] Entering SHORT at ${current_price:.2f}")
            send_trade_order("sell", TRADE_AMOUNT, current_price)
    else:
        # Maintain current position.
        print(f"[{now_str}] Maintaining position. Cumulative Profit: ${profit:.2f}")

def main():
    global candles
    print("🚀 Starting Moving Average Bot with API Integration...")
    while True:
        price = fetch_market_price()
        if price is None:
            print(f"[{datetime.datetime.now().isoformat()}] ⚠️ Skipping this interval due to market data error.")
        else:
            now = datetime.datetime.now()
            # Create a new candle from the fetched price (all OHLC values are equal).
            candle = {
                'timestamp': now,
                'open': price,
                'high': price,
                'low': price,
                'close': price
            }
            candles.append(candle)
            # Keep only the most recent WINDOW candles.
            if len(candles) > WINDOW:
                candles = candles[-WINDOW:]
            evaluate_moving_average()
        time.sleep(EVALUATION_INTERVAL)

if __name__ == '__main__':
    main()
