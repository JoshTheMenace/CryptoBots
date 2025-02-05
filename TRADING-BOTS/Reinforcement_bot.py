#!/usr/bin/env python3
"""
Reinforcement Learning Trading Bot with API Integration

This bot:
  • Polls your market data API every minute (expects data like: {"BTC": 101729.81, "ETH": 3232.82}).
  • Uses a 20–period moving average of the ETH price to discretize the market trend as:
        "up"    : current price > MA * 1.01
        "down"  : current price < MA * 0.99
        "neutral": otherwise.
  • Defines its state as a tuple: (position, trend)
        where position ∈ {0 (no position), 1 (long), -1 (short)}.
  • Has three actions:
        0 = Hold,
        1 = Buy (enter long or exit short and go long),
        2 = Sell (enter short or exit long and go short).
  • Uses a simple Q–learning algorithm (with epsilon–greedy exploration) to update its policy
    based on the change in portfolio value (cash plus unrealized profit) as its reward.
  • Sends trade orders via your API and trades at one–minute intervals.
  
"""

import time
import datetime
import requests
import statistics
import numpy as np

# ------------------------------
# CONFIGURATION
# ------------------------------
BOT_ID = "-OI1xN4O4HnkbxQAAMEb"         # Unique bot identifier
USER_ID = "6xDYg9OrqaRlkLecm4CFG2G1rq93"  # Your user id
# API endpoints – update these as needed.
TRADE_API_URL = f"https://crypto-bots-mu.vercel.app/api/bots/{BOT_ID}/trades"  # Replace <BOT_ID> with your bot's ID.
MARKET_DATA_API_URL = "https://crypto-bots-mu.vercel.app/api/market-data"

# Trading parameters.
SYMBOL = "ETH"
ORDER_TYPE = "market"
TRADE_AMOUNT = 0.1  # Trade amount per order.

# RL parameters.
epsilon = 0.1   # Exploration rate.
alpha = 0.1     # Learning rate.
gamma = 0.99    # Discount factor.

# Moving average window and trend threshold.
MA_WINDOW = 20
TREND_THRESHOLD = 0.01  # 1% deviation from MA to label trend as "up" or "down".

# Evaluation interval (in seconds).
EVALUATION_INTERVAL = 60

# ------------------------------
# GLOBAL STATE
# ------------------------------
# Q–table: mapping state (tuple) → {action: Q_value}
# State is defined as (position, trend) where:
#    position: 0, 1, or -1.
#    trend: "up", "neutral", or "down".
Q_table = {}

# Trading state.
position = 0      # 0 = no position, 1 = long, -1 = short.
entry_price = None
cash = 10000.0    # Starting cash.
# For computing the moving average.
price_history = []

# ------------------------------
# FUNCTIONS
# ------------------------------
def fetch_market_data():
    """
    Fetches current market data from the API.
    Expects a JSON response like: {"BTC": 101729.81, "ETH": 3232.82}
    Returns the ETH price (float) or None on error.
    """
    try:
        response = requests.get(MARKET_DATA_API_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        price = data.get("ETH")
        if price is None:
            print(f"[{datetime.datetime.now().isoformat()}] ⚠️ Incomplete market data: {data}")
            return None
        return float(price)
    except Exception as e:
        print(f"[{datetime.datetime.now().isoformat()}] ❌ Error fetching market data: {e}")
        return None

def send_trade_order(side, amount, price):
    """
    Sends a trade order to your API.
    side: "buy" or "sell"
    amount: trade amount
    price: current market price
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
        print(f"[{datetime.datetime.now().isoformat()}] ✅ {side.upper()} order executed for {amount} {SYMBOL} at ${price:.2f}")
        # Optionally, print updated balances.
        return True
    except Exception as e:
        print(f"[{datetime.datetime.now().isoformat()}] ❌ Error sending {side} order: {e}")
        return False

def get_state(current_price):
    """
    Computes the current state as a tuple (position, trend).
    Trend is determined by comparing the current price to the moving average of the last MA_WINDOW prices.
    If current price > MA * (1 + TREND_THRESHOLD) → "up"
    If current price < MA * (1 - TREND_THRESHOLD) → "down"
    Else → "neutral"
    """
    if len(price_history) < MA_WINDOW:
        return None
    ma = sum(price_history[-MA_WINDOW:]) / MA_WINDOW
    deviation = (current_price - ma) / ma
    if deviation > TREND_THRESHOLD:
        trend = "up"
    elif deviation < -TREND_THRESHOLD:
        trend = "down"
    else:
        trend = "neutral"
    return (position, trend)

def initialize_state_if_needed(state):
    if state not in Q_table:
        Q_table[state] = {0: 0.0, 1: 0.0, 2: 0.0}

def choose_action(state):
    """
    Chooses an action using an epsilon-greedy policy.
    Returns one of 0 (hold), 1 (buy), or 2 (sell).
    """
    initialize_state_if_needed(state)
    if np.random.rand() < epsilon:
        return np.random.choice([0, 1, 2])
    else:
        actions = Q_table[state]
        return max(actions, key=actions.get)

def update_Q(state, action, reward, next_state):
    """
    Updates the Q-value for the (state, action) pair using the Q-learning update rule.
    """
    initialize_state_if_needed(state)
    initialize_state_if_needed(next_state)
    max_next = max(Q_table[next_state].values())
    Q_table[state][action] = Q_table[state][action] + alpha * (reward + gamma * max_next - Q_table[state][action])

def execute_action(action, current_price):
    """
    Executes the chosen action by sending trade orders via the API.
    Action meanings:
      0: Hold (do nothing)
      1: Buy (if no position, enter long; if in short, exit short and go long)
      2: Sell (if no position, enter short; if in long, exit long and go short)
    Updates the global trading state.
    """
    global position, entry_price, cash
    if action == 1:
        # Buy action.
        if position == 0:
            # Enter long.
            if send_trade_order("buy", TRADE_AMOUNT, current_price):
                position = 1
                entry_price = current_price
                print(f"Entered LONG at ${current_price:.2f}")
        elif position == -1:
            # Currently short; exit short and enter long.
            if send_trade_order("buy", TRADE_AMOUNT, current_price):
                profit = entry_price - current_price  # Profit from short.
                cash += profit
                print(f"Exited SHORT, profit: ${profit:.2f}")
                if send_trade_order("buy", TRADE_AMOUNT, current_price):
                    position = 1
                    entry_price = current_price
                    print(f"Entered LONG at ${current_price:.2f}")
    elif action == 2:
        # Sell action.
        if position == 0:
            # Enter short.
            if send_trade_order("sell", TRADE_AMOUNT, current_price):
                position = -1
                entry_price = current_price
                print(f"Entered SHORT at ${current_price:.2f}")
        elif position == 1:
            # Currently long; exit long and enter short.
            if send_trade_order("sell", TRADE_AMOUNT, current_price):
                profit = current_price - entry_price  # Profit from long.
                cash += profit
                print(f"Exited LONG, profit: ${profit:.2f}")
                if send_trade_order("sell", TRADE_AMOUNT, current_price):
                    position = -1
                    entry_price = current_price
                    print(f"Entered SHORT at ${current_price:.2f}")
    else:
        # Hold action.
        print("Holding position.")

def get_portfolio_value(current_price):
    """
    Computes the portfolio value as cash plus unrealized profit (if any).
    For a long position, unrealized profit = (current_price - entry_price).
    For a short position, unrealized profit = (entry_price - current_price).
    """
    global cash, position, entry_price
    if position == 0 or entry_price is None:
        return cash
    elif position == 1:
        return cash + (current_price - entry_price)
    elif position == -1:
        return cash + (entry_price - current_price)

# ------------------------------
# MAIN LOOP
# ------------------------------
def main():
    global price_history
    print("🚀 Starting RL Trading Bot with API Integration...")
    previous_portfolio_value = None
    state = None

    while True:
        # Fetch current market data.
        current_price = fetch_market_data()
        if current_price is None:
            print("Skipping interval due to market data fetch error.")
            time.sleep(EVALUATION_INTERVAL)
            continue

        # Update moving average history.
        price_history.append(current_price)
        if len(price_history) > MA_WINDOW:
            price_history = price_history[-MA_WINDOW:]

        # Compute current state.
        new_state = get_state(current_price)
        if new_state is None:
            print("Not enough data to compute state. Waiting...")
            time.sleep(EVALUATION_INTERVAL)
            continue

        # Initialize state on first valid iteration.
        if state is None:
            state = new_state
            previous_portfolio_value = get_portfolio_value(current_price)

        # Choose an action using the RL policy.
        action = choose_action(state)
        print(f"[{datetime.datetime.now().isoformat()}] State: {state}, Chosen action: {action} (0=Hold, 1=Buy, 2=Sell)")

        # Execute the chosen action.
        execute_action(action, current_price)

        # Wait for the next interval.
        time.sleep(EVALUATION_INTERVAL)

        # Fetch new market data for next state.
        next_price = fetch_market_data()
        if next_price is None:
            print("Skipping Q-update due to market data fetch error.")
            continue

        price_history.append(next_price)
        if len(price_history) > MA_WINDOW:
            price_history = price_history[-MA_WINDOW:]
        next_state = get_state(next_price)
        if next_state is None:
            print("Not enough data for next state. Skipping Q-update.")
            continue

        # Compute reward as change in portfolio value.
        new_portfolio_value = get_portfolio_value(next_price)
        reward = new_portfolio_value - previous_portfolio_value
        print(f"[{datetime.datetime.now().isoformat()}] Reward: ${reward:.2f}")

        # Update Q-table.
        update_Q(state, action, reward, next_state)

        # Update state and portfolio value for the next iteration.
        state = next_state
        previous_portfolio_value = new_portfolio_value

        print(f"Cumulative Cash: ${cash:.2f}, Current Position: {position}, Portfolio Value: ${get_portfolio_value(next_price):.2f}")
        print("-----")

if __name__ == '__main__':
    main()
