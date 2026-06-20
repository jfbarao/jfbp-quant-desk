# =========================================================
# JFBP APP ENTRYPOINT v24.23
# STABLE ROUTER — MARKET HUB SIDEBAR FIX
# FUTURE ASSET MODULES READY
# =========================================================

from pathlib import Path

import streamlit as st

from core.bootstrap import init_core

from pages.Navigation_Guide import run_page as navigation_guide_page

try:
    from pages.Opportunity_Center import run_page as opportunity_center_page
except Exception as opportunity_center_import_error:
    def opportunity_center_page(_err=opportunity_center_import_error):
        st.title("🎯 Opportunity Center")
        st.error("Opportunity Center could not be loaded.")
        st.caption("Make sure Opportunity_Center.py is saved inside the pages folder.")
        st.exception(_err)

try:
    from pages.Options_Center import run_page as options_center_page
except Exception as options_center_import_error:
    def options_center_page(_err=options_center_import_error):
        st.title("🧩 Options Center")
        st.error("Options Center could not be loaded.")
        st.caption("Make sure Options_Center.py is saved inside the pages folder.")
        st.exception(_err)

try:
    from pages.Trade_Command_Center import run_page as trade_command_center_page
except Exception as trade_command_import_error:
    def trade_command_center_page(_err=trade_command_import_error):
        st.title("🎯 Trade Command Center")
        st.error("Trade Command Center could not be loaded.")
        st.caption("Make sure Trade_Command_Center.py is saved inside the pages folder.")
        st.exception(_err)

try:
    from pages.Position_Command_Center import run_page as position_command_center_page
except Exception as position_command_import_error:
    def position_command_center_page(_err=position_command_import_error):
        st.title("🎯 Position Command Center")
        st.error("Position Command Center could not be loaded.")
        st.caption("Make sure Position_Command_Center.py is saved inside the pages folder.")
        st.exception(_err)

from pages.Scanner_page import run_page as scanner_page
from pages.Research_Stock import run_page as research_stock_page
from pages.Automation_Control_Center import run_page as automation_control_page
from pages.OMS_Execution import run_page as oms_page
from pages.page_order_ticket import run_page as order_ticket_page
from pages.Portfolio import run_page as portfolio_page

try:
    from pages.Market_Hub import run_page as market_hub_page
except Exception as market_hub_import_error:
    try:
        # Backward compatibility: keeps the sidebar working if the file has not
        # yet been renamed from Live_Stock.py to Market_Hub.py.
        from pages.Live_Stock import run_page as market_hub_page
    except Exception as live_stock_import_error:
        def market_hub_page(
            _market_hub_err=market_hub_import_error,
            _live_stock_err=live_stock_import_error,
        ):
            st.title("📡 Market Hub")
            st.error("Market Hub could not be loaded.")
            st.caption(
                "Make sure Market_Hub.py is saved inside the pages folder. "
                "Temporary fallback to Live_Stock.py also failed."
            )
            st.exception(_market_hub_err)
            st.exception(_live_stock_err)

from pages.Live_IBKR import run_page as live_ibkr_page
from pages.Journal import run_page as journal_page
from pages.Database import run_page as database_page
from pages.Market_Reaction import run_page as market_pulse_page
from pages.Economic_Calendar import run_page as economic_calendar_page
from pages.Earnings_Calendar import run_page as earnings_calendar_page
from pages.Private_Portfolio_Impact import run_page as private_portfolio_page

try:
    from pages.Crypto_Pulse import run_page as crypto_pulse_page
except Exception as crypto_import_error:
    def crypto_pulse_page(_err=crypto_import_error):
        st.title("₿ Crypto Pulse")
        st.error("Crypto Pulse could not be loaded.")
        st.caption("Make sure Crypto_Pulse.py is saved inside the pages folder.")
        st.exception(_err)

try:
    from pages.Forex_Pulse import run_page as forex_pulse_page
except Exception as forex_import_error:
    def forex_pulse_page(_err=forex_import_error):
        st.title("💱 Forex Pulse")
        st.error("Forex Pulse could not be loaded.")
        st.caption("Make sure Forex_Pulse.py is saved inside the pages folder.")
        st.exception(_err)

try:
    from pages.Gold_Pulse import run_page as gold_pulse_page
except Exception as gold_import_error:
    def gold_pulse_page(_err=gold_import_error):
        st.title("🥇 Gold Pulse")
        st.error("Gold Pulse could not be loaded.")
        st.caption("Make sure Gold_Pulse.py is saved inside the pages folder.")
        st.exception(_err)

try:
    from pages.Oil_Pulse import run_page as oil_pulse_page
except Exception as oil_import_error:
    def oil_pulse_page(_err=oil_import_error):
        st.title("🛢 Oil Pulse")
        st.error("Oil Pulse could not be loaded.")
        st.caption("Make sure Oil_Pulse.py is saved inside the pages folder.")
        st.exception(_err)


st.set_page_config(
    page_title="JFBP Quant Desk",
    layout="wide",
)


# =========================================================
# FALLBACK / FUTURE PAGES
# =========================================================

def empty_page(title: str, description: str = "Page not built yet."):
    st.title(title)
    st.info(description)


def future_asset_page(title: str, asset_class: str):
    st.title(title)
    st.caption("Future JFBP Quant Desk asset module placeholder.")
    st.info(
        f"{asset_class} module is planned for a future build. "
        "The router is already prepared so this page can be upgraded later "
        "without changing the app navigation structure."
    )
    st.markdown(
        """
        **Planned structure:**
        - Market regime
        - Volatility / stress dashboard
        - Leadership and breadth
        - Event catalysts
        - Trade bias / playbook
        - Risk controls
        """
    )


# =========================================================
# SIDEBAR WORKFLOW NAVIGATION
# =========================================================

def inject_sidebar_workflow_css() -> None:
    st.markdown(
        """
        <style>
            section[data-testid="stSidebar"] {
                background: #f8fafc;
            }

            section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] {
                overflow-wrap: anywhere;
            }

            /* Sidebar expander cards: uniform border on all sides. */
            section[data-testid="stSidebar"] details {
                background: #f8fafc !important;
                border: 1px solid #d6dbe5 !important;
                border-radius: 14px !important;
                margin: 0.60rem 0 !important;
                padding: 0 !important;
                overflow: hidden !important;
                box-shadow: none !important;
            }

            section[data-testid="stSidebar"] details:first-of-type {
                margin-top: 0.25rem !important;
            }

            section[data-testid="stSidebar"] details > summary {
                min-height: 2.35rem !important;
                padding: 0.55rem 0.70rem !important;
                border: none !important;
                border-bottom: 0 !important;
                font-weight: 900 !important;
                letter-spacing: 0.035em;
                text-transform: uppercase;
                color: #334155 !important;
                font-size: 0.74rem !important;
                background: #f8fafc !important;
                box-shadow: none !important;
            }

            section[data-testid="stSidebar"] details[open] > summary {
                border-bottom: 1px solid #d6dbe5 !important;
            }

            section[data-testid="stSidebar"] details > div {
                padding: 0.55rem 0.70rem 0.65rem 0.70rem !important;
            }

            section[data-testid="stSidebar"] details::before,
            section[data-testid="stSidebar"] details::after,
            section[data-testid="stSidebar"] summary::before,
            section[data-testid="stSidebar"] summary::after {
                border-top: none !important;
                box-shadow: none !important;
            }

            .jfbp-sidebar-caption {
                margin-top: -0.05rem;
                margin-bottom: 0.38rem;
                font-size: 0.72rem;
                color: #64748b;
                line-height: 1.25;
            }

            section[data-testid="stSidebar"] .stButton > button {
                width: 100%;
                justify-content: flex-start;
                text-align: left;
                min-height: 1.95rem;
                border-radius: 10px;
                font-weight: 700;
                padding-left: 0.60rem;
                padding-right: 0.60rem;
                margin-bottom: 0.16rem;
                white-space: normal;
            }

            section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
                background: #2563eb !important;
                border-color: #2563eb !important;
                color: white !important;
            }

            @media (max-width: 760px) {
                section[data-testid="stSidebar"] summary {
                    font-size: 0.80rem !important;
                }

                section[data-testid="stSidebar"] .stButton > button {
                    min-height: 2.35rem;
                    font-size: 0.92rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _sidebar_nav_button(label: str, page_key: str, container=st.sidebar) -> None:
    current = st.session_state.get("jfbp_main_navigation", "Opportunity Center")
    selected = current == page_key

    if container.button(
        ("✓ " if selected else "") + label,
        key=f"nav_btn_{page_key}",
        width="stretch",
        type="primary" if selected else "secondary",
    ):
        st.session_state["jfbp_main_navigation"] = page_key
        st.rerun()


def _section_is_active(current: str, page_keys: list[str]) -> bool:
    return current in page_keys


def _sidebar_group(title: str, caption: str, page_items: list[tuple[str, str]], expanded: bool = False) -> None:
    with st.sidebar.expander(title, expanded=expanded):
        if caption:
            st.markdown(
                f'<div class="jfbp-sidebar-caption">{caption}</div>',
                unsafe_allow_html=True,
            )

        for label, page_key in page_items:
            _sidebar_nav_button(label, page_key, container=st)


def workflow_sidebar_navigation() -> str:
    st.session_state.setdefault("jfbp_main_navigation", "Opportunity Center")
    current = st.session_state.get("jfbp_main_navigation", "Opportunity Center")

    groups = [
        {
            "title": "🧭 Workflow",
            "caption": "Start here and understand the desk.",
            "items": [
                ("🧭 Navigation Guide", "🧭 Navigation Guide"),
                ("🎯 Opportunity Center", "Opportunity Center"),
            ],
            "always_open": True,
        },
        {
            "title": "📈 Market Intelligence",
            "caption": "Understand the market first.",
            "items": [
                ("Market Pulse", "Market Pulse"),
                ("Economic Calendar", "Economic Calendar"),
                ("Earnings Calendar", "Earnings Calendar"),
            ],
            "always_open": False,
        },
        {
            "title": "🎯 Opportunity Discovery",
            "caption": "Find, validate, and prepare trade ideas.",
            "items": [
                ("Scanner", "Scanner"),
                ("Research Stock", "Research Stock"),
                ("🧩 Options Center", "Options Center"),
                ("🎯 Trade Command Center", "Trade Command Center"),
            ],
            "always_open": False,
        },
        {
            "title": "⚙ Execution",
            "caption": "Control routing, automation, and open risk.",
            "items": [
                ("Automation Control Center", "Automation Control Center"),
                ("OMS Execution", "OMS Execution"),
                ("🎯 Position Command Center", "Position Command Center"),
                ("Live IBKR", "Live IBKR"),
                ("Manual Order Ticket", "Manual Order Ticket"),
            ],
            "always_open": False,
        },
        {
            "title": "💼 Portfolio",
            "caption": "Monitor exposure and performance.",
            "items": [
                ("Portfolio", "Portfolio"),
                ("Private Portfolio", "Private Portfolio"),
                ("📡 Market Hub", "Market Hub"),
            ],
            "always_open": False,
        },
        {
            "title": "📝 Review",
            "caption": "Review trades and system data.",
            "items": [
                ("Journal", "Journal"),
                ("Database", "Database"),
            ],
            "always_open": False,
        },
        {
            "title": "🌍 Multi-Asset",
            "caption": "Crypto, forex, commodities, and macro regimes.",
            "items": [
                ("₿ Crypto Pulse", "Crypto Pulse"),
                ("💱 Forex Pulse", "Forex Pulse"),
                ("🥇 Gold Pulse", "Gold Pulse"),
                ("🛢 Oil Pulse", "Oil Pulse"),
            ],
            "always_open": False,
        },
    ]

    for group in groups:
        page_keys = [page_key for _, page_key in group["items"]]
        expanded = bool(group.get("always_open")) or _section_is_active(current, page_keys)
        _sidebar_group(
            group["title"],
            group["caption"],
            group["items"],
            expanded=expanded,
        )

    return st.session_state.get("jfbp_main_navigation", "Opportunity Center")


# =========================================================
# APP ROUTER
# =========================================================

def app():

    init_core()
    inject_sidebar_workflow_css()

    logo_path = Path(__file__).parent / "JFBP_Quant_Desk.png"

    if logo_path.exists():
        st.sidebar.image(
            str(logo_path),
            width=150,
        )
    else:
        st.sidebar.title("JFBP Desk")

    page = workflow_sidebar_navigation()

    if page == "🧭 Navigation Guide":
        navigation_guide_page()

    elif page == "Opportunity Center":
        opportunity_center_page()

    elif page == "Scanner":
        scanner_page()

    elif page == "Market Hub":
        market_hub_page()

    elif page == "Research Stock":
        research_stock_page()

    elif page == "Trade Command Center":
        trade_command_center_page()

    elif page == "Options Center":
        options_center_page()

    elif page == "Market Pulse":
        market_pulse_page()

    elif page == "Economic Calendar":
        economic_calendar_page()

    elif page == "Earnings Calendar":
        earnings_calendar_page()

    elif page == "Automation Control Center":
        automation_control_page()

    elif page == "OMS Execution":
        oms_page()

    elif page == "Position Command Center":
        position_command_center_page()

    elif page == "Manual Order Ticket":
        order_ticket_page()

    elif page == "Portfolio":
        portfolio_page()

    elif page == "Live IBKR":
        live_ibkr_page()

    elif page == "Journal":
        journal_page()

    elif page == "Database":
        database_page()

    elif page == "Private Portfolio":
        private_portfolio_page()

    elif page == "Crypto Pulse":
        crypto_pulse_page()

    elif page == "Forex Pulse":
        forex_pulse_page()

    elif page == "Gold Pulse":
        gold_pulse_page()

    elif page == "Oil Pulse":
        oil_pulse_page()

    else:
        empty_page("Unknown Page")


if __name__ == "__main__":
    app()
