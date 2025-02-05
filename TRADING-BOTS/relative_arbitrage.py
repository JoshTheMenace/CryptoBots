#!/usr/bin/env python3
"""
Relative Arbitrage Bot with API Integration

This bot:
  • Polls your market data API every minute (expecting data like {"BTC": 101729.81, "ETH": 3232.82}).
  • Computes the ETH/BTC ratio: ratio = ETH_price / BTC_price.
  • Maintains a rolling window (60 data points) to compute the rolling mean and standard deviation of the ratio.
  • Trading rules:
       - If no position is open:
           * If current ratio > (rolling mean + threshold×std): enter short ETH / long BTC.
           * If current ratio < (rolling mean – threshold×std): enter long ETH / short BTC.
       - If a position is open:
           * For a long trade (position = 1): exit when current ratio ≥ rolling mean.
           * For a short trade (position = –1): exit when current ratio ≤ rolling mean.
  • Sends trade orders via your API for each leg.
  • Logs key data and the cumulative profit.

Usage:
    python relative_arbitrage_bot.py
"""

import time
import datetime
import requests
import statistics

# ------------------------------
# CONFIGURATION
# ------------------------------
BOT_ID = "-OI1mCus2-Lb_I76wloJ"         # Unique bot identifier
USER_ID = "6xDYg9OrqaRlkLecm4CFG2G1rq93"  # Your user id
# API endpoints – adjust these as needed.
TRADE_API_URL = f"https://crypto-bots-mu.vercel.app/api/bots/{BOT_ID}/trades"  # Replace <BOT_ID> with your bot's ID.
MARKET_DATA_API_URL = "https://crypto-bots-mu.vercel.app/api/market-data"

# Trading parameters.
SYMBOL_BTC = "BTC"
SYMBOL_ETH = "ETH"
ORDER_TYPE = "market"
TRADE_AMOUNT = 0.02  # Amount to trade per leg (adjust as needed).

# Strategy parameters.
ROLLING_WINDOW = 60   # Number of data points (e.g., minutes) used for rolling statistics.
THRESHOLD = 1.0       # Entry threshold in standard deviations.

# Evaluation interval (in seconds).
EVALUATION_INTERVAL = 60

# ------------------------------
# GLOBAL STATE
# ------------------------------
# Rolling history for the ETH/BTC ratio.
ratio_history = []

# Trade state.
# position: 0 = no open position, 1 = long ETH / short BTC, -1 = short ETH / long BTC
position = 0  
entry_ratio = None   # Ratio at entry
entry_BTC = None     # BTC price at entry
entry_ETH = None     # ETH price at entry

cum_profit = 0.0     # Cumulative profit

# ------------------------------
# FUNCTIONS
# ------------------------------
def fetch_market_data():
    """
    Fetches current market data from your API.
    Expects a JSON response like: {"BTC": 101729.81, "ETH": 3232.82}
    Returns a dict with float values for "BTC" and "ETH", or None on error.
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
    Sends a trade order to your API.
    Parameters:
      - symbol: "BTC" or "ETH"
      - side: "buy" or "sell"
      - amount: trade amount
      - price: current market price
    """
    payload = {
        "side": side,
        "amount": amount,
        "price": price,
        "symbol": symbol,
        "orderType": ORDER_TYPE,
        # Add additional fields (e.g., userId) if required by your API.
    }
    try:
        response = requests.post(TRADE_API_URL, json=payload, timeout=5)
        response.raise_for_status()
        result = response.json()
        print(f"[{datetime.datetime.now().isoformat()}] ✅ {side.upper()} order for {symbol} executed at ${price:.2f}")
        print("API Response:", result)
        return True
    except Exception as e:
        print(f"[{datetime.datetime.now().isoformat()}] ❌ Error sending {side} order for {symbol}: {e}")
        return False

def main():
    global position, entry_ratio, entry_BTC, entry_ETH, cum_profit, ratio_history

    print("🚀 Starting Relative Arbitrage Bot with API Integration...")

    while True:
        # Fetch current market data.
        data = fetch_market_data()
        if data is None:
            print(f"[{datetime.datetime.now().isoformat()}] ⚠️ Market data fetch failed. Skipping this interval.")
            time.sleep(EVALUATION_INTERVAL)
            continue

        BTC_price = data["BTC"]
        ETH_price = data["ETH"]

        # Compute the current ETH/BTC ratio.
        current_ratio = ETH_price / BTC_price

        # Append the current ratio to the rolling history.
        ratio_history.append(current_ratio)
        if len(ratio_history) > ROLLING_WINDOW:
            ratio_history.pop(0)

        current_time = datetime.datetime.now()
        print(f"[{current_time.isoformat()}] BTC: ${BTC_price:.2f}, ETH: ${ETH_price:.2f}, Ratio: {current_ratio:.4f}")

        # Only proceed with trading once the rolling window is full.
        if len(ratio_history) < ROLLING_WINDOW:
            print(f"[{current_time.isoformat()}] Accumulating ratio data ({len(ratio_history)}/{ROLLING_WINDOW})...")
            time.sleep(EVALUATION_INTERVAL)
            continue

        # Compute rolling mean and standard deviation.
        rolling_mean = sum(ratio_history) / len(ratio_history)
        rolling_std = statistics.stdev(ratio_history)
        upper_threshold = rolling_mean + THRESHOLD * rolling_std
        lower_threshold = rolling_mean - THRESHOLD * rolling_std

        print(f"Rolling Mean: {rolling_mean:.4f}, Rolling Std: {rolling_std:.4f}, Upper: {upper_threshold:.4f}, Lower: {lower_threshold:.4f}")

        # ------------------------------
        # Trading Logic
        # ------------------------------
        if position == 0:
            # No open position – check for entry signals.
            if current_ratio > upper_threshold:
                # ETH is expensive relative to BTC: enter short ETH / long BTC.
                print(f"[{current_time.isoformat()}] Signal: Enter SHORT ETH / LONG BTC (ratio {current_ratio:.4f} > upper threshold {upper_threshold:.4f})")
                # Send orders for each leg.
                order_eth = send_trade_order(SYMBOL_ETH, "sell", TRADE_AMOUNT, ETH_price)
                order_btc = send_trade_order(SYMBOL_BTC, "buy", TRADE_AMOUNT, BTC_price)
                if order_eth and order_btc:
                    position = -1
                    entry_ratio = current_ratio
                    entry_BTC = BTC_price
                    entry_ETH = ETH_price
                    print(f"[{current_time.isoformat()}] Entered SHORT ETH / LONG BTC trade.")
            elif current_ratio < lower_threshold:
                # ETH is cheap relative to BTC: enter long ETH / short BTC.
                print(f"[{current_time.isoformat()}] Signal: Enter LONG ETH / SHORT BTC (ratio {current_ratio:.4f} < lower threshold {lower_threshold:.4f})")
                order_eth = send_trade_order(SYMBOL_ETH, "buy", TRADE_AMOUNT, ETH_price)
                order_btc = send_trade_order(SYMBOL_BTC, "sell", TRADE_AMOUNT, BTC_price)
                if order_eth and order_btc:
                    position = 1
                    entry_ratio = current_ratio
                    entry_BTC = BTC_price
                    entry_ETH = ETH_price
                    print(f"[{current_time.isoformat()}] Entered LONG ETH / SHORT BTC trade.")
        else:
            # A position is open – check for exit conditions.
            if position == 1 and current_ratio >= rolling_mean:
                # For a LONG ETH / SHORT BTC trade: exit when the ratio reverts (rises to or above the rolling mean).
                profit_trade = (ETH_price - entry_ETH) - entry_ratio * (BTC_price - entry_BTC)
                cum_profit += profit_trade
                print(f"[{current_time.isoformat()}] Signal: Exit LONG ETH / SHORT BTC (ratio {current_ratio:.4f} >= rolling mean {rolling_mean:.4f}). Trade profit: ${profit_trade:.2f}")
                order_eth = send_trade_order(SYMBOL_ETH, "sell", TRADE_AMOUNT, ETH_price)
                order_btc = send_trade_order(SYMBOL_BTC, "buy", TRADE_AMOUNT, BTC_price)
                if order_eth and order_btc:
                    position = 0
                    entry_ratio = None
                    entry_BTC = None
                    entry_ETH = None
            elif position == -1 and current_ratio <= rolling_mean:
                # For a SHORT ETH / LONG BTC trade: exit when the ratio reverts (falls to or below the rolling mean).
                profit_trade = entry_ratio * (BTC_price - entry_BTC) - (ETH_price - entry_ETH)
                cum_profit += profit_trade
                print(f"[{current_time.isoformat()}] Signal: Exit SHORT ETH / LONG BTC (ratio {current_ratio:.4f} <= rolling mean {rolling_mean:.4f}). Trade profit: ${profit_trade:.2f}")
                order_eth = send_trade_order(SYMBOL_ETH, "buy", TRADE_AMOUNT, ETH_price)
                order_btc = send_trade_order(SYMBOL_BTC, "sell", TRADE_AMOUNT, BTC_price)
                if order_eth and order_btc:
                    position = 0
                    entry_ratio = None
                    entry_BTC = None
                    entry_ETH = None

        print(f"Cumulative Profit: ${cum_profit:.2f}\n")
        time.sleep(EVALUATION_INTERVAL)

if __name__ == '__main__':
    main()
