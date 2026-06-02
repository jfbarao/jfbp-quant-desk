# =========================================================
# 🧠 JFBP QUANT DESK — v15 CORE SIGNAL ENGINE
# =========================================================

from typing import Tuple, Optional

import numpy as np
import pandas as pd


# =========================================================
# ⚡ LIVE SIGNAL ENGINE (CORE PURE FUNCTION)
# =========================================================

def live_signal_from_price(
    features_last_row: pd.Series,
    live_price: float
) -> Tuple[str, float]:

    # =====================================================
    # INPUT VALIDATION
    # =====================================================

    if (
        live_price is None
        or not np.isfinite(live_price)
        or live_price <= 0
    ):
        return "AVOID", 0.0

    price = float(live_price)

    try:
        ma = float(features_last_row["MA"])
        rs = float(features_last_row["RS_SCORE"])
        atr = float(features_last_row["ATR"])
    except Exception:
        return "AVOID", 0.0

    if ma <= 0:
        return "AVOID", 0.0

    # =====================================================
    # VOLATILITY FILTER (KILL SWITCH)
    # =====================================================

    atr_pct = atr / price if price > 0 else 0.0

    if not np.isfinite(atr_pct) or atr_pct > 0.25:
        return "AVOID", 0.0

    # =====================================================
    # CORE SIGNAL FEATURES
    # =====================================================

    trend = (price - ma) / ma
    momentum = rs - 1.0

    trend = np.clip(trend, -0.2, 0.2)
    momentum = np.clip(momentum, -0.3, 0.5)
    vol_penalty = np.clip(atr_pct, 0, 0.1)

    # =====================================================
    # SCORE MODEL (STABLE WEIGHTED SYSTEM)
    # =====================================================

    score = (
        0.50 * trend +
        0.35 * momentum -
        0.15 * vol_penalty
    )

    # =====================================================
    # PROBABILITY MAPPING
    # =====================================================

    prob = 1 / (1 + np.exp(-9 * score))

    # =====================================================
    # SIGNAL DECISION LAYER
    # =====================================================

    if prob > 0.67:
        return "BUY", float(prob)

    if prob > 0.52:
        return "WATCH", float(prob)

    return "AVOID", float(prob)


# =========================================================
# 📊 SCANNER SIGNAL WRAPPER (DATAFRAME INPUT)
# =========================================================

def signal_engine(df: pd.DataFrame) -> Tuple[str, float]:

    if df is None or df.empty:
        return "AVOID", 0.0

    try:
        last_row = df.iloc[-1]
        last_price = float(df["Close"].iloc[-1])

        return live_signal_from_price(last_row, last_price)

    except Exception:
        return "AVOID", 0.0