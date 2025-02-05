#!/usr/bin/env python3
"""
Spread Trading Bot with API Integration

This bot:
  • Fetches market data every minute from your API.
  • Accumulates historical BTC and ETH prices to estimate the hedge ratio (beta) using the first 100 data points.
  • Computes the spread as: spread = ETH_close - beta * BTC_close.
  • Maintains a rolling window (60 minutes) to compute the rolling mean and standard deviation of the spread.
  • Trading rules:
      - If no position is open:
          * If current spread > (rolling mean + threshold * std), enter a short spread trade (short ETH, long BTC).
          * If current spread < (rolling mean - threshold * std), enter a long spread trade (long ETH, short BTC).
      - If a position is open:
          * For a long spread trade, exit when the spread reverts (i.e. current spread ≥ rolling mean).
          * For a short spread trade, exit when the spread reverts (i.e. current spread ≤ rolling mean).
  • Sends trade orders via your API.
  • Logs trade signals and cumulative profit.

Usage:
    python spread_trading_bot.py
"""

import time
import datetime
import requests
import statistics


BOT_ID = "-OI1ZbJHzjC7dQmXiujQ"         # Unique bot identifier
USER_ID = "6xDYg9OrqaRlkLecm4CFG2G1rq93"  # Your user id
# ------------------------------
# CONFIGURATION
# ------------------------------
# API Endpoints – update as needed.
TRADE_API_URL = f"https://crypto-bots-mu.vercel.app/api/bots/{BOT_ID}/trades"  # Replace <BOT_ID> with your bot's ID.
MARKET_DATA_API_URL = "https://crypto-bots-mu.vercel.app/api/market-data"

# Trading parameters.
SYMBOL_BTC = "BTC"
SYMBOL_ETH = "ETH"
ORDER_TYPE = "market"
TRADE_AMOUNT = 0.05  # Trade amount for each leg (adjust as needed).

# Strategy parameters.
INITIAL_WINDOW = 100  # Number of data points to estimate beta.
ROLLING_WINDOW = 60   # Number of minutes for rolling statistics.
THRESHOLD = 1.0       # Threshold in standard deviations.

# Evaluation interval in seconds (e.g. 60 seconds = 1 minute).
EVALUATION_INTERVAL = 60

# ------------------------------
# GLOBAL STATE
# ------------------------------
historical_data = []   # List of dicts: { "time": ..., "BTC_close": ..., "ETH_close": ... }
spread_history = []    # List of recent spread values.
beta = None            # Hedge ratio (to be estimated once INITIAL_WINDOW data points are collected).
position = 0           # 0: no position, 1: long spread (long ETH, short BTC), -1: short spread (short ETH, long BTC)
entry_BTC = None       # BTC price at trade entry.
entry_ETH = None       # ETH price at trade entry.
entry_spread = None    # Spread value at entry.
cum_profit = 0.0       # Cumulative profit.

# ------------------------------
# FUNCTIONS
# ------------------------------
def fetch_market_data():
    """
    Fetches current market data from the API.
    Expects JSON like: {"BTC": 101729.81, "ETH": 3232.82}.
    Returns a dictionary with keys "BTC" and "ETH" or None on error.
    """
    try:
        response = requests.get(MARKET_DATA_API_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        btc_price = data.get("BTC")
        eth_price = data.get("ETH")
        if btc_price is None or eth_price is None:
            print(f"[{datetime.datetime.now().isoformat()}] ⚠️ Incomplete market data: {data}")
            return None
        return {"BTC": float(btc_price), "ETH": float(eth_price)}
    except Exception as e:
        print(f"[{datetime.datetime.now().isoformat()}] ❌ Error fetching market data: {e}")
        return None

def send_trade_order(symbol, side, amount, price):
    """
    Sends a trade order via the API.
    Parameters:
      symbol: e.g. "BTC" or "ETH"
      side: "buy" or "sell"
      amount: trade amount
      price: current market price
    """
    payload = {
        "side": side,
        "amount": amount,
        "price": price,
        "symbol": symbol,
        "orderType": ORDER_TYPE,
        "userId": USER_ID
        # Add additional fields (e.g., userId) if required by your API.
    }
    try:
        response = requests.post(TRADE_API_URL, json=payload, timeout=5)
        response.raise_for_status()
        result = response.json()
        print(f"[{datetime.datetime.now().isoformat()}] ✅ {side.upper()} order executed for {amount} {symbol} at ${price:.2f}")
        print("API Response:", result)
        return True
    except Exception as e:
        print(f"[{datetime.datetime.now().isoformat()}] ❌ Error sending {side} order for {symbol}: {e}")
        return False

def estimate_beta(data_points):
    """
    Estimates the hedge ratio (beta) using OLS from the provided data points.
    data_points: list of dicts with keys "BTC_close" and "ETH_close".
    beta = covariance(ETH, BTC) / variance(BTC)
    """
    btc_prices = [d["BTC_close"] for d in data_points]
    eth_prices = [d["ETH_close"] for d in data_points]
    n = len(btc_prices)
    mean_btc = sum(btc_prices) / n
    mean_eth = sum(eth_prices) / n
    cov = sum((eth_prices[i] - mean_eth) * (btc_prices[i] - mean_btc) for i in range(n))
    var_btc = sum((btc_prices[i] - mean_btc) ** 2 for i in range(n))
    if var_btc == 0:
        return 0
    return cov / var_btc

def main():
    global beta, position, entry_BTC, entry_ETH, entry_spread, cum_profit

    print("🚀 Starting Spread Trading Bot with API Integration...")
    
    while True:
        data = fetch_market_data()
        if data is None:
            print(f"[{datetime.datetime.now().isoformat()}] ⚠️ Market data fetch failed. Skipping this interval.")
            time.sleep(EVALUATION_INTERVAL)
            continue

        current_time = datetime.datetime.now()
        BTC_close = data["BTC"]
        ETH_close = data["ETH"]
        
        # Store the new data point.
        historical_data.append({
            "time": current_time,
            "BTC_close": BTC_close,
            "ETH_close": ETH_close
        })
        
        # Estimate beta once enough data has been collected.
        if beta is None and len(historical_data) >= INITIAL_WINDOW:
            initial_data = historical_data[:INITIAL_WINDOW]
            beta = estimate_beta(initial_data)
            print(f"Estimated hedge ratio (beta): {beta:.4f}")
        
        if beta is None:
            print(f"[{current_time.isoformat()}] Collecting data for beta estimation ({len(historical_data)}/{INITIAL_WINDOW})...")
            time.sleep(EVALUATION_INTERVAL)
            continue
        
        # Compute the current spread.
        current_spread = ETH_close - beta * BTC_close
        
        # Update the rolling spread history.
        spread_history.append(current_spread)
        if len(spread_history) > ROLLING_WINDOW:
            spread_history.pop(0)
        
        if len(spread_history) < ROLLING_WINDOW:
            print(f"[{current_time.isoformat()}] Collecting data for rolling window ({len(spread_history)}/{ROLLING_WINDOW})...")
            time.sleep(EVALUATION_INTERVAL)
            continue
        
        # Compute rolling mean and standard deviation of the spread.
        rolling_mean = sum(spread_history) / len(spread_history)
        rolling_std = statistics.pstdev(spread_history)  # Using population stdev.
        upper_bound = rolling_mean + THRESHOLD * rolling_std
        lower_bound = rolling_mean - THRESHOLD * rolling_std
        
        print(f"[{current_time.isoformat()}] BTC: ${BTC_close:.2f}, ETH: ${ETH_close:.2f}, Spread: {current_spread:.4f}")
        print(f"Rolling Mean: {rolling_mean:.4f}, Rolling Std: {rolling_std:.4f}, Upper Bound: {upper_bound:.4f}, Lower Bound: {lower_bound:.4f}")
        
        # Trading logic.
        if position == 0:
            # No open position: check for entry signals.
            if current_spread > upper_bound:
                # Enter short spread trade: short ETH, long BTC.
                print(f"[{current_time.isoformat()}] Signal: Enter short spread (spread {current_spread:.4f} > upper bound {upper_bound:.4f})")
                order1 = send_trade_order(SYMBOL_ETH, "sell", TRADE_AMOUNT, ETH_close)
                order2 = send_trade_order(SYMBOL_BTC, "buy", TRADE_AMOUNT, BTC_close)
                if order1 and order2:
                    position = -1
                    entry_spread = current_spread
                    entry_BTC = BTC_close
                    entry_ETH = ETH_close
                    print(f"[{current_time.isoformat()}] Entered short spread trade.")
            elif current_spread < lower_bound:
                # Enter long spread trade: long ETH, short BTC.
                print(f"[{current_time.isoformat()}] Signal: Enter long spread (spread {current_spread:.4f} < lower bound {lower_bound:.4f})")
                order1 = send_trade_order(SYMBOL_ETH, "buy", TRADE_AMOUNT, ETH_close)
                order2 = send_trade_order(SYMBOL_BTC, "sell", TRADE_AMOUNT, BTC_close)
                if order1 and order2:
                    position = 1
                    entry_spread = current_spread
                    entry_BTC = BTC_close
                    entry_ETH = ETH_close
                    print(f"[{current_time.isoformat()}] Entered long spread trade.")
        else:
            # Position is open: check for exit signals.
            if position == 1 and current_spread >= rolling_mean:
                # For a long spread trade (long ETH, short BTC): exit when spread reverts.
                profit_trade = (ETH_close - entry_ETH) - beta * (BTC_close - entry_BTC)
                cum_profit += profit_trade
                print(f"[{current_time.isoformat()}] Signal: Exit long spread (spread {current_spread:.4f} >= rolling mean {rolling_mean:.4f}). Trade Profit: ${profit_trade:.2f}")
                order1 = send_trade_order(SYMBOL_ETH, "sell", TRADE_AMOUNT, ETH_close)
                order2 = send_trade_order(SYMBOL_BTC, "buy", TRADE_AMOUNT, BTC_close)
                if order1 and order2:
                    position = 0
                    entry_spread = None
                    entry_BTC = None
                    entry_ETH = None
            elif position == -1 and current_spread <= rolling_mean:
                # For a short spread trade (short ETH, long BTC): exit when spread reverts.
                profit_trade = beta * (BTC_close - entry_BTC) - (ETH_close - entry_ETH)
                cum_profit += profit_trade
                print(f"[{current_time.isoformat()}] Signal: Exit short spread (spread {current_spread:.4f} <= rolling mean {rolling_mean:.4f}). Trade Profit: ${profit_trade:.2f}")
                order1 = send_trade_order(SYMBOL_ETH, "buy", TRADE_AMOUNT, ETH_close)
                order2 = send_trade_order(SYMBOL_BTC, "sell", TRADE_AMOUNT, BTC_close)
                if order1 and order2:
                    position = 0
                    entry_spread = None
                    entry_BTC = None
                    entry_ETH = None
        
        print(f"Cumulative Profit: ${cum_profit:.2f}\n")
        # Wait for the next evaluation interval.
        time.sleep(EVALUATION_INTERVAL)

if __name__ == '__main__':
    main()
