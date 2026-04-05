#!/usr/bin/env python3
"""
KORA Paper Trading Bot
- Pulls market data from Yahoo Finance (free)
- Uses Venice/Qwen to reason over signals
- Paper trades: logs decisions, tracks P&L
- Run: python3 trader.py [once|watch]
"""

import os, sys, json, requests, datetime
from pathlib import Path

# Load API keys
_env = Path.home() / "kora_local/.env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"')

VENICE_KEY = os.environ.get("VENICE_API_KEY")
STATE_FILE = Path.home() / "kora_local/trader_state.json"
LOG_FILE   = Path.home() / "kora_local/trader_log.jsonl"

# Watchlist — start simple
WATCHLIST = ["AAPL", "NVDA", "MSFT", "SPY", "AMD"]

STARTING_CASH = 10000.00  # paper money

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"cash": STARTING_CASH, "positions": {}, "trades": []}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def get_price_data(ticker, days=20):
    try:
        r = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range={days}d",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=10
        )
        d = r.json()
        result = d["chart"]["result"][0]
        closes = [c for c in result["indicators"]["quote"][0]["close"] if c]
        timestamps = result["timestamp"][-len(closes):]
        dates = [datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d") for t in timestamps]
        return {"ticker": ticker, "closes": closes, "dates": dates, "current": closes[-1]}
    except Exception as e:
        return None

def moving_avg(prices, n):
    if len(prices) < n:
        return None
    return sum(prices[-n:]) / n

def basic_signals(data):
    closes = data["closes"]
    current = data["current"]
    ma5  = moving_avg(closes, 5)
    ma10 = moving_avg(closes, 10)
    ma20 = moving_avg(closes, 20)
    pct_change_5d = ((current - closes[-6]) / closes[-6] * 100) if len(closes) >= 6 else 0

    signals = []
    if ma5 and ma10 and ma5 > ma10:
        signals.append("MA5 above MA10 (bullish)")
    if ma5 and ma10 and ma5 < ma10:
        signals.append("MA5 below MA10 (bearish)")
    if pct_change_5d > 3:
        signals.append(f"Up {pct_change_5d:.1f}% in 5 days (momentum)")
    if pct_change_5d < -3:
        signals.append(f"Down {pct_change_5d:.1f}% in 5 days (weakness)")

    return {
        "current_price": current,
        "ma5": round(ma5, 2) if ma5 else None,
        "ma10": round(ma10, 2) if ma10 else None,
        "ma20": round(ma20, 2) if ma20 else None,
        "pct_5d": round(pct_change_5d, 2),
        "signals": signals
    }

def ask_venice(prompt):
    if not VENICE_KEY:
        return "NO_KEY"
    try:
        r = requests.post(
            "https://api.venice.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {VENICE_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b",
                "messages": [
                    {"role": "system", "content": "You are a trading analyst. Respond with only: BUY, SELL, or HOLD followed by one sentence reason. Nothing else."},
                    {"role": "user", "content": prompt}
                ],
                "venice_parameters": {"include_venice_system_prompt": False}
            },
            timeout=30
        )
        return r.json()["choices"][0]["message"]["content"].strip()
    except:
        return "HOLD (venice error)"

def analyze_ticker(ticker, state):
    data = get_price_data(ticker)
    if not data:
        print(f"  {ticker}: failed to fetch")
        return

    sigs = basic_signals(data)
    position = state["positions"].get(ticker, 0)

    prompt = f"""Stock: {ticker}
Current price: ${sigs['current_price']:.2f}
MA5: {sigs['ma5']}, MA10: {sigs['ma10']}, MA20: {sigs['ma20']}
5-day change: {sigs['pct_5d']}%
Signals: {', '.join(sigs['signals']) or 'neutral'}
Current position: {position} shares
Available cash: ${state['cash']:.2f}

Should I BUY, SELL, or HOLD?"""

    decision = ask_venice(prompt)
    action = "HOLD"
    if decision.upper().startswith("BUY"):
        action = "BUY"
    elif decision.upper().startswith("SELL"):
        action = "SELL"

    price = sigs["current_price"]
    shares_owned = position
    trade = None

    if action == "BUY" and state["cash"] >= price * 10:
        shares = int((state["cash"] * 0.1) / price)  # use 10% of cash
        if shares > 0:
            cost = shares * price
            state["cash"] -= cost
            state["positions"][ticker] = shares_owned + shares
            trade = {"action": "BUY", "shares": shares, "price": price, "cost": cost}
            print(f"  {ticker}: BUY {shares} @ ${price:.2f} = ${cost:.2f} | {decision}")

    elif action == "SELL" and shares_owned > 0:
        proceeds = shares_owned * price
        state["cash"] += proceeds
        state["positions"][ticker] = 0
        trade = {"action": "SELL", "shares": shares_owned, "price": price, "proceeds": proceeds}
        print(f"  {ticker}: SELL {shares_owned} @ ${price:.2f} = ${proceeds:.2f} | {decision}")

    else:
        print(f"  {ticker}: HOLD @ ${price:.2f} | {decision}")

    # Log it
    log_entry = {
        "ts": datetime.datetime.now().isoformat(),
        "ticker": ticker,
        "price": price,
        "signals": sigs["signals"],
        "decision": decision,
        "trade": trade
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    if trade:
        state["trades"].append({**log_entry, "ticker": ticker})

def portfolio_value(state):
    total = state["cash"]
    for ticker, shares in state["positions"].items():
        if shares > 0:
            data = get_price_data(ticker, days=2)
            if data:
                total += shares * data["current"]
    return total

def run():
    state = load_state()
    print(f"\n=== KORA TRADER — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    print(f"Cash: ${state['cash']:.2f}")
    print(f"Positions: {state['positions']}")

    pval = portfolio_value(state)
    pnl = pval - STARTING_CASH
    print(f"Portfolio value: ${pval:.2f} | P&L: ${pnl:+.2f}\n")

    print("Analyzing watchlist...")
    for ticker in WATCHLIST:
        analyze_ticker(ticker, state)

    save_state(state)
    print(f"\nDone. State saved.")

if __name__ == "__main__":
    run()
