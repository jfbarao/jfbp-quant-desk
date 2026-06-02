# =========================================================
# 📊 JFBP LIVE STOCK PAGE — TABLE VERSION
# FAST / CACHE-ONLY RENDER
# =========================================================

import streamlit as st
import pandas as pd

from core.bootstrap import init_core


def run_page():

    gateway, market, oms, portfolio_engine = init_core()

    st.title("📊 Live Stock")
    st.caption("LIVE_STOCK_TABLE_VERSION_ACTIVE — cache-only render")

    symbol = st.text_input(
        "Symbol",
        value=st.session_state.get("selected_symbol", "AAPL"),
    ).upper().strip()

    st.session_state["selected_symbol"] = symbol

    # =====================================================
    # CACHE-ONLY MARKET SNAPSHOT
    # =====================================================

    snapshot = {}

    if market is not None:
        for attr in (
            "prices",
            "last_prices",
            "data",
            "snapshot_cache",
            "cache",
            "last_snapshot",
        ):
            try:
                value = getattr(market, attr, None)

                if isinstance(value, dict):
                    snapshot = value
                    break

            except Exception:
                pass

    data = snapshot.get(symbol, {})

    if not isinstance(data, dict):
        data = {
            "price": data,
        }

    # =====================================================
    # HEADER METRICS
    # =====================================================

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Price",
            data.get("price", "N/A") if data else "N/A",
        )

    with col2:
        st.metric("Hub Size", len(snapshot))

    st.divider()

    # =====================================================
    # CONTROLS
    # =====================================================

    colA, colB, colC = st.columns(3)

    with colA:
        if st.button("Refresh View", width="stretch"):
            st.rerun()

    with colB:
        if st.button("Simulate Tick", width="stretch"):
            current_price = data.get("price", 0) if data else 0

            try:
                new_price = round(float(current_price or 0) * 1.001, 2)
            except Exception:
                new_price = 0.0

            if market is not None and hasattr(market, "update_price"):
                try:
                    market.update_price(symbol, new_price)
                except Exception:
                    pass

            st.rerun()

    with colC:
        if st.button("Clear Selection", width="stretch"):
            st.session_state["selected_symbol"] = "AAPL"
            st.rerun()

    st.divider()

    # =====================================================
    # SELECTED SYMBOL
    # =====================================================

    st.subheader("Selected Symbol Table")

    selected_df = pd.DataFrame([
        {
            "Symbol": str(symbol),
            "Price": str(data.get("price", "N/A") if data else "N/A"),
            "Status": "ACTIVE" if data else "NO DATA",
        }
    ])

    st.dataframe(
        selected_df,
        width="stretch",
    )

    # =====================================================
    # MARKET SNAPSHOT TABLE
    # =====================================================

    st.subheader("Full Market Snapshot Table")

    if snapshot:
        rows = []

        for sym, payload in snapshot.items():
            if isinstance(payload, dict):
                price = payload.get("price", "N/A")
            else:
                price = payload

            rows.append({
                "Symbol": str(sym),
                "Price": str(price),
            })

        market_df = pd.DataFrame(rows)

        st.dataframe(
            market_df,
            width="stretch",
        )

    else:
        st.warning(
            "Market snapshot cache is empty. "
            "No live market fetch was performed during page render."
        )