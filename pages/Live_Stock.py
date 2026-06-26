# =========================================================
# 📡 JFBP MARKET HUB PAGE — v1.0 FREEZE READY
# CACHE-ONLY MARKET HUB + SYMBOL HANDOFF WORKFLOW
# JFBP Quant Desk
# =========================================================

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from core.bootstrap import init_core
from core.responsive import inject_responsive_css as jfbp_inject_responsive_css
from core.responsive import columns as jfbp_columns
from core.ui_cards import inject_card_css as jfbp_inject_card_css
from core.ui_cards import metric_card as jfbp_metric_card
from core.ui_cards import hero_card as jfbp_hero_card


# =========================================================
# RESPONSIVE CSS
# =========================================================

def inject_live_stock_responsive_css() -> None:
    """Visual-only mobile guardrails for Market Hub.

    Keeps the page cache-only and preserves the existing behavior while making
    the controls, cards, and tables behave cleanly on iPhone/Safari and narrow
    desktop windows.
    """

    jfbp_inject_responsive_css(max_width=1500)
    jfbp_inject_card_css()
    st.markdown(
        """
        <style>
            .block-container {
                max-width: 1500px !important;
                padding-top: 1.4rem !important;
                padding-bottom: 2.5rem !important;
                padding-left: clamp(0.9rem, 2.4vw, 2.25rem) !important;
                padding-right: clamp(0.9rem, 2.4vw, 2.25rem) !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }

            h1 {
                font-size: var(--jfbp-type-h1, clamp(1.75rem, 3.6vw, 2.45rem)) !important;
                line-height: 1.12 !important;
                font-weight: 850 !important;
                color: #1f2937 !important;
            }

            h2, h3 {
                font-size: var(--jfbp-type-section, clamp(1.02rem, 1.9vw, 1.22rem)) !important;
                line-height: 1.18 !important;
                font-weight: 850 !important;
                color: #1f2937 !important;
            }

            div[data-testid="stHorizontalBlock"] {
                gap: 0.85rem !important;
                align-items: stretch !important;
            }

            div[data-testid="stHorizontalBlock"] > div,
            div[data-testid="column"] {
                min-width: 0 !important;
            }

            div[data-testid="stMetric"] {
                background: #f7fbff;
                border: 1px solid #d9e8ff;
                border-radius: 14px;
                padding: 14px;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
                min-height: 92px;
            }

            [data-testid="stMetricLabel"],
            [data-testid="stMetricValue"] {
                white-space: normal !important;
                overflow: visible !important;
                text-overflow: clip !important;
                overflow-wrap: anywhere !important;
            }

            div[data-testid="stMetricLabel"] {
                font-size: 0.82rem !important;
                font-weight: 800 !important;
                color: #48617a !important;
                text-transform: uppercase;
                letter-spacing: 0.03em;
            }

            div[data-testid="stMetricValue"] {
                font-size: 1.25rem !important;
                font-weight: 850 !important;
                color: #1f2937 !important;
            }

            div[data-testid="stDataFrame"] {
                width: 100% !important;
                max-width: 100% !important;
                overflow-x: auto !important;
                border-radius: 12px !important;
            }

            div[data-testid="stDataFrame"] * {
                overflow-wrap: anywhere !important;
            }

            .stButton > button {
                border-radius: 10px !important;
                font-weight: 750 !important;
                min-height: 40px !important;
                border: 1px solid #d7e3f5 !important;
            }

            .jfbp-live-card {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 16px;
                padding: 1.0rem 1.1rem;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
                margin-bottom: 0.85rem;
                overflow-wrap: anywhere;
            }

            .jfbp-live-card-title {
                font-size: 0.76rem;
                font-weight: 850;
                color: #52677d;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                margin-bottom: 0.35rem;
            }

            .jfbp-live-card-value {
                font-size: 1.45rem;
                font-weight: 900;
                color: #1f2937;
                line-height: 1.12;
            }

            .jfbp-live-card-note {
                font-size: 0.84rem;
                color: #64748b;
                margin-top: 0.35rem;
                line-height: 1.35;
            }

            .jfbp-live-status-pill {
                display: inline-flex;
                align-items: center;
                gap: 0.45rem;
                border-radius: 999px;
                padding: 0.28rem 0.62rem;
                font-weight: 780;
                font-size: 0.84rem;
                background: #eff6ff;
                color: #1d4ed8;
                border: 1px solid #bfdbfe;
                margin: 0.20rem 0 0.60rem 0;
                overflow-wrap: anywhere;
            }

            @media (max-width: 1180px) {
                .block-container {
                    max-width: 100% !important;
                    padding-left: 1.25rem !important;
                    padding-right: 1.25rem !important;
                }

                div[data-testid="stHorizontalBlock"] {
                    flex-wrap: wrap !important;
                }

                div[data-testid="stHorizontalBlock"] > div,
                div[data-testid="column"] {
                    flex: 1 1 100% !important;
                    width: 100% !important;
                    min-width: 100% !important;
                }
            }

            @media (max-width: 760px) {
                .block-container {
                    padding-left: 0.9rem !important;
                    padding-right: 0.9rem !important;
                }

                div[data-testid="stMetric"] {
                    padding: 11px 12px !important;
                    min-height: 82px !important;
                }

                div[data-testid="stMetricValue"] {
                    font-size: 1.08rem !important;
                }

                div[data-testid="stDataFrame"] {
                    font-size: 0.82rem !important;
                }

                .jfbp-live-card {
                    padding: 0.9rem 0.95rem;
                }

                .jfbp-live-card-value {
                    font-size: 1.25rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# HELPERS
# =========================================================

def safe_price_text(value) -> str:
    if value is None:
        return "N/A"

    try:
        numeric = float(value)
        return f"${numeric:,.2f}"
    except Exception:
        text = str(value or "").strip()
        return text if text else "N/A"


def compact_card(label: str, value, note: str = "") -> None:
    note_html = ""
    if note:
        note_html = f'<div class="jfbp-live-card-note">{html.escape(str(note))}</div>'

    st.markdown(
        f"""
        <div class="jfbp-live-card">
            <div class="jfbp-live-card-title">{html.escape(str(label))}</div>
            <div class="jfbp-live-card-value">{html.escape(str(value))}</div>
            {note_html}
        </div>
        """,
        unsafe_allow_html=True,
    )




def live_stock_tip(text: str) -> None:
    """Small educational helper used across Market Hub."""
    st.caption(f"💡 {text}")


def live_stock_help_expander(title: str, body: str) -> None:
    """Compact explanatory expander for the Market Hub page."""
    with st.expander(f"ℹ️ {title}", expanded=False):
        st.markdown(body)

def read_market_snapshot(market) -> dict:
    snapshot = {}

    if market is None:
        return snapshot

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

    return snapshot if isinstance(snapshot, dict) else {}


def normalize_symbol_payload(payload) -> dict:
    if isinstance(payload, dict):
        return payload

    if payload is None:
        return {}

    return {"price": payload}


def build_market_snapshot_df(snapshot: dict) -> pd.DataFrame:
    rows = []

    for sym, payload in snapshot.items():
        payload = normalize_symbol_payload(payload)

        row = {
            "Symbol": str(sym).upper().strip(),
            "Price": safe_price_text(payload.get("price", "N/A")),
        }

        for optional_col in ("bid", "ask", "last", "volume", "timestamp"):
            if optional_col in payload:
                label = optional_col.replace("_", " ").title()
                row[label] = payload.get(optional_col)

        rows.append(row)

    if not rows:
        return pd.DataFrame(columns=["Symbol", "Price"])

    return pd.DataFrame(rows).sort_values("Symbol").reset_index(drop=True)


# =========================================================
# COMMANDER LAYER — MARKET HUB v1.0
# =========================================================

def inject_live_stock_commander_css() -> None:
    """Institutional command-center visual layer for Market Hub v1.0."""

    st.markdown(
        """
        <style>
            .jfbp-live-workflow {
                background: #eff6ff;
                border: 1px solid #bfdbfe;
                border-radius: 12px;
                padding: 0.72rem 0.82rem;
                color: #1d4ed8;
                font-weight: 750;
                margin: 0.50rem 0 0.78rem 0;
                line-height: 1.4;
            }

            .jfbp-live-hero {
                border: 1px solid #bbf7d0;
                background: #ecfdf5;
                border-radius: 18px;
                padding: 0.88rem 0.92rem;
                margin: 0.60rem 0 0.82rem 0;
                box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05);
            }
            .jfbp-live-hero.watch {
                border-color: #fde68a;
                background: #fffbeb;
            }
            .jfbp-live-hero.risk {
                border-color: #fecaca;
                background: #fef2f2;
            }
            .jfbp-live-hero.info {
                border-color: #bfdbfe;
                background: #eff6ff;
            }

            .jfbp-live-kicker {
                font-size: var(--jfbp-type-card-label, 0.72rem);
                letter-spacing: 0.055em;
                text-transform: uppercase;
                color: #64748b;
                font-weight: 850;
                margin-bottom: 0.24rem;
            }

            .jfbp-live-hero-title {
                font-size: clamp(1.22rem, 2.35vw, 1.62rem);
                line-height: 1.14;
                font-weight: 880;
                color: #166534;
                margin-bottom: 0.30rem;
            }
            .jfbp-live-hero.watch .jfbp-live-hero-title { color: #92400e; }
            .jfbp-live-hero.risk .jfbp-live-hero-title { color: #991b1b; }
            .jfbp-live-hero.info .jfbp-live-hero-title { color: #1d4ed8; }

            .jfbp-live-summary {
                font-size: var(--jfbp-type-body, 0.94rem);
                color: #1f2937;
                font-weight: 700;
                line-height: 1.38;
            }

            .jfbp-live-action {
                margin-top: 0.36rem;
                background: #ffffff;
                border: 1px solid #dbe3ef;
                border-radius: 12px;
                padding: 0.60rem 0.78rem;
                color: #111827;
                font-size: var(--jfbp-type-body, 0.94rem);
                font-weight: 820;
                line-height: 1.35;
            }

            .jfbp-live-table-guard {
                margin-bottom: 0.90rem;
            }

            @media (max-width: 760px) {
                .jfbp-live-workflow {
                    font-size: 0.86rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def live_stock_metric_card(label: str, value, detail: str = "", tone: str = "neutral") -> None:
    """Shared JFBP card wrapper for Market Hub command metrics."""
    jfbp_metric_card(label, value, detail, tone=tone)


def _payload_timestamp(payload: dict) -> str:
    if not isinstance(payload, dict):
        return "N/A"

    for key in ("timestamp", "time", "updated", "last_update", "last_updated"):
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)

    return "N/A"


def _payload_volume(payload: dict) -> str:
    if not isinstance(payload, dict):
        return "N/A"

    value = payload.get("volume")
    if value in (None, ""):
        return "N/A"

    try:
        return f"{float(value):,.0f}"
    except Exception:
        return str(value)


def _payload_bid_ask(payload: dict) -> str:
    if not isinstance(payload, dict):
        return "N/A"

    bid = payload.get("bid")
    ask = payload.get("ask")

    if bid in (None, "") and ask in (None, ""):
        return "N/A"

    return f"{safe_price_text(bid)} / {safe_price_text(ask)}"


def _live_stock_status(snapshot: dict, data: dict) -> tuple[str, str, str, str]:
    if not snapshot:
        return (
            "CACHE EMPTY",
            "risk",
            "No market symbols are currently cached.",
            "Open Scanner, Research Stock, or another market page to populate the cache.",
        )

    if data:
        return (
            "ACTIVE",
            "good",
            "Selected symbol is present in the market cache.",
            "Use Market Hub to verify cached price state before moving to Research Stock or Scanner.",
        )

    return (
        "NO DATA",
        "warning",
        "Selected symbol is not present in the current market cache.",
        "Load this symbol from Scanner or Research Stock, then return here to verify the cache.",
    )


def render_live_stock_commander_report(symbol: str, data: dict, snapshot: dict) -> None:
    status, tone, summary, action = _live_stock_status(snapshot, data)
    hero_class = "risk" if tone == "risk" else "watch" if tone == "warning" else ""

    price = safe_price_text(data.get("price", "N/A")) if data else "N/A"
    hub_size = len(snapshot)

    st.subheader("🎖️ Commander Market Hub Report")
    st.caption("Fast single-symbol read: cache state, price, hub size, and next action.")

    st.markdown(
        f"""
        <div class="jfbp-live-hero {hero_class}">
            <div class="jfbp-live-kicker">Institutional Market Hub Command · Cache-Only</div>
            <div class="jfbp-live-hero-title">📡 MARKET HUB STATUS: {html.escape(status)}</div>
            <div class="jfbp-live-summary">
                Symbol: {html.escape(symbol)} ·
                Cached Price: {html.escape(price)} ·
                Hub Size: {hub_size} symbol(s) ·
                Render Mode: CACHE ONLY ·
                Live Fetch: OFF
            </div>
            <div class="jfbp-live-action">ACTION: {html.escape(action)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_live_stock_command_brief(symbol: str, data: dict, snapshot: dict) -> None:
    status, tone, _, _ = _live_stock_status(snapshot, data)

    st.subheader("Command Brief")
    st.caption("One-glance operational state for the selected cached symbol.")

    c1, c2, c3, c4 = jfbp_columns(4)

    with c1:
        live_stock_metric_card(
            "Selected Symbol",
            symbol,
            status,
            tone=tone,
        )

    with c2:
        live_stock_metric_card(
            "Cached Price",
            safe_price_text(data.get("price", "N/A")) if data else "N/A",
            "Last known cache value",
            tone="good" if data else "warning",
        )

    with c3:
        live_stock_metric_card(
            "Hub Size",
            len(snapshot),
            "Cached market symbols",
            tone="info" if snapshot else "warning",
        )

    with c4:
        live_stock_metric_card(
            "Render Mode",
            "CACHE ONLY",
            "No live fetch during render",
            tone="good",
        )

    d1, d2, d3, d4 = jfbp_columns(4)

    with d1:
        live_stock_metric_card(
            "Bid / Ask",
            _payload_bid_ask(data),
            "If available from cache",
            tone="neutral",
        )

    with d2:
        live_stock_metric_card(
            "Volume",
            _payload_volume(data),
            "If available from cache",
            tone="neutral",
        )

    with d3:
        live_stock_metric_card(
            "Timestamp",
            _payload_timestamp(data),
            "Cached update marker",
            tone="info" if data and _payload_timestamp(data) != "N/A" else "neutral",
        )

    with d4:
        live_stock_metric_card(
            "Data Quality",
            "GOOD" if data else "MISSING",
            "Selected symbol cache check",
            tone="good" if data else "warning",
        )


def render_live_stock_handoff_center(symbol: str, data: dict) -> None:
    st.subheader("🧭 Symbol Handoff Center")
    st.caption("Prepare the selected symbol for the next page in the research and execution workflow.")

    h1, h2, h3, h4, h5 = jfbp_columns(5)

    with h1:
        if st.button("Research", width="stretch", key="live_stock_send_research"):
            st.session_state["selected_symbol"] = symbol
            st.session_state["research_symbol"] = symbol
            st.session_state["research_ticker"] = symbol
            st.session_state["research_ticker_input"] = symbol
            st.session_state["jfbp_main_navigation"] = "Research Stock"
            st.rerun()

    with h2:
        if st.button("Scanner", width="stretch", key="live_stock_send_scanner"):
            st.session_state["selected_symbol"] = symbol
            st.session_state["scanner_focus_symbol"] = symbol
            st.session_state["jfbp_main_navigation"] = "Scanner"
            st.rerun()

    with h3:
        if st.button("Trade Command", width="stretch", key="live_stock_send_trade_command"):
            st.session_state["selected_symbol"] = symbol
            st.session_state["trade_command_symbol"] = symbol
            st.session_state["jfbp_main_navigation"] = "Trade Command Center"
            st.rerun()

    with h4:
        if st.button("OMS", width="stretch", key="live_stock_send_oms"):
            st.session_state["selected_symbol"] = symbol
            st.session_state["oms_order_symbol"] = symbol
            st.session_state["jfbp_main_navigation"] = "OMS Execution"
            st.rerun()

    with h5:
        if st.button("Position Command", width="stretch", key="live_stock_send_position_command"):
            st.session_state["selected_symbol"] = symbol
            st.session_state["position_command_symbol"] = symbol
            st.session_state["jfbp_main_navigation"] = "Position Command Center"
            st.rerun()

    if not data:
        st.warning(
            "Selected symbol is not cached yet. Open Scanner or Research Stock first if you need a cached price before handoff."
        )


def _cache_last_update(snapshot: dict) -> str:
    """Return the most recent timestamp-like value found in the market cache."""
    if not snapshot:
        return "N/A"

    timestamps = []

    for payload in snapshot.values():
        payload = normalize_symbol_payload(payload)
        value = _payload_timestamp(payload)
        if value != "N/A":
            timestamps.append(str(value))

    if not timestamps:
        return "N/A"

    return sorted(timestamps)[-1]


def _cache_command_status(snapshot: dict, symbol: str, data: dict) -> tuple[str, str, str]:
    """Classify the market-cache command state for the diagnostic universe table."""
    if not snapshot:
        return (
            "EMPTY",
            "risk",
            "No market cache available. Run Scanner, Research Stock, or Market Pulse first.",
        )

    if data:
        return (
            "OPERATIONAL",
            "good",
            f"{len(snapshot)} symbols cached and {symbol} is available for handoff.",
        )

    return (
        "PARTIAL",
        "warning",
        f"{len(snapshot)} symbols cached, but {symbol} is not in the cache yet.",
    )


def render_market_cache_command_center(symbol: str, data: dict, snapshot: dict) -> None:
    """Institutional cache command module above the full market snapshot table."""
    cache_status, tone, message = _cache_command_status(snapshot, symbol, data)
    hero_class = "risk" if tone == "risk" else "watch" if tone == "warning" else ""
    last_update = _cache_last_update(snapshot)

    st.subheader("📡 Market Cache Command Center")
    st.caption(
        "Command view of the symbols currently held in the JFBP market cache. "
        "This page verifies cached state only and does not force a new market download."
    )

    st.markdown(
        f"""
        <div class="jfbp-live-hero {hero_class}">
            <div class="jfbp-live-kicker">Institutional Market Cache Command</div>
            <div class="jfbp-live-hero-title">📡 CACHE STATUS: {html.escape(cache_status)}</div>
            <div class="jfbp-live-summary">{html.escape(message)}</div>
            <div class="jfbp-live-action">ACTION: Use Scanner and Research Stock for analysis. Use Market Hub for verification and symbol handoff.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = jfbp_columns(4)

    with c1:
        live_stock_metric_card(
            "Cached Symbols",
            len(snapshot),
            "Market-cache universe size",
            tone="info" if snapshot else "warning",
        )

    with c2:
        live_stock_metric_card(
            "Active Symbol",
            symbol,
            "Cached" if data else "Not cached",
            tone="good" if data else "warning",
        )

    with c3:
        live_stock_metric_card(
            "Cache Health",
            "GOOD" if data else "PARTIAL" if snapshot else "EMPTY",
            "Selected-symbol check",
            tone=tone,
        )

    with c4:
        live_stock_metric_card(
            "Last Cache Update",
            last_update,
            "Latest timestamp marker" if last_update != "N/A" else "No timestamp in cache",
            tone="info" if last_update != "N/A" else "neutral",
        )

def render_live_stock_snapshot_tables(symbol: str, selected_price, selected_status: str, snapshot: dict) -> None:
    data = normalize_symbol_payload(snapshot.get(symbol, {})) if snapshot else {}

    render_market_cache_command_center(symbol, data, snapshot)

    with st.expander("📡 Cached Market Universe", expanded=False):
        live_stock_tip(
            "Symbols currently available in the JFBP market cache. Use Scanner and Research Stock for analysis. Use Market Hub for verification and handoff."
        )

        if snapshot:
            market_df = build_market_snapshot_df(snapshot)

            st.dataframe(
                market_df,
                width="stretch",
                hide_index=True,
                height=min(520, max(220, 38 * (len(market_df) + 1))),
            )

            st.caption(
                "Cached market universe is diagnostic. For full analysis, use Research Stock. For rankings, use Scanner."
            )

        else:
            st.warning(
                "Market snapshot cache is empty. "
                "No live market fetch was performed during page render."
            )


# =========================================================
# PAGE
# =========================================================

def run_page():

    inject_live_stock_responsive_css()

    gateway, market, oms, portfolio_engine = init_core()

    inject_live_stock_commander_css()

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

    live_stock_help_expander(
        "How to use this page",
        """
        **Market Hub is the single-symbol cache command center.** It verifies the data already loaded by the app and does not fetch new live data while the page renders, keeping the page fast and stable.

        **Symbol** shows the selected ticker from the current market cache. If the ticker exists in the cache, the page shows its cached price and marks it **ACTIVE**.

        **Hub Size** shows how many symbols are currently stored in the local market cache. A larger hub means other parts of the app have already loaded more market data.

        **Simulate Tick** is only a local test button. It nudges the cached price slightly so you can confirm that the cache and refresh logic are working.
        """,
    )

    snapshot = read_market_snapshot(market)

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

    live_stock_tip(
        "Market Hub reads from the app's existing market cache only. Use it to verify what the app already knows, not to force a new quote download."
    )

    symbol = st.text_input(
        "Symbol",
        value=st.session_state.get("selected_symbol", "AAPL"),
        help="Uses the local market cache only. No live market fetch is performed during page render.",
    ).upper().strip()

    if not symbol:
        symbol = "AAPL"

    st.session_state["selected_symbol"] = symbol

    data = normalize_symbol_payload(snapshot.get(symbol, {}))
    selected_price = data.get("price", "N/A") if data else "N/A"
    selected_status = "ACTIVE" if data else "NO DATA"

    render_live_stock_commander_report(symbol, data, snapshot)
    render_live_stock_handoff_center(symbol, data)
    render_live_stock_command_brief(symbol, data, snapshot)

    live_stock_tip(
        "If Price shows N/A, it usually means that symbol has not been loaded into the market cache yet. Open Scanner, Research Stock, or another market page first, then come back to Market Hub."
    )

    # =====================================================
    # CONTROLS
    # =====================================================

    with st.expander("⚙️ Market Hub Controls", expanded=False):
        live_stock_tip(
            "Refresh View reloads the Streamlit page. Simulate Tick tests whether the market cache updates. Clear Selection resets the symbol back to AAPL."
        )

        control_cols = jfbp_columns(3)

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

    st.divider()

    # =====================================================
    # CACHE DIAGNOSTICS
    # =====================================================

    render_live_stock_snapshot_tables(
        symbol=symbol,
        selected_price=selected_price,
        selected_status=selected_status,
        snapshot=snapshot,
    )


def page() -> None:
    run_page()


if __name__ == "__main__":
    run_page()
