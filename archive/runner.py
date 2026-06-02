# =========================================================
# 🧠 JFBP QUANT DESK — v15 RUNNER (ORCHESTRATOR LAYER)
# =========================================================

import time
from typing import Dict, Any, List

import streamlit as st

# =========================================================
# IMPORT ENGINE LAYERS (v15 architecture)
# =========================================================

from core.engine import compute_signal
from risk.engine import risk_check
from oms.engine import oms_engine


# =========================================================
# 📡 MARKET EVENT ENTRY POINT
# =========================================================

def process_market_tick(
    symbol: str,
    market_data: Dict[str, Any],
    ib=None
) -> None:
    """
    MAIN ORCHESTRATION PIPELINE

    Called on every tick or periodic refresh.
    """

    try:

        # =====================================================
        # 1. SIGNAL GENERATION (PURE LOGIC LAYER)
        # =====================================================

        signal = compute_signal(symbol, market_data)

        if signal is None:
            return

        # OMS expects last_price
        price = market_data.get("last")

        if price is None:
            return

        # =====================================================
        # 2. ATTACH SIGNAL INTO SESSION STATE (NORMALIZED)
        # =====================================================

        if "signals" not in st.session_state:
            st.session_state.signals = {}

        st.session_state.signals[symbol] = {
            "signal": signal,
            "last_price": float(price),
            "timestamp": time.time(),
        }

        # =====================================================
        # 3. OMS EXECUTION LAYER
        # =====================================================

        if ib is not None:

            oms_engine(ib)

    except Exception as e:
        print(f"[RUNNER ERROR] {symbol}: {e}")


# =========================================================
# 📡 BATCH SCANNER MODE (UNIVERSE LOOP)
# =========================================================

def run_universe_scan(
    universe: List[str],
    build_features_fn,
    signal_engine_fn,
) -> List[Dict[str, Any]]:

    results = []

    for symbol in universe:

        try:

            df = build_features_fn(symbol)

            if df is None or df.empty:
                continue

            signal, prob = signal_engine_fn(df)

            results.append({
                "symbol": symbol,
                "signal": signal,
                "probability": float(prob),
                "last_price": float(df["Close"].iloc[-1]),
                "timestamp": time.time(),
            })

            # =================================================
            # SYNC INTO STREAMLIT STATE
            # =================================================

            if "signal_table" not in st.session_state:
                st.session_state.signal_table = []

            st.session_state.signal_table.append(results[-1])

        except Exception as e:
            print(f"[SCAN ERROR] {symbol}: {e}")

    return results


# =========================================================
# 📡 STREAM INITIALIZATION HOOK
# =========================================================

def attach_stream_handler(
    ib,
    symbol: str,
    ticker,
) -> None:
    """
    Ensures all IBKR ticks route into runner pipeline.
    """

    def _handler(tick):

        try:

            market_data = {
                "bid": getattr(tick, "bid", None),
                "ask": getattr(tick, "ask", None),
                "last": getattr(tick, "last", None),
                "close": getattr(tick, "close", None),
                "volume": getattr(tick, "volume", None),
                "timestamp": time.time(),
            }

            process_market_tick(symbol, market_data, ib)

        except Exception as e:
            print(f"[TICK ERROR] {symbol}: {e}")

    ticker.updateEvent += _handler