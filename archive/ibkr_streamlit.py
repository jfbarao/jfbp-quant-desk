from ib_insync import Stock
import streamlit as st

def subscribe_symbol(ib, symbol):

    # ensure registry exists
    if "subscriptions" not in st.session_state:
        st.session_state.subscriptions = {}

    subs = st.session_state.subscriptions

    # 🚫 prevent duplicate subscriptions
    if symbol in subs:
        return subs[symbol]

    # create contract
    contract = Stock(symbol, "SMART", "USD")

    # subscribe once
    ticker = ib.reqMktData(contract, snapshot=False)

    # store reference
    subs[symbol] = ticker

    return ticker