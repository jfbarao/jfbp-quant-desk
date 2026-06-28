# =========================================================
# 📊 JFBP PORTFOLIO PAGE
# COMMANDER PORTFOLIO CENTER
# RESPONSIVE + COMPACT 70/30 LAYOUT + TABBED OPERATIONS
# LIVE MODE USES BROKER POSITIONS ONLY
# =========================================================

from __future__ import annotations

import streamlit as st
import pandas as pd
import html
import time
from datetime import datetime

from core.bootstrap import init_core
from analytics.performance import PerformanceAnalyzer
from core.responsive import inject_responsive_css as jfbp_inject_responsive_css
from core.responsive import columns as jfbp_columns
from core.ui_cards import inject_card_css as jfbp_inject_card_css
from core.ui_cards import metric_card as jfbp_metric_card
from core.ui_cards import hero_card as jfbp_hero_card
from core.ui_cards import score_row as jfbp_score_row


# =========================================================
# HELPERS
# =========================================================

def _safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _normalize_position_row(pos) -> dict | None:

    if pos is None:
        return None

    if isinstance(pos, dict):

        contract = pos.get("contract")

        symbol = (
            pos.get("symbol")
            or pos.get("ticker")
            or pos.get("contract_symbol")
        )

        if not symbol and contract is not None:
            symbol = getattr(contract, "symbol", None)

        qty = (
            pos.get("signed_qty")
            or pos.get("position")
            or pos.get("qty")
            or pos.get("quantity")
            or pos.get("shares")
            or 0
        )

        avg_price = (
            pos.get("avg_cost")
            or pos.get("avgCost")
            or pos.get("average_cost")
            or pos.get("avgPrice")
            or pos.get("avg_price")
            or 0
        )

        last_price = (
            pos.get("marketPrice")
            or pos.get("market_price")
            or pos.get("last_price")
            or pos.get("last")
            or pos.get("price")
            or 0
        )

        market_value = (
            pos.get("marketValue")
            or pos.get("market_value")
            or pos.get("position_value")
            or 0
        )

        realized_pnl = (
            pos.get("realized_pnl")
            or pos.get("realized")
            or 0
        )

    else:

        contract = getattr(pos, "contract", None)

        symbol = (
            getattr(pos, "symbol", None)
            or getattr(contract, "symbol", None)
        )

        qty = (
            getattr(pos, "signed_qty", None)
            or getattr(pos, "position", None)
            or getattr(pos, "qty", None)
            or getattr(pos, "quantity", None)
            or 0
        )

        avg_price = (
            getattr(pos, "avgCost", None)
            or getattr(pos, "avg_cost", None)
            or getattr(pos, "average_cost", None)
            or getattr(pos, "avgPrice", None)
            or getattr(pos, "avg_price", None)
            or 0
        )

        last_price = (
            getattr(pos, "marketPrice", None)
            or getattr(pos, "market_price", None)
            or getattr(pos, "last_price", None)
            or getattr(pos, "last", None)
            or getattr(pos, "price", None)
            or 0
        )

        market_value = (
            getattr(pos, "marketValue", None)
            or getattr(pos, "market_value", None)
            or getattr(pos, "position_value", None)
            or 0
        )

        realized_pnl = (
            getattr(pos, "realized_pnl", None)
            or getattr(pos, "realized", None)
            or 0
        )

    if not symbol:
        return None

    qty = _safe_float(qty)
    avg_price = _safe_float(avg_price)
    last_price = _safe_float(last_price)
    market_value = _safe_float(market_value)
    realized_pnl = _safe_float(realized_pnl)

    if abs(qty) <= 0:
        return None

    symbol = str(symbol).upper().strip()

    if last_price <= 0 and market_value > 0 and abs(qty) > 0:
        last_price = abs(market_value / qty)

    if last_price <= 0:
        last_price = avg_price

    if market_value > 0:
        position_value = abs(market_value)
    else:
        position_value = abs(qty) * last_price

    cost_basis = abs(qty) * avg_price

    if qty > 0:
        unrealized_pnl = position_value - cost_basis
    else:
        unrealized_pnl = cost_basis - position_value

    return {
        "symbol": symbol,
        "side": "LONG" if qty > 0 else "SHORT",
        "qty": abs(qty),
        "signed_qty": qty,
        "avg_price": avg_price,
        "last_price": last_price,
        "position_value": position_value,
        "unrealized_pnl": unrealized_pnl,
        "realized_pnl": realized_pnl,
        "total_pnl": unrealized_pnl + realized_pnl,
    }


def _normalize_positions(raw_positions) -> dict:

    if raw_positions is None:
        return {}

    if isinstance(raw_positions, pd.DataFrame):
        raw_positions = raw_positions.to_dict("records")

    elif isinstance(raw_positions, dict):

        if all(isinstance(v, dict) for v in raw_positions.values()):
            raw_positions = list(raw_positions.values())
        else:
            raw_positions = [raw_positions]

    elif not isinstance(raw_positions, (list, tuple, set)):
        raw_positions = [raw_positions]

    normalized = {}

    for pos in list(raw_positions):

        row = _normalize_position_row(pos)

        if row is None:
            continue

        normalized[row["symbol"]] = row

    return normalized


def _pull_portfolio_positions(portfolio_engine) -> dict:

    if portfolio_engine is None:
        return {}

    for method_name in (
        "get_all_positions",
        "positions_snapshot",
        "open_positions",
        "snapshot",
    ):
        if hasattr(portfolio_engine, method_name):
            try:
                candidate = getattr(portfolio_engine, method_name)

                if callable(candidate):
                    candidate = candidate()

                positions = _normalize_positions(candidate)

                if positions:
                    return positions

            except Exception:
                continue

    if hasattr(portfolio_engine, "positions"):
        try:
            candidate = portfolio_engine.positions

            if callable(candidate):
                candidate = candidate()

            positions = _normalize_positions(candidate)

            if positions:
                return positions

        except Exception:
            pass

    return {}


def _pull_gateway_positions(gateway) -> dict:

    if gateway is None:
        return {}

    for method_name in (
        "get_positions",
        "positions",
        "positions_snapshot",
        "broker_positions",
        "broker_positions_snapshot",
        "positions_cache",
    ):
        if hasattr(gateway, method_name):
            try:
                candidate = getattr(gateway, method_name)

                if callable(candidate):
                    candidate = candidate()

                positions = _normalize_positions(candidate)

                if positions:
                    return positions

            except Exception:
                continue

    return {}


def _get_live_price(symbol: str, gateway=None, market=None) -> float:

    symbol = str(symbol).upper().strip()

    if not symbol:
        return 0.0



    # -----------------------------------------------------
    # Gateway price methods
    # -----------------------------------------------------

    if gateway is not None:

        for method_name in (
            "get_price",
            "get_quote",
            "latest_price",
            "get_last_price",
            "last_price",
            "market_price",
        ):
            if hasattr(gateway, method_name):
                try:
                    value = _safe_float(
                        getattr(gateway, method_name)(symbol)
                    )
                    if value > 0:
                        return value
                except Exception:
                    pass

        try:
            quotes = getattr(gateway, "last_quotes", {})
            quote = quotes.get(symbol)

            if isinstance(quote, dict):
                for key in ("price", "last", "mark", "close", "bid", "ask"):
                    value = _safe_float(quote.get(key))
                    if value > 0:
                        return value
        except Exception:
            pass

        try:
            df = getattr(gateway, "last_quotes_df", None)

            if df is not None and not df.empty and "symbol" in df.columns:
                rows = df[df["symbol"].astype(str).str.upper() == symbol]

                if not rows.empty:
                    for key in ("price", "last", "mark", "close", "bid", "ask"):
                        if key in rows.columns:
                            value = _safe_float(rows.iloc[-1][key])
                            if value > 0:
                                return value
        except Exception:
            pass

    # -----------------------------------------------------
    # Market hub
    # -----------------------------------------------------

    if market is not None:

        for method_name in (
            "get_price",
            "latest_price",
            "get_last_price",
            "last_price",
            "market_price",
        ):
            if hasattr(market, method_name):
                try:
                    value = _safe_float(
                        getattr(market, method_name)(symbol)
                    )
                    if value > 0:
                        return value
                except Exception:
                    pass

        if hasattr(market, "snapshot"):
            try:
                snapshot = market.snapshot()

                if isinstance(snapshot, dict):
                    row = snapshot.get(symbol)

                    if isinstance(row, dict):
                        for key in ("price", "last", "mark", "close", "bid", "ask"):
                            value = _safe_float(row.get(key))
                            if value > 0:
                                return value
            except Exception:
                pass

    return 0.0


def _apply_live_marks(
    positions: dict,
    gateway=None,
    market=None,
) -> dict:

    if not positions:
        return positions

    broker_positions = _pull_gateway_positions(gateway)

    marked = {}

    for symbol, row in positions.items():

        if not isinstance(row, dict):
            continue

        symbol = str(
            row.get("symbol") or symbol
        ).upper().strip()

        if not symbol:
            continue

        broker_row = broker_positions.get(symbol, {})

        qty = _safe_float(
            broker_row.get("signed_qty")
            or broker_row.get("qty")
            or row.get("signed_qty")
            or row.get("qty")
        )

        avg_price = _safe_float(
            broker_row.get("avg_price")
            or broker_row.get("avg_cost")
            or broker_row.get("average_cost")
            or row.get("avg_price")
        )

        if avg_price <= 0:
            avg_price = _safe_float(row.get("avg_price"))

        last_price = _get_live_price(
            symbol=symbol,
            gateway=gateway,
            market=market,
        )

        if last_price <= 0:
            last_price = _safe_float(
                broker_row.get("last_price")
                or row.get("last_price")
                or avg_price
            )

        if abs(qty) <= 0:
            continue

        position_value = abs(qty) * last_price
        cost_basis = abs(qty) * avg_price

        if qty > 0:
            unrealized_pnl = position_value - cost_basis
        else:
            unrealized_pnl = cost_basis - position_value

        realized_pnl = _safe_float(
            row.get("realized_pnl")
        )

        marked[symbol] = {
            **row,
            "symbol": symbol,
            "side": "LONG" if qty > 0 else "SHORT",
            "qty": abs(qty),
            "signed_qty": qty,
            "avg_price": avg_price,
            "last_price": last_price,
            "position_value": position_value,
            "unrealized_pnl": unrealized_pnl,
            "realized_pnl": realized_pnl,
            "total_pnl": unrealized_pnl + realized_pnl,
        }

    return marked


def _build_exposure(positions: dict) -> dict:

    long_exposure = 0.0
    short_exposure = 0.0
    unrealized_pnl = 0.0
    realized_pnl = 0.0

    for row in positions.values():

        signed_qty = _safe_float(row.get("signed_qty"))
        value = _safe_float(row.get("position_value"))

        unrealized_pnl += _safe_float(row.get("unrealized_pnl"))
        realized_pnl += _safe_float(row.get("realized_pnl"))

        if signed_qty >= 0:
            long_exposure += abs(value)
        else:
            short_exposure += abs(value)

    return {
        "positions": len(positions),
        "gross_exposure": long_exposure + short_exposure,
        "long_exposure": long_exposure,
        "short_exposure": short_exposure,
        "net_exposure": long_exposure - short_exposure,
        "unrealized_pnl": unrealized_pnl,
        "realized_pnl": realized_pnl,
        "total_pnl": unrealized_pnl + realized_pnl,
    }


def _pull_ledger(portfolio_engine) -> list:

    if portfolio_engine is None:
        return []

    if hasattr(portfolio_engine, "ledger_snapshot"):
        try:
            ledger = portfolio_engine.ledger_snapshot()

            if isinstance(ledger, (list, tuple)):
                return list(ledger)

        except Exception:
            return []

    if hasattr(portfolio_engine, "ledger"):
        try:
            ledger = portfolio_engine.ledger

            if isinstance(ledger, (list, tuple)):
                return list(ledger)

        except Exception:
            return []

    return []


def _current_saas_user_id() -> str:
    saas_user = st.session_state.get("saas_user")
    user_id = getattr(saas_user, "user_id", "") if saas_user is not None else ""
    return str(user_id or "").strip()


def _ensure_portfolio_loaded_for_user(portfolio_engine, user_id: str) -> dict:
    if portfolio_engine is None or not user_id:
        st.session_state["portfolio_supabase_loaded"] = False
        st.session_state["portfolio_supabase_load_status"] = "SKIPPED"
        return {"status": "SKIPPED", "reason": "missing_engine_or_user"}

    if not hasattr(portfolio_engine, "load_positions_from_supabase"):
        st.session_state["portfolio_supabase_loaded"] = False
        st.session_state["portfolio_supabase_load_status"] = "SKIPPED"
        return {"status": "SKIPPED", "reason": "load_positions_from_supabase unavailable"}

    loaded_user = str(st.session_state.get("portfolio_supabase_loaded_user_id") or "")
    if loaded_user == user_id:
        st.session_state.setdefault("portfolio_supabase_loaded", True)
        st.session_state["portfolio_supabase_load_status"] = "SKIPPED"
        return {"status": "SKIPPED", "reason": "already_loaded_this_user"}

    try:
        report = portfolio_engine.load_positions_from_supabase(user_id)
        st.session_state["portfolio_supabase_loaded_user_id"] = user_id
        st.session_state["portfolio_supabase_loaded"] = True
        st.session_state["portfolio_supabase_load_status"] = str(report.get("status") or "OK") if isinstance(report, dict) else "OK"
        st.session_state["portfolio_supabase_load_report"] = report
        st.session_state["portfolio_supabase_load_error"] = ""
        return report if isinstance(report, dict) else {"status": "OK"}
    except Exception as exc:
        st.session_state["portfolio_supabase_loaded"] = False
        st.session_state["portfolio_supabase_load_status"] = "ERROR"
        st.session_state["portfolio_supabase_load_error"] = str(exc)
        return {"status": "ERROR", "reason": str(exc)}


def _positions_signature(positions: dict) -> str:
    rows = []
    for symbol in sorted((positions or {}).keys()):
        row = positions.get(symbol) or {}
        rows.append(
            (
                str(symbol),
                round(_safe_float(row.get("signed_qty")), 8),
                round(_safe_float(row.get("avg_price")), 8),
                round(_safe_float(row.get("realized_pnl")), 8),
            )
        )
    return str(rows)


def _persist_portfolio_for_user(portfolio_engine, user_id: str, positions: dict) -> dict:
    if portfolio_engine is None or not user_id:
        st.session_state["portfolio_supabase_saved"] = False
        st.session_state["portfolio_supabase_save_status"] = "SKIPPED"
        return {"status": "SKIPPED", "reason": "missing_engine_or_user"}

    if not hasattr(portfolio_engine, "persist_all_positions"):
        st.session_state["portfolio_supabase_saved"] = False
        st.session_state["portfolio_supabase_save_status"] = "SKIPPED"
        return {"status": "SKIPPED", "reason": "persist_all_positions unavailable"}

    signature = _positions_signature(positions)
    signature_key = f"portfolio_last_persist_signature_{user_id}"
    if str(st.session_state.get(signature_key) or "") == signature:
        st.session_state["portfolio_supabase_saved"] = True
        st.session_state["portfolio_supabase_save_status"] = "SKIPPED"
        return {"status": "SKIPPED", "reason": "snapshot_unchanged"}

    try:
        if hasattr(portfolio_engine, "set_user_id"):
            portfolio_engine.set_user_id(user_id)

        report = portfolio_engine.persist_all_positions(user_id=user_id)
        st.session_state[signature_key] = signature
        st.session_state["portfolio_supabase_persist_report"] = report
        st.session_state["portfolio_supabase_persist_error"] = ""
        save_status = str(report.get("status") or "OK") if isinstance(report, dict) else "OK"
        st.session_state["portfolio_supabase_save_status"] = save_status
        st.session_state["portfolio_supabase_saved"] = save_status.upper() == "OK"
        return report if isinstance(report, dict) else {"status": "OK"}
    except Exception as exc:
        st.session_state["portfolio_supabase_saved"] = False
        st.session_state["portfolio_supabase_save_status"] = "ERROR"
        st.session_state["portfolio_supabase_persist_error"] = str(exc)
        return {"status": "ERROR", "reason": str(exc)}


# =========================================================
# RESPONSIVE UI HELPERS
# =========================================================

def inject_portfolio_responsive_css() -> None:
    """Visual-only responsive CSS for the trading/runtime Portfolio page."""
    jfbp_inject_responsive_css(max_width=1500)
    jfbp_inject_card_css()
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1.4rem !important;
                padding-bottom: 2.5rem !important;
                max-width: 1500px !important;
                padding-left: clamp(0.9rem, 2.2vw, 2.4rem) !important;
                padding-right: clamp(0.9rem, 2.2vw, 2.4rem) !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }

            h1 {
                font-size: var(--jfbp-type-h1) !important;
                font-weight: 850 !important;
                color: #1f2937 !important;
                line-height: 1.12 !important;
            }

            h2, h3 {
                font-size: var(--jfbp-type-h2) !important;
                font-weight: 850 !important;
                color: #1f2937 !important;
                line-height: 1.18 !important;
            }

            div[data-testid="stHorizontalBlock"] {
                gap: 0.85rem !important;
                align-items: stretch !important;
            }

            div[data-testid="stHorizontalBlock"] > div,
            div[data-testid="column"] {
                min-width: 0 !important;
            }

            div[data-testid="stDataFrame"] {
                width: 100% !important;
                max-width: 100% !important;
                overflow-x: auto !important;
                border-radius: 12px !important;
            }

            div[data-testid="stDataFrame"] div {
                max-width: 100% !important;
            }

            div[data-testid="stAlert"],
            div[data-testid="stMarkdownContainer"] {
                overflow-wrap: anywhere !important;
            }

            .stButton > button {
                border-radius: 10px !important;
                font-weight: 750 !important;
                min-height: 38px !important;
                border: 1px solid #d7e3f5 !important;
            }

            .jfbp-portfolio-card {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 16px;
                padding: 0.88rem 0.96rem;
                margin-bottom: 0.72rem;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
                min-height: 90px;
                overflow-wrap: anywhere;
            }

            .jfbp-portfolio-card.info {
                background: #eff6ff;
                border-color: #bfdbfe;
            }

            .jfbp-portfolio-card.good {
                background: #ecfdf5;
                border-color: #bbf7d0;
            }

            .jfbp-portfolio-card.warning {
                background: #fffbeb;
                border-color: #fde68a;
            }

            .jfbp-portfolio-card.risk {
                background: #fef2f2;
                border-color: #fecaca;
            }

            .jfbp-portfolio-label {
                font-size: var(--jfbp-type-card-label);
                text-transform: uppercase;
                letter-spacing: 0.045em;
                color: #64748b;
                font-weight: 850;
                margin-bottom: 0.35rem;
            }

            .jfbp-portfolio-value {
                font-size: var(--jfbp-type-card-value);
                line-height: 1.16;
                font-weight: 900;
                color: #111827;
            }

            .jfbp-portfolio-card.good .jfbp-portfolio-value { color: #166534; }
            .jfbp-portfolio-card.warning .jfbp-portfolio-value { color: #92400e; }
            .jfbp-portfolio-card.risk .jfbp-portfolio-value { color: #991b1b; }
            .jfbp-portfolio-card.info .jfbp-portfolio-value { color: #1d4ed8; }

            .jfbp-portfolio-detail {
                font-size: var(--jfbp-type-caption);
                color: #64748b;
                margin-top: 0.35rem;
                line-height: 1.35;
            }

            .jfbp-status-pill {
                display: inline-flex;
                align-items: center;
                gap: 0.4rem;
                background: #eff6ff;
                border: 1px solid #bfdbfe;
                color: #1d4ed8;
                border-radius: 999px;
                padding: 0.28rem 0.62rem;
                font-weight: 780;
                font-size: 0.84rem;
                margin: 0.20rem 0 0.60rem 0;
            }



            .jfbp-portfolio-hero {
                border: 1px solid;
                border-radius: 20px;
                padding: 1rem 1rem;
                margin: 0.75rem 0 0.95rem 0;
                box-shadow: 0 4px 14px rgba(15,23,42,0.06);
                overflow-wrap: anywhere;
            }

            .jfbp-portfolio-hero-kicker {
                font-size: 0.72rem;
                font-weight: 950;
                letter-spacing: 0.075em;
                text-transform: uppercase;
                color: #64748b;
                margin-bottom: 0.35rem;
            }

            .jfbp-portfolio-hero-title {
                font-size: clamp(1.65rem, 3.4vw, 2.25rem);
                font-weight: 1000;
                line-height: 1.06;
                margin-bottom: 0.42rem;
            }

            .jfbp-portfolio-hero-text {
                font-size: clamp(0.90rem, 1.45vw, 1.04rem);
                font-weight: 760;
                color: #334155;
                line-height: 1.44;
                margin-bottom: 0.45rem;
            }

            .jfbp-portfolio-hero-action {
                border-radius: 14px;
                padding: 0.72rem 0.90rem;
                background: rgba(255,255,255,0.76);
                border: 1px solid rgba(148,163,184,0.35);
                color: #111827;
                font-size: 0.92rem;
                font-weight: 900;
            }

            .jfbp-score-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 0.75rem;
                padding: 0.62rem 0.72rem;
                margin-bottom: 0.42rem;
                background: #f8fafc;
                border: 1px solid #dbe3ef;
                border-radius: 12px;
                font-size: 0.90rem;
                font-weight: 750;
                color: #111827;
            }

            .jfbp-score-detail {
                color: #64748b;
                font-size: 0.78rem;
                font-weight: 750;
                text-align: right;
            }

            @media (max-width: 1180px) {
                div[data-testid="stHorizontalBlock"] {
                    flex-wrap: wrap !important;
                }

                div[data-testid="stHorizontalBlock"] > div,
                div[data-testid="column"] {
                    flex: 1 1 48% !important;
                    width: 48% !important;
                }
            }

            @media (max-width: 760px) {
                .block-container {
                    padding-left: 0.9rem !important;
                    padding-right: 0.9rem !important;
                }

                div[data-testid="stHorizontalBlock"] > div,
                div[data-testid="column"] {
                    flex: 1 1 100% !important;
                    width: 100% !important;
                    min-width: 100% !important;
                }

                .jfbp-portfolio-card {
                    min-height: 88px;
                    padding: 0.88rem 0.95rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def responsive_columns(spec, gap: str = "small"):
    return jfbp_columns(spec, gap=gap)


def portfolio_tip(text: str) -> None:
    st.caption(f"💡 {text}")


def format_money(value) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "$0.00"


def portfolio_metric_card(label: str, value, detail: str = "", tone: str = "neutral") -> None:
    """Shared JFBP metric card wrapper.

    Kept as a local function name so the rest of this page remains stable,
    but the visual rendering now comes from core.ui_cards.
    """
    jfbp_metric_card(label, value, detail, tone=tone)


def render_portfolio_help() -> None:
    with st.expander("ℹ️ How to use this page", expanded=False):
        st.markdown(
            """
            **Portfolio** is the trading/runtime portfolio dashboard. It shows the positions and ledger used by the JFBP execution and risk engine.

            **Portfolio Exposure** shows current position exposure: gross exposure is total market exposure, long exposure is bullish exposure, short exposure is bearish exposure, and net exposure is long minus short.

            **Realized P&L** is profit or loss already locked in from closed trades. **Unrealized P&L** is profit or loss still open in current positions.

            **Performance Analytics** uses the trade ledger to calculate win rate, profit factor, expectancy, winners, losers, best trade, and worst trade.

            **Open / Active Positions** shows the current runtime or broker-truth position book. In LIVE mode, broker positions are used and old SIM/test positions are intentionally ignored.

            **Trade Ledger** is the historical fill record used to calculate performance statistics.

            **Portfolio Health** is the diagnostic section. It tells you whether the engine is online, where positions came from, whether broker truth is active, and whether any portfolio error was recorded.
            """
        )


def render_health_cards(health: dict) -> None:
    keys = [
        ("Portfolio Engine", "Engine"),
        ("Position Source", "Source"),
        ("Runtime Positions", "Positions"),
        ("Ledger Entries", "Ledger"),
        ("Live Mode", "Live Mode"),
        ("Broker Truth Active", "Broker Truth"),
    ]

    cols = responsive_columns(3)
    for idx, (key, label) in enumerate(keys):
        with cols[idx % 3]:
            value = health.get(key, "N/A")
            tone = "good" if str(value).upper() in ("ONLINE", "TRUE") else "info"
            if key == "Position Source" and str(value).upper() in ("NONE", "UNKNOWN"):
                tone = "warning"
            portfolio_metric_card(label, value, key, tone=tone)



def portfolio_tone_palette(tone: str):
    palette = {
        "neutral": ("#f8fafc", "#dbe3ef", "#111827"),
        "info": ("#eff6ff", "#bfdbfe", "#1d4ed8"),
        "good": ("#ecfdf5", "#bbf7d0", "#166534"),
        "warning": ("#fffbeb", "#fde68a", "#92400e"),
        "risk": ("#fef2f2", "#fecaca", "#991b1b"),
    }
    return palette.get(str(tone), palette["neutral"])


def render_portfolio_hero(title: str, subtitle: str, action: str, tone: str = "info") -> None:
    jfbp_hero_card(
        title=title,
        subtitle=subtitle,
        action=action,
        kicker="Institutional Portfolio Command",
        tone=tone,
    )


def render_score_row(label: str, score: float, detail: str = "") -> None:
    jfbp_score_row(label, score, detail)


def _position_pnl_pct(row: dict) -> float:
    avg = _safe_float(row.get("avg_price"), 0.0)
    qty = _safe_float(row.get("qty"), 0.0)
    cost = abs(avg * qty)
    if cost <= 0:
        return 0.0
    return _safe_float(row.get("unrealized_pnl"), 0.0) / cost * 100.0


def _build_concentration(positions: dict, exposure: dict) -> dict:
    gross = max(_safe_float(exposure.get("gross_exposure"), 0.0), 0.0)
    rows = []
    for symbol, row in positions.items():
        value = abs(_safe_float(row.get("position_value"), 0.0))
        if value <= 0:
            continue
        rows.append((str(symbol).upper(), value))
    rows.sort(key=lambda x: x[1], reverse=True)
    largest_symbol = rows[0][0] if rows else "—"
    largest_value = rows[0][1] if rows else 0.0
    top3_value = sum(v for _, v in rows[:3])
    denom = gross if gross > 0 else max(largest_value, 1.0)
    return {
        "largest_symbol": largest_symbol,
        "largest_value": largest_value,
        "largest_pct": largest_value / denom * 100.0 if denom > 0 else 0.0,
        "top3_value": top3_value,
        "top3_pct": top3_value / denom * 100.0 if denom > 0 else 0.0,
        "rows": rows,
    }


def _portfolio_grade(score: float) -> str:
    if score >= 90:
        return "A+"
    if score >= 82:
        return "A"
    if score >= 74:
        return "B"
    if score >= 64:
        return "C"
    if score >= 50:
        return "D"
    return "F"


def _build_portfolio_scorecard(report, positions: dict, exposure: dict, concentration: dict) -> dict:
    position_count = len(positions)
    gross = _safe_float(exposure.get("gross_exposure"), 0.0)
    net = abs(_safe_float(exposure.get("net_exposure"), 0.0))
    long_exposure = _safe_float(exposure.get("long_exposure"), 0.0)
    short_exposure = _safe_float(exposure.get("short_exposure"), 0.0)
    winners = sum(1 for row in positions.values() if _safe_float(row.get("unrealized_pnl"), 0.0) > 0)
    losers = sum(1 for row in positions.values() if _safe_float(row.get("unrealized_pnl"), 0.0) < 0)

    diversification = min(100.0, position_count / 8.0 * 100.0)
    if concentration.get("largest_pct", 0.0) >= 35:
        diversification -= 25
    elif concentration.get("largest_pct", 0.0) >= 25:
        diversification -= 12
    if concentration.get("top3_pct", 0.0) >= 65:
        diversification -= 20
    elif concentration.get("top3_pct", 0.0) >= 50:
        diversification -= 10

    exposure_score = 85.0
    if gross <= 0:
        exposure_score = 60.0
    elif short_exposure > 0 and long_exposure > 0:
        exposure_score += 5
    if net > gross * 0.90 and gross > 0:
        exposure_score -= 10

    win_rate = _safe_float(getattr(report, "win_rate", 0.0), 0.0)
    profit_factor = _safe_float(getattr(report, "profit_factor", 0.0), 0.0)
    expectancy = _safe_float(getattr(report, "expectancy", 0.0), 0.0)
    total_pnl = _safe_float(getattr(report, "total_pnl", 0.0), 0.0)

    performance_score = 50.0
    performance_score += min(25.0, win_rate * 35.0)
    if profit_factor >= 2:
        performance_score += 20
    elif profit_factor >= 1:
        performance_score += 12
    elif profit_factor > 0:
        performance_score -= 8
    if expectancy > 0:
        performance_score += 8
    if total_pnl > 0:
        performance_score += 8
    elif total_pnl < 0:
        performance_score -= 12

    open_risk_score = 80.0
    if losers > winners and position_count > 0:
        open_risk_score -= 18
    if _safe_float(getattr(report, "unrealized_pnl", 0.0), 0.0) < 0:
        open_risk_score -= 15
    if concentration.get("top3_pct", 0.0) >= 60:
        open_risk_score -= 12

    execution_score = 75.0
    if getattr(report, "total_trades", 0) > 0:
        execution_score += 10
    if profit_factor >= 1:
        execution_score += 8
    if _safe_float(getattr(report, "worst_trade", 0.0), 0.0) < 0 and _safe_float(getattr(report, "best_trade", 0.0), 0.0) <= abs(_safe_float(getattr(report, "worst_trade", 0.0), 0.0)):
        execution_score -= 10

    scores = {
        "Diversification": max(0.0, min(100.0, diversification)),
        "Exposure": max(0.0, min(100.0, exposure_score)),
        "Performance": max(0.0, min(100.0, performance_score)),
        "Open Risk": max(0.0, min(100.0, open_risk_score)),
        "Execution": max(0.0, min(100.0, execution_score)),
    }
    composite = sum(scores.values()) / max(len(scores), 1)
    scores["Composite"] = composite
    scores["Grade"] = _portfolio_grade(composite)
    return scores


def _build_position_ranking(positions: dict, exposure: dict) -> pd.DataFrame:
    rows = []
    gross = max(_safe_float(exposure.get("gross_exposure"), 0.0), 1.0)
    for symbol, row in positions.items():
        value = _safe_float(row.get("position_value"), 0.0)
        pnl = _safe_float(row.get("unrealized_pnl"), 0.0)
        pnl_pct = _position_pnl_pct(row)
        weight = abs(value) / gross * 100.0 if gross > 0 else 0.0
        score = 50.0 + max(-30.0, min(30.0, pnl_pct * 2.0))
        if pnl > 0:
            score += 10
        if weight > 35:
            score -= 8
        rows.append({
            "Symbol": str(symbol).upper(),
            "Side": row.get("side", ""),
            "Qty": _safe_float(row.get("qty"), 0.0),
            "Weight": f"{weight:.1f}%",
            "Unrealized P&L": format_money(pnl),
            "P&L %": f"{pnl_pct:.2f}%",
            "Score Raw": max(0.0, min(100.0, score)),
            "Score": f"{max(0.0, min(100.0, score)):.0f}/100",
        })
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).sort_values(["Score Raw", "Symbol"], ascending=[False, True]).reset_index(drop=True)
    df.insert(0, "Rank", [f"#{i + 1}" for i in range(len(df))])
    return df[["Rank", "Symbol", "Side", "Qty", "Weight", "Unrealized P&L", "P&L %", "Score"]]


def _build_rebalance_rows(positions: dict, exposure: dict) -> pd.DataFrame:
    if not positions:
        return pd.DataFrame()
    gross = max(_safe_float(exposure.get("gross_exposure"), 0.0), 1.0)
    target = 100.0 / max(len(positions), 1)
    rows = []
    for symbol, row in positions.items():
        value = abs(_safe_float(row.get("position_value"), 0.0))
        current = value / gross * 100.0 if gross > 0 else 0.0
        drift = current - target
        if drift > 7.5:
            action = "TRIM / REVIEW"
        elif drift < -7.5:
            action = "UNDERWEIGHT"
        else:
            action = "BALANCED"
        rows.append({
            "Symbol": str(symbol).upper(),
            "Current Weight": f"{current:.1f}%",
            "Equal-Weight Guide": f"{target:.1f}%",
            "Drift": f"{drift:+.1f}%",
            "Action": action,
        })
    return pd.DataFrame(rows).sort_values("Symbol")


def _build_commander_report(report, positions: dict, exposure: dict, concentration: dict, scorecard: dict, live_mode: bool) -> dict:
    total_pnl = _safe_float(getattr(report, "total_pnl", 0.0), 0.0)
    unrealized = _safe_float(getattr(report, "unrealized_pnl", 0.0), 0.0)
    win_rate = _safe_float(getattr(report, "win_rate", 0.0), 0.0) * 100.0
    profit_factor = _safe_float(getattr(report, "profit_factor", 0.0), 0.0)
    grade = scorecard.get("Grade", "N/A")
    composite = _safe_float(scorecard.get("Composite", 0.0), 0.0)
    positions_count = len(positions)
    review_symbols = []
    for symbol, row in positions.items():
        if _safe_float(row.get("unrealized_pnl"), 0.0) < 0 or abs(_position_pnl_pct(row)) >= 8:
            review_symbols.append(str(symbol).upper())
    if composite >= 82 and total_pnl >= 0 and concentration.get("top3_pct", 0.0) < 60:
        status, tone = "HEALTHY", "good"
    elif composite >= 65 and concentration.get("top3_pct", 0.0) < 70:
        status, tone = "SELECTIVE", "warning"
    elif positions_count == 0:
        status, tone = "STANDBY", "info"
    else:
        status, tone = "DEFENSIVE", "risk"

    if concentration.get("top3_pct", 0.0) >= 65:
        action = f"ACTION: Concentration risk elevated. Review top holdings before adding exposure."
    elif review_symbols:
        action = f"ACTION: Review open-risk symbols — {', '.join(review_symbols[:5])}."
    elif total_pnl < 0:
        action = "ACTION: Portfolio P&L is negative. Review losing positions before adding exposure."
    elif positions_count == 0:
        action = "ACTION: No active portfolio positions. Stand by for qualified setups."
    else:
        action = "ACTION: No immediate portfolio action required. Continue monitoring exposure and ledger quality."

    subtitle = (
        f"Mode: {'LIVE broker truth' if live_mode else 'SIM / portfolio engine'} · "
        f"Positions: {positions_count} · Net Exposure: {format_money(exposure.get('net_exposure', 0.0))} · "
        f"Open P&L: {format_money(unrealized)} · Win Rate: {win_rate:.1f}% · "
        f"Profit Factor: {profit_factor:.2f} · Grade: {grade}"
    )
    return {"status": status, "tone": tone, "title": f"🏛 PORTFOLIO STATUS: {status}", "subtitle": subtitle, "action": action, "grade": grade}


def render_commander_portfolio_report(report_dict: dict, report, positions: dict, exposure: dict, concentration: dict, scorecard: dict) -> None:
    render_portfolio_hero(report_dict["title"], report_dict["subtitle"], report_dict["action"], report_dict["tone"])
    cols = responsive_columns(4)
    with cols[0]:
        portfolio_metric_card("Portfolio Grade", report_dict.get("grade", "N/A"), f"Composite {scorecard.get('Composite', 0):.0f}/100", tone=report_dict.get("tone", "info"))
    with cols[1]:
        portfolio_metric_card("Total P&L", format_money(getattr(report, "total_pnl", 0.0)), "Realized + unrealized", tone="good" if _safe_float(getattr(report, "total_pnl", 0.0)) >= 0 else "risk")
    with cols[2]:
        portfolio_metric_card("Largest Position", concentration.get("largest_symbol", "—"), f"{concentration.get('largest_pct', 0):.1f}% of gross exposure", tone="risk" if concentration.get("largest_pct", 0) >= 35 else "warning" if concentration.get("largest_pct", 0) >= 25 else "info")
    with cols[3]:
        portfolio_metric_card("Top 3 Concentration", f"{concentration.get('top3_pct', 0):.1f}%", "Red above 65%", tone="risk" if concentration.get("top3_pct", 0) >= 65 else "warning" if concentration.get("top3_pct", 0) >= 50 else "good")


def render_portfolio_scorecard(scorecard: dict) -> None:
    left, right = responsive_columns([0.58, 0.42], gap="large")
    with left:
        render_score_row("Diversification", scorecard.get("Diversification", 0), "Position count and concentration")
        render_score_row("Exposure", scorecard.get("Exposure", 0), "Gross/net risk profile")
        render_score_row("Performance", scorecard.get("Performance", 0), "Win rate, profit factor, P&L")
        render_score_row("Open Risk", scorecard.get("Open Risk", 0), "Open losers and concentration")
        render_score_row("Execution", scorecard.get("Execution", 0), "Ledger quality and trade outcomes")
    with right:
        grade = scorecard.get("Grade", "N/A")
        composite = scorecard.get("Composite", 0)
        tone = "good" if composite >= 82 else "warning" if composite >= 65 else "risk"
        portfolio_metric_card("Portfolio Grade", grade, f"Composite score {composite:.0f}/100", tone=tone)
        if composite >= 82:
            st.success("Portfolio command score is strong.")
        elif composite >= 65:
            st.warning("Portfolio is workable, but selectivity and risk discipline matter.")
        else:
            st.error("Portfolio requires defensive review before adding risk.")

# =========================================================
# PAGE
# =========================================================

def run_page():

    inject_portfolio_responsive_css()

    gateway, market, oms, portfolio_engine = init_core()

    st.title("🏛 Portfolio")
    st.caption("Institutional portfolio command center for exposure, performance, concentration, rebalance, ledger, and engine health.")

    st.markdown(
        """
        <div class="jfbp-status-pill">
            🚀 Workflow: Opportunity Center → Trade Command Center → OMS Execution → Position Command Center → Portfolio → Journal
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_portfolio_help()

    if portfolio_engine is None:
        st.error("Portfolio engine unavailable.")
        return

    user_id = _current_saas_user_id()
    user_id_present = bool(user_id)
    if hasattr(portfolio_engine, "set_user_id"):
        try:
            portfolio_engine.set_user_id(user_id)
        except Exception:
            pass

    load_report = _ensure_portfolio_loaded_for_user(portfolio_engine, user_id)
    if str(load_report.get("status") or "").upper() == "ERROR":
        st.warning("Portfolio load warning: unable to load saved positions from Supabase for this user.")

    live_mode = st.session_state.get("mode") == "LIVE"

    # =====================================================
    # BROKER CONTROL — compact expander
    # =====================================================

    st.session_state.setdefault("portfolio_live_refresh_enabled", False)
    st.session_state.setdefault("portfolio_last_live_refresh_ts", 0.0)

    with st.expander("📡 Broker / Refresh Control", expanded=False):
        status_text = "LIVE broker truth" if live_mode else "SIM / portfolio engine"
        st.markdown(
            f"""
            <div class="jfbp-status-pill">
                <span>📡</span><span>{html.escape(status_text)}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        refresh_cols = responsive_columns([1.25, 0.75])

        with refresh_cols[0]:
            live_refresh_enabled = st.checkbox(
                "Auto-refresh live broker data every 30 seconds",
                value=bool(st.session_state.get("portfolio_live_refresh_enabled", False)),
                key="portfolio_live_refresh_enabled",
                help=(
                    "Leave this off for faster page loads. Turn it on only when you want "
                    "the Portfolio page to refresh broker data automatically."
                ),
            )

        with refresh_cols[1]:
            st.caption("Broker Snapshot")
            manual_refresh_btn = st.button(
                "Refresh Now",
                width="stretch",
                key="portfolio_manual_broker_refresh_commander",
                help=(
                    "Immediately refresh broker data when LIVE mode and the gateway are available. "
                    "In SIM mode this button will explain why no broker refresh was run."
                ),
            )

        last_refresh_ts = float(
            st.session_state.get("portfolio_last_live_refresh_ts", 0.0)
            or 0.0
        )

        if last_refresh_ts > 0:
            last_refresh_text = datetime.fromtimestamp(last_refresh_ts).strftime("%H:%M:%S")
        else:
            last_refresh_text = "Not refreshed this session"

        portfolio_tip(
            "Auto-refresh keeps broker data current when LIVE mode is active. "
            "Refresh Now forces a broker snapshot immediately after an order or position change."
        )

        st.caption(f"Last broker refresh: {last_refresh_text}")

        if manual_refresh_btn:
            if not live_mode:
                st.info(
                    "Refresh Now is available, but no broker refresh was run because "
                    "Portfolio is currently in SIM mode. Switch to LIVE mode to refresh "
                    "IBKR broker positions from the gateway."
                )
            elif gateway is None:
                st.warning(
                    "Refresh Now is available, but the broker gateway is not connected. "
                    "Open Live IBKR first, confirm the gateway connection, then return here."
                )
            else:
                try:
                    if hasattr(gateway, "refresh_all"):
                        gateway.refresh_all()
                        st.session_state["portfolio_last_live_refresh_ts"] = time.time()
                        st.session_state["portfolio_live_refresh_error"] = ""
                        st.success("Broker snapshot refreshed.")
                        st.rerun()
                    else:
                        st.warning("Broker gateway refresh method is unavailable.")
                except Exception as exc:
                    st.session_state["portfolio_live_refresh_error"] = str(exc)
                    st.warning(f"Broker refresh failed: {exc}")

    live_refresh_enabled = bool(st.session_state.get("portfolio_live_refresh_enabled", False))

    if live_mode and live_refresh_enabled and gateway is not None:
        try:
            now = time.time()
            last_refresh = float(st.session_state.get("portfolio_last_live_refresh_ts", 0.0) or 0.0)
            if now - last_refresh >= 30:
                if hasattr(gateway, "refresh_all"):
                    gateway.refresh_all()
                st.session_state["portfolio_last_live_refresh_ts"] = now
            else:
                st.caption(
                    "Live broker refresh skipped to avoid slow reloads "
                    f"({int(30 - (now - last_refresh))}s cooldown)."
                )
        except Exception as exc:
            st.session_state["portfolio_live_refresh_error"] = str(exc)
    elif live_mode:
        st.caption(
            "Portfolio page live broker refresh is off for faster reloads. "
            "Use Live IBKR page to refresh broker truth."
        )

    # =====================================================
    # SNAPSHOTS
    # =====================================================

    positions = {}
    position_source = "NONE"

    if live_mode:
        positions = _pull_gateway_positions(gateway)
        if positions:
            position_source = "IBKR_GATEWAY"

        if not positions and not user_id_present:
            for key in ("broker_snapshot_positions", "broker_positions", "ibkr_positions", "live_positions"):
                candidate = st.session_state.get(key)
                positions = _normalize_positions(candidate)
                if positions:
                    position_source = f"SESSION:{key}"
                    break

        if not positions:
            st.warning(
                "LIVE mode is active, but no live broker positions were found. "
                "Old SIM/test portfolio positions are intentionally ignored in LIVE mode."
            )

    else:
        positions = _pull_portfolio_positions(portfolio_engine)
        if positions:
            position_source = "PORTFOLIO_ENGINE"

        if not positions:
            positions = _pull_gateway_positions(gateway)
            if positions:
                position_source = "GATEWAY_FALLBACK"

        if not positions and not user_id_present:
            for key in ("portfolio_positions", "positions", "broker_positions", "ibkr_positions", "live_positions"):
                candidate = st.session_state.get(key)
                positions = _normalize_positions(candidate)
                if positions:
                    position_source = f"SESSION:{key}"
                    break

        if not positions and user_id_present and position_source == "NONE":
            position_source = "USER_SCOPED_EMPTY"

    st.caption(
        "Live mark-to-market disabled for fast Portfolio loading. "
        "In LIVE mode, positions come from IBKR broker truth only; old SIM/test portfolio positions are ignored."
    )

    persist_report = _persist_portfolio_for_user(portfolio_engine, user_id, positions)
    if str(persist_report.get("status") or "").upper() == "ERROR":
        st.warning("Portfolio save warning: unable to persist positions to Supabase for this user.")

    # =====================================================
    # ANALYTICS
    # =====================================================

    exposure = _build_exposure(positions)
    ledger = _pull_ledger(portfolio_engine)

    analyzer = PerformanceAnalyzer()
    report = analyzer.analyze(
        ledger=ledger,
        positions_snapshot=positions,
        exposure_snapshot=exposure,
    )

    concentration = _build_concentration(positions, exposure)
    scorecard = _build_portfolio_scorecard(report, positions, exposure, concentration)
    commander_report = _build_commander_report(report, positions, exposure, concentration, scorecard, live_mode)
    ranking_df = _build_position_ranking(positions, exposure)
    rebalance_df = _build_rebalance_rows(positions, exposure)

    # =====================================================
    # COMMANDER REPORT
    # =====================================================

    st.subheader("🎖 Commander Portfolio Report")
    portfolio_tip("Fast read: portfolio status, grade, exposure, P&L, concentration, and immediate action.")
    render_commander_portfolio_report(commander_report, report, positions, exposure, concentration, scorecard)

    # =====================================================
    # 70/30 COMMAND LAYOUT
    # =====================================================

    left, right = responsive_columns([0.70, 0.30], gap="large")

    with left:
        st.subheader("🏆 Portfolio Ranking Engine")
        portfolio_tip("Ranks active positions by open P&L strength, weight, and risk profile.")
        if ranking_df.empty:
            st.info("No position ranking available yet.")
        else:
            st.dataframe(ranking_df, width="stretch", hide_index=True, height=260)

        st.subheader("📋 Portfolio Scorecard")
        portfolio_tip("Institutional report card for diversification, exposure, performance, open risk, and execution quality.")
        render_portfolio_scorecard(scorecard)

    with right:
        st.subheader("📐 Concentration Monitor")
        portfolio_tip("Largest-position and top-3 concentration risk.")
        portfolio_metric_card(
            "Largest Position",
            concentration.get("largest_symbol", "—"),
            f"{concentration.get('largest_pct', 0):.1f}% of gross exposure",
            tone="risk" if concentration.get("largest_pct", 0) >= 35 else "warning" if concentration.get("largest_pct", 0) >= 25 else "info",
        )
        portfolio_metric_card(
            "Top 3 Concentration",
            f"{concentration.get('top3_pct', 0):.1f}%",
            format_money(concentration.get("top3_value", 0.0)),
            tone="risk" if concentration.get("top3_pct", 0) >= 65 else "warning" if concentration.get("top3_pct", 0) >= 50 else "good",
        )

        if concentration.get("top3_pct", 0.0) >= 65:
            st.error("Concentration risk is elevated. Review top holdings before adding exposure.")
        elif concentration.get("top3_pct", 0.0) >= 50:
            st.warning("Top-3 concentration is moderate. Add risk selectively.")
        else:
            st.success("Concentration profile is within normal guide.")

        st.subheader("⚖ Rebalance Guide")
        if rebalance_df.empty:
            st.info("No rebalance guide available yet.")
        else:
            st.dataframe(rebalance_df, width="stretch", hide_index=True, height=230)

    # =====================================================
    # LOWER OPERATING TABS
    # =====================================================

    tab_exposure, tab_performance, tab_positions, tab_ledger, tab_health = st.tabs([
        "📊 Exposure",
        "📈 Performance",
        "📘 Positions",
        "📒 Ledger",
        "🩺 Health",
    ])

    with tab_exposure:
        st.subheader("Portfolio Exposure")
        portfolio_tip("Exposure shows how much market risk the trading engine is carrying right now.")

        row1 = responsive_columns(4)
        with row1[0]:
            portfolio_metric_card("Positions", exposure.get("positions", len(positions)), "Open runtime positions", tone="info")
        with row1[1]:
            portfolio_metric_card("Gross Exposure", format_money(report.gross_exposure), "Long + short exposure", tone="info")
        with row1[2]:
            portfolio_metric_card("Long Exposure", format_money(report.long_exposure), "Bullish exposure", tone="good" if report.long_exposure > 0 else "neutral")
        with row1[3]:
            portfolio_metric_card("Short Exposure", format_money(report.short_exposure), "Bearish exposure", tone="risk" if report.short_exposure > 0 else "neutral")

        row2 = responsive_columns(4)
        with row2[0]:
            portfolio_metric_card("Net Exposure", format_money(report.net_exposure), "Long minus short", tone="info")
        with row2[1]:
            portfolio_metric_card("Unrealized P&L", format_money(report.unrealized_pnl), "Open positions", tone="good" if report.unrealized_pnl >= 0 else "risk")
        with row2[2]:
            portfolio_metric_card("Realized P&L", format_money(report.realized_pnl), "Closed trades", tone="good" if report.realized_pnl >= 0 else "risk")
        with row2[3]:
            portfolio_metric_card("Total P&L", format_money(report.total_pnl), "Realized + unrealized", tone="good" if report.total_pnl >= 0 else "risk")

    with tab_performance:
        st.subheader("Performance Analytics")
        portfolio_tip("Performance metrics are calculated from the trade ledger.")

        p_row1 = responsive_columns(4)
        with p_row1[0]:
            portfolio_metric_card("Total Trades", report.total_trades, "Ledger count", tone="info")
        with p_row1[1]:
            portfolio_metric_card("Win Rate", f"{report.win_rate * 100:.1f}%", "Winning trades / total", tone="good" if report.win_rate >= 0.5 else "warning")
        with p_row1[2]:
            portfolio_metric_card("Profit Factor", f"{report.profit_factor:.2f}", "Gross wins / gross losses", tone="good" if report.profit_factor >= 1 else "warning")
        with p_row1[3]:
            portfolio_metric_card("Expectancy", format_money(report.expectancy), "Average expected trade", tone="good" if report.expectancy >= 0 else "risk")

        p_row2 = responsive_columns(4)
        with p_row2[0]:
            portfolio_metric_card("Winners", report.winners, "Profitable trades", tone="good")
        with p_row2[1]:
            portfolio_metric_card("Losers", report.losers, "Losing trades", tone="risk" if report.losers else "neutral")
        with p_row2[2]:
            portfolio_metric_card("Best Trade", format_money(report.best_trade), "Largest closed gain", tone="good" if report.best_trade >= 0 else "neutral")
        with p_row2[3]:
            portfolio_metric_card("Worst Trade", format_money(report.worst_trade), "Largest closed loss", tone="risk" if report.worst_trade < 0 else "neutral")

    with tab_positions:
        st.subheader("Open / Active Positions")
        portfolio_tip("Current position book used by the runtime portfolio and risk engine.")

        if positions:
            positions_df = pd.DataFrame(list(positions.values()))
            ordered_cols = [
                "symbol", "side", "qty", "signed_qty", "avg_price", "last_price",
                "position_value", "unrealized_pnl", "realized_pnl", "total_pnl",
            ]
            available_cols = [col for col in ordered_cols if col in positions_df.columns]
            if available_cols:
                positions_df = positions_df[available_cols]
            for col in positions_df.columns:
                if positions_df[col].dtype == "object":
                    positions_df[col] = positions_df[col].astype(str)
            st.dataframe(positions_df, width="stretch", hide_index=True, height=360)
        else:
            st.info("No portfolio positions.")

    with tab_ledger:
        st.subheader("Trade Ledger")
        portfolio_tip("Historical fills used to calculate realized P&L, win rate, profit factor, expectancy, and best/worst trade.")

        if ledger:
            ledger_df = pd.DataFrame(ledger)
            preferred_cols = ["timestamp", "symbol", "action", "qty", "fill_price", "realized_delta", "source"]
            available_cols = [c for c in preferred_cols if c in ledger_df.columns]
            if available_cols:
                ledger_df = ledger_df[available_cols]
            for col in ledger_df.columns:
                if ledger_df[col].dtype == "object":
                    ledger_df[col] = ledger_df[col].astype(str)
            st.dataframe(ledger_df, width="stretch", hide_index=True, height=360)
        else:
            st.info("No portfolio ledger entries.")

    with tab_health:
        st.subheader("Portfolio Health")
        portfolio_tip("Diagnostic view showing engine status, source of positions, ledger count, and broker truth status.")

        health = {
            "Portfolio Engine": "ONLINE",
            "Portfolio Supabase Loaded": bool(st.session_state.get("portfolio_supabase_loaded", False)),
            "Portfolio Supabase Saved": bool(st.session_state.get("portfolio_supabase_saved", False)),
            "Current User ID Present": user_id_present,
            "Position Count": len(positions),
            "Ledger Count": len(ledger),
            "Last Persistence Error": st.session_state.get("portfolio_supabase_persist_error", "") or st.session_state.get("portfolio_supabase_load_error", ""),
            "Runtime Positions": len(positions),
            "Position Source": position_source,
            "Ledger Entries": len(ledger),
            "Long Positions": report.long_positions,
            "Short Positions": report.short_positions,
            "Last Error": getattr(portfolio_engine, "last_error", ""),
            "Live Mode": live_mode,
            "Broker Truth Active": live_mode,
        }

        render_health_cards(health)

        with st.expander("Full Portfolio Health Diagnostics", expanded=False):
            health_df = pd.DataFrame(list(health.items()), columns=["Metric", "Value"])
            health_df["Metric"] = health_df["Metric"].astype(str)
            health_df["Value"] = health_df["Value"].astype(str)
            st.dataframe(health_df, width="stretch", hide_index=True)

def page():
    run_page()
