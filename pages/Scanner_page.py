# =========================================================
# 📡 JFBP SCANNER PAGE v35.3
# RESEARCH-MODEL SIGNAL TRUTH + MARKET REACTION OVERLAY + PORTFOLIO FILTER
# EQUAL-WEIGHT POSITION SIZING — $50K TEST PORTFOLIO
# NO FORCED FALLBACK BUY/SELL SIGNALS
# =========================================================

from __future__ import annotations

from datetime import datetime, timezone
from math import floor
from typing import Dict, Any, List

import pandas as pd
import streamlit as st
import yfinance as yf

from core.bootstrap import init_core

try:
    from universe.jfbp_universe import JFBP_UNIVERSE
except Exception:
    JFBP_UNIVERSE = {}

try:
    from universe.ost_universe import OST_UNIVERSE
except Exception:
    OST_UNIVERSE = {}


# =========================================================
# PAGE ALIAS
# =========================================================

def page():
    run_page()


# =========================================================
# FALLBACK UNIVERSE
# =========================================================

def fallback_universe():
    return {
        "SPY": {"sector": "ETF", "liquidity": 5, "volatility": 2, "regime": ["benchmark"]},
        "QQQ": {"sector": "ETF", "liquidity": 5, "volatility": 3, "regime": ["growth"]},
        "IWM": {"sector": "ETF", "liquidity": 4, "volatility": 3, "regime": ["small_caps"]},
        "DIA": {"sector": "ETF", "liquidity": 4, "volatility": 2, "regime": ["blue_chip"]},
        "TQQQ": {"sector": "ETF", "liquidity": 4, "volatility": 5, "regime": ["leveraged_momentum"]},
        "UVXY": {"sector": "ETF", "liquidity": 4, "volatility": 5, "regime": ["volatility"]},
        "AAPL": {"sector": "Tech", "liquidity": 5, "volatility": 2, "regime": ["defensive_growth"]},
        "MSFT": {"sector": "Tech", "liquidity": 5, "volatility": 2, "regime": ["defensive_growth"]},
        "NVDA": {"sector": "Tech", "liquidity": 5, "volatility": 4, "regime": ["momentum"]},
        "AMZN": {"sector": "Consumer", "liquidity": 5, "volatility": 3, "regime": ["growth"]},
        "COIN": {"sector": "Crypto", "liquidity": 4, "volatility": 5, "regime": ["high_beta"]},
        "DE": {"sector": "Industrial", "liquidity": 3, "volatility": 3, "regime": ["cyclical"]},
        "WMT": {"sector": "Consumer Defensive", "liquidity": 5, "volatility": 2, "regime": ["defensive"]},
        "BA": {"sector": "Industrial", "liquidity": 4, "volatility": 4, "regime": ["cyclical"]},
        "BX": {"sector": "Financial", "liquidity": 4, "volatility": 3, "regime": ["financial"]},
        "LRCX": {"sector": "Semiconductors", "liquidity": 4, "volatility": 4, "regime": ["semis"]},
        "ASML": {"sector": "Semiconductors", "liquidity": 4, "volatility": 3, "regime": ["semis"]},
        "ARM": {"sector": "Semiconductors", "liquidity": 4, "volatility": 5, "regime": ["semis"]},
        "FUTU": {"sector": "Financial", "liquidity": 3, "volatility": 5, "regime": ["high_beta"]},
        "JPM": {"sector": "Financial", "liquidity": 5, "volatility": 2, "regime": ["financial"]},
    }


def run_page():

    gateway, market, oms, portfolio_engine = init_core()

    risk_engine = st.session_state.get("risk_engine")
    pipeline = st.session_state.get("pipeline")

    # =====================================================
    # POSITION SIZING CONFIG
    # =====================================================

    SCANNER_TEST_PORTFOLIO_VALUE = 50_000.0
    SCANNER_TARGET_POSITION_PCT = 0.05
    SCANNER_TARGET_POSITION_VALUE = (
        SCANNER_TEST_PORTFOLIO_VALUE
        * SCANNER_TARGET_POSITION_PCT
    )
    SCANNER_MIN_QTY = 1

    st.title("📡 Scanner")
    st.subheader("Research-Model Scanner Execution — Batch Rotation Mode")

    # =====================================================
    # UNIVERSE SELECTION
    # =====================================================

    universe_options = [
        "JFBP",
        "OST",
        "FALLBACK",
    ]

    current_universe_mode = st.session_state.get(
        "scanner_universe_mode",
        "JFBP",
    )

    if current_universe_mode not in universe_options:
        current_universe_mode = "JFBP"

    u1, u2 = st.columns([1, 3])

    with u1:
        universe_mode = st.selectbox(
            "Universe",
            universe_options,
            index=universe_options.index(current_universe_mode),
            key="scanner_universe_mode_selector",
        )

    st.session_state["scanner_universe_mode"] = universe_mode

    if universe_mode == "OST":

        active_universe = (
            OST_UNIVERSE
            if isinstance(OST_UNIVERSE, dict)
            and OST_UNIVERSE
            else fallback_universe()
        )

    elif universe_mode == "FALLBACK":

        active_universe = fallback_universe()

    else:

        active_universe = (
            JFBP_UNIVERSE
            if isinstance(JFBP_UNIVERSE, dict)
            and JFBP_UNIVERSE
            else fallback_universe()
        )

    st.session_state["universe"] = active_universe

    with u2:
        st.caption(
            f"Active universe: {universe_mode} "
            f"({len(active_universe)} symbols)"
        )

    # =====================================================
    # LOCAL HELPERS
    # =====================================================

    def now():
        return datetime.now(timezone.utc).isoformat()

    def clear_scanner_warning():
        st.session_state["scanner_last_error"] = ""

    def safe_snapshot(obj):
        if obj and hasattr(obj, "snapshot"):
            try:
                snap = obj.snapshot()
                return snap if isinstance(snap, dict) else {}
            except Exception as exc:
                st.session_state["scanner_last_error"] = f"snapshot failed: {exc}"
                return {}
        return {}

    def normalize_action(value: Any) -> str:
        action = str(value or "").upper().strip()

        action_map = {
            "LONG": "BUY",
            "BUY_LONG": "BUY",
            "ENTER_LONG": "BUY",
            "OPEN_LONG": "BUY",
            "BULLISH": "BUY",

            "SHORT": "SELL",
            "SELL_SHORT": "SELL",
            "ENTER_SHORT": "SELL",
            "OPEN_SHORT": "SELL",
            "BEARISH": "SELL",

            "NO TRADE": "HOLD",
            "NO_TRADE": "HOLD",
            "NONE": "HOLD",
            "FLAT": "HOLD",
            "NEUTRAL": "HOLD",
            "": "HOLD",
        }

        return action_map.get(action, action)

    def safe_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    def safe_qty(value: Any, default: float = 1.0) -> float:
        qty = safe_float(value, default)
        if qty <= 0:
            return default
        return abs(qty)

    def calculate_equal_weight_qty(
        price: Any,
        action: str = "BUY",
        existing_qty: float = 0.0,
    ) -> float:
        """
        Target-weight sizing.

        BUY:
        - Buy only the delta needed to reach the target position value.
        - If already at or above target, return 0.

        SELL:
        - Sell the existing long position only.
        """

        price = safe_float(price, 0.0)
        action = normalize_action(action)
        existing_qty = safe_float(existing_qty, 0.0)

        if price <= 0:
            return 0.0

        current_position_value = max(0.0, existing_qty * price)

        if action == "SELL":
            return float(max(0.0, existing_qty))

        if action != "BUY":
            return 0.0

        delta_value = SCANNER_TARGET_POSITION_VALUE - current_position_value

        if delta_value <= 0:
            return 0.0

        qty = floor(delta_value / price)

        return float(max(0.0, qty))

    def apply_equal_weight_position_sizing(
        row: Dict[str, Any],
        existing_qty: float = 0.0,
    ) -> Dict[str, Any]:
        row = row if isinstance(row, dict) else {}

        action = normalize_action(
            row.get("scanner_action")
            or row.get("action")
            or row.get("signal")
            or row.get("side")
        )

        price = safe_float(row.get("price"), 0.0)
        existing_qty = safe_float(existing_qty, 0.0)

        current_position_value = max(0.0, existing_qty * price)
        delta_to_target_value = max(
            0.0,
            SCANNER_TARGET_POSITION_VALUE - current_position_value,
        )

        sized_qty = calculate_equal_weight_qty(
            price=price,
            action=action,
            existing_qty=existing_qty,
        )

        sizing_status = "SIZED_TO_TARGET"

        if action == "BUY" and sized_qty <= 0:
            sizing_status = "AT_OR_ABOVE_TARGET"
        elif action == "SELL":
            sizing_status = "SELL_EXISTING_LONG_ONLY"
        elif action not in ("BUY", "SELL"):
            sizing_status = "NO_TRADE_NO_SIZE"

        return {
            **row,
            "qty": sized_qty,
            "sizing_model": "TARGET_WEIGHT_5PCT_TEST_PORTFOLIO",
            "sizing_status": sizing_status,
            "sizing_portfolio_value": SCANNER_TEST_PORTFOLIO_VALUE,
            "sizing_target_pct": SCANNER_TARGET_POSITION_PCT,
            "sizing_target_value": SCANNER_TARGET_POSITION_VALUE,
            "sizing_existing_qty": existing_qty,
            "sizing_current_value": round(current_position_value, 4),
            "sizing_delta_value": round(delta_to_target_value, 4),
        }

    def first_session_value(keys: List[str], default: Any = None) -> Any:
        for key in keys:
            if key in st.session_state:
                value = st.session_state.get(key)
                if value is not None:
                    return value
        return default

    def market_reaction_context() -> Dict[str, Any]:
        raw_score = first_session_value(
            [
                "market_reaction_score",
                "reaction_score",
                "market_score",
                "market_event_score",
            ],
            None,
        )

        raw_confidence = first_session_value(
            [
                "market_reaction_confidence",
                "risk_confidence",
                "event_confidence",
            ],
            None,
        )

        raw_event = first_session_value(
            [
                "market_reaction_event",
                "market_event",
                "event_type",
                "market_regime",
                "reaction_regime",
            ],
            "",
        )

        raw_playbook = first_session_value(
            [
                "market_reaction_playbook",
                "playbook",
                "market_playbook",
            ],
            "",
        )

        score = safe_float(raw_score, 0.0)
        confidence = safe_float(raw_confidence, 0.0)

        event = str(raw_event or "").upper().strip()
        playbook = str(raw_playbook or "").upper().strip()

        risk_off_terms = [
            "RISK OFF",
            "RISK-OFF",
            "INSTITUTIONAL RISK OFF",
            "PANIC",
            "LIQUIDATION",
            "CRASH",
            "SELL-OFF",
            "SEVERE STRESS",
        ]

        risk_on_terms = [
            "RISK ON",
            "RISK-ON",
            "EXPANSION",
            "ACCUMULATION",
            "BULLISH",
        ]

        combined = f"{event} {playbook}"

        risk_off = any(term in combined for term in risk_off_terms)
        risk_on = any(term in combined for term in risk_on_terms)

        if not risk_off and score >= 85 and confidence >= 70:
            risk_off = True

        if risk_off:
            execution_multiplier = 0.50
            buy_allowed = False
            sell_allowed = True
            regime_label = "RISK_OFF"
        elif risk_on:
            execution_multiplier = 1.00
            buy_allowed = True
            sell_allowed = True
            regime_label = "RISK_ON"
        else:
            execution_multiplier = 1.00
            buy_allowed = True
            sell_allowed = True
            regime_label = "NEUTRAL"

        return {
            "score": score,
            "confidence": confidence,
            "event": raw_event or "",
            "playbook": raw_playbook or "",
            "risk_off": risk_off,
            "risk_on": risk_on,
            "regime_label": regime_label,
            "execution_multiplier": execution_multiplier,
            "buy_allowed": buy_allowed,
            "sell_allowed": sell_allowed,
        }

    def apply_market_reaction_overlay(row: Dict[str, Any]) -> Dict[str, Any]:
        row = row if isinstance(row, dict) else {}
        ctx = market_reaction_context()

        scanner_action = normalize_action(
            row.get("scanner_action")
            or row.get("action")
            or row.get("signal")
            or row.get("side")
        )

        original_qty = safe_qty(row.get("qty"), 1.0)
        adjusted_qty = max(
            1.0,
            round(original_qty * ctx["execution_multiplier"], 4),
        )

        overlay_reason = ""

        if ctx["risk_off"]:

            if scanner_action == "BUY":
                scanner_action = "HOLD"
                adjusted_qty = 0.0
                overlay_reason = "MARKET_REACTION_RISK_OFF_BUY_BLOCKED"

            elif scanner_action == "SELL":
                overlay_reason = "MARKET_REACTION_RISK_OFF_SELL_ALLOWED"

            else:
                scanner_action = "HOLD"
                adjusted_qty = 0.0
                overlay_reason = "MARKET_REACTION_RISK_OFF_HOLD"

        elif ctx["risk_on"]:

            if scanner_action == "BUY":
                overlay_reason = "MARKET_REACTION_RISK_ON_BUY_ALLOWED"

            elif scanner_action == "SELL":
                overlay_reason = "MARKET_REACTION_RISK_ON_SELL_ALLOWED"

            else:
                scanner_action = "HOLD"
                adjusted_qty = 0.0
                overlay_reason = "MARKET_REACTION_RISK_ON_HOLD"

        else:

            if scanner_action in ("BUY", "SELL"):
                overlay_reason = "MARKET_REACTION_NEUTRAL_TRADE_ALLOWED"

            else:
                scanner_action = "HOLD"
                adjusted_qty = 0.0
                overlay_reason = "MARKET_REACTION_NEUTRAL_HOLD"

        return {
            **row,
            "scanner_action": scanner_action,
            "market_reaction_regime": ctx["regime_label"],
            "market_reaction_score": ctx["score"],
            "market_reaction_confidence": ctx["confidence"],
            "market_reaction_event": ctx["event"],
            "market_reaction_playbook": ctx["playbook"],
            "market_reaction_overlay": overlay_reason,
            "qty": adjusted_qty,
        }

    def get_price(symbol: str) -> float:
        symbol = str(symbol or "").upper().strip()

        try:
            if market and hasattr(market, "get_price"):
                price = market.get_price(symbol)
                if price:
                    return float(price)
        except Exception:
            pass

        try:
            if market and hasattr(market, "snapshot"):
                snap = market.snapshot()
                if isinstance(snap, dict):
                    row = snap.get(symbol)
                    price = row.get("price") if isinstance(row, dict) else row
                    if price:
                        return float(price)
        except Exception:
            pass

        return 100.0

    def normalize_meta(symbol: str, meta: Any) -> Dict[str, Any]:
        symbol = str(symbol or "").upper().strip()

        if not isinstance(meta, dict):
            meta = {}

        regime = meta.get("regime", [])

        raw_data_symbol = meta.get("data_symbol")
        raw_data_symbols = meta.get("data_symbols", [])

        if raw_data_symbols is None:
            raw_data_symbols = []

        if isinstance(raw_data_symbols, str):
            raw_data_symbols = [raw_data_symbols]

        if not isinstance(raw_data_symbols, (list, tuple)):
            raw_data_symbols = []

        data_symbols = []

        if raw_data_symbol:
            data_symbols.append(raw_data_symbol)

        for item in raw_data_symbols:
            data_symbols.append(item)

        data_symbols.append(symbol)

        cleaned_data_symbols = []

        for item in data_symbols:
            item = str(item or "").upper().strip()

            if item and item not in cleaned_data_symbols:
                cleaned_data_symbols.append(item)

        data_symbol = cleaned_data_symbols[0] if cleaned_data_symbols else symbol

        return {
            "symbol": symbol,
            "data_symbol": data_symbol,
            "data_symbols": cleaned_data_symbols,
            "sector": meta.get("sector", "Unknown"),
            "liquidity": int(meta.get("liquidity", 3) or 3),
            "volatility": int(meta.get("volatility", 3) or 3),
            "regime": ",".join(regime) if isinstance(regime, list) else str(regime),
        }
    
    # =====================================================
    # RESEARCH MODEL ENGINE
    # =====================================================

    @st.cache_data(ttl=300)
    def load_symbol_data(symbol: str):
        return yf.download(
            symbol,
            period="6mo",
            interval="1d",
            progress=False,
            auto_adjust=False,
            threads=False,
        )

    @st.cache_data(ttl=300)
    def load_benchmark_data():
        return yf.download(
            "SPY",
            period="6mo",
            interval="1d",
            progress=False,
            auto_adjust=False,
            threads=False,
        )

    def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
        frame = frame.copy()

        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = [
                "_".join([str(i) for i in col if i])
                for col in frame.columns
            ]

        return frame

    def find_col(frame: pd.DataFrame, name: str):
        exact = [
            c for c in frame.columns
            if str(c).lower() == name.lower()
        ]

        if exact:
            return exact[0]

        matches = [
            c for c in frame.columns
            if name.lower() in str(c).lower()
        ]

        return matches[0] if matches else None

    def resolve_data_symbols(symbol: str, meta: Dict[str, Any]) -> list:
        candidates = []

        data_symbols = meta.get("data_symbols")

        if isinstance(data_symbols, (list, tuple)):
            candidates.extend(data_symbols)

        data_symbol = meta.get("data_symbol")

        if data_symbol:
            candidates.append(data_symbol)

        candidates.append(symbol)

        cleaned = []

        for item in candidates:
            item = str(item or "").upper().strip()

            if item and item not in cleaned:
                cleaned.append(item)

        return cleaned

    def load_first_valid_symbol(
        display_symbol: str,
        meta: Dict[str, Any],
    ):
        attempted_symbols = []
        last_error = None

        for data_symbol in resolve_data_symbols(display_symbol, meta):
            attempted_symbols.append(data_symbol)

            try:
                df = load_symbol_data(data_symbol)

                if df is not None and not df.empty:
                    return data_symbol, df, attempted_symbols

                last_error = "No stock data"

            except Exception as exc:
                last_error = str(exc)

        raise RuntimeError(last_error or "No stock data")

    def research_model_signal(symbol: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        symbol = str(symbol or "").upper().strip()
        meta = normalize_meta(symbol, meta)

        data_symbol = meta.get("data_symbol", symbol)
        attempted_symbols = []

        try:
            data_symbol, df, attempted_symbols = load_first_valid_symbol(
                symbol,
                meta,
            )

            benchmark = load_benchmark_data()

            if df is None or df.empty:
                raise RuntimeError("No stock data")

            if benchmark is None or benchmark.empty:
                raise RuntimeError("No benchmark data")

            df = normalize_columns(df)
            benchmark = normalize_columns(benchmark)

            close_col = find_col(df, "Close")
            high_col = find_col(df, "High")
            low_col = find_col(df, "Low")
            open_col = find_col(df, "Open")
            bench_close_col = find_col(benchmark, "Close")

            if close_col is None:
                raise RuntimeError("Missing required close column")

            if bench_close_col is None:
                raise RuntimeError("Missing benchmark close column")

            df["Open"] = pd.to_numeric(
                df[open_col] if open_col else df[close_col],
                errors="coerce",
            )
            df["High"] = pd.to_numeric(
                df[high_col] if high_col else df[close_col],
                errors="coerce",
            )
            df["Low"] = pd.to_numeric(
                df[low_col] if low_col else df[close_col],
                errors="coerce",
            )
            df["Close"] = pd.to_numeric(
                df[close_col],
                errors="coerce",
            )

            benchmark["Benchmark"] = pd.to_numeric(
                benchmark[bench_close_col],
                errors="coerce",
            )

            df = df.sort_index()
            benchmark = benchmark.sort_index()

            df = df[~df.index.duplicated(keep="last")]
            benchmark = benchmark[~benchmark.index.duplicated(keep="last")]

            df = df.join(benchmark[["Benchmark"]], how="left")
            df["Benchmark"] = df["Benchmark"].ffill().bfill()

            df = df.dropna(
                subset=[
                    "Open",
                    "High",
                    "Low",
                    "Close",
                    "Benchmark",
                ]
            )

            if len(df) < 30:
                raise RuntimeError("Not enough historical data")

            df["MA20"] = df["Close"].rolling(20).mean()

            if len(df) >= 50:
                df["MA50"] = df["Close"].rolling(50).mean()
            else:
                df["MA50"] = df["MA20"]

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

            df = df.dropna(
                subset=[
                    "Close",
                    "MA20",
                    "MA50",
                    "RS_SCORE",
                    "ATR",
                    "20D_HIGH",
                    "20D_LOW",
                ]
            )

            if df.empty:
                raise RuntimeError("Not enough clean indicator data")

            if len(df) < 2:
                raise RuntimeError("Not enough clean rows for previous close")

            latest_close = round(float(df["Close"].iloc[-1]), 2)
            previous_close = round(float(df["Close"].iloc[-2]), 2)
            latest_ma20 = round(float(df["MA20"].iloc[-1]), 2)
            latest_ma50 = round(float(df["MA50"].iloc[-1]), 2)
            latest_rs_score = round(float(df["RS_SCORE"].iloc[-1]), 4)
            latest_atr = round(float(df["ATR"].iloc[-1]), 4)
            latest_20d_high = round(float(df["20D_HIGH"].iloc[-1]), 2)
            latest_20d_low = round(float(df["20D_LOW"].iloc[-1]), 2)

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

            if (
                above_ma20
                and above_ma50
                and improving_today
                and strong_rs
                and near_high
            ):
                signal = "BUY"
            elif (
                below_ma20
                and below_ma50
                and falling_today
                and weak_rs
            ):
                signal = "SELL"
            else:
                signal = "NO TRADE"

            scanner_action = normalize_action(signal)
            trend = "BULLISH" if above_ma20 and above_ma50 else "BEARISH"

            return {
                "timestamp": now(),
                "symbol": symbol,
                "data_symbol": data_symbol,
                "sector": meta["sector"],
                "liquidity": meta["liquidity"],
                "volatility": meta["volatility"],
                "regime": meta["regime"],
                "signal": signal,
                "scanner_action": scanner_action,
                "action": scanner_action,
                "side": scanner_action,
                "qty": 1,
                "price": latest_close,
                "model_score": model_score,
                "score": model_score,
                "trend": trend,
                "ma20": latest_ma20,
                "ma50": latest_ma50,
                "rs_score": latest_rs_score,
                "atr": latest_atr,
                "support": latest_20d_low,
                "resistance": latest_20d_high,
                "prev_close": previous_close,
                "attempted_symbols": ", ".join(attempted_symbols),
                "source": "research_model_scanner_v35_3",
                "mode": st.session_state.get("mode", "SIM"),
                "reason": None,
            }

        except Exception as exc:
            price = get_price(data_symbol or symbol)

            return {
                "timestamp": now(),
                "symbol": symbol,
                "data_symbol": data_symbol,
                "sector": meta["sector"],
                "liquidity": meta["liquidity"],
                "volatility": meta["volatility"],
                "regime": meta["regime"],
                "signal": "NO TRADE",
                "scanner_action": "HOLD",
                "action": "HOLD",
                "side": "HOLD",
                "qty": 1,
                "price": price,
                "model_score": 0,
                "score": 0,
                "trend": "UNKNOWN",
                "ma20": None,
                "ma50": None,
                "rs_score": None,
                "atr": None,
                "support": None,
                "resistance": None,
                "prev_close": None,
                "attempted_symbols": ", ".join(attempted_symbols),
                "reason": str(exc),
                "source": "research_model_scanner_v35_3_error_safe",
                "mode": st.session_state.get("mode", "SIM"),
            }

    # =====================================================
    # PORTFOLIO / RISK SYNC
    # =====================================================

    def coerce_position_row(symbol: str, row: Any) -> Dict[str, Any]:
        symbol = str(symbol or "").upper().strip()

        if isinstance(row, dict):
            signed_qty = row.get("signed_qty", row.get("quantity", row.get("qty", 0)))
            side = str(row.get("side", "") or "").upper()

            signed_qty = safe_float(signed_qty, 0.0)

            if "signed_qty" not in row and side == "SHORT":
                signed_qty = -abs(signed_qty)

            avg_price = row.get("avg_price", row.get("price", 0))
            last_price = row.get("last_price", avg_price)
            realized_pnl = row.get("realized_pnl", 0)
            unrealized_pnl = row.get("unrealized_pnl", 0)
            total_pnl = row.get("total_pnl", 0)

        else:
            signed_qty = getattr(row, "quantity", getattr(row, "qty", 0.0))
            signed_qty = safe_float(signed_qty, 0.0)

            avg_price = getattr(row, "avg_price", 0.0)
            last_price = avg_price
            realized_pnl = getattr(row, "realized_pnl", 0.0)
            unrealized_pnl = 0.0
            total_pnl = realized_pnl

        avg_price = safe_float(avg_price, 0.0)
        last_price = safe_float(last_price, avg_price or get_price(symbol))
        realized_pnl = safe_float(realized_pnl, 0.0)
        unrealized_pnl = safe_float(unrealized_pnl, 0.0)
        total_pnl = safe_float(total_pnl, realized_pnl + unrealized_pnl)

        return {
            "symbol": symbol,
            "side": "LONG" if signed_qty > 0 else "SHORT" if signed_qty < 0 else "FLAT",
            "qty": abs(signed_qty),
            "signed_qty": signed_qty,
            "avg_price": avg_price,
            "last_price": last_price,
            "position_value": abs(signed_qty) * last_price,
            "unrealized_pnl": unrealized_pnl,
            "realized_pnl": realized_pnl,
            "total_pnl": total_pnl,
        }

    def get_portfolio_positions() -> Dict[str, Dict[str, Any]]:
        rows = {}

        if portfolio_engine is None:
            return rows

        try:
            if hasattr(portfolio_engine, "snapshot"):
                snap = portfolio_engine.snapshot()
                if isinstance(snap, dict):
                    for symbol, value in snap.items():
                        row = coerce_position_row(symbol, value)
                        if abs(row["signed_qty"]) > 1e-9 or abs(row["realized_pnl"]) > 1e-9:
                            rows[row["symbol"]] = row
        except Exception as exc:
            st.session_state["scanner_last_error"] = f"portfolio.snapshot failed: {exc}"

        if rows:
            return rows

        try:
            if hasattr(portfolio_engine, "risk_positions"):
                risk_positions = portfolio_engine.risk_positions()
                if isinstance(risk_positions, dict):
                    for symbol, signed_qty in risk_positions.items():
                        signed_qty = safe_float(signed_qty, 0.0)

                        if abs(signed_qty) <= 1e-9:
                            continue

                        symbol = str(symbol).upper().strip()
                        price = get_price(symbol)

                        rows[symbol] = {
                            "symbol": symbol,
                            "side": "LONG" if signed_qty > 0 else "SHORT",
                            "qty": abs(signed_qty),
                            "signed_qty": signed_qty,
                            "avg_price": price,
                            "last_price": price,
                            "position_value": abs(signed_qty) * price,
                            "unrealized_pnl": 0.0,
                            "realized_pnl": 0.0,
                            "total_pnl": 0.0,
                        }
        except Exception as exc:
            st.session_state["scanner_last_error"] = f"portfolio.risk_positions failed: {exc}"

        return rows

    def sync_market_reaction_to_risk_engine():
        try:
            if not risk_engine:
                return False

            if not hasattr(risk_engine, "update_market_reaction"):
                return False

            ctx = market_reaction_context()

            risk_engine.update_market_reaction(
                regime=ctx.get("regime_label", "NEUTRAL"),
                score=ctx.get("score", 0.0),
                confidence=ctx.get("confidence", 0.0),
            )

            return True

        except Exception as exc:
            st.session_state["scanner_last_error"] = (
                f"market reaction risk sync failed: {exc}"
            )
            return False

    def sync_risk():
        try:
            sync_market_reaction_to_risk_engine()

            if portfolio_engine and risk_engine and hasattr(risk_engine, "sync_positions"):
                positions = get_portfolio_positions()
                try:
                    risk_engine.sync_positions(positions, historical=True)
                except TypeError:
                    risk_engine.sync_positions(positions)

                sync_market_reaction_to_risk_engine()
                return True

        except Exception as exc:
            st.session_state["scanner_last_error"] = f"sync_risk failed: {exc}"

        return False

    # =====================================================
    # SIGNAL GENERATION / NORMALIZATION
    # =====================================================

    def generate_signals() -> List[Dict[str, Any]]:
        clear_scanner_warning()

        universe_mode = st.session_state.get(
            "scanner_universe_mode",
            "JFBP",
        )

        universe = st.session_state.get("universe")

        if not isinstance(universe, dict) or not universe:

            if universe_mode == "OST":

                universe = (
                    OST_UNIVERSE
                    if isinstance(OST_UNIVERSE, dict)
                    and OST_UNIVERSE
                    else fallback_universe()
                )

            elif universe_mode == "FALLBACK":

                universe = fallback_universe()

            else:

                universe = (
                    JFBP_UNIVERSE
                    if isinstance(JFBP_UNIVERSE, dict)
                    and JFBP_UNIVERSE
                    else fallback_universe()
                )

            st.session_state["universe"] = universe

        rows = []

        for symbol, meta in universe.items():

            symbol = str(symbol).upper().strip()

            if not symbol:
                continue

            row = research_model_signal(
                symbol=symbol,
                meta=meta if isinstance(meta, dict) else {},
            )

            rows.append(row)

        st.session_state["scanner_last_raw_signals"] = rows
        st.session_state["scanner_last_status"] = (
            f"GENERATED_{len(rows)}_RESEARCH_MODEL_SIGNALS"
        )

        return rows

    def normalize_signal(row: Dict[str, Any]) -> Dict[str, Any]:
        row = row if isinstance(row, dict) else {}
        row = apply_market_reaction_overlay(row)

        symbol = str(row.get("symbol") or "").upper().strip()

        scanner_action = normalize_action(
            row.get("scanner_action")
            or row.get("action")
            or row.get("signal")
            or row.get("side")
        )

        price = safe_float(row.get("price"), get_price(symbol))

        portfolio_positions = get_portfolio_positions()
        existing_qty = 0.0

        if isinstance(portfolio_positions, dict):
            position_row = portfolio_positions.get(symbol, {})
            if isinstance(position_row, dict):
                existing_qty = safe_float(
                    position_row.get("signed_qty", position_row.get("qty", 0.0)),
                    0.0,
                )

        row = apply_equal_weight_position_sizing(
            row=row,
            existing_qty=existing_qty,
        )

        qty = safe_float(row.get("qty"), 0.0)

        if qty < 0:
            qty = abs(qty)

        execution_action = (
            scanner_action
            if scanner_action in ("BUY", "SELL")
            else "HOLD"
        )

        return {
            **row,
            "timestamp": row.get("timestamp") or now(),
            "symbol": symbol,
            "scanner_action": scanner_action,
            "risk_action": execution_action,
            "execution_action": execution_action,
            "action": execution_action,
            "side": execution_action,
            "qty": qty,
            "price": price,
            "source": row.get("source") or "research_model_scanner_v35_3",
            "mode": st.session_state.get("mode", "SIM"),
        }

    def make_hold_row(signal: Dict[str, Any]) -> Dict[str, Any]:
        signal = normalize_signal(signal)

        return {
            **signal,
            "risk_status": "IGNORED",
            "risk_approved": False,
            "risk_reason": "NON_EXECUTABLE_RESEARCH_MODEL_SIGNAL",
            "risk_reducing": False,
            "position_action": "NO_TRADE",
            "position_before": 0.0,
            "position_after": 0.0,
            "gross_before": 0.0,
            "gross_after": 0.0,
            "executable": False,
        }

    def coerce_batch_rows(batch_rows: Any) -> List[Dict[str, Any]]:
        if batch_rows is None:
            return []

        if isinstance(batch_rows, dict):
            return [batch_rows]

        if isinstance(batch_rows, list):
            return [row for row in batch_rows if isinstance(row, dict)]

        try:
            return [row for row in list(batch_rows) if isinstance(row, dict)]
        except Exception:
            return []

    def scanner_status_label(
        plan: List[Dict[str, Any]],
        hold_rows: List[Dict[str, Any]],
    ) -> str:
        plan = plan if isinstance(plan, list) else []
        hold_rows = hold_rows if isinstance(hold_rows, list) else []

        executable_count = len([
            row for row in plan
            if bool(row.get("executable"))
        ])

        blocked_short_count = len([
            row for row in hold_rows
            if row.get("position_action") == "BLOCKED_OPEN_SHORT"
        ])

        at_target_count = len([
            row for row in hold_rows
            if row.get("position_action") == "AT_TARGET_WEIGHT"
        ])

        risk_off_hold_count = len([
            row for row in hold_rows
            if row.get("market_reaction_overlay") == "MARKET_REACTION_RISK_OFF_HOLD"
        ])

        market_ctx = market_reaction_context()
        regime = str(
            market_ctx.get("regime_label", "NEUTRAL")
        ).upper().strip()

        if st.session_state.get("risk_kill_switch", False):
            return "KILL_SWITCH_ACTIVE"

        if regime == "RISK_OFF":
            return "DEFENSIVE_RISK_OFF"

        if regime == "RISK_ON" and executable_count > 0:
            return "RISK_ON_PLAN_READY"

        if executable_count <= 0:
            if blocked_short_count:
                return "NO_TRADES_LONG_ONLY_FILTER"

            if at_target_count:
                return "NO_TRADES_AT_TARGET"

            if risk_off_hold_count:
                return "NO_TRADES_RISK_OFF"

            return "NO_EXECUTABLE_TRADES"

        return "BATCH_PLAN_READY"

    def check_single_signal(signal: Dict[str, Any]) -> Dict[str, Any]:
        signal = normalize_signal(signal)

        if st.session_state.get("risk_kill_switch", False):
            return {
                **signal,
                "risk_status": "BLOCKED",
                "risk_approved": False,
                "risk_reason": "KILL_SWITCH_ACTIVE",
                "risk_reducing": False,
                "position_action": "KILL_SWITCH",
                "position_before": None,
                "position_after": None,
                "gross_before": None,
                "gross_after": None,
                "executable": False,
            }

        approved = False
        reason = "RISK_ENGINE_MISSING"

        try:
            if risk_engine and hasattr(risk_engine, "check"):
                sync_market_reaction_to_risk_engine()
                check_result = risk_engine.check(signal)

                if isinstance(check_result, tuple):
                    approved = bool(check_result[0])
                    reason = check_result[1] if len(check_result) > 1 else ""

                elif isinstance(check_result, dict):
                    approved = bool(
                        check_result.get("approved")
                        or check_result.get("risk_approved")
                    )
                    reason = (
                        check_result.get("reason")
                        or check_result.get("risk_reason")
                        or ""
                    )

                else:
                    approved = bool(check_result)
                    reason = "APPROVED" if approved else "BLOCKED"

        except Exception as exc:
            approved = False
            reason = str(exc)

        risk_snapshot = safe_snapshot(risk_engine)

        last_check = (
            risk_snapshot.get("last_check", {})
            if isinstance(risk_snapshot, dict)
            else {}
        )

        execution_action = normalize_action(signal.get("execution_action"))

        executable = (
            bool(approved)
            and execution_action in ("BUY", "SELL")
        )

        return {
            **signal,
            "risk_status": "APPROVED" if approved else "BLOCKED",
            "risk_approved": bool(approved),
            "risk_reason": reason,
            "risk_reducing": bool(last_check.get("risk_reducing", False)),
            "position_action": last_check.get("position_action"),
            "position_before": last_check.get("position_before"),
            "position_after": last_check.get("position_after"),
            "gross_before": last_check.get("gross_before"),
            "gross_after": last_check.get("gross_after"),
            "executable": executable,
        }

    def build_risk_plan(signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        clear_scanner_warning()

        if not signals:
            signals = generate_signals()

        sync_market_reaction_to_risk_engine()
        sync_risk()

        normalized = [
            normalize_signal(signal)
            for signal in signals
        ]

        # =================================================
        # PORTFOLIO-AWARE LONG-ONLY + TARGET-WEIGHT FILTER
        # =================================================
        # Scanner is long-only.
        #
        # SELL:
        #   Allowed only when the portfolio already holds a long position.
        #
        # BUY:
        #   Allowed only when sizing says there is still room to buy.
        #   If qty <= 0, the position is already at/above target weight.
        #
        # This prevents:
        #   SELL + position 0 -> BLOCKED_OPEN_SHORT
        #   BUY repeatedly -> position keeps growing above target

        portfolio_positions = get_portfolio_positions()

        def portfolio_signed_qty(symbol: str) -> float:
            symbol = str(symbol or "").upper().strip()
            row = portfolio_positions.get(symbol, {})

            if isinstance(row, dict):
                return safe_float(
                    row.get("signed_qty", row.get("qty", 0.0)),
                    0.0,
                )

            return 0.0

        portfolio_filtered_rows = []
        trade_candidates = []

        for signal in normalized:
            signal = normalize_signal(signal)

            execution_action = normalize_action(
                signal.get("execution_action")
                or signal.get("action")
                or signal.get("side")
                or signal.get("scanner_action")
            )

            symbol = str(signal.get("symbol") or "").upper().strip()
            position_before = portfolio_signed_qty(symbol)
            planned_qty = safe_float(signal.get("qty"), 0.0)

            signal = {
                **signal,
                "symbol": symbol,
                "execution_action": execution_action,
                "action": execution_action,
                "side": execution_action,
                "qty": planned_qty,
                "position_before": position_before,
            }

            if execution_action == "BUY" and planned_qty <= 0:
                portfolio_filtered_rows.append({
                    **signal,
                    "scanner_action": "BUY",
                    "risk_action": "HOLD",
                    "execution_action": "HOLD",
                    "action": "HOLD",
                    "side": "HOLD",
                    "qty": 0.0,
                    "risk_status": "IGNORED",
                    "risk_approved": False,
                    "risk_reason": "AT_OR_ABOVE_TARGET_WEIGHT",
                    "risk_reducing": False,
                    "position_action": "AT_TARGET_WEIGHT",
                    "position_before": position_before,
                    "position_after": position_before,
                    "gross_before": None,
                    "gross_after": None,
                    "executable": False,
                    "portfolio_filter": True,
                })
                continue

            if execution_action == "SELL" and position_before <= 0:
                portfolio_filtered_rows.append({
                    **signal,
                    "scanner_action": "SELL",
                    "risk_action": "HOLD",
                    "execution_action": "HOLD",
                    "action": "HOLD",
                    "side": "HOLD",
                    "qty": 0.0,
                    "risk_status": "IGNORED",
                    "risk_approved": False,
                    "risk_reason": "PORTFOLIO_FILTER_NO_LONG_POSITION",
                    "risk_reducing": False,
                    "position_action": "BLOCKED_OPEN_SHORT",
                    "position_before": position_before,
                    "position_after": position_before,
                    "gross_before": None,
                    "gross_after": None,
                    "executable": False,
                    "portfolio_filter": True,
                })
                continue

            trade_candidates.append(signal)

        executable_signals = []

        for signal in trade_candidates:
            execution_action = normalize_action(
                signal.get("execution_action")
                or signal.get("action")
                or signal.get("side")
            )

            planned_qty = safe_float(signal.get("qty"), 0.0)

            if execution_action in ("BUY", "SELL") and planned_qty > 0:
                executable_signals.append({
                    **signal,
                    "execution_action": execution_action,
                    "action": execution_action,
                    "side": execution_action,
                    "qty": planned_qty,
                })

        hold_rows = [
            make_hold_row(signal)
            for signal in trade_candidates
            if (
                normalize_action(
                    signal.get("execution_action")
                    or signal.get("action")
                    or signal.get("side")
                ) not in ("BUY", "SELL")
                or safe_float(signal.get("qty"), 0.0) <= 0
            )
        ]

        hold_rows.extend(portfolio_filtered_rows)

        if st.session_state.get("risk_kill_switch", False):

            plan = [
                {
                    **signal,
                    "risk_status": "BLOCKED",
                    "risk_approved": False,
                    "risk_reason": "KILL_SWITCH_ACTIVE",
                    "risk_reducing": False,
                    "position_action": "KILL_SWITCH",
                    "position_before": signal.get("position_before"),
                    "position_after": signal.get("position_before"),
                    "gross_before": None,
                    "gross_after": None,
                    "executable": False,
                }
                for signal in executable_signals
            ]

            st.session_state["scanner_last_risk_plan"] = plan
            st.session_state["scanner_last_hold_rows"] = hold_rows
            st.session_state["scanner_last_status"] = scanner_status_label(
                plan,
                hold_rows,
            )

            return plan

        plan = []

        if (
            risk_engine
            and hasattr(risk_engine, "check_batch")
            and executable_signals
        ):

            try:
                sync_market_reaction_to_risk_engine()
                raw_batch_rows = risk_engine.check_batch(executable_signals)
                batch_rows = coerce_batch_rows(raw_batch_rows)

                if not batch_rows:
                    raise RuntimeError("check_batch returned no usable rows")

                for row in batch_rows:
                    row = normalize_signal(row)

                    approved = bool(
                        row.get("approved")
                        or row.get("risk_approved")
                    )

                    execution_action = normalize_action(
                        row.get("execution_action")
                        or row.get("risk_action")
                        or row.get("action")
                        or row.get("side")
                    )

                    planned_qty = safe_float(row.get("qty"), 0.0)

                    executable = (
                        approved
                        and execution_action in ("BUY", "SELL")
                        and planned_qty > 0
                    )

                    plan.append({
                        **row,
                        "scanner_action": row.get("scanner_action"),
                        "risk_action": execution_action,
                        "execution_action": execution_action,
                        "action": execution_action,
                        "side": execution_action,
                        "qty": planned_qty,
                        "risk_status": "APPROVED" if approved else "BLOCKED",
                        "risk_approved": approved,
                        "risk_reason": row.get("reason") or row.get("risk_reason"),
                        "risk_reducing": bool(row.get("risk_reducing")),
                        "position_action": row.get("position_action"),
                        "position_before": row.get("position_before"),
                        "position_after": row.get("position_after"),
                        "gross_before": row.get("gross_before"),
                        "gross_after": row.get("gross_after"),
                        "executable": executable,
                    })

            except Exception as exc:
                st.session_state["scanner_last_error"] = (
                    f"risk_engine.check_batch failed: {exc}"
                )

                plan = [
                    check_single_signal(signal)
                    for signal in executable_signals
                ]

        else:

            plan = [
                check_single_signal(signal)
                for signal in executable_signals
            ]

        st.session_state["scanner_last_risk_plan"] = plan
        st.session_state["scanner_last_hold_rows"] = hold_rows
        st.session_state["scanner_last_status"] = scanner_status_label(
            plan,
            hold_rows,
        )

        return plan
        
    # =====================================================
    # EXECUTION ENGINE
    # =====================================================

    def execute_plan(plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        clear_scanner_warning()

        plan = [
            row for row in plan
            if isinstance(row, dict)
        ] if isinstance(plan, list) else []

        if st.session_state.get("risk_kill_switch", False):
            blocked_count = len(plan)

            results = [{
                "timestamp": now(),
                "status": "BLOCKED",
                "reason": "KILL_SWITCH_ACTIVE",
                "blocked_count": blocked_count,
                "source": "scanner_execute_v35_3",
            }]

            st.session_state["scanner_last_execution_results"] = results
            st.session_state["scanner_last_status"] = (
                f"EXECUTION_BLOCKED_KILL_SWITCH_{blocked_count}_ROWS"
            )

            st.error("🛑 KILL SWITCH ACTIVE — scanner execution blocked.")
            return results

        if not plan:
            st.session_state["scanner_last_execution_results"] = []
            st.session_state["scanner_last_status"] = (
                "EXECUTION_SKIPPED_NO_APPROVED_ROWS"
            )
            return []

        sync_market_reaction_to_risk_engine()
        sync_risk()

        executable_rows = []

        for row in plan:
            execution_action = normalize_action(
                row.get("execution_action")
                or row.get("action")
                or row.get("side")
            )

            risk_approved = bool(row.get("risk_approved"))
            executable = bool(row.get("executable"))

            qty = safe_float(row.get("qty"), 0.0)
            price = safe_float(row.get("price"), 0.0)

            if (
                risk_approved
                and executable
                and execution_action in ("BUY", "SELL")
                and qty > 0
                and price > 0
            ):
                executable_rows.append({
                    **row,
                    "execution_action": execution_action,
                    "action": execution_action,
                    "side": execution_action,
                    "qty": qty,
                    "price": price,
                })

        if not executable_rows:
            results = [{
                "timestamp": now(),
                "status": "SKIPPED",
                "reason": "NO_EXECUTABLE_APPROVED_ROWS",
                "rows_received": len(plan),
                "source": "scanner_execute_v35_3",
            }]

            st.session_state["scanner_last_execution_results"] = results
            st.session_state["scanner_last_status"] = (
                "EXECUTION_SKIPPED_NO_EXECUTABLE_ROWS"
            )

            return results

        results = []

        if pipeline is None or not hasattr(pipeline, "execute"):
            results = [{
                "timestamp": now(),
                "status": "PIPELINE_MISSING",
                "reason": "pipeline.execute unavailable",
                "rows_received": len(plan),
                "executable_rows": len(executable_rows),
                "source": "scanner_execute_v35_3",
            }]

            st.session_state["scanner_last_execution_results"] = results
            st.session_state["scanner_last_status"] = (
                "EXECUTION_FAILED_PIPELINE_MISSING"
            )

            return results

        executed = 0
        skipped = 0
        failed = 0

        for row in executable_rows:
            execution_action = normalize_action(
                row.get("execution_action")
                or row.get("action")
                or row.get("side")
            )

            risk_approved = bool(row.get("risk_approved"))
            executable = bool(row.get("executable"))
            qty = safe_float(row.get("qty"), 0.0)
            price = safe_float(row.get("price"), 0.0)

            if not (
                risk_approved
                and executable
                and execution_action in ("BUY", "SELL")
                and qty > 0
                and price > 0
            ):
                skipped += 1

                results.append({
                    "timestamp": now(),
                    "symbol": row.get("symbol"),
                    "scanner_action": row.get("scanner_action"),
                    "risk_action": row.get("risk_action"),
                    "execution_action": execution_action,
                    "action": execution_action,
                    "qty": qty,
                    "price": price,
                    "status": "SKIPPED",
                    "reason": row.get("risk_reason") or "NOT_EXECUTABLE",
                    "risk_approved": risk_approved,
                    "position_action": row.get("position_action"),
                    "position_before": row.get("position_before"),
                    "position_after_expected": row.get("position_after"),
                    "source": row.get("source"),
                })
                continue

            signal = {
                "symbol": row.get("symbol"),
                "action": execution_action,
                "side": execution_action,
                "qty": qty,
                "price": price,
                "risk_approved": True,
                "scanner_action": row.get("scanner_action"),
                "risk_action": row.get("risk_action"),
                "execution_action": execution_action,
                "position_action": row.get("position_action"),
                "position_before": row.get("position_before"),
                "position_after": row.get("position_after"),
                "mode": st.session_state.get("mode", "SIM"),
                "source": "scanner_execute_v35_3",
            }

            try:
                raw_result = pipeline.execute(signal)

                normalized = normalize_execution_result(
                    raw_result,
                    {
                        **row,
                        "execution_action": execution_action,
                        "qty": qty,
                        "price": price,
                    },
                )

                status = str(
                    normalized.get("status", "")
                ).upper().strip()

                if status in (
                    "ERROR",
                    "REJECTED",
                    "BLOCKED",
                    "NO_RESULT",
                    "PIPELINE_MISSING",
                    "TIMEOUT",
                ):
                    failed += 1
                elif status == "SKIPPED":
                    skipped += 1
                else:
                    executed += 1

                results.append(normalized)

            except Exception as exc:
                failed += 1

                results.append({
                    "timestamp": now(),
                    "symbol": row.get("symbol"),
                    "scanner_action": row.get("scanner_action"),
                    "risk_action": row.get("risk_action"),
                    "execution_action": execution_action,
                    "action": execution_action,
                    "qty": qty,
                    "price": price,
                    "status": "ERROR",
                    "reason": str(exc),
                    "risk_approved": risk_approved,
                    "position_action": row.get("position_action"),
                    "position_before": row.get("position_before"),
                    "position_after_expected": row.get("position_after"),
                    "source": row.get("source"),
                })

        st.session_state["scanner_last_execution_results"] = results
        st.session_state["scanner_last_status"] = (
            f"EXECUTED_{executed}_SKIPPED_{skipped}_FAILED_{failed}"
        )

        sync_market_reaction_to_risk_engine()
        sync_risk()

        return results

    def normalize_execution_result(
        raw_result: Any,
        source_row: Dict[str, Any],
    ) -> Dict[str, Any]:
        source_row = source_row if isinstance(source_row, dict) else {}

        base = {
            "timestamp": now(),
            "symbol": source_row.get("symbol"),
            "scanner_action": source_row.get("scanner_action"),
            "risk_action": source_row.get("risk_action"),
            "execution_action": source_row.get("execution_action"),
            "action": source_row.get("execution_action"),
            "qty": source_row.get("qty"),
            "price": source_row.get("price"),
            "risk_approved": source_row.get("risk_approved"),
            "position_action": source_row.get("position_action"),
            "position_before": source_row.get("position_before"),
            "position_after_expected": source_row.get("position_after"),
            "source": source_row.get("source"),
        }

        if raw_result is None:
            return {
                **base,
                "status": "NO_RESULT",
                "reason": "pipeline.execute returned None",
            }

        if isinstance(raw_result, dict):
            status = str(
                raw_result.get("status")
                or raw_result.get("state")
                or raw_result.get("result")
                or "SUBMITTED"
            ).upper().strip()

            return {
                **base,
                **raw_result,
                "timestamp": raw_result.get("timestamp") or base["timestamp"],
                "symbol": raw_result.get("symbol") or base["symbol"],
                "scanner_action": (
                    raw_result.get("scanner_action")
                    or base["scanner_action"]
                ),
                "risk_action": (
                    raw_result.get("risk_action")
                    or base["risk_action"]
                ),
                "execution_action": (
                    raw_result.get("execution_action")
                    or raw_result.get("action")
                    or base["execution_action"]
                ),
                "action": raw_result.get("action") or base["action"],
                "qty": raw_result.get("qty") or base["qty"],
                "price": raw_result.get("price") or base["price"],
                "fill_price": (
                    raw_result.get("fill_price")
                    or raw_result.get("avg_fill_price")
                ),
                "status": status,
                "reason": (
                    raw_result.get("reason")
                    or raw_result.get("message")
                ),
                "risk_approved": raw_result.get(
                    "risk_approved",
                    base["risk_approved"],
                ),
                "position_action": (
                    raw_result.get("position_action")
                    or base["position_action"]
                ),
                "position_before": raw_result.get(
                    "position_before",
                    base["position_before"],
                ),
                "position_after_expected": raw_result.get(
                    "position_after_expected",
                    base["position_after_expected"],
                ),
                "lifecycle_stage": raw_result.get("lifecycle_stage"),
                "realized_delta": raw_result.get("realized_delta"),
                "order_id": raw_result.get("order_id"),
                "fill_id": raw_result.get("fill_id"),
                "source": raw_result.get("source") or base["source"],
            }

        return {
            **base,
            "status": "SUBMITTED",
            "reason": str(raw_result),
        }

    # =====================================================
    # TABLE CLEANERS
    # =====================================================

    def clean_plan_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [{
            "timestamp": row.get("timestamp"),
            "symbol": row.get("symbol"),
            "scanner_action": row.get("scanner_action"),
            "risk_action": row.get("risk_action"),
            "execution_action": row.get("execution_action"),
            "qty": row.get("qty"),
            "price": row.get("price"),
            "model_score": row.get("model_score"),
            "trend": row.get("trend"),
            "rs_score": row.get("rs_score"),
            "sizing_model": row.get("sizing_model"),
            "sizing_target_value": row.get("sizing_target_value"),
            "market_reaction_regime": row.get("market_reaction_regime"),
            "market_reaction_score": row.get("market_reaction_score"),
            "market_reaction_confidence": row.get("market_reaction_confidence"),
            "market_reaction_overlay": row.get("market_reaction_overlay"),
            "risk_status": row.get("risk_status"),
            "risk_reason": row.get("risk_reason"),
            "risk_reducing": row.get("risk_reducing"),
            "position_action": row.get("position_action"),
            "position_before": row.get("position_before"),
            "position_after": row.get("position_after"),
            "gross_before": row.get("gross_before"),
            "gross_after": row.get("gross_after"),
            "executable": row.get("executable"),
            "source": row.get("source"),
        } for row in rows]

    def clean_result_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        cleaned = []

        for row in rows:
            if not isinstance(row, dict):
                continue

            cleaned.append({
                "timestamp": row.get("timestamp"),
                "symbol": row.get("symbol"),
                "scanner_action": row.get("scanner_action"),
                "risk_action": row.get("risk_action"),
                "execution_action": row.get("execution_action"),
                "qty": row.get("qty"),
                "price": row.get("price"),
                "fill_price": row.get("fill_price"),
                "status": row.get("status"),
                "reason": row.get("reason"),
                "risk_approved": row.get("risk_approved"),
                "position_action": row.get("position_action"),
                "position_before": row.get("position_before"),
                "position_after_expected": row.get("position_after_expected"),
                "lifecycle_stage": row.get("lifecycle_stage"),
                "realized_delta": row.get("realized_delta"),
                "order_id": row.get("order_id"),
                "fill_id": row.get("fill_id"),
                "source": row.get("source"),
            })

        return cleaned

    # =====================================================
    # PAGE RENDER
    # =====================================================

    sync_market_reaction_to_risk_engine()
    sync_risk()
    sync_market_reaction_to_risk_engine()

    risk_snapshot = safe_snapshot(risk_engine)
    positions = get_portfolio_positions()

    def display_scanner_status(raw_status: Any) -> str:
        status = str(raw_status or "READY").upper().strip()

        if status.startswith("DEFENSIVE_RISK_OFF"):
            return "Risk-Off"

        if status.startswith("KILL_SWITCH"):
            return "Kill Switch"

        if status.startswith("EXECUTION_BLOCKED"):
            return "Execution Blocked"

        if status.startswith("EXECUTION_SKIPPED"):
            return "No Trades"

        if status.startswith("EXECUTED_"):
            return "Executed"

        if status.startswith("GENERATED_"):
            return "Signals Generated"

        if status.startswith("NO_EXECUTABLE"):
            return "No Trades"

        if status.startswith("BATCH_PLAN_READY"):
            return "Plan Ready"

        if status.startswith("CLEARED"):
            return "Cleared"

        if status.startswith("REFRESHED"):
            return "Refreshed"

        return status.title().replace("_", " ")

    scanner_status_raw = st.session_state.get(
        "scanner_last_status",
        "READY",
    )

    scanner_status_display = display_scanner_status(scanner_status_raw)
    market_ctx = market_reaction_context()

    st.subheader("System Status")

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    c1.metric("Scanner Status", scanner_status_display)
    c2.metric("Pipeline", "READY" if pipeline else "MISSING")
    c3.metric("Risk State", risk_snapshot.get("risk_state", "UNKNOWN"))
    c4.metric(
        "Gross Exposure",
        f"${safe_float(risk_snapshot.get('gross_exposure'), 0.0):,.2f}",
    )
    c5.metric(
        "Open Positions",
        (
            f"{risk_snapshot.get('open_positions', 0)} / "
            f"{risk_snapshot.get('max_open_positions', 0)}"
        ),
    )

    with c6:
        st.metric("Portfolio Positions", len(positions))

        with st.popover("Diagnostics"):
            st.write(
                {
                    "Market Reaction": {
                        "Regime": market_ctx["regime_label"],
                        "Score": market_ctx["score"],
                        "Confidence": market_ctx["confidence"],
                        "Event": market_ctx["event"],
                        "Playbook": market_ctx["playbook"],
                        "BUY Allowed": market_ctx["buy_allowed"],
                        "SELL Allowed": market_ctx["sell_allowed"],
                        "Execution Multiplier": market_ctx["execution_multiplier"],
                    },
                    "Position Sizing": {
                        "Sizing Model": "Equal Weight",
                        "Test Portfolio Value": SCANNER_TEST_PORTFOLIO_VALUE,
                        "Target Position %": SCANNER_TARGET_POSITION_PCT,
                        "Target Position Value": SCANNER_TARGET_POSITION_VALUE,
                        "Minimum Quantity": SCANNER_MIN_QTY,
                    },
                    "Raw Scanner Status": scanner_status_raw,
                }
            )

    last_error = st.session_state.get("scanner_last_error", "")

    if last_error:
        st.warning(f"Scanner warning: {last_error}")

    st.divider()
    
    # =====================================================
    # CONTROLS
    # =====================================================

    st.subheader("Scanner Controls")

    s1, s2, s3, s4 = st.columns(4)

    with s1:
        run_scan_btn = st.button(
            "Run Scanner",
            use_container_width=True,
            key="scanner_run_v35_3",
        )

    with s2:
        build_plan_btn = st.button(
            "Build Risk-Aware Plan",
            use_container_width=True,
            key="scanner_plan_v35_3",
        )

    with s3:
        refresh_btn = st.button(
            "Refresh",
            use_container_width=True,
            key="scanner_refresh_v35_3",
        )

    with s4:
        clear_btn = st.button(
            "Clear Scanner View",
            use_container_width=True,
            key="scanner_clear_v35_3",
        )

    if run_scan_btn:
        signals = generate_signals()
        build_risk_plan(signals)
        st.rerun()

    if build_plan_btn:
        signals = st.session_state.get("scanner_last_raw_signals", [])
        build_risk_plan(signals)
        st.rerun()

    if refresh_btn:
        sync_market_reaction_to_risk_engine()
        sync_risk()
        st.session_state["scanner_last_status"] = "REFRESHED"
        clear_scanner_warning()
        st.rerun()

    if clear_btn:
        st.session_state["scanner_last_raw_signals"] = []
        st.session_state["scanner_last_risk_plan"] = []
        st.session_state["scanner_last_hold_rows"] = []
        st.session_state["scanner_last_execution_results"] = []
        st.session_state["scanner_last_status"] = "CLEARED"
        clear_scanner_warning()
        st.rerun()

    # =====================================================
    # RAW SIGNALS
    # =====================================================

    st.subheader("Raw Scanner Signals")

    raw_signals = st.session_state.get(
        "scanner_last_raw_signals",
        [],
    )

    raw_signals = [
        row for row in raw_signals
        if isinstance(row, dict)
    ] if isinstance(raw_signals, list) else []

    if raw_signals:

        raw_df = pd.DataFrame(raw_signals)

        st.dataframe(
            raw_df,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info("No scanner signals yet. Click Run Scanner.")

    st.divider()

    # =====================================================
    # RISK-AWARE EXECUTION PLAN
    # =====================================================

    st.subheader("Risk-Aware Execution Plan")

    plan = st.session_state.get("scanner_last_risk_plan", [])
    hold_rows = st.session_state.get("scanner_last_hold_rows", [])

    plan_df = (
        pd.DataFrame(clean_plan_rows(plan))
        if plan
        else pd.DataFrame()
    )

    hold_df = (
        pd.DataFrame(clean_plan_rows(hold_rows))
        if hold_rows
        else pd.DataFrame()
    )

    executable_count = (
        int(plan_df["executable"].fillna(False).sum())
        if not plan_df.empty and "executable" in plan_df
        else 0
    )

    planned_count = len(plan_df)
    blocked_count = planned_count - executable_count
    hold_count = len(hold_df)

    blocked_open_short_count = 0
    at_target_count = 0
    risk_off_hold_count = 0

    if not hold_df.empty:

        if "position_action" in hold_df:
            blocked_open_short_count = int(
                (hold_df["position_action"] == "BLOCKED_OPEN_SHORT").sum()
            )
            at_target_count = int(
                (hold_df["position_action"] == "AT_TARGET_WEIGHT").sum()
            )

        if "market_reaction_overlay" in hold_df:
            risk_off_hold_count = int(
                (
                    hold_df["market_reaction_overlay"]
                    == "MARKET_REACTION_RISK_OFF_HOLD"
                ).sum()
            )

    p1, p2, p3, p4, p5 = st.columns(5)
    p1.metric("Executable", executable_count)
    p2.metric("Planned", planned_count)
    p3.metric("Hold / Ignored", hold_count)
    p4.metric("Blocked Shorts", blocked_open_short_count)
    p5.metric("Risk-Off Holds", risk_off_hold_count)

    if executable_count > 0:
        st.success(
            f"{executable_count} executable trade(s) approved by the risk engine."
        )

    elif hold_count > 0 or blocked_count > 0:
        st.info(
            "No executable trades generated. "
            f"{hold_count} row(s) were HOLD / ignored, "
            f"{blocked_open_short_count} SELL row(s) were blocked by long-only rules, "
            f"{at_target_count} BUY row(s) were already at target weight, "
            f"and {risk_off_hold_count} row(s) were held due to Risk-Off conditions."
        )

    else:
        st.info("No scanner plan built yet. Run Scanner, then Build Risk-Aware Plan.")

    if not plan_df.empty:
        with st.expander("Risk Engine Plan Details", expanded=False):
            st.dataframe(plan_df, use_container_width=True)

        if blocked_count:
            with st.expander("Blocked Risk Engine Rows", expanded=False):
                blocked_df = (
                    plan_df[plan_df["executable"] == False]
                    if "executable" in plan_df
                    else plan_df
                )
                st.dataframe(blocked_df, use_container_width=True)

    if not hold_df.empty:
        with st.expander("Ignored / Non-Executable Scanner Rows", expanded=False):
            st.dataframe(hold_df, use_container_width=True)

    st.divider()

    # =====================================================
    # EXECUTION CONTROLS
    # =====================================================

    current_mode = str(st.session_state.get("mode", "SIM")).upper().strip()
    is_live_mode = current_mode == "LIVE"

    plan = st.session_state.get("scanner_last_risk_plan", [])

    has_executable_rows = any(
        bool(row.get("executable"))
        and normalize_action(row.get("execution_action")) in ("BUY", "SELL")
        for row in plan
        if isinstance(row, dict)
    )

    if has_executable_rows:

        st.subheader("Execution Controls")

        if is_live_mode:
            st.error("🚨 LIVE TRADING MODE — REAL ORDERS CAN BE SENT")

        e1, e2 = st.columns([1, 3])

        with e1:
            confirm_execute = st.checkbox(
                "Confirm scanner execution",
                key="scanner_confirm_execute_v35_3",
            )

            live_ack = True
            live_phrase_ok = True

            if is_live_mode:
                live_ack = st.checkbox(
                    "I understand this sends LIVE broker orders",
                    key="scanner_live_ack_v35_3",
                )

                live_phrase = st.text_input(
                    "Type EXECUTE LIVE ORDERS to arm live execution",
                    key="scanner_live_phrase_v35_3",
                )

                live_phrase_ok = (
                    live_phrase.strip().upper()
                    == "EXECUTE LIVE ORDERS"
                )

                if confirm_execute and live_ack and live_phrase_ok:
                    st.error("🚨 LIVE TRADING ARMED")
                else:
                    st.warning("LIVE execution is locked.")

            execution_unlocked = (
                confirm_execute
                and live_ack
                and live_phrase_ok
            )

            execute_btn = st.button(
                "Execute Approved Signals Only",
                use_container_width=True,
                disabled=not execution_unlocked,
                key="scanner_execute_v35_3",
            )

        with e2:
            st.caption(
                "Only rows with risk_approved=True and execution_action BUY/SELL "
                "are routed to pipeline."
            )

            if is_live_mode:
                st.warning(
                    "LIVE mode requires checkbox confirmation and the exact typed "
                    "phrase before routing orders."
                )
            else:
                st.info(
                    "SIM mode active. Orders are simulated unless pipeline mode "
                    "says otherwise."
                )

        if execute_btn:

            if is_live_mode and not execution_unlocked:
                st.error(
                    "LIVE execution blocked. Required confirmations missing."
                )
                st.stop()

            results = execute_plan(
                st.session_state.get(
                    "scanner_last_risk_plan",
                    [],
                )
            )

            st.session_state[
                "scanner_last_execution_results"
            ] = results

            st.success(
                f"Scanner execution complete. Rows processed: {len(results)}"
            )

    # =====================================================
    # EXECUTION RESULTS
    # =====================================================

    results = st.session_state.get(
        "scanner_last_execution_results",
        [],
    )

    results = [
        row for row in results
        if isinstance(row, dict)
    ] if isinstance(results, list) else []

    if results:

        st.subheader("Last Execution Results")

        result_df = pd.DataFrame(
            clean_result_rows(results)
        )

        status_counts = {}

        if "status" in result_df:
            status_counts = (
                result_df["status"]
                .astype(str)
                .str.upper()
                .value_counts()
                .to_dict()
            )

        complete_count = status_counts.get("COMPLETE", 0)
        partial_count = status_counts.get("PARTIAL", 0)
        skipped_count = status_counts.get("SKIPPED", 0)
        blocked_count = status_counts.get("BLOCKED", 0)
        rejected_count = status_counts.get("REJECTED", 0)
        error_count = status_counts.get("ERROR", 0)
        timeout_count = status_counts.get("TIMEOUT", 0)

        failed_count = (
            rejected_count
            + error_count
            + timeout_count
        )

        r1, r2, r3, r4, r5 = st.columns(5)
        r1.metric("Complete", complete_count)
        r2.metric("Partial", partial_count)
        r3.metric("Skipped", skipped_count)
        r4.metric("Blocked", blocked_count)
        r5.metric("Failed", failed_count)

        if complete_count or partial_count:
            st.success(
                f"{complete_count + partial_count} order result(s) completed."
            )

        elif skipped_count or blocked_count:
            st.info(
                f"{skipped_count + blocked_count} execution row(s) were skipped or blocked."
            )

        elif failed_count:
            st.error(
                f"{failed_count} execution row(s) failed."
            )

        with st.expander("Execution Result Details", expanded=False):
            st.dataframe(
                result_df,
                use_container_width=True,
            )

        st.divider()

    # =====================================================
    # RISK SNAPSHOT
    # =====================================================

    st.subheader("Risk Snapshot")

    sync_market_reaction_to_risk_engine()
    risk_snapshot = safe_snapshot(risk_engine)

    if risk_snapshot:

        risk_state = str(
            risk_snapshot.get("risk_state", "UNKNOWN")
        )

        risk_reason = str(
            risk_snapshot.get("risk_state_reason", "")
        )

        market_regime = str(
            risk_snapshot.get("market_reaction_regime", "UNKNOWN")
        )

        market_score = safe_float(
            risk_snapshot.get("market_reaction_score"),
            0.0,
        )

        market_confidence = safe_float(
            risk_snapshot.get("market_reaction_confidence"),
            0.0,
        )

        gross_exposure = safe_float(
            risk_snapshot.get("gross_exposure"),
            0.0,
        )

        open_positions = int(
            safe_float(
                risk_snapshot.get("open_positions"),
                0.0,
            )
        )

        max_open_positions = int(
            safe_float(
                risk_snapshot.get("max_open_positions"),
                0.0,
            )
        )

        daily_trades = int(
            safe_float(
                risk_snapshot.get("daily_trades"),
                0.0,
            )
        )

        max_daily_trades = int(
            safe_float(
                risk_snapshot.get("max_daily_trades"),
                0.0,
            )
        )

        r1, r2, r3, r4, r5, r6 = st.columns(6)

        r1.metric("Risk State", risk_state)
        r2.metric("Regime", market_regime)
        r3.metric("Exposure", f"${gross_exposure:,.0f}")
        r4.metric(
            "Positions",
            f"{open_positions}/{max_open_positions}",
        )
        r5.metric("Score", f"{market_score:.0f}")
        r6.metric("Confidence", f"{market_confidence:.0f}")

        st.caption(
            (
                f"Reason: {risk_reason} · "
                f"Daily Trades: {daily_trades}/{max_daily_trades}"
            )
            if risk_reason
            else f"Daily Trades: {daily_trades}/{max_daily_trades}"
        )

        diagnostics_available = any(
            key in risk_snapshot
            for key in (
                "positions",
                "last_prices",
                "last_check",
                "last_sync",
                "last_batch_check",
            )
        )

        if diagnostics_available:
            with st.popover("Diagnostics"):
                diagnostic_keys = [
                    "positions",
                    "last_prices",
                    "last_check",
                    "last_sync",
                    "last_batch_check",
                ]

                diagnostics = {
                    key: risk_snapshot.get(key)
                    for key in diagnostic_keys
                    if key in risk_snapshot
                }

                st.json(diagnostics)

    else:
        st.info("No risk snapshot available.")

    st.divider()

    # =====================================================
    # PORTFOLIO POSITIONS
    # =====================================================

    positions = get_portfolio_positions()

    if positions:

        positions_df = pd.DataFrame(positions).T

        for col in positions_df.columns:
            if positions_df[col].dtype == "object":
                positions_df[col] = (
                    positions_df[col]
                    .astype(str)
                )

        with st.expander(
    f"Portfolio Positions ({len(positions_df)})",
    expanded=False,
):
            st.dataframe(
                positions_df,
                use_container_width=True,
            )

    else:
        st.info("No portfolio positions.")