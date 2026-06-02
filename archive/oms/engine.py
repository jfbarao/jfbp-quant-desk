# =========================================================
# ⚡ JFBP QUANT DESK — v15 OMS ENGINE
# =========================================================

import time
import uuid
from typing import Dict, Any

import streamlit as st
from ib_insync import Stock, MarketOrder

from risk.engine import risk_check


# =========================================================
# 🧠 OMS ENGINE (EXECUTION + STATE + CONTROL)
# =========================================================

def oms_engine(ib):

    if not st.session_state.get("oms_enabled", False):
        return

    signals: Dict[str, Any] = st.session_state.get("signals", {})

    if not signals:
        return

    for symbol, sig in signals.items():

        try:

            action = sig.get("signal")
            price = sig.get("last_price")

            # =====================================================
            # SIGNAL VALIDATION (ONLY TRADE BUY/SELL)
            # =====================================================

            if action not in ["BUY", "SELL"]:
                continue

            if price is None:
                continue

            now = time.time()

            # =====================================================
            # 🛡 RISK GATE (HARD STOP)
            # =====================================================

            ok, reason = risk_check(symbol, action, price)

            if not ok:

                st.session_state.orders.append({
                    "id": str(uuid.uuid4()),
                    "symbol": symbol,
                    "signal": action,
                    "price": price,
                    "timestamp": now,
                    "status": f"BLOCKED: {reason}",
                })

                continue

            # =====================================================
            # ⛔ THROTTLE (ANTI-SPAM)
            # =====================================================

            last_time = st.session_state.last_order_time.get(symbol, 0)

            if now - last_time < 5:
                continue

            st.session_state.last_order_time[symbol] = now

            # =====================================================
            # ⛔ DEDUPE (60s WINDOW PER SIGNAL TYPE)
            # =====================================================

            key = f"{symbol}_{action}"
            last_exec = st.session_state.get(f"{key}_ts", 0)

            if now - last_exec < 60:
                continue

            st.session_state[f"{key}_ts"] = now

            # =====================================================
            # 📦 ORDER OBJECT (PRE-EXECUTION LOG)
            # =====================================================

            order_record = {
                "id": str(uuid.uuid4()),
                "symbol": symbol,
                "signal": action,
                "price": price,
                "timestamp": now,
                "status": "PENDING",
            }

            st.session_state.orders.append(order_record)

            # =====================================================
            # 📡 IBKR EXECUTION
            # =====================================================

            contract = Stock(symbol, "SMART", "USD")
            ib.qualifyContracts(contract)

            qty = 1  # NOTE: fixed sizing (v15 baseline)

            trade = ib.placeOrder(contract, MarketOrder(action, qty))

            order_record["status"] = "SENT"

            # =====================================================
            # 📊 METRICS
            # =====================================================

            st.session_state.daily_trades += 1

            # =====================================================
            # 📈 POSITION TRACKING
            # =====================================================

            pos = st.session_state.position_limits.get(symbol, 0)

            if action == "BUY":
                pos += qty
            else:
                pos -= qty

            st.session_state.position_limits[symbol] = pos

            # =====================================================
            # 💰 ENTRY PRICE MODEL (SMOOTHED AVERAGING)
            # =====================================================

            entry = st.session_state.entry_price.get(symbol)

            if entry is None:
                st.session_state.entry_price[symbol] = price
            else:
                st.session_state.entry_price[symbol] = (
                    0.7 * entry + 0.3 * price
                )

            entry = st.session_state.entry_price[symbol]

            # =====================================================
            # 💰 PnL (MARK-TO-MARKET)
            # =====================================================

            pnl = (price - entry) * pos

            st.session_state.daily_pnl = pnl

            # =====================================================
            # 📦 FILL LOGGING
            # =====================================================

            if "fills" not in st.session_state:
                st.session_state.fills = []

            st.session_state.fills.append({
                "symbol": symbol,
                "action": action,
                "qty": qty,
                "price": price,
                "timestamp": now,
                "trade": str(trade),
            })

        except Exception as e:

            st.session_state.orders.append({
                "id": str(uuid.uuid4()),
                "symbol": symbol,
                "signal": sig.get("signal"),
                "price": sig.get("last_price"),
                "timestamp": time.time(),
                "status": f"FAILED: {e}",
            })

            continue


# =========================================================
# 🧠 OMS STATE RESET HELPERS (OPTIONAL BUT IMPORTANT)
# =========================================================

def reset_daily_state():

    st.session_state.daily_trades = 0
    st.session_state.daily_pnl = 0.0
    st.session_state.position_limits = {}
    st.session_state.last_order_time = {}
    st.session_state.entry_price = {}