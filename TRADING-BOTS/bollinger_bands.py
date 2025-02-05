#!/usr/bin/env python3
"""
Bollinger Bands Bot with API Integration

This bot:
  • Polls your market data API every minute for the current price.
  • Constructs a candle (with open, high, low, and close all equal to the fetched price).
  • Maintains a history of 20 candles to compute the 20–bar moving average (MA) and standard deviation.
  • Computes Bollinger Bands:
        - Upper Band = MA + 2 * std
        - Lower Band = MA - 2 * std
  • Trading rules:
        - If not in a position:
            • Enter LONG (buy) if current price > Upper Band.
            • Enter SHORT (sell) if current price < Lower Band.
        - If in a position:
            • For a LONG position: exit when price falls below the MA.
            • For a SHORT position: exit when price rises above the MA.
  • Sends trade orders to your API and logs the actions and cumulative profit.
  
No charts are displayed.
"""

import time
import datetime
import requests
import statistics

# ------------------------------
# CONFIGURATION
# ------------------------------
BOT_ID = "-OI07GvtxsdiuHxQ3DNy"         # Unique bot identifier
USER_ID = "6xDYg9OrqaRlkLecm4CFG2G1rq93"  # Your user id
SYMBOL = "BTC"                           # Trading symbol
ORDER_TYPE = "market"                    # Order type ("market")
TRADE_AMOUNT = 0.01                      # Amount to trade per order

# API endpoints (adjust host/port if necessary)
TRADE_API_URL = f"https://crypto-bots-mu.vercel.app/api/bots/{BOT_ID}/trades"
MARKET_DATA_API_URL = "https://crypto-bots-mu.vercel.app/api/market-data"
# For local testing you might use:
# TRADE_API_URL = f"http://localhost:3000/api/bots/{BOT_ID}/trades"
# MARKET_DATA_API_URL = "http://localhost:3000/api/market-data"

# Bollinger Bands Parameters
WINDOW = 20  # Number of candles used for the moving average and standard deviation

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
      - amount: the trade amount
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

def evaluate_bollinger_bands():
    """
    Evaluates the Bollinger Bands strategy using the last WINDOW candles.
    Computes:
      - Moving Average (MA) of the close prices.
      - Standard Deviation (std) of the close prices.
      - Upper Band = MA + 2 * std.
      - Lower Band = MA - 2 * std.
    
    Trading logic:
      - If not in a position:
          • Enter LONG if current price > Upper Band.
          • Enter SHORT if current price < Lower Band.
      - If in a position:
          • For LONG positions: exit when current price falls below the MA.
          • For SHORT positions: exit when current price rises above the MA.
    """
    global position, entry_price, profit, candles

    if len(candles) < WINDOW:
        print(f"[{datetime.datetime.now().isoformat()}] ⏳ Not enough data to compute Bollinger Bands ({len(candles)}/{WINDOW}).")
        return

    # Compute indicators using the last WINDOW candles.
    recent_candles = candles[-WINDOW:]
    close_prices = [candle['close'] for candle in recent_candles]
    ma = sum(close_prices) / WINDOW
    std_dev = statistics.stdev(close_prices)
    upper_band = ma + 2 * std_dev
    lower_band = ma - 2 * std_dev

    current_price = candles[-1]['close']
    now_str = datetime.datetime.now().isoformat()

    print(f"[{now_str}] Current Price: ${current_price:.2f}, MA: ${ma:.2f}, Upper Band: ${upper_band:.2f}, Lower Band: ${lower_band:.2f}")

    if position == 0:
        # Entry signals based on breakout above upper band or below lower band.
        if current_price > upper_band:
            position = 1
            entry_price = current_price
            print(f"[{now_str}] Entering LONG as price ${current_price:.2f} > Upper Band ${upper_band:.2f}")
            send_trade_order("buy", TRADE_AMOUNT, current_price)
        elif current_price < lower_band:
            position = -1
            entry_price = current_price
            print(f"[{now_str}] Entering SHORT as price ${current_price:.2f} < Lower Band ${lower_band:.2f}")
            send_trade_order("sell", TRADE_AMOUNT, current_price)
    else:
        # Exit conditions:
        if position == 1 and current_price < ma:
            profit_change = current_price - entry_price
            profit += profit_change
            print(f"[{now_str}] Exiting LONG as price ${current_price:.2f} < MA ${ma:.2f} (Profit: ${profit_change:.2f}). Cumulative Profit: ${profit:.2f}")
            send_trade_order("sell", TRADE_AMOUNT, current_price)
            position = 0
            entry_price = None
        elif position == -1 and current_price > ma:
            profit_change = entry_price - current_price
            profit += profit_change
            print(f"[{now_str}] Exiting SHORT as price ${current_price:.2f} > MA ${ma:.2f} (Profit: ${profit_change:.2f}). Cumulative Profit: ${profit:.2f}")
            send_trade_order("buy", TRADE_AMOUNT, current_price)
            position = 0
            entry_price = None

def main():
    global candles
    print("🚀 Starting Bollinger Bands Bot with API Integration...")
    while True:
        price = fetch_market_price()
        if price is None:
            print(f"[{datetime.datetime.now().isoformat()}] ⚠️ Skipping this interval due to market data error.")
        else:
            now = datetime.datetime.now()
            # Create a new candle (since we fetch one price per interval, all OHLC values are the same).
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
            evaluate_bollinger_bands()
        time.sleep(EVALUATION_INTERVAL)

if __name__ == '__main__':
    main()
