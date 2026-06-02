import asyncio
import streamlit as st

# =====================================================
# ENSURE EVENT LOOP EXISTS
# =====================================================

try:
    asyncio.get_running_loop()

except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# IMPORTANT:
# import AFTER event loop exists

from ib_insync import IB

HOST = "127.0.0.1"
PORT = 7497
CLIENT_ID = 1


def create_ib_connection():

    ib = IB()

    if not ib.isConnected():

        ib.connect(
            HOST,
            PORT,
            clientId=CLIENT_ID,
            timeout=5
        )

    return ib


def get_ib():

    if "ib" not in st.session_state:

        st.session_state.ib = create_ib_connection()

    return st.session_state.ib