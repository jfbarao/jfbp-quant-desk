# =========================================================
# JFBP APP ENTRYPOINT v24.24
# STABLE ROUTER — SAAS LOGIN GATE ENABLED
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


try:
    from pages.SaaS_Core import (
        run_page as saas_core_page,
        init_saas_state,
        get_current_user,
        inject_saas_css,
        render_auth_panel,
        require_page_access,
        supabase_logout,
        is_admin_user,
    )
except Exception as saas_import_error:
    def saas_core_page(_err=saas_import_error):
        st.title("🔐 SaaS Core")
        st.error("SaaS Core could not be loaded.")
        st.caption("Make sure SaaS_Core.py is saved inside the pages folder.")
        st.exception(_err)

    def init_saas_state():
        st.session_state.setdefault("saas_logged_in", False)
        st.session_state.setdefault("saas_user", None)

    def get_current_user():
        return None

    def inject_saas_css():
        return None

    def render_auth_panel():
        st.error("SaaS Core could not be loaded, so login is unavailable.")
        st.exception(saas_import_error)

    def require_page_access(page_name: str) -> bool:
        st.error("SaaS Core could not be loaded, so access control is unavailable.")
        st.exception(saas_import_error)
        return False

    def supabase_logout():
        st.session_state["saas_logged_in"] = False
        st.session_state["saas_user"] = None
        return True, "Logged out."

    def is_admin_user(user):
        return False


try:
    from pages.Admin_Control_Center import run_page as admin_control_center_page
except Exception as admin_control_import_error:
    def admin_control_center_page(_err=admin_control_import_error):
        st.title("🛡️ Admin Control Center")
        st.error("Admin Control Center could not be loaded.")
        st.caption("Make sure Admin_Control_Center.py is saved inside the pages folder.")
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

            section[data-testid="stSidebar"] > div:first-child {
                display: flex;
                flex-direction: column;
                min-height: 100vh;
            }

            section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] {
                overflow-wrap: anywhere;
            }

            .jfbp-sidebar-footer {
                margin-top: auto;
                padding-top: 0.72rem;
                padding-bottom: 0.52rem;
                background: #f8fafc;
                border-top: 1px solid #d6dbe5;
            }

            .jfbp-sidebar-footer-email {
                margin-top: 0.35rem;
                font-size: 0.74rem;
                color: #64748b;
                line-height: 1.25;
                overflow-wrap: anywhere;
            }

            /* Sidebar expander cards: uniform border on all sides. */
            section[data-testid="stSidebar"] details {
                background: #f8fafc !important;
                border: 1px solid #d6dbe5 !important;
                border-radius: 12px !important;
                margin: 0.42rem 0 !important;
                padding: 0 !important;
                overflow: hidden !important;
                box-shadow: none !important;
            }

            section[data-testid="stSidebar"] details:first-of-type {
                margin-top: 0.25rem !important;
            }

            section[data-testid="stSidebar"] details > summary {
                min-height: 2.10rem !important;
                padding: 0.46rem 0.72rem !important;
                border: none !important;
                border-bottom: 0 !important;
                font-weight: 640 !important;
                letter-spacing: 0.01em;
                text-transform: none;
                color: #334155 !important;
                font-size: 0.96rem !important;
                background: #f8fafc !important;
                box-shadow: none !important;
            }

            section[data-testid="stSidebar"] details[open] > summary {
                border-bottom: 1px solid #d6dbe5 !important;
            }

            section[data-testid="stSidebar"] details > div {
                padding: 0.36rem 0.64rem 0.44rem 0.64rem !important;
            }

            section[data-testid="stSidebar"] details::before,
            section[data-testid="stSidebar"] details::after,
            section[data-testid="stSidebar"] summary::before,
            section[data-testid="stSidebar"] summary::after {
                border-top: none !important;
                box-shadow: none !important;
            }

            .jfbp-sidebar-caption {
                margin-top: 0;
                margin-bottom: 0.26rem;
                font-size: 0.76rem;
                color: #64748b;
                line-height: 1.35;
            }

            section[data-testid="stSidebar"] .stButton > button {
                width: 100%;
                justify-content: flex-start;
                text-align: left;
                min-height: 2.50rem;
                border-radius: 9px;
                font-weight: 620;
                font-size: 0.90rem;
                padding-left: 0.64rem;
                padding-right: 0.64rem;
                margin-bottom: 0.14rem;
                white-space: normal;
                line-height: 1.25;
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
                    min-height: 2.40rem;
                    font-size: 0.88rem;
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
    current_user = get_current_user()
    admin_pages = {"SaaS Core", "Admin Control Center"}

    # Never expose internal admin pages to regular users. If a non-admin
    # session was previously parked on an admin page, move it back to the
    # normal workflow start page before rendering the sidebar.
    if current in admin_pages and not is_admin_user(current_user):
        current = "Opportunity Center"
        st.session_state["jfbp_main_navigation"] = current

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
        {
            "title": "🔐 Admin",
            "caption": "SaaS infrastructure and subscription controls.",
            "items": [
                ("🔐 SaaS Core", "SaaS Core"),
                ("🛡️ Admin Control Center", "Admin Control Center"),
            ],
            "always_open": False,
        },
    ]

    for group in groups:
        if group["title"] == "🔐 Admin" and not is_admin_user(current_user):
            continue

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
# SAAS FRONT-DOOR GATE
# =========================================================

ACCESS_NAME_BY_PAGE = {
    "🧭 Navigation Guide": "Navigation Guide",
    "Opportunity Center": "Opportunity Center",
    "Scanner": "Scanner",
    "Market Hub": "Market Hub",
    "Research Stock": "Research Stock",
    "Trade Command Center": "Trade Command Center",
    "Options Center": "Options Center",
    "Market Pulse": "Market Pulse",
    "Economic Calendar": "Economic Calendar",
    "Earnings Calendar": "Earnings Calendar",
    "Automation Control Center": "Automation Control Center",
    "OMS Execution": "OMS Execution",
    "Position Command Center": "Position Command Center",
    "Manual Order Ticket": "Manual Order Ticket",
    "Portfolio": "Portfolio",
    "Live IBKR": "Live IBKR",
    "Journal": "Journal",
    "Database": "Database",
    "Private Portfolio": "Private Portfolio",
    "Crypto Pulse": "Crypto Pulse",
    "Forex Pulse": "Forex Pulse",
    "Gold Pulse": "Gold Pulse",
    "Oil Pulse": "Oil Pulse",
    "SaaS Core": "SaaS Core",
    "Admin Control Center": "Admin Control Center",
}

# Internal operating pages must be admin-only. They are hidden from regular
# users in the sidebar and blocked again here at the router layer.
ALWAYS_ALLOW_AFTER_LOGIN = set()
ADMIN_ONLY_PAGES = {"SaaS Core", "Admin Control Center"}


def render_front_door() -> None:
    """Public landing screen shown before the platform is unlocked."""
    inject_saas_css()

    logo_path = Path(__file__).parent / "JFBP_Quant_Desk.png"
    if logo_path.exists():
        st.image(str(logo_path), width=130)

    st.markdown(
        """
        <div class="saas-hero">
            <div class="saas-kicker">JFBP Quant Desk · Secure Access</div>
            <div class="saas-title">Start your 30-Day Free Trial</div>
            <div class="saas-text">
                Create your account or log in to access the platform. No credit card required for the trial.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_auth_panel()


def enforce_app_login() -> bool:
    """Stop the app before sidebar/page rendering unless a real user is logged in."""
    init_saas_state()
    if get_current_user() is not None:
        return True

    render_front_door()
    st.stop()
    return False


def run_protected_page(page_key: str, runner) -> None:
    """Run a page only when the logged-in user has plan or admin access."""
    access_name = ACCESS_NAME_BY_PAGE.get(page_key, page_key)
    current_user = get_current_user()

    if access_name in ADMIN_ONLY_PAGES and not is_admin_user(current_user):
        st.error("Admin access required.")
        return

    if access_name not in ALWAYS_ALLOW_AFTER_LOGIN:
        if not require_page_access(access_name):
            return

    runner()

# =========================================================
# APP ROUTER
# =========================================================

def app():

    init_core()
    enforce_app_login()
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

    current_user = get_current_user()
    if current_user is not None:
        st.sidebar.markdown(
            '<div class="jfbp-sidebar-footer">',
            unsafe_allow_html=True,
        )

        st.sidebar.link_button(
            "💳 Manage Subscription",
            "https://billing.stripe.com/p/login/3cIcN63Kpe2GcELaKp7IY00",
            use_container_width=True,
        )

        if st.sidebar.button("Logout", key="sidebar_saas_logout", width="stretch"):
            supabase_logout()
            st.rerun()

        st.sidebar.markdown(
            f'<div class="jfbp-sidebar-footer-email">Signed in:<br>{current_user.email}</div>',
            unsafe_allow_html=True,
        )

        st.sidebar.markdown("</div>", unsafe_allow_html=True)

    if page == "🧭 Navigation Guide":
        run_protected_page(page, navigation_guide_page)

    elif page == "Opportunity Center":
        run_protected_page(page, opportunity_center_page)

    elif page == "Scanner":
        run_protected_page(page, scanner_page)

    elif page == "Market Hub":
        run_protected_page(page, market_hub_page)

    elif page == "Research Stock":
        run_protected_page(page, research_stock_page)

    elif page == "Trade Command Center":
        run_protected_page(page, trade_command_center_page)

    elif page == "Options Center":
        run_protected_page(page, options_center_page)

    elif page == "Market Pulse":
        run_protected_page(page, market_pulse_page)

    elif page == "Economic Calendar":
        run_protected_page(page, economic_calendar_page)

    elif page == "Earnings Calendar":
        run_protected_page(page, earnings_calendar_page)

    elif page == "Automation Control Center":
        run_protected_page(page, automation_control_page)

    elif page == "OMS Execution":
        run_protected_page(page, oms_page)

    elif page == "Position Command Center":
        run_protected_page(page, position_command_center_page)

    elif page == "Manual Order Ticket":
        run_protected_page(page, order_ticket_page)

    elif page == "Portfolio":
        run_protected_page(page, portfolio_page)

    elif page == "Live IBKR":
        run_protected_page(page, live_ibkr_page)

    elif page == "Journal":
        run_protected_page(page, journal_page)

    elif page == "Database":
        run_protected_page(page, database_page)

    elif page == "Private Portfolio":
        run_protected_page(page, private_portfolio_page)

    elif page == "Crypto Pulse":
        run_protected_page(page, crypto_pulse_page)

    elif page == "Forex Pulse":
        run_protected_page(page, forex_pulse_page)

    elif page == "Gold Pulse":
        run_protected_page(page, gold_pulse_page)

    elif page == "Oil Pulse":
        run_protected_page(page, oil_pulse_page)

    elif page == "SaaS Core":
        run_protected_page(page, saas_core_page)

    elif page == "Admin Control Center":
        run_protected_page(page, admin_control_center_page)

    else:
        empty_page("Unknown Page")


if __name__ == "__main__":
    app()
