# =========================================================
# JFBP APP ENTRYPOINT v24.8
# STABLE ROUTER — FULL PLATFORM ENABLED + BRANDED SIDEBAR
# =========================================================

from pathlib import Path

import streamlit as st

from core.bootstrap import init_core

from pages.Scanner_page import run_page as scanner_page
from pages.Live_Stock import run_page as live_stock_page
from pages.Research_Stock import run_page as research_stock_page
from pages.OMS_Execution import run_page as oms_page
from pages.Portfolio import run_page as portfolio_page
from pages.Live_IBKR import run_page as live_ibkr_page
from pages.Journal import run_page as journal_page
from pages.Database import run_page as database_page
from pages.page_order_ticket import run_page as order_ticket_page


# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="JFBP Quant Desk",
    layout="wide",
)


# =========================================================
# SAFE FALLBACK
# =========================================================

def empty_page(title: str):
    st.title(title)
    st.info("Page not built yet.")


# =========================================================
# APP
# =========================================================

def app():

    init_core()

    # =====================================================
    # SIDEBAR BRANDING
    # =====================================================

    logo_path = Path(__file__).parent / "JFBP_Quant_Desk.png"

    if logo_path.exists():
        st.sidebar.image(
            str(logo_path),
            width=150,
        )
    else:
        st.sidebar.title("JFBP Desk")

    # =====================================================
    # NAVIGATION
    # =====================================================

    page = st.sidebar.radio(
        "Navigation",
        [
            "Scanner",
            "Live Stock",
            "Research Stock",
            "OMS Execution",
            "Manual Order Ticket",
            "Portfolio",
            "Live IBKR",
            "Journal",
            "Database",
        ],
        key="jfbp_main_navigation",
    )

    # =====================================================
    # ROUTER
    # =====================================================

    if page == "Scanner":
        scanner_page()

    elif page == "Live Stock":
        live_stock_page()

    elif page == "Research Stock":
        research_stock_page()

    elif page == "OMS Execution":
        oms_page()

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

    else:
        empty_page("Unknown Page")


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    app()