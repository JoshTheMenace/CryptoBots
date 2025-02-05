#!/usr/bin/env python3
"""
RSI Bot with API Integration

This bot:
  • Polls your market data API every minute for the current price.
  • Constructs a candle (with open, high, low, and close all equal to the fetched price) per interval.
  • Maintains a history of candles to compute the 14–bar RSI.
  • Trading rules:
      - If not in a position:
          • If RSI < 30, go LONG.
          • If RSI > 70, go SHORT.
      - If in a position:
          • For LONG positions, exit when RSI > 50.
          • For SHORT positions, exit when RSI < 50.
  • Sends trade orders to your API.
  
No charting is performed.
"""

import time
import datetime
import requests
import pandas as pd
import numpy as np

# ------------------------------
# CONFIGURATION
# ------------------------------
BOT_ID = "-OI06Bn4r8qCHY8LsMrh"         # Unique bot identifier
USER_ID = "6xDYg9OrqaRlkLecm4CFG2G1rq93"  # Your user id
SYMBOL = "BTC"                           # Trading symbol
ORDER_TYPE = "market"                    # Order type ("market")
TRADE_AMOUNT = 0.01                      # Amount to trade per order

# API Endpoints (adjust host/port if necessary)
TRADE_API_URL = f"https://crypto-bots-mu.vercel.app/api/bots/{BOT_ID}/trades"
MARKET_DATA_API_URL = "https://crypto-bots-mu.vercel.app/api/market-data"
# For local testing you might use:
# TRADE_API_URL = f"http://localhost:3000/api/bots/{BOT_ID}/trades"
# MARKET_DATA_API_URL = "http://localhost:3000/api/market-data"

# RSI Parameters
RSI_PERIOD = 14  # Number of bars used for RSI calculation

# Evaluation interval (in seconds)
EVALUATION_INTERVAL = 60

# ------------------------------
# GLOBAL STATE
# ------------------------------
position = 0       # 0: no position, 1: long, -1: short
entry_price = None # Price at which the current position was entered
profit = 0.0       # Cumulative profit
candles = []       # List to store recent candles (each candle is a dict)

# ------------------------------
# FUNCTIONS
# ------------------------------

def compute_RSI(series, period=14):
    """
    Compute the Relative Strength Index (RSI) for a given pandas Series.
    """
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    # Compute the rolling average of gains and losses.
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def fetch_market_price():
    """
    Fetch the current market price for SYMBOL from the market data API.
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
      - amount: trade amount
      - price: current market price
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

def evaluate_RSI():
    """
    Evaluates the RSI strategy using the close prices from the recent candles.
    
    Trading rules:
      - If not in a position:
          • If RSI < 30 → enter LONG.
          • If RSI > 70 → enter SHORT.
      - If in a position:
          • For LONG: exit when RSI > 50.
          • For SHORT: exit when RSI < 50.
    """
    global position, entry_price, profit, candles

    # Need at least (RSI_PERIOD + 1) data points to compute RSI
    if len(candles) < RSI_PERIOD + 1:
        print(f"[{datetime.datetime.now().isoformat()}] ⏳ Not enough data to compute RSI ({len(candles)}/{RSI_PERIOD + 1}).")
        return

    # Create a pandas Series of close prices.
    closes = [candle['close'] for candle in candles]
    price_series = pd.Series(closes)
    rsi_series = compute_RSI(price_series, period=RSI_PERIOD)
    current_rsi = rsi_series.iloc[-1]
    current_price = candles[-1]['close']
    now_str = datetime.datetime.now().isoformat()
    print(f"[{now_str}] Current Price: ${current_price:.2f}, RSI: {current_rsi:.2f}")

    # Trading logic:
    if position == 0:
        if current_rsi < 30:
            position = 1
            entry_price = current_price
            print(f"[{now_str}] Entering LONG as RSI {current_rsi:.2f} < 30")
            send_trade_order("buy", TRADE_AMOUNT, current_price)
        elif current_rsi > 70:
            position = -1
            entry_price = current_price
            print(f"[{now_str}] Entering SHORT as RSI {current_rsi:.2f} > 70")
            send_trade_order("sell", TRADE_AMOUNT, current_price)
    else:
        if position == 1 and current_rsi > 50:
            profit_change = current_price - entry_price
            profit += profit_change
            print(f"[{now_str}] Exiting LONG as RSI {current_rsi:.2f} > 50 (Profit: ${profit_change:.2f}). Cumulative Profit: ${profit:.2f}")
            send_trade_order("sell", TRADE_AMOUNT, current_price)
            position = 0
            entry_price = None
        elif position == -1 and current_rsi < 50:
            profit_change = entry_price - current_price
            profit += profit_change
            print(f"[{now_str}] Exiting SHORT as RSI {current_rsi:.2f} < 50 (Profit: ${profit_change:.2f}). Cumulative Profit: ${profit:.2f}")
            send_trade_order("buy", TRADE_AMOUNT, current_price)
            position = 0
            entry_price = None

def main():
    global candles
    print("🚀 Starting RSI Bot with API Integration...")
    while True:
        price = fetch_market_price()
        if price is None:
            print(f"[{datetime.datetime.now().isoformat()}] ⚠️ Skipping this interval due to market data error.")
        else:
            now = datetime.datetime.now()
            # Build a new candle from the fetched price (all OHLC values are the same).
            candle = {
                'timestamp': now,
                'open': price,
                'high': price,
                'low': price,
                'close': price
            }
            candles.append(candle)
            # Optionally, keep only the most recent (RSI_PERIOD + 1) candles.
            if len(candles) > RSI_PERIOD + 1:
                candles = candles[-(RSI_PERIOD + 1):]
            evaluate_RSI()
        time.sleep(EVALUATION_INTERVAL)

if __name__ == '__main__':
    main()
