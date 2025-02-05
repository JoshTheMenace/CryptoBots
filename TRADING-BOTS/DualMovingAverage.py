#!/usr/bin/env python3
"""
Dual Moving Average Crossover Trading Bot
-------------------------------------------
This bot is designed with a sole focus on making profit.
It uses a dual moving average crossover strategy:
  • A fast moving average (10-minute window) and a slow moving average (50-minute window)
  • When the fast MA is above the slow MA, the bot goes LONG.
  • When the fast MA is below the slow MA, the bot goes SHORT.
It polls your market data API once every minute (which returns a JSON object like {"BTC": 12345.67})
and sends trade orders to your trade API.
  
Configuration:
  • Adjust the API endpoints below to match your system.
  • The target crypto symbol is assumed to be "BTC".
  • Trade orders are sent as market orders.
"""

import time
import datetime
import requests
import numpy as np

# ------------------------------
# CONFIGURATION
# ------------------------------
BOT_ID = "-OI1xN4O4HnkbxQAAMEb"         # Unique bot identifier
USER_ID = "6xDYg9OrqaRlkLecm4CFG2G1rq93"  # Your user id

# Replace <BOT_ID> with your actual bot id.
TRADE_API_URL = f"https://crypto-bots-mu.vercel.app/api/bots/{BOT_ID}/trades"
MARKET_DATA_API_URL = "https://crypto-bots-mu.vercel.app/api/market-data"

SYMBOL = "BTC"            # Target crypto symbol.
ORDER_TYPE = "market"     # Market order.
TRADE_AMOUNT = 0.01       # Amount to trade per order.
EVALUATION_INTERVAL = 60  # Polling interval in seconds (1 minute).

# Moving Average Parameters
FAST_WINDOW = 10  # Fast MA period (in minutes)
SLOW_WINDOW = 50  # Slow MA period (in minutes)

# ------------------------------
# GLOBAL STATE
# ------------------------------
price_history = []  # List of the most recent prices (one per minute)
position = 0        # 0 = no position, 1 = long, -1 = short
entry_price = None  # Price at which the current position was entered
cum_profit = 0.0    # Cumulative profit

# ------------------------------
# FUNCTIONS
# ------------------------------
def fetch_market_price():
    """
    Fetch the current market price for SYMBOL from your market data API.
    Expected JSON response: { "BTC": 12345.67, ... }
    Returns the price as a float, or None on error.
    """
    try:
        response = requests.get(MARKET_DATA_API_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        price = data.get(SYMBOL)
        if price is None:
            print(f"[{datetime.datetime.now().isoformat()}] ⚠️ {SYMBOL} not found in market data response.")
            return None
        return float(price)
    except Exception as e:
        print(f"[{datetime.datetime.now().isoformat()}] ❌ Error fetching market data: {e}")
        return None

def send_trade_order(side, amount, price):
    """
    Sends a trade order to your API.
    Parameters:
      - side: "buy" or "sell"
      - amount: trade amount (float)
      - price: current market price (float)
    Returns True if the order is executed successfully.
    """
    payload = {
        "side": side,
        "amount": amount,
        "price": price,
        "symbol": SYMBOL,
        "orderType": ORDER_TYPE,
        "userId": USER_ID
        # Add additional fields (e.g., userId) if required.
    }
    try:
        response = requests.post(TRADE_API_URL, json=payload, timeout=5)
        response.raise_for_status()
        result = response.json()
        print(f"[{datetime.datetime.now().isoformat()}] ✅ {side.upper()} order executed: {amount} {SYMBOL} at ${price:.2f}")
        print("API Response:", result)
        return True
    except Exception as e:
        print(f"[{datetime.datetime.now().isoformat()}] ❌ Error sending {side} order: {e}")
        return False

def main():
    global price_history, position, entry_price, cum_profit

    print("🚀 Starting Dual MA Crossover Trading Bot...")
    
    while True:
        current_price = fetch_market_price()
        if current_price is None:
            print("Skipping this interval due to market data error.")
            time.sleep(EVALUATION_INTERVAL)
            continue

        # Append current price to history.
        price_history.append(current_price)
        # Keep only the most recent SLOW_WINDOW prices.
        if len(price_history) > SLOW_WINDOW:
            price_history = price_history[-SLOW_WINDOW:]
        
        current_time = datetime.datetime.now().isoformat()
        
        # Wait until we have enough data for the slow MA.
        if len(price_history) < SLOW_WINDOW:
            print(f"[{current_time}] Collecting price data: {len(price_history)}/{SLOW_WINDOW} points.")
            time.sleep(EVALUATION_INTERVAL)
            continue
        
        # Compute the moving averages.
        fast_ma = np.mean(price_history[-FAST_WINDOW:])
        slow_ma = np.mean(price_history)
        
        print(f"[{current_time}] Current Price: ${current_price:.2f}, Fast MA: ${fast_ma:.2f}, Slow MA: ${slow_ma:.2f}")

        # ------------------------------
        # Trading Logic
        # ------------------------------
        # Bullish signal: fast MA > slow MA.
        if fast_ma > slow_ma:
            # If no position, enter long.
            if position == 0:
                if send_trade_order("buy", TRADE_AMOUNT, current_price):
                    position = 1
                    entry_price = current_price
                    print(f"[{current_time}] Entered LONG at ${current_price:.2f}")
            # If currently short, close short and then enter long.
            elif position == -1:
                if send_trade_order("buy", TRADE_AMOUNT, current_price):
                    profit = entry_price - current_price  # Profit from short.
                    cum_profit += profit
                    print(f"[{current_time}] Exited SHORT with profit: ${profit:.2f}")
                    # Now enter long.
                    if send_trade_order("buy", TRADE_AMOUNT, current_price):
                        position = 1
                        entry_price = current_price
                        print(f"[{current_time}] Entered LONG at ${current_price:.2f}")
        
        # Bearish signal: fast MA < slow MA.
        else:
            # If no position, enter short.
            if position == 0:
                if send_trade_order("sell", TRADE_AMOUNT, current_price):
                    position = -1
                    entry_price = current_price
                    print(f"[{current_time}] Entered SHORT at ${current_price:.2f}")
            # If currently long, close long and then enter short.
            elif position == 1:
                if send_trade_order("sell", TRADE_AMOUNT, current_price):
                    profit = current_price - entry_price  # Profit from long.
                    cum_profit += profit
                    print(f"[{current_time}] Exited LONG with profit: ${profit:.2f}")
                    # Now enter short.
                    if send_trade_order("sell", TRADE_AMOUNT, current_price):
                        position = -1
                        entry_price = current_price
                        print(f"[{current_time}] Entered SHORT at ${current_price:.2f}")
        
        print(f"[{current_time}] Cumulative Profit: ${cum_profit:.2f}\n")
        time.sleep(EVALUATION_INTERVAL)

if __name__ == '__main__':
    main()
