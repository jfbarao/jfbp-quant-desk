# =========================================================
# 📈 JFBP RESEARCH STOCK PAGE — STRICT NO TRADE MODEL
# =========================================================

import streamlit as st
import pandas as pd
import yfinance as yf

try:
    from universe.jfbp_universe import JFBP_UNIVERSE
except Exception:
    JFBP_UNIVERSE = {}


def run_page():

    st.title("📈 Research Stock Analysis")

    ticker = st.text_input(
        "Enter Ticker",
        value=st.session_state.get("research_ticker", "WMT"),
        key="research_ticker_input",
    ).upper()

    st.session_state["research_ticker"] = ticker

    profile = JFBP_UNIVERSE.get(ticker, {})

    st.subheader("🌍 JFBP Universe Profile")

    if profile:
        colU1, colU2, colU3, colU4 = st.columns(4)

        colU1.metric("Sector", profile.get("sector", "N/A"))
        colU2.metric("Liquidity", profile.get("liquidity", "N/A"))
        colU3.metric("Volatility", profile.get("volatility", "N/A"))
        colU4.metric("Regime", ", ".join(profile.get("regime", [])))
    else:
        st.warning("Ticker not found in JFBP Universe metadata")

    colA, colB, colC = st.columns(3)

    with colA:
        analyze = st.button(
            "Analyze",
            width="stretch",
            key="research_analyze_btn",
        )

    with colB:
        refresh = st.button(
            "Refresh + Clear Cache",
            width="stretch",
            key="research_refresh_btn",
        )

    with colC:
        clear = st.button(
            "Clear",
            width="stretch",
            key="research_clear_btn",
        )

    if refresh:
        st.cache_data.clear()
        st.session_state["research_last_analyze"] = True
        st.rerun()

    if clear:
        st.session_state["research_ticker"] = "WMT"
        st.session_state["research_last_analyze"] = False
        st.cache_data.clear()
        st.rerun()

    if analyze:
        st.session_state["research_last_analyze"] = True

    if not st.session_state.get("research_last_analyze", False):
        st.info("Enter ticker and click Analyze")
        return

    @st.cache_data(ttl=300)
    def load_data(symbol):
        return yf.download(
            symbol,
            period="6mo",
            interval="1d",
            progress=False,
            auto_adjust=False,
        )

    @st.cache_data(ttl=300)
    def load_benchmark():
        return yf.download(
            "SPY",
            period="6mo",
            interval="1d",
            progress=False,
            auto_adjust=False,
        )

    df = load_data(ticker)
    benchmark = load_benchmark()

    if df is None or df.empty:
        st.error("No stock data found.")
        return

    if benchmark is None or benchmark.empty:
        st.error("No benchmark data found.")
        return

    def normalize_columns(frame):
        frame = frame.copy()

        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = [
                "_".join([str(i) for i in col if i])
                for col in frame.columns
            ]

        return frame

    df = normalize_columns(df)
    benchmark = normalize_columns(benchmark)

    def find_col(frame, name):
        exact = [c for c in frame.columns if str(c).lower() == name.lower()]

        if exact:
            return exact[0]

        matches = [
            c for c in frame.columns
            if name.lower() in str(c).lower()
        ]

        return matches[0] if matches else None

    close_col = find_col(df, "Close")
    high_col = find_col(df, "High")
    low_col = find_col(df, "Low")
    open_col = find_col(df, "Open")
    bench_close_col = find_col(benchmark, "Close")

    if close_col is None or bench_close_col is None:
        st.error("Missing required Close column.")
        return

    if open_col:
        df["Open"] = pd.to_numeric(df[open_col], errors="coerce")
    else:
        df["Open"] = pd.to_numeric(df[close_col], errors="coerce")

    if high_col:
        df["High"] = pd.to_numeric(df[high_col], errors="coerce")
    else:
        df["High"] = pd.to_numeric(df[close_col], errors="coerce")

    if low_col:
        df["Low"] = pd.to_numeric(df[low_col], errors="coerce")
    else:
        df["Low"] = pd.to_numeric(df[close_col], errors="coerce")

    df["Close"] = pd.to_numeric(df[close_col], errors="coerce")

    benchmark["Benchmark"] = pd.to_numeric(
        benchmark[bench_close_col],
        errors="coerce",
    )

    df = df.join(benchmark[["Benchmark"]], how="inner")
    df = df.dropna(subset=["Open", "High", "Low", "Close", "Benchmark"])

    if len(df) < 60:
        st.warning("Not enough historical data.")
        return

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    df["RS"] = df["Close"] / df["Benchmark"]
    df["RS_MA20"] = df["RS"].rolling(20).mean()
    df["RS_SCORE"] = df["RS"] / df["RS_MA20"]

    prev_close = df["Close"].shift(1)

    tr1 = df["High"] - df["Low"]
    tr2 = (df["High"] - prev_close).abs()
    tr3 = (df["Low"] - prev_close).abs()

    df["TR"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["ATR"] = df["TR"].rolling(14).mean()

    df["20D_HIGH"] = df["High"].rolling(20).max()
    df["20D_LOW"] = df["Low"].rolling(20).min()

    df = df.dropna()

    if df.empty:
        st.warning("Not enough clean indicator data.")
        return

    latest_close = round(float(df["Close"].iloc[-1]), 2)
    previous_close = round(float(df["Close"].iloc[-2]), 2)

    latest_ma20 = round(float(df["MA20"].iloc[-1]), 2)
    latest_ma50 = round(float(df["MA50"].iloc[-1]), 2)
    latest_rs_score = round(float(df["RS_SCORE"].iloc[-1]), 4)
    latest_atr = round(float(df["ATR"].iloc[-1]), 4)

    latest_20d_high = round(float(df["20D_HIGH"].iloc[-1]), 2)
    latest_20d_low = round(float(df["20D_LOW"].iloc[-1]), 2)

    support = latest_20d_low
    resistance = latest_20d_high

    above_ma20 = latest_close > latest_ma20
    above_ma50 = latest_close > latest_ma50
    improving_today = latest_close > previous_close
    strong_rs = latest_rs_score >= 1.05
    near_high = latest_close >= latest_20d_high * 0.98

    weak_rs = latest_rs_score <= 0.97
    below_ma20 = latest_close < latest_ma20
    below_ma50 = latest_close < latest_ma50
    falling_today = latest_close < previous_close

    model_score = 0

    if above_ma20:
        model_score += 1
    if above_ma50:
        model_score += 1
    if improving_today:
        model_score += 1
    if strong_rs:
        model_score += 1
    if near_high:
        model_score += 1

    if above_ma20 and above_ma50 and improving_today and strong_rs and near_high:
        signal = "BUY"
    elif below_ma20 and below_ma50 and falling_today and weak_rs:
        signal = "SELL"
    else:
        signal = "NO TRADE"

    trend = "BULLISH" if above_ma20 and above_ma50 else "BEARISH"

    if trend == "BULLISH":
        trend_text = f"{ticker} remains in a constructive bullish trend."
    else:
        trend_text = f"{ticker} remains under bearish pressure."

    if latest_rs_score >= 1.05:
        momentum_text = "Relative strength is strong versus the benchmark."
    elif latest_rs_score <= 0.97:
        momentum_text = "Relative strength is weak versus the benchmark."
    else:
        momentum_text = "Relative strength remains neutral to constructive."

    commentary = (
        f"{trend_text} "
        f"{momentum_text} "
        f"Key support is near ${support:.2f}. "
        f"Resistance is located near ${resistance:.2f}."
    )

    st.info(commentary)

    col1, col2, col3 = st.columns(3)

    col1.metric("Signal", signal)
    col2.metric("Model Score", model_score)
    col3.metric("Last Price", latest_close)

    col4, col5, col6 = st.columns(3)

    col4.metric("MA20", latest_ma20)
    col5.metric("MA50", latest_ma50)
    col6.metric("RS Score", latest_rs_score)

    col7, col8, col9 = st.columns(3)

    col7.metric("ATR", latest_atr)
    col8.metric("20D High", latest_20d_high)
    col9.metric("Prev Close", previous_close)

    st.subheader("Price Chart")

    chart_df = df[
        [
            "Close",
            "MA20",
            "MA50",
        ]
    ].copy()

    st.line_chart(
        chart_df,
        width="stretch",
    )

    st.subheader("Key Levels")
    st.markdown(f"Support: ${support:.2f}")
    st.markdown(f"Resistance: ${resistance:.2f}")

    st.subheader("Model Table")

    table_df = df[
        [
            "Open",
            "High",
            "Low",
            "Close",
            "Benchmark",
            "RS",
            "RS_MA20",
            "RS_SCORE",
            "MA20",
            "MA50",
            "ATR",
            "20D_HIGH",
            "20D_LOW",
        ]
    ].copy()

    table_df = table_df.reset_index()
    first_col = table_df.columns[0]
    table_df = table_df.rename(columns={first_col: "Date"})
    table_df["Date"] = pd.to_datetime(table_df["Date"], errors="coerce")
    table_df = table_df.sort_values("Date", ascending=False)

    st.dataframe(
        table_df.head(20),
        width="stretch",
    )