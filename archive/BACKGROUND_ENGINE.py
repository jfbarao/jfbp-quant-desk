import time
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import os

# =========================================================
# TELEGRAM
# =========================================================
def send_telegram(message):

    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("Missing Telegram credentials")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    try:
        requests.post(url, data={"chat_id": chat_id, "text": message}, timeout=10)
    except Exception as e:
        print("Telegram error:", e)


# =========================================================
# UNIVERSE
# =========================================================
UNIVERSE = [
    "AAPL","MSFT","NVDA","AMZN","META",
    "TSLA","GOOG","AMD","NFLX","AVGO"
]


# =========================================================
# SAFE DATA LOADER
# =========================================================
def get_data(symbol):

    df = yf.download(symbol, period="6mo", progress=False)

    if df is None or df.empty:
        return None

    # FIX MULTIINDEX ISSUE
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()

    df = df[["Date", "Open", "High", "Low", "Close"]].dropna()

    return df


# =========================================================
# COMPUTE SIGNAL (STABLE + PROPER ALIGNMENT)
# =========================================================
def compute(symbol, benchmark="SPY"):

    df = get_data(symbol)
    bench = get_data(benchmark)

    if df is None or bench is None:
        return None

    # FORCE CLEAN INDEX ALIGNMENT
    df["Date"] = pd.to_datetime(df["Date"])
    bench["Date"] = pd.to_datetime(bench["Date"])

    df = df.set_index("Date")
    bench = bench.set_index("Date")

    df["Benchmark"] = bench["Close"]

    df = df.dropna()

    # Not enough data
    if len(df) < 60:
        return None

    # =====================================================
    # INDICATORS
    # =====================================================
    df["MA50"] = df["Close"].rolling(50).mean()
    df["RS"] = df["Close"] / df["MA50"]

    last = df.iloc[-1]

    close = float(last["Close"])

    ma_val = last["MA50"]
    ma = float(ma_val) if pd.notna(ma_val) else close

    rs_val = last["RS"]
    rs = float(rs_val) if pd.notna(rs_val) else 1.0

    # =====================================================
    # SIGNAL LOGIC
    # =====================================================
    trend = close > ma

    score = int(trend) + int(rs > 1) + int(rs > 1.05)

    if score >= 2:
        return "BUY", score

    return "HOLD", score


# =========================================================
# ENGINE LOOP
# =========================================================
def run():

    print("🏛 BACKGROUND ENGINE STARTED (STABLE v1)")

    last_alerts = set()

    while True:

        try:

            current = set()

            for symbol in UNIVERSE:

                result = compute(symbol)

                if result is None:
                    continue

                signal, score = result

                if signal == "BUY":
                    current.add(symbol)

            # ALERT LOGIC
            new_signals = current - last_alerts

            print("\nCURRENT:", current)
            print("NEW:", new_signals)

            if new_signals:
                message = "🟢 NEW BUY SIGNALS:\n" + "\n".join(sorted(new_signals))
                print(message)
                send_telegram(message)

            last_alerts = current

        except Exception as e:
            print("ENGINE ERROR:", e)

        time.sleep(120)


# =========================================================
# ENTRY POINT
# =========================================================
if __name__ == "__main__":
    run()