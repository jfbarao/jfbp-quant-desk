# =========================================================
# 🧭 JFBP USER GUIDE CENTER v2.0
# Guided onboarding + workflow map + execution safety manual
# JFBP Quant Desk
# =========================================================

from __future__ import annotations

import html
from typing import Any, Dict, List, Tuple

import streamlit as st


# =========================================================
# RESPONSIVE HELPERS
# =========================================================

def inject_navigation_guide_css() -> None:
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1.4rem !important;
                padding-bottom: 2.5rem !important;
                max-width: 1500px !important;
                padding-left: clamp(0.9rem, 2.2vw, 2.6rem) !important;
                padding-right: clamp(0.9rem, 2.2vw, 2.6rem) !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }

            h1 {
                font-size: clamp(1.9rem, 4vw, 2.70rem) !important;
                font-weight: 900 !important;
                line-height: 1.08 !important;
                color: #1f2937 !important;
            }

            h2, h3 {
                font-size: clamp(1.12rem, 2.35vw, 1.55rem) !important;
                font-weight: 850 !important;
                line-height: 1.2 !important;
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

            div[data-testid="stDataFrame"] {
                width: 100% !important;
                max-width: 100% !important;
                overflow-x: auto !important;
                border-radius: 12px !important;
            }

            div[data-testid="stAlert"] {
                overflow-wrap: anywhere !important;
                word-break: normal !important;
            }

            .stButton > button {
                border-radius: 10px !important;
                font-weight: 750 !important;
                min-height: 38px !important;
                border: 1px solid #d7e3f5 !important;
            }

            .guide-hero {
                border: 1px solid #bfdbfe;
                background:
                    radial-gradient(circle at top left, rgba(37,99,235,0.14), transparent 34%),
                    linear-gradient(135deg, rgba(239,246,255,0.96), rgba(248,250,252,0.96));
                border-radius: 22px;
                padding: 1.25rem 1.35rem;
                margin: 0.75rem 0 1rem 0;
                box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05);
                overflow: hidden;
            }

            .guide-hero-kicker {
                color:#64748b;
                font-size:0.72rem;
                font-weight:950;
                letter-spacing:0.08em;
                text-transform:uppercase;
                margin-bottom:0.32rem;
            }

            .guide-hero-title {
                color:#1d4ed8;
                font-size:clamp(1.85rem, 4vw, 3.05rem);
                font-weight:1000;
                line-height:1.02;
                margin-bottom:0.55rem;
                overflow-wrap:anywhere;
            }

            .guide-hero-text {
                color:#334155;
                font-size:clamp(0.94rem, 1.5vw, 1.10rem);
                line-height:1.45;
                font-weight:760;
                max-width: 1100px;
            }

            .guide-flow {
                background: #eff6ff;
                border: 1px solid #bfdbfe;
                border-radius: 14px;
                padding: 0.9rem 1rem;
                margin: 0.65rem 0 1rem 0;
                overflow-wrap: anywhere;
                color:#334155;
            }

            .guide-warning {
                background: #fffbeb;
                border: 1px solid #fde68a;
                border-radius: 14px;
                padding: 1rem;
                margin: 0.7rem 0 1rem 0;
                overflow-wrap: anywhere;
                color:#334155;
            }

            .guide-card-grid {
                display:grid;
                grid-template-columns: repeat(auto-fit, minmax(min(100%, 235px), 1fr));
                gap:0.82rem;
                margin:0.55rem 0 1rem 0;
            }

            .guide-card {
                border:1px solid #dbe3ef;
                background:#f8fafc;
                border-radius:16px;
                padding:0.9rem 1rem;
                min-height:112px;
                overflow:hidden;
                box-sizing:border-box;
            }

            .guide-card-title {
                font-size:0.72rem;
                text-transform:uppercase;
                letter-spacing:0.045em;
                color:#64748b;
                font-weight:900;
                margin-bottom:0.32rem;
                line-height:1.25;
            }

            .guide-card-value {
                font-size:clamp(1.05rem, 2vw, 1.35rem);
                line-height:1.14;
                font-weight:950;
                color:#111827;
                margin-bottom:0.36rem;
                overflow-wrap:anywhere;
            }

            .guide-card-detail {
                font-size:0.84rem;
                line-height:1.38;
                color:#475569;
                overflow-wrap:anywhere;
            }

            .guide-card.good { background:#ecfdf5; border-color:#bbf7d0; }
            .guide-card.warning { background:#fffbeb; border-color:#fde68a; }
            .guide-card.risk { background:#fef2f2; border-color:#fecaca; }
            .guide-card.info { background:#eff6ff; border-color:#bfdbfe; }
            .guide-card.dark { background:#111827; border-color:#334155; }
            .guide-card.dark .guide-card-title { color:#cbd5e1; }
            .guide-card.dark .guide-card-value { color:#ffffff; }
            .guide-card.dark .guide-card-detail { color:#e5e7eb; }

            .guide-step-grid {
                display:grid;
                grid-template-columns: repeat(auto-fit, minmax(min(100%, 195px), 1fr));
                gap:0.72rem;
                margin:0.55rem 0 1rem 0;
            }

            .guide-step-card {
                border:1px solid #dbe3ef;
                background:#ffffff;
                border-radius:16px;
                padding:0.85rem 0.92rem;
                min-height:118px;
                box-shadow:0 1px 2px rgba(15, 23, 42, 0.04);
                overflow:hidden;
            }

            .guide-step-num {
                display:inline-flex;
                width:1.65rem;
                height:1.65rem;
                align-items:center;
                justify-content:center;
                border-radius:999px;
                background:#dbeafe;
                color:#1d4ed8;
                font-weight:950;
                margin-bottom:0.45rem;
            }

            .guide-step-title {
                font-size:1.0rem;
                font-weight:950;
                color:#111827;
                line-height:1.2;
                margin-bottom:0.28rem;
            }

            .guide-step-detail {
                color:#475569;
                font-size:0.82rem;
                line-height:1.36;
            }

            .guide-path {
                display:flex;
                flex-wrap:wrap;
                align-items:center;
                gap:0.45rem;
                margin:0.55rem 0 1rem 0;
            }

            .guide-pill {
                border:1px solid #bfdbfe;
                background:#eff6ff;
                color:#1e3a8a;
                border-radius:999px;
                padding:0.38rem 0.72rem;
                font-weight:900;
                font-size:0.83rem;
                white-space:normal;
                overflow-wrap:anywhere;
            }

            .guide-arrow {
                color:#64748b;
                font-weight:950;
            }

            .guide-section-card {
                background:#ffffff;
                border:1px solid #e5eaf3;
                border-radius:18px;
                padding:1rem;
                margin:0 0 1rem 0;
                overflow:hidden;
            }

            .guide-check-row {
                display:grid;
                grid-template-columns: minmax(0, 1fr) auto;
                gap:0.7rem;
                align-items:center;
                background:#f8fafc;
                border:1px solid #e5e7eb;
                border-radius:12px;
                padding:0.62rem 0.72rem;
                margin-bottom:0.42rem;
            }

            .guide-check-title {
                color:#111827;
                font-weight:900;
                line-height:1.25;
            }

            .guide-check-detail {
                color:#64748b;
                font-size:0.78rem;
                line-height:1.32;
                margin-top:0.12rem;
            }

            .guide-check-badge {
                color:#1d4ed8;
                font-weight:950;
                white-space:nowrap;
            }

            @media (max-width: 1180px) {
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
                .guide-card-grid,
                .guide-step-grid {
                    grid-template-columns: 1fr;
                }
                .guide-hero { padding: 1rem; border-radius:18px; }
                .guide-check-row { grid-template-columns: 1fr; }
                .guide-check-badge { white-space:normal; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def responsive_columns(spec, gap: str = "small"):
    return st.columns(spec, gap=gap)


def _escape(value: Any) -> str:
    return html.escape(str(value))


def guide_card(title: str, value: str, detail: str, tone: str = "neutral") -> None:
    st.markdown(
        f'<div class="guide-card {_escape(tone)}">'
        f'<div class="guide-card-title">{_escape(title)}</div>'
        f'<div class="guide-card-value">{_escape(value)}</div>'
        f'<div class="guide-card-detail">{_escape(detail)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def guide_card_grid(cards: List[Dict[str, str]]) -> None:
    pieces = ['<div class="guide-card-grid">']
    for card in cards:
        tone = _escape(card.get("tone", "neutral"))
        pieces.append(
            f'<div class="guide-card {tone}">'
            f'<div class="guide-card-title">{_escape(card.get("title", ""))}</div>'
            f'<div class="guide-card-value">{_escape(card.get("value", ""))}</div>'
            f'<div class="guide-card-detail">{_escape(card.get("detail", ""))}</div>'
            f'</div>'
        )
    pieces.append('</div>')
    st.markdown(''.join(pieces), unsafe_allow_html=True)


def step_grid(steps: List[Tuple[str, str]]) -> None:
    pieces = ['<div class="guide-step-grid">']
    for idx, (title, detail) in enumerate(steps, start=1):
        pieces.append(
            '<div class="guide-step-card">'
            f'<div class="guide-step-num">{idx}</div>'
            f'<div class="guide-step-title">{_escape(title)}</div>'
            f'<div class="guide-step-detail">{_escape(detail)}</div>'
            '</div>'
        )
    pieces.append('</div>')
    st.markdown(''.join(pieces), unsafe_allow_html=True)


def workflow_path(items: List[str]) -> None:
    pieces = ['<div class="guide-path">']
    for idx, item in enumerate(items):
        pieces.append(f'<span class="guide-pill">{_escape(item)}</span>')
        if idx < len(items) - 1:
            pieces.append('<span class="guide-arrow">→</span>')
    pieces.append('</div>')
    st.markdown(''.join(pieces), unsafe_allow_html=True)


def check_row(title: str, detail: str, badge: str = "Required") -> None:
    st.markdown(
        '<div class="guide-check-row">'
        '<div>'
        f'<div class="guide-check-title">{_escape(title)}</div>'
        f'<div class="guide-check-detail">{_escape(detail)}</div>'
        '</div>'
        f'<div class="guide-check-badge">{_escape(badge)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def tip(text: str) -> None:
    st.caption(f"💡 {text}")


def nav_button(label: str, page_key: str, key: str) -> None:
    if st.button(label, width="stretch", key=key):
        st.session_state["jfbp_main_navigation"] = page_key
        st.rerun()


# =========================================================
# PAGE SECTIONS
# =========================================================

def commander_welcome() -> None:
    st.title("🧭 User Guide Center")
    st.caption(
        "JFBP Quant Desk v2.0 onboarding, workflow map, execution safety guide, and operator manual."
    )

    st.markdown(
        """
        <div class="guide-hero">
            <div class="guide-hero-kicker">Commander Onboarding · JFBP Quant Desk</div>
            <div class="guide-hero-title">Welcome aboard the command desk.</div>
            <div class="guide-hero-text">
                This page teaches the crew how to use the platform without getting lost at sea.
                Start with market context, find opportunity, validate the trade, route safely through OMS,
                manage the position, and review everything in Journal.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    guide_card_grid([
        {"title": "Primary Mission", "value": "Decision Support", "detail": "Analyze markets, rank opportunities, prepare trades, and review outcomes.", "tone": "info"},
        {"title": "Execution Rule", "value": "Safety First", "detail": "SIM for testing. LIVE only after OMS, IBKR, snapshot, and risk gates are verified.", "tone": "warning"},
        {"title": "Main Workflow", "value": "Signal → Trade → Review", "detail": "Market Pulse → Scanner → Research → Trade Command → OMS → Position Command → Journal.", "tone": "good"},
        {"title": "Asset Classes", "value": "Stocks + Multi-Asset", "detail": "Stocks, options planning, crypto, forex, gold, oil, and portfolio intelligence.", "tone": "neutral"},
    ])


def quick_start() -> None:
    st.subheader("🚀 New User Quick Start")
    st.caption("Use this every morning until the workflow becomes automatic.")

    step_grid([
        ("Read Market Pulse", "Identify regime, stress, breadth, leadership, and the current playbook."),
        ("Check Calendars", "Review Economic Calendar and Earnings Calendar before trusting any trade idea."),
        ("Run Scanner", "Find ranked opportunities that match current market conditions and risk filters."),
        ("Research One Symbol", "Validate the setup, thesis, levels, sector strength, and recommendation."),
        ("Prepare Trade Command", "Convert the idea into a trade plan, risk/reward, conviction, and OMS handoff."),
        ("Route Through OMS", "Execute only approved signals or manual tickets after safety gates are confirmed."),
        ("Manage Position", "Use Position Command Center to review holds, trims, stops, exits, and portfolio heat."),
        ("Journal Review", "Record outcomes, lessons, mistakes, and process improvements."),
    ])


def workflow_maps() -> None:
    st.subheader("🗺️ Workflow Maps")
    st.caption("The platform is not a pile of pages. It is a connected operating chain.")

    with st.container(border=True):
        st.markdown("#### 📈 Research-to-Trade Chain")
        workflow_path([
            "Market Pulse",
            "Scanner",
            "Research Stock",
            "Trade Command Center",
            "OMS Execution",
            "Position Command Center",
            "Journal",
        ])
        cols = responsive_columns(4)
        with cols[0]: nav_button("Open Market Pulse", "Market Pulse", "guide_nav_market_pulse")
        with cols[1]: nav_button("Open Scanner", "Scanner", "guide_nav_scanner")
        with cols[2]: nav_button("Open Research", "Research Stock", "guide_nav_research")
        with cols[3]: nav_button("Open Trade Command", "Trade Command Center", "guide_nav_trade_command")

    with st.container(border=True):
        st.markdown("#### ⚙️ Execution Chain")
        workflow_path([
            "Trade Command Center",
            "OMS Execution",
            "Live IBKR",
            "Position Command Center",
            "Journal",
            "Database",
        ])
        cols = responsive_columns(4)
        with cols[0]: nav_button("Open OMS", "OMS Execution", "guide_nav_oms")
        with cols[1]: nav_button("Open Live IBKR", "Live IBKR", "guide_nav_live_ibkr")
        with cols[2]: nav_button("Open Position Command", "Position Command Center", "guide_nav_position")
        with cols[3]: nav_button("Open Journal", "Journal", "guide_nav_journal")

    with st.container(border=True):
        st.markdown("#### 💼 Portfolio Chain")
        workflow_path([
            "Portfolio",
            "Private Portfolio",
            "Market Hub",
            "Journal",
        ])
        cols = responsive_columns(3)
        with cols[0]: nav_button("Open Portfolio", "Portfolio", "guide_nav_portfolio")
        with cols[1]: nav_button("Open Private Portfolio", "Private Portfolio", "guide_nav_private_portfolio")
        with cols[2]: nav_button("Open Market Hub", "Market Hub", "guide_nav_market_hub")


def page_catalog() -> None:
    st.subheader("📚 Page-by-Page Guide")
    st.caption("What each page does and when the crew should use it.")

    left, right = responsive_columns([7, 3], gap="large")

    with left:
        st.markdown("### 📈 Market Intelligence")
        guide_card_grid([
            {"title": "Market Pulse", "value": "Market regime", "detail": "Use first. Reads stress, breadth, leadership, event risk, and trading bias.", "tone": "info"},
            {"title": "Economic Calendar", "value": "Macro risk", "detail": "Tracks CPI, PPI, FOMC, NFP, GDP, and macro events that can change the tape.", "tone": "neutral"},
            {"title": "Earnings Calendar", "value": "Catalyst risk", "detail": "Checks upcoming earnings risk and exports context for Scanner and Market Pulse.", "tone": "neutral"},
        ])

        st.markdown("### 🎯 Opportunity Discovery")
        guide_card_grid([
            {"title": "Opportunity Center", "value": "Global ranking", "detail": "Command view for best opportunities across major workflows and asset classes.", "tone": "info"},
            {"title": "Scanner", "value": "Find candidates", "detail": "Ranks opportunities by trend, relative strength, sector leadership, score, and risk filters.", "tone": "good"},
            {"title": "Research Stock", "value": "Validate setup", "detail": "Deep research page for chart, thesis, levels, sector leadership, peers, and recommendation.", "tone": "good"},
            {"title": "Options Center", "value": "Options planning", "detail": "Advisory-only options idea planning, strike builder, wheel desk, and risk review.", "tone": "neutral"},
        ])

        st.markdown("### ⚙️ Execution & Automation")
        guide_card_grid([
            {"title": "Trade Command Center", "value": "Trade plan", "detail": "Converts a validated idea into conviction, risk/reward, trade grade, and OMS handoff.", "tone": "good"},
            {"title": "Automation Control Center", "value": "Signal governance", "detail": "Controls Signal Watcher, Quant Executor, automation rules, safety gates, and Telegram alerts.", "tone": "warning"},
            {"title": "OMS Execution", "value": "Execution control", "detail": "SIM/LIVE control, approved signal execution, emergency flatten, reconciliation, and audit trail.", "tone": "risk"},
            {"title": "Live IBKR", "value": "Broker bridge", "detail": "Connect gateway, pull broker snapshot, verify balances, positions, executions, and account state.", "tone": "risk"},
            {"title": "Manual Order Ticket", "value": "Manual routing", "detail": "Manual order-entry workflow after mode, broker, risk, symbol, side, and quantity are verified.", "tone": "warning"},
            {"title": "Position Command Center", "value": "Manage open risk", "detail": "Review holds, trims, exits, portfolio heat, scanner alignment, and journal handoff.", "tone": "good"},
        ])

    with right:
        st.markdown("### 🧭 Commander Rules")
        check_row("Start with context", "Market Pulse and calendars come before Scanner decisions.", "Rule 1")
        check_row("Research before routing", "Scanner finds candidates; Research validates them.", "Rule 2")
        check_row("OMS owns execution", "Do not treat analysis pages as order-routing pages.", "Rule 3")
        check_row("IBKR snapshot matters", "Before LIVE routing, pull and verify broker snapshot.", "Rule 4")
        check_row("Journal closes the loop", "Every important trade should produce a lesson.", "Rule 5")

        st.markdown("### 🔐 Safety Labels")
        guide_card("SIM", "Testing mode", "No real broker orders should be routed from SIM testing.", "good")
        guide_card("LIVE", "Real-risk mode", "LIVE can route real broker orders after OMS and IBKR gates are armed.", "risk")
        guide_card("Paper", "Local simulation", "Quant Executor paper positions are local simulator records, not IBKR positions.", "warning")


def live_trading_safety() -> None:
    st.subheader("🔌 LIVE Trading Safety Procedure")
    st.caption("This checklist is intentionally strict. It prevents accidental broker routing.")

    st.markdown(
        """
        <div class="guide-warning">
            <strong>Commander Safety Reminder:</strong> LIVE mode can route real broker orders only after the required OMS and IBKR gates are armed.
            Do not skip the sequence. Do not trade if account balances, positions, or buying power do not match expectations.
        </div>
        """,
        unsafe_allow_html=True,
    )

    step_grid([
        ("Open TWS / IBKR Gateway", "Log in to the correct account before using LIVE controls."),
        ("Open OMS Execution", "Set Mode = LIVE."),
        ("Acknowledge OMS LIVE Risk", "Tick the checkbox confirming OMS LIVE can route real broker orders."),
        ("Type ARM OMS LIVE", "Type the exact phrase and press Enter."),
        ("Arm LIVE Trading", "Tick LIVE Trading Armed only when you intentionally want real routing enabled."),
        ("Open Live IBKR", "Confirm IBKR connect and click Connect Gateway."),
        ("Pull Broker Snapshot", "Verify balances, buying power, positions, orders, and executions."),
        ("Return to OMS", "Execute only after all checks are green and the trade plan is approved."),
    ])


def quant_executor_guide() -> None:
    st.subheader("🤖 Quant Executor Guide")
    st.caption("The automated engine must stay inside the safety fence.")

    left, right = responsive_columns(2, gap="large")
    with left:
        st.markdown("### Entry Logic")
        guide_card_grid([
            {"title": "Signal Source", "value": "Signal Watcher", "detail": "Reads BUY / STRONG BUY alerts from scanner-style signal logs.", "tone": "info"},
            {"title": "Market Filter", "value": "Regime-aware", "detail": "Uses allowed asset classes, allowed symbols, minimum score, and risk limits.", "tone": "good"},
            {"title": "Position Size", "value": "Configured allocation", "detail": "BUY and STRONG BUY allocations are defined in Automation Control Center.", "tone": "neutral"},
        ])

    with right:
        st.markdown("### Exit Logic")
        guide_card_grid([
            {"title": "Stop Loss", "value": "-8%", "detail": "Protects capital if the trade moves against the paper position.", "tone": "risk"},
            {"title": "Take Profit", "value": "+15%", "detail": "Captures gains when a target is reached.", "tone": "good"},
            {"title": "Trailing Stop", "value": "10% after +10%", "detail": "Activates after a gain and trails from the highest price.", "tone": "warning"},
            {"title": "Signal Exit", "value": "Loss of BUY", "detail": "Exits if the signal no longer supports the trade.", "tone": "info"},
            {"title": "Time Exit", "value": "Max holding days", "detail": "Prevents stale paper positions from sitting forever.", "tone": "neutral"},
        ])

    nav_button("Open Automation Control Center", "Automation Control Center", "guide_nav_automation")


def multi_asset_guide() -> None:
    st.subheader("🌍 Asset-Class Intelligence")
    st.caption("These pages help the desk understand non-stock regimes before taking risk.")

    guide_card_grid([
        {"title": "Crypto Pulse", "value": "BTC / ETH / altcoin regime", "detail": "Reads crypto stress, breadth, BTC leadership, liquidity proxy, market cycle, and opportunities.", "tone": "info"},
        {"title": "Forex Pulse", "value": "Currency regime", "detail": "Tracks major FX pairs, USD pressure, macro sensitivity, and currency risk conditions.", "tone": "neutral"},
        {"title": "Gold Pulse", "value": "Safe-haven / real-rate read", "detail": "Helps interpret gold, inflation pressure, dollar pressure, and defensive demand.", "tone": "warning"},
        {"title": "Oil Pulse", "value": "Energy / inflation read", "detail": "Tracks crude oil, energy leadership, supply shock risk, and commodity pressure.", "tone": "warning"},
    ])

    cols = responsive_columns(4)
    with cols[0]: nav_button("Open Crypto", "Crypto Pulse", "guide_nav_crypto")
    with cols[1]: nav_button("Open Forex", "Forex Pulse", "guide_nav_forex")
    with cols[2]: nav_button("Open Gold", "Gold Pulse", "guide_nav_gold")
    with cols[3]: nav_button("Open Oil", "Oil Pulse", "guide_nav_oil")


def faq_section() -> None:
    st.subheader("❓ FAQ")

    with st.expander("Does JFBP Quant Desk place trades automatically?", expanded=False):
        st.write(
            "It can prepare and govern automated workflows, but real broker routing requires explicit OMS LIVE arming, IBKR connection, and safety gates. Quant Executor is currently described as paper/local unless live routing is intentionally built and armed."
        )

    with st.expander("What is the difference between OMS Execution and Quant Executor?", expanded=False):
        st.write(
            "OMS Execution is the institutional control layer for routing, reconciliation, emergency flatten, and audit. Quant Executor is the automated paper-testing engine that reads signals, opens local paper positions, and manages exits."
        )

    with st.expander("What is Market Hub?", expanded=False):
        st.write(
            "Market Hub is the cache and symbol handoff center. It verifies cached market data and routes symbols toward Research, Scanner, Trade Command, OMS, or Position Command."
        )

    with st.expander("Do I need IBKR?", expanded=False):
        st.write(
            "You need IBKR only for broker connection and live/paper broker workflows. Analysis, scanner, portfolio review, and local paper testing can still be used without a live broker connection."
        )

    with st.expander("Can the platform handle crypto, forex, gold, and oil?", expanded=False):
        st.write(
            "Yes. The sidebar already includes Crypto Pulse, Forex Pulse, Gold Pulse, and Oil Pulse. These pages are asset-class intelligence modules and can later feed the multi-asset signal bus."
        )

    with st.expander("Can I receive Telegram alerts?", expanded=False):
        st.write(
            "Yes. Telegram alerts are controlled through Automation Control Center and OMS Execution. Signal Watcher can send BUY alerts, and OMS can send execution, kill-switch, emergency-flatten, and LIVE-armed alerts."
        )


def final_checklist() -> None:
    st.subheader("✅ Commander Operating Checklist")
    st.caption("Use this before any serious SIM or LIVE session.")

    check_row("Market context reviewed", "Market Pulse, Economic Calendar, and Earnings Calendar checked.", "Before Scanner")
    check_row("Opportunity validated", "Scanner candidate reviewed in Research Stock and Trade Command Center.", "Before OMS")
    check_row("Mode confirmed", "SIM or LIVE mode verified in OMS Execution.", "Critical")
    check_row("Risk controls checked", "Kill switch, risk engine, account state, and broker snapshot verified.", "Critical")
    check_row("IBKR connected only when intended", "Gateway connected and broker snapshot pulled only when ready.", "LIVE")
    check_row("Position managed", "Open risk reviewed in Position Command Center after execution.", "After fill")
    check_row("Journal completed", "Lessons, mistakes, and process notes recorded.", "After trade")

    st.markdown(
        """
        <div class="guide-warning">
            <strong>Final Safety Reminder:</strong> Analysis pages are advisory. OMS and Manual Order Ticket are the order-routing layers.
            LIVE trading requires deliberate arming, broker verification, and risk review.
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# PAGE
# =========================================================

def run_page() -> None:
    inject_navigation_guide_css()
    commander_welcome()

    tabs = st.tabs([
        "Quick Start",
        "Workflow Maps",
        "Page Catalog",
        "LIVE Safety",
        "Quant Executor",
        "Multi-Asset",
        "FAQ",
        "Checklist",
    ])

    with tabs[0]:
        quick_start()

    with tabs[1]:
        workflow_maps()

    with tabs[2]:
        page_catalog()

    with tabs[3]:
        live_trading_safety()

    with tabs[4]:
        quant_executor_guide()

    with tabs[5]:
        multi_asset_guide()

    with tabs[6]:
        faq_section()

    with tabs[7]:
        final_checklist()


def page() -> None:
    run_page()
