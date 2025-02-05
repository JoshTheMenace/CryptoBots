#!/usr/bin/env python3
"""
Mean Reversion Bot with API Integration

This bot:
  • Polls your market data endpoint every minute.
  • Maintains a history of candles (each candle is built from the fetched price).
  • Computes a 20–bar moving average and Bollinger Bands (±2 standard deviations).
  • Trading signals:
      - If not in a position:
          • If current price < lower Bollinger band, go LONG.
          • If current price > upper Bollinger band, go SHORT.
      - If in a position:
          • For LONG: exit when price reverts to or above the moving average.
          • For SHORT: exit when price reverts to or below the moving average.
  • Sends trade orders to your API.
  • Tracks cumulative profit.

Configuration:
  • Update BOT_ID, USER_ID, SYMBOL, TRADE_AMOUNT, and the API endpoints below as needed.
  • This bot does not display any charts.
"""

import time
import datetime
import requests
import statistics

# ------------------------------
# CONFIGURATION
# ------------------------------
BOT_ID = "-OI03MY90hlJZdXyJfKD"        # Unique bot identifier
USER_ID = "6xDYg9OrqaRlkLecm4CFG2G1rq93"  # Your user id
SYMBOL = "BTC"                          # Trading symbol
ORDER_TYPE = "market"                   # Order type ("market")
TRADE_AMOUNT = 0.01                     # Amount to trade per order

# API Endpoints (adjust host/port as needed)
TRADE_API_URL = f"https://crypto-bots-mu.vercel.app/api/bots/{BOT_ID}/trades"
MARKET_DATA_API_URL = "https://crypto-bots-mu.vercel.app/api/market-data"
# For local testing you might use:
# TRADE_API_URL = f"http://localhost:3000/api/bots/{BOT_ID}/trades"
# MARKET_DATA_API_URL = "http://localhost:3000/api/market-data"

# Mean Reversion Parameters
WINDOW = 20  # Number of candles for moving average and Bollinger Bands

# Evaluation interval (in seconds)
EVALUATION_INTERVAL = 60

# ------------------------------
# GLOBAL STATE
# ------------------------------
position = 0      # 0: no position, 1: long, -1: short
entry_price = None
profit = 0.0
candles = []      # List to store candles; each candle is a dict with open, high, low, close

# ------------------------------
# FUNCTIONS
# ------------------------------

def fetch_market_price():
    """
    Fetch the current market price for SYMBOL from the market data API.
    Expects a JSON response like { "BTC": 12345.67, ... }.
    """
    try:
        response = requests.get(MARKET_DATA_API_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        price = data.get(SYMBOL)
        if price is None:
            print(f"[{datetime.datetime.now().isoformat()}] ⚠️ {SYMBOL} not found in market data.")
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
    Returns True if the order was executed successfully.
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

def evaluate_mean_reversion():
    """
    Evaluates the mean reversion strategy using the last WINDOW candles:
      - Computes the moving average (ma) and standard deviation (std) of the close prices.
      - Calculates the upper and lower Bollinger Bands (ma ± 2*std).
      
    Trading logic:
      - If not in a position:
          • Enter LONG if current price is below the lower band.
          • Enter SHORT if current price is above the upper band.
      - If in a position:
          • For LONG: exit when current price reverts to or exceeds the moving average.
          • For SHORT: exit when current price reverts to or falls below the moving average.
    """
    global position, entry_price, profit, candles

    if len(candles) < WINDOW:
        print(f"[{datetime.datetime.now().isoformat()}] ⏳ Not enough data to evaluate strategy ({len(candles)}/{WINDOW}).")
        return

    # Use the last WINDOW candles to calculate indicators
    recent_candles = candles[-WINDOW:]
    close_prices = [candle['close'] for candle in recent_candles]
    
    ma = sum(close_prices) / WINDOW
    std = statistics.stdev(close_prices)
    upper_band = ma + 2 * std
    lower_band = ma - 2 * std

    # Get current price from the most recent candle
    current_candle = candles[-1]
    current_price = current_candle['close']
    now_str = datetime.datetime.now().isoformat()

    print(f"[{now_str}] Current Price: ${current_price:.2f}, MA: ${ma:.2f}, Upper: ${upper_band:.2f}, Lower: ${lower_band:.2f}")

    if position == 0:
        # Entry conditions: go long if price is "too low"; go short if "too high"
        if current_price < lower_band:
            position = 1
            entry_price = current_price
            print(f"[{now_str}] Signal: Price ${current_price:.2f} below Lower Band ${lower_band:.2f}. Entering LONG.")
            send_trade_order("buy", TRADE_AMOUNT, current_price)
        elif current_price > upper_band:
            position = -1
            entry_price = current_price
            print(f"[{now_str}] Signal: Price ${current_price:.2f} above Upper Band ${upper_band:.2f}. Entering SHORT.")
            send_trade_order("sell", TRADE_AMOUNT, current_price)
    else:
        # Exit conditions: exit when price reverts to the moving average
        if position == 1 and current_price >= ma:
            profit += current_price - entry_price
            print(f"[{now_str}] Exiting LONG: Price ${current_price:.2f} reverted to MA ${ma:.2f}. Cumulative Profit: ${profit:.2f}")
            send_trade_order("sell", TRADE_AMOUNT, current_price)
            position = 0
            entry_price = None
        elif position == -1 and current_price <= ma:
            profit += entry_price - current_price
            print(f"[{now_str}] Exiting SHORT: Price ${current_price:.2f} reverted to MA ${ma:.2f}. Cumulative Profit: ${profit:.2f}")
            send_trade_order("buy", TRADE_AMOUNT, current_price)
            position = 0
            entry_price = None

def main():
    global candles
    print("🚀 Starting Mean Reversion Bot with API Integration...")
    while True:
        price = fetch_market_price()
        if price is None:
            print(f"[{datetime.datetime.now().isoformat()}] ⚠️ Skipping this interval due to market data error.")
        else:
            now = datetime.datetime.now()
            # Construct a candle from the fetched price.
            # Since we fetch one price per interval, open, high, low, close are identical.
            candle = {
                'timestamp': now,
                'open': price,
                'high': price,
                'low': price,
                'close': price
            }
            candles.append(candle)
            # Keep only the most recent WINDOW candles
            if len(candles) > WINDOW:
                candles = candles[-WINDOW:]
                
            evaluate_mean_reversion()

        time.sleep(EVALUATION_INTERVAL)

if __name__ == '__main__':
    main()
