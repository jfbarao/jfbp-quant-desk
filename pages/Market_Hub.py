from __future__ import annotations

import html

import streamlit as st

from pages import Live_Stock as live_stock


def run_page() -> None:
    live_stock.inject_live_stock_responsive_css()

    gateway, market, oms, portfolio_engine = live_stock.init_core()
    live_stock.inject_live_stock_commander_css()

    st.title("📡 Market Hub")
    st.caption(
        "Verify cached market data, inspect a selected symbol, and hand it off to Research, Trade Command, OMS, or Position Command."
    )

    st.markdown(
        """
        <div class="jfbp-live-workflow">
            🚀 Workflow: Market Pulse → Scanner → Research Stock → Market Hub → Trade Command → OMS → Position Command → Journal
        </div>
        """,
        unsafe_allow_html=True,
    )

    live_stock.live_stock_help_expander(
        "How to use this page",
        """
        **Market Hub is the single-symbol cache command center.** It verifies the data already loaded by the app and does not fetch new live data while the page renders, keeping the page fast and stable.

        **Symbol** shows the selected ticker from the current market cache. If the ticker exists in the cache, the page shows its cached price and marks it **ACTIVE**.

        **Hub Size** shows how many symbols are currently stored in the local market cache. A larger hub means other parts of the app have already loaded more market data.

        **Simulate Tick** is only a local test button. It nudges the cached price slightly so you can confirm that the cache and refresh logic are working.
        """,
    )

    symbol = st.text_input(
        "Symbol",
        value=st.session_state.get("selected_symbol", "AAPL"),
        help="Uses the local market cache only. No live market fetch is performed during page render.",
    ).upper().strip()

    if not symbol:
        symbol = "AAPL"

    st.session_state["selected_symbol"] = symbol

    snapshot = live_stock.read_market_snapshot(market)
    data = live_stock.normalize_symbol_payload(snapshot.get(symbol, {}))
    selected_price = data.get("price", "N/A") if data else "N/A"
    selected_status = "ACTIVE" if data else "NO DATA"
    analytics_df = live_stock.build_market_analytics_df(snapshot)

    status_text = "Cache Active" if snapshot else "Cache Empty"
    st.markdown(
        f"""
        <div class="jfbp-live-status-pill">
            <span>📡</span>
            <span>{html.escape(status_text)}</span>
            <span style="color:#64748b;">{len(snapshot)} symbol(s)</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    live_stock.live_stock_tip(
        "Market Hub reads from the app's existing market cache only. Use it to verify what the app already knows, not to force a new quote download."
    )

    live_stock.render_live_stock_commander_report(symbol, data, snapshot)

    # HOTFIX: place handoff immediately after the commander banner.
    live_stock.render_live_stock_handoff_center(symbol, data)

    with st.expander("⚙️ Market Hub Controls", expanded=False):
        live_stock.live_stock_tip(
            "Refresh View reloads the Streamlit page. Simulate Tick tests whether the market cache updates. Clear Selection resets the symbol back to AAPL."
        )

        control_cols = live_stock.jfbp_columns(3)

        with control_cols[0]:
            if st.button("Refresh View", width="stretch"):
                st.rerun()

        with control_cols[1]:
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

        with control_cols[2]:
            if st.button("Clear Selection", width="stretch"):
                st.session_state["selected_symbol"] = "AAPL"
                st.rerun()

    live_stock.render_live_stock_command_brief(symbol, data, snapshot)

    live_stock.live_stock_tip(
        "If Price shows N/A, it usually means that symbol has not been loaded into the market cache yet. Open Scanner, Research Stock, or another market page first, then come back to Market Hub."
    )

    live_stock.render_market_opportunity_dashboard(analytics_df)
    live_stock.render_market_radar(analytics_df)
    live_stock.render_market_watchlists(symbol, analytics_df)

    st.subheader("Market Trend")
    st.caption("Performance visualization and market-cache historical context.")

    if analytics_df.empty:
        st.info("No cached analytics available for trend visualization.")
    else:
        move_df = analytics_df.dropna(subset=["Move %"]).sort_values("Move %", ascending=False).head(15)
        if not move_df.empty:
            st.markdown("**Move Distribution (Top 15)**")
            st.bar_chart(move_df.set_index("Symbol")[["Move %"]], height=320, use_container_width=True)

        vol_df = analytics_df.sort_values("Volume", ascending=False).head(15)
        if (vol_df["Volume"] > 0).any():
            st.markdown("**Volume Leadership (Top 15)**")
            st.bar_chart(vol_df.set_index("Symbol")[["Volume"]], height=280, use_container_width=True)

    # Keep cache command center and cached-universe table in the final section.
    live_stock.render_live_stock_snapshot_tables(
        symbol=symbol,
        selected_price=selected_price,
        selected_status=selected_status,
        snapshot=snapshot,
    )


def page() -> None:
    run_page()


if __name__ == "__main__":
    run_page()
