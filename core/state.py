# =========================================================
# 🧠 JFBP QUANT DESK — SYSTEM STATE (SINGLE SOURCE OF TRUTH)
# =========================================================

import streamlit as st
from brokers.ibkr_gateway import IBKRGateway
from execution.pipeline import TradingPipeline


def init_state():
    """
    Single authoritative state initializer.
    NOTHING else in the app should create gateway/pipeline.
    """

    # -------------------------
    # SYSTEM MODE
    # -------------------------
    if "mode" not in st.session_state:
        st.session_state["mode"] = "SIM"

    # -------------------------
    # GATEWAY (SINGLETON)
    # -------------------------
    if "gateway" not in st.session_state:
        st.session_state["gateway"] = IBKRGateway(mode="SIM")

    st.session_state["gateway"].ensure_runtime_fields()

    # -------------------------
    # PIPELINE (SINGLETON)
    # -------------------------
    if "pipeline" not in st.session_state:
        st.session_state["pipeline"] = TradingPipeline(
            gateway=st.session_state["gateway"]
        )

    # -------------------------
    # UI STATE SAFETY
    # -------------------------
    if "signal_table" not in st.session_state:
        st.session_state["signal_table"] = []

    if "signals" not in st.session_state:
        st.session_state["signals"] = {}

    if "portfolio" not in st.session_state:
        st.session_state["portfolio"] = {}

    if "selected_symbol" not in st.session_state:
        st.session_state["selected_symbol"] = "AAPL"