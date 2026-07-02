import streamlit as st

from options_engine.models.trade_model import TradeModel


def get_trade() -> TradeModel:

    if "trade" not in st.session_state:

        st.session_state.trade = TradeModel()

    return st.session_state.trade


def reset_trade():

    st.session_state.trade = TradeModel()