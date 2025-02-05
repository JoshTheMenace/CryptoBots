#!/usr/bin/env python3
"""
Breakout Strategy Bot with API Integration

This bot:
  • Polls your market data endpoint every minute.
  • Maintains a history of “candles” (each candle here is built from the single fetched price).
  • Computes:
      - The highest high and lowest low from the previous 20 candles (excluding the current one)
      - A 20–bar moving average (using the most recent 20 candles)
  • Generates trading signals:
      - If not in a position and current price > previous highest high → enter LONG.
      - If not in a position and current price < previous lowest low → enter SHORT.
      - If long and price falls below the moving average → exit LONG.
      - If short and price rises above the moving average → exit SHORT.
  • Sends trade orders to your API.
  • Logs activity and tracks a simulated cumulative profit.
  
Configuration:
  • Update BOT_ID, USER_ID, SYMBOL, TRADE_AMOUNT, and the API endpoints below as needed.
  • This bot no longer displays charts.
"""

import time
import datetime
import requests

# ------------------------------
# CONFIGURATION
# ------------------------------
BOT_ID = "-OI01thU7u6BqGPPX_1I"        # Unique bot identifier
USER_ID = "6xDYg9OrqaRlkLecm4CFG2G1rq93"  # Your user id
SYMBOL = "BTC"                          # Trading symbol (adjust if needed)
ORDER_TYPE = "market"                   # Order type ("market")
TRADE_AMOUNT = 0.01                     # Amount to trade per order

# API Endpoints (adjust host/port if necessary)
TRADE_API_URL = f"https://crypto-bots-mu.vercel.app/api/bots/{BOT_ID}/trades"
MARKET_DATA_API_URL = "https://crypto-bots-mu.vercel.app/api/market-data"
# For local testing, you might use:
# TRADE_API_URL = f"http://localhost:3000/api/bots/{BOT_ID}/trades"
# MARKET_DATA_API_URL = "http://localhost:3000/api/market-data"

# Breakout Strategy Parameters
LOOKBACK = 20  # Number of previous candles to determine breakout and compute MA

# Evaluation interval in seconds (e.g. 60 for 1 minute)
EVALUATION_INTERVAL = 60

# ------------------------------
# GLOBAL STATE
# ------------------------------
position = 0      # 0: no position, 1: long, -1: short
entry_price = None
profit = 0.0
candles = []      # Will store our candle data (each candle is a dict)

# ------------------------------
# FUNCTIONS
# ------------------------------
def fetch_market_price():
    """
    Fetch the current market price for SYMBOL from the API.
    Expects a JSON response with the symbol as a key, e.g.: { "BTC": 12345.67, ... }
    """
    try:
        response = requests.get(MARKET_DATA_API_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        price = data.get(SYMBOL)
        if price is None:
            print(f"[{datetime.datetime.now().isoformat()}] ⚠️ Symbol {SYMBOL} not found in market data response.")
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
      - price: execution price (current market price)
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

def evaluate_breakout():
    """
    Evaluates breakout conditions and sends trade orders if signals are generated.
    Uses the history of candles:
      - Highest high and lowest low are computed from the previous LOOKBACK candles (excluding current).
      - The moving average is computed over the last LOOKBACK candles (including current).
    Trading Logic:
      - If not in a position:
          • Enter LONG if current price > previous highest high.
          • Enter SHORT if current price < previous lowest low.
      - If in a position:
          • For LONG: exit if current price < moving average.
          • For SHORT: exit if current price > moving average.
    """
    global position, entry_price, profit, candles

    if len(candles) < (LOOKBACK + 1):
        print(f"[{datetime.datetime.now().isoformat()}] ⏳ Waiting for enough data... ({len(candles)}/{LOOKBACK + 1})")
        return

    # Compute breakout levels from the previous LOOKBACK candles (exclude the current candle)
    previous_candles = candles[-(LOOKBACK + 1):-1]
    highest = max(candle['high'] for candle in previous_candles)
    lowest = min(candle['low'] for candle in previous_candles)

    # Compute moving average using the last LOOKBACK candles (including the current candle)
    ma_candles = candles[-LOOKBACK:]
    moving_average = sum(candle['close'] for candle in ma_candles) / LOOKBACK

    # Get current candle (most recent)
    current_candle = candles[-1]
    current_price = current_candle['close']
    now_str = datetime.datetime.now().isoformat()

    print(f"[{now_str}] Current Price: ${current_price:.2f}, Highest: ${highest:.2f}, Lowest: ${lowest:.2f}, MA: ${moving_average:.2f}")

    if position == 0:
        # Look for breakout entries
        if current_price > highest:
            position = 1
            entry_price = current_price
            print(f"[{now_str}] Breakout: Price ${current_price:.2f} > Highest ${highest:.2f}. Entering LONG.")
            send_trade_order("buy", TRADE_AMOUNT, current_price)
        elif current_price < lowest:
            position = -1
            entry_price = current_price
            print(f"[{now_str}] Breakout: Price ${current_price:.2f} < Lowest ${lowest:.2f}. Entering SHORT.")
            send_trade_order("sell", TRADE_AMOUNT, current_price)
    else:
        # Evaluate exit conditions based on the moving average
        if position == 1 and current_price < moving_average:
            profit += current_price - entry_price
            print(f"[{now_str}] Exiting LONG: Price ${current_price:.2f} fell below MA ${moving_average:.2f}. Cumulative Profit: ${profit:.2f}")
            send_trade_order("sell", TRADE_AMOUNT, current_price)
            position = 0
            entry_price = None
        elif position == -1 and current_price > moving_average:
            profit += entry_price - current_price
            print(f"[{now_str}] Exiting SHORT: Price ${current_price:.2f} rose above MA ${moving_average:.2f}. Cumulative Profit: ${profit:.2f}")
            send_trade_order("buy", TRADE_AMOUNT, current_price)
            position = 0
            entry_price = None

def main():
    global candles
    print("🚀 Starting Breakout Strategy Bot with API Integration...")
    while True:
        price = fetch_market_price()
        if price is None:
            print(f"[{datetime.datetime.now().isoformat()}] ⚠️ Skipping this interval due to market data fetch error.")
        else:
            now = datetime.datetime.now()
            # Build a new candle from the fetched price.
            # (Here we assume one price per interval makes a complete candle.)
            candle = {
                'timestamp': now,
                'open': price,
                'high': price,
                'low': price,
                'close': price
            }
            candles.append(candle)
            # Keep only the most recent (LOOKBACK + 1) candles in history.
            if len(candles) > (LOOKBACK + 1):
                candles = candles[-(LOOKBACK + 1):]

            evaluate_breakout()

        time.sleep(EVALUATION_INTERVAL)

if __name__ == '__main__':
    main()
