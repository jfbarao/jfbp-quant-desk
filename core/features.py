# =========================================================
# 📊 core/features.py — v15 FEATURE ENGINE
# =========================================================

from __future__ import annotations

import numpy as np
import pandas as pd

from typing import Optional

from data.market_data import get_price_history


# =========================================================
# 📈 RSI
# =========================================================

def compute_rsi(
    series: pd.Series,
    period: int = 14
) -> pd.Series:

    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    rsi = 100 - (100 / (1 + rs))

    return rsi.fillna(50)


# =========================================================
# 📈 ATR
# =========================================================

def compute_atr(
    df: pd.DataFrame,
    period: int = 14
) -> pd.Series:

    high_low = df["High"] - df["Low"]

    high_close = np.abs(df["High"] - df["Close"].shift(1))
    low_close = np.abs(df["Low"] - df["Close"].shift(1))

    true_range = pd.concat(
        [high_low, high_close, low_close],
        axis=1
    ).max(axis=1)

    return true_range.rolling(period).mean()


# =========================================================
# 📈 RELATIVE STRENGTH SCORE
# =========================================================

def compute_rs_score(
    close: pd.Series,
    lookback: int = 20
) -> pd.Series:

    momentum = close / close.shift(lookback)
    return momentum.fillna(1.0)


# =========================================================
# 🧠 SIGNAL FEATURES (NEW LAYER)
# =========================================================

def add_signal_features(df: pd.DataFrame) -> pd.DataFrame:

    # -------------------------
    # MOMENTUM SIGNALS
    # -------------------------

    df["EMA_10"] = df["Close"].ewm(span=10).mean()
    df["EMA_20"] = df["Close"].ewm(span=20).mean()

    df["EMA_SLOPE"] = df["EMA_10"] - df["EMA_10"].shift(5)

    df["MACD"] = (
        df["Close"].ewm(span=12).mean()
        - df["Close"].ewm(span=26).mean()
    )

    # -------------------------
    # RSI REGIME SIGNAL
    # -------------------------

    df["RSI_SIGNAL"] = np.where(
        df["RSI"] > 70,
        -1,
        np.where(df["RSI"] < 30, 1, 0)
    )

    # -------------------------
    # VOLATILITY REGIME
    # -------------------------

    df["VOL_REGIME"] = (
        df["Volatility"] /
        df["Volatility"].rolling(50).mean()
    )

    # -------------------------
    # BREAKOUT SIGNAL
    # -------------------------

    df["BREAKOUT"] = (
        df["Close"] >
        df["Close"].rolling(20).max().shift(1)
    ).astype(int)

    # -------------------------
    # VOLUME SURGE
    # -------------------------

    df["VOLUME_SPIKE"] = (
        df["Volume_Ratio"] > 2.0
    ).astype(int)

    return df


# =========================================================
# 📊 FEATURE BUILDER
# =========================================================

def build_features(
    symbol: str,
    bars: int = 252
) -> Optional[pd.DataFrame]:

    try:

        # =====================================================
        # LOAD PRICE HISTORY
        # =====================================================

        df = get_price_history(symbol=symbol, bars=bars)

        if df is None or df.empty:
            return None

        required_cols = ["Open", "High", "Low", "Close", "Volume"]

        for col in required_cols:
            if col not in df.columns:
                return None

        # =====================================================
        # CLEAN NUMERIC TYPES
        # =====================================================

        for col in required_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna().copy()

        if len(df) < 50:
            return None

        # =====================================================
        # CORE FEATURES
        # =====================================================

        df["Returns"] = df["Close"].pct_change()

        df["MA"] = df["Close"].rolling(20).mean()
        df["MA_50"] = df["Close"].rolling(50).mean()

        df["Volatility"] = df["Returns"].rolling(20).std()

        df["RSI"] = compute_rsi(df["Close"])
        df["ATR"] = compute_atr(df)
        df["RS_SCORE"] = compute_rs_score(df["Close"])

        # =====================================================
        # TREND FEATURES
        # =====================================================

        df["Trend"] = (df["Close"] - df["MA"]) / df["MA"]
        df["Trend_50"] = (df["Close"] - df["MA_50"]) / df["MA_50"]

        # =====================================================
        # VOLUME FEATURES
        # =====================================================

        df["Volume_MA"] = df["Volume"].rolling(20).mean()
        df["Volume_Ratio"] = df["Volume"] / df["Volume_MA"]

        # =====================================================
        # SIGNAL FEATURES LAYER
        # =====================================================

        df = add_signal_features(df)

        # =====================================================
        # CLEAN FINAL DATASET
        # =====================================================

        df = df.replace([np.inf, -np.inf], np.nan).dropna().copy()

        if df.empty:
            return None

        return df

    except Exception as e:
        print(f"Feature build error ({symbol}): {e}")
        return None