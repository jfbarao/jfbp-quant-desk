# =========================================================
# 📊 JFBP PORTFOLIO PAGE v24.8
# INSTITUTIONAL PORTFOLIO + PERFORMANCE DASHBOARD
# BROKER TRUTH + LIVE MARK-TO-MARKET FIX
# =========================================================

from __future__ import annotations

import streamlit as st
import pandas as pd

from core.bootstrap import init_core
from analytics.performance import PerformanceAnalyzer


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


# =========================================================
# PAGE
# =========================================================

def run_page():

    gateway, market, oms, portfolio_engine = init_core()

    st.title("📊 Portfolio")

    if portfolio_engine is None:
        st.error("Portfolio engine unavailable.")
        return

    live_mode = (
        st.session_state.get("mode") == "LIVE"
    )

    # =====================================================
    # LIVE REFRESH
    # =====================================================

    st.session_state.setdefault("portfolio_live_refresh_enabled", False)
    st.session_state.setdefault("portfolio_last_live_refresh_ts", 0.0)

    live_refresh_enabled = st.checkbox(
        "Refresh live broker data on Portfolio page",
        value=bool(st.session_state.get("portfolio_live_refresh_enabled", False)),
        key="portfolio_live_refresh_enabled",
        help="Leave this off for faster page loads. Use Live IBKR page for broker refresh.",
    )

    if live_mode and live_refresh_enabled and gateway is not None:
        try:
            import time

            now = time.time()
            last_refresh = float(
                st.session_state.get("portfolio_last_live_refresh_ts", 0.0)
                or 0.0
            )

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

    positions = _pull_portfolio_positions(
        portfolio_engine
    )

    if not positions:
        positions = _pull_gateway_positions(
            gateway
        )

    if not positions:

        for key in (
            "broker_positions",
            "positions",
            "ibkr_positions",
            "live_positions",
            "portfolio_positions",
        ):

            candidate = st.session_state.get(key)
            positions = _normalize_positions(candidate)

            if positions:
                break

    # =====================================================
    # LIVE MARK-TO-MARKET OVERRIDE
    # =====================================================

    # Hard-disabled for performance.
    # Portfolio page must not call IBKR, yfinance, market.snapshot(),
    # market.get_price(), or live mark-to-market during page render.
    #
    # Portfolio will display cached portfolio prices only.
    # Use Live IBKR / manual refresh workflows for broker/account truth.

    st.caption(
        "Live mark-to-market disabled for fast Portfolio loading. "
        "Cached portfolio prices only."
    )

    # =====================================================
    # EXPOSURE + LEDGER
    # =====================================================

    exposure = _build_exposure(
        positions
    )

    ledger = _pull_ledger(
        portfolio_engine
    )

    # =====================================================
    # PERFORMANCE ANALYTICS
    # =====================================================

    analyzer = PerformanceAnalyzer()

    report = analyzer.analyze(
        ledger=ledger,
        positions_snapshot=positions,
        exposure_snapshot=exposure,
    )

    # =====================================================
    # EXPOSURE DASHBOARD
    # =====================================================

    st.subheader("Portfolio Exposure")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Positions",
        exposure.get("positions", len(positions))
    )

    c2.metric(
        "Gross Exposure",
        f"${report.gross_exposure:,.2f}"
    )

    c3.metric(
        "Long Exposure",
        f"${report.long_exposure:,.2f}"
    )

    c4.metric(
        "Short Exposure",
        f"${report.short_exposure:,.2f}"
    )

    c5, c6, c7, c8 = st.columns(4)

    c5.metric(
        "Net Exposure",
        f"${report.net_exposure:,.2f}"
    )

    c6.metric(
        "Unrealized P&L",
        f"${report.unrealized_pnl:,.2f}"
    )

    c7.metric(
        "Realized P&L",
        f"${report.realized_pnl:,.2f}"
    )

    c8.metric(
        "Total P&L",
        f"${report.total_pnl:,.2f}"
    )

    st.divider()

    # =====================================================
    # PERFORMANCE METRICS
    # =====================================================

    st.subheader("Performance Analytics")

    p1, p2, p3, p4 = st.columns(4)

    p1.metric("Total Trades", report.total_trades)
    p2.metric("Win Rate", f"{report.win_rate * 100:.1f}%")
    p3.metric("Profit Factor", f"{report.profit_factor:.2f}")
    p4.metric("Expectancy", f"${report.expectancy:,.2f}")

    p5, p6, p7, p8 = st.columns(4)

    p5.metric("Winners", report.winners)
    p6.metric("Losers", report.losers)
    p7.metric("Best Trade", f"${report.best_trade:,.2f}")
    p8.metric("Worst Trade", f"${report.worst_trade:,.2f}")

    st.divider()

    # =====================================================
    # POSITION BOOK
    # =====================================================

    st.subheader("Open / Active Positions")

    if positions:

        positions_df = pd.DataFrame(
            list(positions.values())
        )

        ordered_cols = [
            "symbol",
            "side",
            "qty",
            "signed_qty",
            "avg_price",
            "last_price",
            "position_value",
            "unrealized_pnl",
            "realized_pnl",
            "total_pnl",
        ]

        available_cols = [
            col for col in ordered_cols
            if col in positions_df.columns
        ]

        if available_cols:
            positions_df = positions_df[available_cols]

        # Arrow-safe cleanup for Streamlit dataframe rendering.
        for col in positions_df.columns:
            if positions_df[col].dtype == "object":
                positions_df[col] = positions_df[col].astype(str)

        st.dataframe(
            positions_df,
            width="stretch",
        )

    else:
        st.info("No portfolio positions.")

    st.divider()

    # =====================================================
    # TRADE LEDGER
    # =====================================================

    st.subheader("Trade Ledger")

    if ledger:

        ledger_df = pd.DataFrame(ledger)

        preferred_cols = [
            "timestamp",
            "symbol",
            "action",
            "qty",
            "fill_price",
            "realized_delta",
            "source",
        ]

        available_cols = [
            c for c in preferred_cols
            if c in ledger_df.columns
        ]

        if available_cols:
            ledger_df = ledger_df[available_cols]

        # Arrow-safe cleanup for Streamlit dataframe rendering.
        for col in ledger_df.columns:
            if ledger_df[col].dtype == "object":
                ledger_df[col] = ledger_df[col].astype(str)

        st.dataframe(
            ledger_df,
            width="stretch",
        )

    else:
        st.info("No portfolio ledger entries.")

    st.divider()

    # =====================================================
    # PORTFOLIO HEALTH
    # =====================================================

    st.subheader("Portfolio Health")

    health = {
        "Portfolio Engine": "ONLINE",
        "Runtime Positions": len(positions),
        "Ledger Entries": len(ledger),
        "Long Positions": report.long_positions,
        "Short Positions": report.short_positions,
        "Last Error": getattr(portfolio_engine, "last_error", ""),
        "Live Mode": live_mode,
        "Broker Truth Active": live_mode,
    }

    health_df = pd.DataFrame(
        list(health.items()),
        columns=["Metric", "Value"],
    )

    health_df["Metric"] = health_df["Metric"].astype(str)
    health_df["Value"] = health_df["Value"].astype(str)

    st.table(health_df)


def page():
    run_page()