# =========================================================
# 📓 JFBP JOURNAL PAGE v28.0
# TRADE JOURNAL INTELLIGENCE
# =========================================================

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.bootstrap import init_core
from analytics.performance import PerformanceAnalyzer


def page():
    run_page()


def run_page():

    gateway, market, oms, portfolio_engine = init_core()

    st.title("📓 Journal Intelligence")

    if portfolio_engine is None:
        st.error("Portfolio engine unavailable.")
        return

    ledger = []
    positions = {}
    exposure = {}

    if hasattr(portfolio_engine, "ledger_snapshot"):
        ledger = portfolio_engine.ledger_snapshot()

    if hasattr(portfolio_engine, "snapshot"):
        positions = portfolio_engine.snapshot()

    if hasattr(portfolio_engine, "exposure_snapshot"):
        exposure = portfolio_engine.exposure_snapshot()

    analyzer = PerformanceAnalyzer()

    report = analyzer.analyze(
        ledger=ledger,
        positions_snapshot=positions,
        exposure_snapshot=exposure,
    )

    # =====================================================
    # SUMMARY
    # =====================================================

    st.subheader("Performance Summary")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Trades", report.total_trades)
    c2.metric("Win Rate", f"{report.win_rate * 100:.1f}%")
    c3.metric("Profit Factor", f"{report.profit_factor:.2f}")
    c4.metric("Expectancy", f"${report.expectancy:,.2f}")

    c5, c6, c7, c8 = st.columns(4)

    c5.metric("Winners", report.winners)
    c6.metric("Losers", report.losers)
    c7.metric("Best Trade", f"${report.best_trade:,.2f}")
    c8.metric("Worst Trade", f"${report.worst_trade:,.2f}")

    c9, c10, c11, c12 = st.columns(4)

    c9.metric("Realized P&L", f"${report.realized_pnl:,.2f}")
    c10.metric("Unrealized P&L", f"${report.unrealized_pnl:,.2f}")
    c11.metric("Total P&L", f"${report.total_pnl:,.2f}")
    c12.metric("Open Positions", len(positions))

    st.divider()

    # =====================================================
    # LEDGER
    # =====================================================

    st.subheader("Trade Ledger")

    if not ledger:
        st.info("No trades available yet.")
        return

    df = pd.DataFrame(ledger)

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            errors="coerce",
        )

    # =====================================================
    # FILTERS
    # =====================================================

    f1, f2, f3, f4 = st.columns(4)

    with f1:
        symbols = sorted(df["symbol"].dropna().unique()) if "symbol" in df.columns else []
        selected_symbols = st.multiselect("Symbols", symbols)

    with f2:
        actions = sorted(df["action"].dropna().unique()) if "action" in df.columns else []
        selected_actions = st.multiselect("Actions", actions)

    with f3:
        sources = sorted(df["source"].dropna().unique()) if "source" in df.columns else []
        selected_sources = st.multiselect("Sources", sources)

    with f4:
        pnl_filter = st.selectbox(
            "P&L Filter",
            ["All", "Winners", "Losers", "Breakeven"],
        )

    filtered = df.copy()

    if selected_symbols and "symbol" in filtered.columns:
        filtered = filtered[filtered["symbol"].isin(selected_symbols)]

    if selected_actions and "action" in filtered.columns:
        filtered = filtered[filtered["action"].isin(selected_actions)]

    if selected_sources and "source" in filtered.columns:
        filtered = filtered[filtered["source"].isin(selected_sources)]

    pnl_col = "realized_delta" if "realized_delta" in filtered.columns else "realized_pnl"

    if pnl_col in filtered.columns:
        filtered[pnl_col] = pd.to_numeric(filtered[pnl_col], errors="coerce").fillna(0.0)

        if pnl_filter == "Winners":
            filtered = filtered[filtered[pnl_col] > 0]
        elif pnl_filter == "Losers":
            filtered = filtered[filtered[pnl_col] < 0]
        elif pnl_filter == "Breakeven":
            filtered = filtered[filtered[pnl_col] == 0]

    preferred_cols = [
        "timestamp",
        "symbol",
        "action",
        "qty",
        "fill_price",
        "old_side",
        "old_qty",
        "new_side",
        "new_qty",
        "realized_delta",
        "realized_pnl",
        "source",
        "fill_id",
        "order_id",
    ]

    display_cols = [
        col for col in preferred_cols
        if col in filtered.columns
    ]

    st.dataframe(
        filtered[display_cols] if display_cols else filtered,
        use_container_width=True,
    )

    st.divider()

    # =====================================================
    # SYMBOL PERFORMANCE
    # =====================================================

    st.subheader("Symbol Performance")

    if "symbol" in df.columns and pnl_col in df.columns:

        symbol_perf = (
            df.assign(
                pnl=pd.to_numeric(df[pnl_col], errors="coerce").fillna(0.0)
            )
            .groupby("symbol", as_index=False)
            .agg(
                trades=("symbol", "count"),
                realized_pnl=("pnl", "sum"),
                avg_trade=("pnl", "mean"),
                best_trade=("pnl", "max"),
                worst_trade=("pnl", "min"),
            )
            .sort_values("realized_pnl", ascending=False)
        )

        st.dataframe(
            symbol_perf,
            use_container_width=True,
        )

    else:
        st.info("Not enough data for symbol performance.")

    st.divider()

    # =====================================================
    # LONG / SHORT + ACTION BREAKDOWN
    # =====================================================

    st.subheader("Trade Breakdown")

    b1, b2 = st.columns(2)

    with b1:
        if "action" in df.columns:
            action_counts = (
                df["action"]
                .value_counts()
                .reset_index()
            )
            action_counts.columns = ["Action", "Count"]
            st.dataframe(action_counts, use_container_width=True)
        else:
            st.info("No action data.")

    with b2:
        if "new_side" in df.columns:
            side_counts = (
                df["new_side"]
                .value_counts()
                .reset_index()
            )
            side_counts.columns = ["Post-Trade Side", "Count"]
            st.dataframe(side_counts, use_container_width=True)
        else:
            st.info("No side data.")

    st.divider()

    # =====================================================
    # DAILY PERFORMANCE
    # =====================================================

    st.subheader("Daily Review")

    if "timestamp" in df.columns and pnl_col in df.columns:

        daily_df = df.copy()

        daily_df["date"] = daily_df["timestamp"].dt.date
        daily_df["pnl"] = pd.to_numeric(
            daily_df[pnl_col],
            errors="coerce",
        ).fillna(0.0)

        daily_perf = (
            daily_df.groupby("date", as_index=False)
            .agg(
                trades=("symbol", "count"),
                realized_pnl=("pnl", "sum"),
                avg_trade=("pnl", "mean"),
            )
            .sort_values("date", ascending=False)
        )

        st.dataframe(
            daily_perf,
            use_container_width=True,
        )

    else:
        st.info("No timestamp/P&L data available for daily review.")

    st.divider()

    # =====================================================
    # MANUAL REVIEW NOTE
    # =====================================================

    st.subheader("Manual Trade Review")

    st.info(
        "Manual notes are preview-only in v28.0. "
        "Next version can persist notes to SQLite."
    )

    n1, n2, n3 = st.columns(3)

    with n1:
        selected_symbol = st.text_input("Symbol").upper().strip()
        setup_grade = st.selectbox("Setup Grade", ["A", "B", "C", "D", "F"])

    with n2:
        execution_grade = st.selectbox("Execution Grade", ["A", "B", "C", "D", "F"])
        mistake = st.checkbox("Mistake?")

    with n3:
        tag = st.selectbox(
            "Tag",
            [
                "None",
                "Perfect Execution",
                "FOMO",
                "Revenge Trade",
                "Early Exit",
                "Late Entry",
                "Thesis Break",
                "Good Process",
                "Bad Process",
            ],
        )

    notes = st.text_area("Notes")

    if st.button("Preview Journal Note", use_container_width=True):
        st.write(
            {
                "symbol": selected_symbol,
                "setup_grade": setup_grade,
                "execution_grade": execution_grade,
                "mistake": mistake,
                "tag": tag,
                "notes": notes,
            }
        )

    st.divider()

    # =====================================================
    # HEALTH
    # =====================================================

    st.subheader("Journal Health")

    health = {
        "Portfolio Engine": "ONLINE",
        "Ledger Entries": len(ledger),
        "Filtered Entries": len(filtered),
        "Positions": len(positions),
        "Bootstrap Recovery": st.session_state.get("bootstrap_recovery_status", ""),
        "Runtime/Audit Recovery OK": st.session_state.get(
            "bootstrap_recovered_ok",
            False,
        ),
    }

    st.table(
        pd.DataFrame(
            list(health.items()),
            columns=["Metric", "Value"],
        )
    )