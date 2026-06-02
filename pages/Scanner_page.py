# =========================================================
# 📡 JFBP SCANNER PAGE v35.0
# RESEARCH-MODEL SIGNAL TRUTH
# NO FORCED FALLBACK BUY/SELL SIGNALS
# =========================================================

from __future__ import annotations

from datetime import datetime, timezone
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
        if not isinstance(meta, dict):
            meta = {}

        regime = meta.get("regime", [])

        return {
            "symbol": symbol,
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
        )

    @st.cache_data(ttl=300)
    def load_benchmark_data():
        return yf.download(
            "SPY",
            period="6mo",
            interval="1d",
            progress=False,
            auto_adjust=False,
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

    def research_model_signal(symbol: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        symbol = str(symbol or "").upper().strip()
        meta = normalize_meta(symbol, meta)

        try:
            df = load_symbol_data(symbol)
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

            if close_col is None or bench_close_col is None:
                raise RuntimeError("Missing required close column")

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

            df = df.join(benchmark[["Benchmark"]], how="inner")
            df = df.dropna(subset=["Open", "High", "Low", "Close", "Benchmark"])

            if len(df) < 60:
                raise RuntimeError("Not enough historical data")

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
                raise RuntimeError("Not enough clean indicator data")

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
                "data_symbol": symbol,
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
                "source": "research_model_scanner_v35_0",
                "mode": st.session_state.get("mode", "SIM"),
            }

        except Exception as exc:
            price = get_price(symbol)

            return {
                "timestamp": now(),
                "symbol": symbol,
                "data_symbol": symbol,
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
                "reason": str(exc),
                "source": "research_model_scanner_v35_0_error_safe",
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

    def sync_risk():
        try:
            if portfolio_engine and risk_engine and hasattr(risk_engine, "sync_positions"):
                positions = get_portfolio_positions()
                try:
                    risk_engine.sync_positions(positions, historical=True)
                except TypeError:
                    risk_engine.sync_positions(positions)
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

        symbol = str(row.get("symbol") or "").upper().strip()

        scanner_action = normalize_action(
            row.get("scanner_action")
            or row.get("action")
            or row.get("signal")
            or row.get("side")
        )

        price = safe_float(row.get("price"), get_price(symbol))
        qty = safe_qty(row.get("qty"), 1.0)

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
            "source": row.get("source") or "research_model_scanner_v35_0",
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

        sync_risk()

        normalized = [
            normalize_signal(signal)
            for signal in signals
        ]

        executable_signals = [
            signal
            for signal in normalized
            if signal.get("execution_action") in ("BUY", "SELL")
        ]

        hold_rows = [
            make_hold_row(signal)
            for signal in normalized
            if signal.get("execution_action") not in ("BUY", "SELL")
        ]

        if st.session_state.get("risk_kill_switch", False):

            plan = [
                {
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
                for signal in executable_signals
            ]

            st.session_state["scanner_last_risk_plan"] = plan
            st.session_state["scanner_last_hold_rows"] = hold_rows
            st.session_state["scanner_last_status"] = (
                f"KILL_SWITCH_BLOCKED_{len(plan)}_ROWS"
            )

            return plan

        plan = []

        if (
            risk_engine
            and hasattr(risk_engine, "check_batch")
            and executable_signals
        ):

            try:
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
                    )

                    executable = (
                        approved
                        and execution_action in ("BUY", "SELL")
                    )

                    plan.append({
                        **row,
                        "scanner_action": row.get("scanner_action"),
                        "risk_action": execution_action,
                        "execution_action": execution_action,
                        "action": execution_action,
                        "side": execution_action,
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
        st.session_state["scanner_last_status"] = (
            f"BATCH_PLAN_BUILT_{len(plan)}_EXECUTABLE_ROWS"
        )

        return plan

    # =====================================================
    # EXECUTION ENGINE
    # =====================================================

    def execute_plan(plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        clear_scanner_warning()

        if st.session_state.get("risk_kill_switch", False):
            blocked_count = len(plan) if isinstance(plan, list) else 0

            results = [{
                "timestamp": now(),
                "status": "BLOCKED",
                "reason": "KILL_SWITCH_ACTIVE",
                "blocked_count": blocked_count,
                "source": "scanner_execute_v35_0",
            }]

            st.session_state["scanner_last_execution_results"] = results
            st.session_state["scanner_last_status"] = (
                f"EXECUTED_0_BLOCKED_{blocked_count}_FAILED_0"
            )

            st.error("🛑 KILL SWITCH ACTIVE — scanner execution blocked.")
            return results

        if not plan:
            plan = build_risk_plan(generate_signals())

        sync_risk()

        results = []

        if pipeline is None or not hasattr(pipeline, "execute"):
            results = [{
                "timestamp": now(),
                "status": "PIPELINE_MISSING",
                "reason": "pipeline.execute unavailable",
            }]
            st.session_state["scanner_last_execution_results"] = results
            return results

        executed = 0
        skipped = 0
        failed = 0

        for row in plan:
            execution_action = normalize_action(
                row.get("execution_action")
            )

            risk_approved = bool(
                row.get("risk_approved")
            )

            executable = (
                risk_approved
                and execution_action in ("BUY", "SELL")
            )

            if not executable:
                skipped += 1

                results.append({
                    "timestamp": now(),
                    "symbol": row.get("symbol"),
                    "scanner_action": row.get("scanner_action"),
                    "risk_action": row.get("risk_action"),
                    "execution_action": execution_action,
                    "action": execution_action,
                    "qty": row.get("qty"),
                    "price": row.get("price"),
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
                "qty": row.get("qty"),
                "price": row.get("price"),
                "mode": st.session_state.get("mode", "SIM"),
                "source": "scanner_execute_v35_0",
            }

            try:
                raw_result = pipeline.execute(signal)

                normalized = normalize_execution_result(
                    raw_result,
                    {
                        **row,
                        "execution_action": execution_action,
                    }
                )

                if normalized["status"] in (
                    "ERROR",
                    "REJECTED",
                    "BLOCKED",
                    "NO_RESULT",
                    "PIPELINE_MISSING",
                ):
                    failed += 1
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
                    "qty": row.get("qty"),
                    "price": row.get("price"),
                    "status": "ERROR",
                    "reason": str(exc),
                    "risk_approved": risk_approved,
                    "source": row.get("source"),
                })

        st.session_state["scanner_last_execution_results"] = results
        st.session_state["scanner_last_status"] = (
            f"EXECUTED_{executed}_SKIPPED_{skipped}_FAILED_{failed}"
        )

        sync_risk()

        return results

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

    sync_risk()
    risk_snapshot = safe_snapshot(risk_engine)
    positions = get_portfolio_positions()

    st.subheader("System Status")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Scanner Status", st.session_state.get("scanner_last_status"))
    c2.metric("Pipeline", "READY" if pipeline else "MISSING")
    c3.metric("Risk State", risk_snapshot.get("risk_state", "UNKNOWN"))
    c4.metric("Gross Exposure", f"${float(risk_snapshot.get('gross_exposure', 0)):,.2f}")
    c5.metric(
        "Open Positions",
        f"{risk_snapshot.get('open_positions', 0)} / {risk_snapshot.get('max_open_positions', 0)}",
    )
    c6.metric("Portfolio Positions", len(positions))

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
            key="scanner_run_v35_0",
        )

    with s2:
        build_plan_btn = st.button(
            "Build Risk-Aware Plan",
            use_container_width=True,
            key="scanner_plan_v35_0",
        )

    with s3:
        refresh_btn = st.button(
            "Refresh",
            use_container_width=True,
            key="scanner_refresh_v35_0",
        )

    with s4:
        clear_btn = st.button(
            "Clear Scanner View",
            use_container_width=True,
            key="scanner_clear_v35_0",
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
    raw_signals = st.session_state.get("scanner_last_raw_signals", [])

    if raw_signals:
        st.dataframe(pd.DataFrame(raw_signals), use_container_width=True)
    else:
        st.info("No scanner signals yet. Click Run Scanner.")

    st.divider()

    # =====================================================
    # NON-EXECUTABLE SCANNER ROWS
    # =====================================================

    hold_rows = st.session_state.get("scanner_last_hold_rows", [])

    with st.expander("Ignored / Non-Executable Scanner Rows", expanded=False):
        if hold_rows:
            st.dataframe(pd.DataFrame(clean_plan_rows(hold_rows)), use_container_width=True)
        else:
            st.info("No ignored HOLD / NO TRADE rows.")

    st.divider()

    # =====================================================
    # RISK-AWARE EXECUTION PLAN
    # =====================================================

    st.subheader("Risk-Aware Execution Plan")

    plan = st.session_state.get("scanner_last_risk_plan", [])

    if plan:
        plan_df = pd.DataFrame(clean_plan_rows(plan))
        st.dataframe(plan_df, use_container_width=True)

        executable_count = (
            int(plan_df["executable"].fillna(False).sum())
            if "executable" in plan_df
            else 0
        )
        blocked_count = len(plan_df) - executable_count

        p1, p2, p3 = st.columns(3)
        p1.metric("Executable", executable_count)
        p2.metric("Blocked", blocked_count)
        p3.metric("Planned Rows", len(plan_df))

        if blocked_count:
            st.warning("Some executable scanner signals are blocked by risk.")
            st.dataframe(
                plan_df[plan_df["executable"] == False],
                use_container_width=True,
            )
        else:
            st.success("All planned scanner signals are executable.")
    else:
        st.info("No risk-aware plan yet.")

    st.divider()

    # =====================================================
    # EXECUTION CONTROLS
    # =====================================================

    st.subheader("Execution Controls")

    current_mode = str(st.session_state.get("mode", "SIM")).upper().strip()
    is_live_mode = current_mode == "LIVE"

    if is_live_mode:
        st.error("🚨 LIVE TRADING MODE — REAL ORDERS CAN BE SENT")

    e1, e2 = st.columns([1, 3])

    with e1:
        confirm_execute = st.checkbox(
            "Confirm scanner execution",
            key="scanner_confirm_execute_v35_0",
        )

        live_ack = True
        live_phrase_ok = True

        if is_live_mode:
            live_ack = st.checkbox(
                "I understand this sends LIVE broker orders",
                key="scanner_live_ack_v35_0",
            )

            live_phrase = st.text_input(
                "Type EXECUTE LIVE ORDERS to arm live execution",
                key="scanner_live_phrase_v35_0",
            )

            live_phrase_ok = (
                live_phrase.strip().upper() == "EXECUTE LIVE ORDERS"
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
            key="scanner_execute_v35_0",
        )

    with e2:
        st.caption(
            "Only rows with risk_approved=True and execution_action BUY/SELL are routed to pipeline."
        )

        if is_live_mode:
            st.warning(
                "LIVE mode requires checkbox confirmation and the exact typed phrase before routing orders."
            )
        else:
            st.info("SIM mode active. Orders are simulated unless pipeline mode says otherwise.")

    if execute_btn:
        if is_live_mode and not execution_unlocked:
            st.error("LIVE execution blocked. Required confirmations missing.")
            st.stop()

        results = execute_plan(
            st.session_state.get("scanner_last_risk_plan", [])
        )

        st.success(
            f"Scanner execution complete. Rows processed: {len(results)}"
        )

        st.rerun()

    # =====================================================
    # EXECUTION RESULTS
    # =====================================================

    st.subheader("Last Execution Results")

    results = st.session_state.get("scanner_last_execution_results", [])

    if results:
        st.dataframe(
            pd.DataFrame(clean_result_rows(results)),
            use_container_width=True,
        )
    else:
        st.info("No scanner execution results yet.")

    st.divider()

    # =====================================================
    # RISK SNAPSHOT
    # =====================================================

    st.subheader("Risk Snapshot")
    risk_snapshot = safe_snapshot(risk_engine)

    if risk_snapshot:

        risk_snapshot_df = pd.DataFrame(
            list(risk_snapshot.items()),
            columns=["Metric", "Value"],
        )

        risk_snapshot_df["Metric"] = (
            risk_snapshot_df["Metric"]
            .astype(str)
        )

        risk_snapshot_df["Value"] = (
            risk_snapshot_df["Value"]
            .astype(str)
        )

        st.dataframe(
            risk_snapshot_df,
            width="stretch",
        )

    else:
        st.info("No risk snapshot available.")

    st.divider()

    # =====================================================
    # PORTFOLIO POSITIONS
    # =====================================================

    st.subheader("Portfolio Positions")
    positions = get_portfolio_positions()

    if positions:

        positions_df = pd.DataFrame(positions).T

        for col in positions_df.columns:
            if positions_df[col].dtype == "object":
                positions_df[col] = (
                    positions_df[col]
                    .astype(str)
                )

        st.dataframe(
            positions_df,
            width="stretch",
        )

    else:
        st.info("No portfolio positions.")