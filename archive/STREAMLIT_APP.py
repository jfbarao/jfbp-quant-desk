import streamlit as st
import json
import pandas as pd

STATE_FILE = "state.json"

st.set_page_config(layout="wide")
st.title("🏛 v7 Institutional Dashboard")

def load():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return None

data = load()

if not data:
    st.warning("Engine not running or state missing")
    st.stop()

signals = data.get("signals", {})

rows = []

for k,v in signals.items():
    rows.append({
        "Symbol": k,
        "Signal": v["signal"],
        "Score": v["score"]
    })

df = pd.DataFrame(rows)

st.subheader("📡 Live Institutional Signals")
st.dataframe(df.sort_values("Score", ascending=False))

st.subheader("🟢 BUY LIST")
st.dataframe(df[df["Signal"] == "BUY"])

st.subheader("🟡 WATCH LIST")
st.dataframe(df[df["Signal"] == "WATCH"])

st.subheader("🔴 AVOID LIST")
st.dataframe(df[df["Signal"] == "AVOID"])