# =========================================================
# 🎫 MANUAL ORDER TICKET
# LIVE-SAFE OMS ORDER ENTRY
# FILL PROPAGATION DIAGNOSTICS
# CLEAN MKT/LMT HANDLING
# BROKER ORDER CANCEL CONTROLS
# =========================================================

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, List

import pandas as pd
import streamlit as st

from core.bootstrap import init_core


def now():
    return datetime.now(timezone.utc).isoformat()


def flatten_for_table(data: Dict[str, Any]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []

    if not isinstance(data, dict):
        return pd.DataFrame([{"Field": "value", "Value": str(data)}])

    for key, value in data.items():
        if isinstance(value, (dict, list, tuple)):
            value = str(value)

        rows.append({
            "Field": str(key),
            "Value": value,
        })

    return pd.DataFrame(rows)


def _safe_len(obj) -> int:
    try:
        return len(obj)
    except Exception:
        return 0


def _extract_oms_fills(oms):
    if oms is None:
        return []

    for name in (
        "fills_snapshot",
        "raw_fills_snapshot",
        "fills",
        "fill_registry",
        "execution_fills",
        "fill_history",
        "completed_fills",
        "recent_fills",
        "fills_by_id",
        "broker_fills",
    ):
        if hasattr(oms, name):
            try:
                value = getattr(oms, name)

                if callable(value):
                    value = value()

                if isinstance(value, dict):
                    return list(value.values())

                if isinstance(value, list):
                    return value

            except Exception:
                pass

    try:
        snapshot = oms.snapshot()
        if isinstance(snapshot, dict):
            runtime_fill_count = snapshot.get("raw_fills")
            if isinstance(runtime_fill_count, int):
                return [None] * runtime_fill_count
    except Exception:
        pass

    return []


def _extract_execution_registry(oms):
    if oms is None:
        return []

    for name in (
        "execution_registry",
        "fill_identity_registry",
        "broker_execution_registry",
        "execution_map",
        "executions",
        "broker_fills",
    ):
        if hasattr(oms, name):
            try:
                value = getattr(oms, name)

                if callable(value):
                    value = value()

                if isinstance(value, dict):
                    return list(value.values())

                if isinstance(value, list):
                    return value

            except Exception:
                pass

    try:
        snapshot = oms.snapshot()
        if isinstance(snapshot, dict):
            count = snapshot.get("execution_registry")
            if isinstance(count, int):
                return [None] * count
    except Exception:
        pass

    return []


def _extract_last_fill(oms):
    if oms is None:
        return None

    for name in (
        "last_fill",
        "last_execution",
        "last_fill_payload",
        "latest_fill",
        "last_broker_fill",
    ):
        if hasattr(oms, name):
            try:
                value = getattr(oms, name)

                if callable(value):
                    value = value()

                if value:
                    return value

            except Exception:
                pass

    try:
        snapshot = oms.snapshot()
        if isinstance(snapshot, dict):
            if snapshot.get("last_fill"):
                return snapshot.get("last_fill")
    except Exception:
        pass

    return None


def _extract_audit_store(oms, gateway):
    candidates = [
        getattr(oms, "audit_store", None),
        getattr(oms, "audit_logger", None),
        getattr(gateway, "audit_store", None),
        st.session_state.get("audit_store"),
    ]

    for candidate in candidates:
        if candidate is not None:
            return candidate

    return None


def _extract_audit_fills(audit_store):
    if audit_store is None:
        return []

    for name in (
        "fills",
        "recent_fills",
        "records",
        "entries",
        "events",
        "get_fills",
        "get_records",
    ):
        if hasattr(audit_store, name):
            try:
                value = getattr(audit_store, name)

                if callable(value):
                    try:
                        value = value(limit=10000)
                    except TypeError:
                        value = value()

                if isinstance(value, dict):
                    return list(value.values())

                if isinstance(value, list):
                    return value

            except Exception:
                pass

    return []


def _extract_portfolio_ledger(portfolio_engine):
    if portfolio_engine is None:
        return []

    for name in (
        "ledger_snapshot",
        "ledger",
        "fills",
        "positions_ledger",
        "transactions",
        "trade_log",
    ):
        if hasattr(portfolio_engine, name):
            try:
                value = getattr(portfolio_engine, name)

                if callable(value):
                    value = value()

                if isinstance(value, dict):
                    return list(value.values())

                if isinstance(value, list):
                    return value

            except Exception:
                pass

    return []


def _extract_broker_positions(gateway):
    positions = []

    if gateway is None:
        return positions

    try:
        if hasattr(gateway, "positions_snapshot"):
            positions = gateway.positions_snapshot()

        elif hasattr(gateway, "get_positions"):
            raw_positions = gateway.get_positions()

            if isinstance(raw_positions, dict):
                positions = [
                    {"symbol": symbol, "position": qty}
                    for symbol, qty in raw_positions.items()
                ]
            elif isinstance(raw_positions, list):
                positions = raw_positions

    except Exception:
        positions = []

    if isinstance(positions, dict):
        positions = list(positions.values())

    return positions if isinstance(positions, list) else []


def _extract_broker_open_orders(gateway):
    open_orders = []

    if gateway is None:
        return open_orders

    try:
        if hasattr(gateway, "open_orders"):
            open_orders = gateway.open_orders()
        elif hasattr(gateway, "get_open_orders"):
            open_orders = gateway.get_open_orders()
    except Exception:
        open_orders = []

    if isinstance(open_orders, dict):
        open_orders = list(open_orders.values())

    return open_orders if isinstance(open_orders, list) else []


def _cancel_broker_order(gateway, broker_order_id: str) -> bool:
    if gateway is None:
        return False

    broker_order_id = str(broker_order_id or "").strip()

    if not broker_order_id:
        return False

    if hasattr(gateway, "cancel_order"):
        try:
            return bool(gateway.cancel_order(broker_order_id))
        except Exception as exc:
            st.session_state["manual_ticket_cancel_error"] = str(exc)
            return False

    return False


def page():

    gateway, market, oms, portfolio_engine = init_core()

    st.title("🎫 Manual Order Ticket")
    st.caption("Live-safe OMS-routed manual order entry")

    mode = str(st.session_state.get("mode", "SIM")).upper().strip()
    live_armed = bool(st.session_state.get("live_trading_armed", False))
    kill_switch = bool(st.session_state.get("risk_kill_switch", False))

    st.subheader("Execution Guard")

    c1, c2, c3 = st.columns(3)

    c1.metric("Mode", mode)
    c2.metric("LIVE Armed", "YES" if live_armed else "NO")
    c3.metric("Kill Switch", "ON" if kill_switch else "OFF")

    if mode == "LIVE" and not live_armed:
        st.warning(
            "LIVE infrastructure is active, but LIVE trading is not armed. "
            "Orders will be blocked."
        )

    if kill_switch:
        st.error("Kill switch is active. Orders are blocked.")

    st.divider()

    st.subheader("Order Entry")

    with st.form("manual_order_ticket_form"):

        symbol = st.text_input("Symbol", value="AAPL").upper().strip()

        side = st.selectbox(
            "Side",
            ["BUY", "SELL"],
        )

        qty = st.number_input(
            "Quantity",
            min_value=1,
            max_value=100000,
            value=1,
            step=1,
        )

        order_type = st.selectbox(
            "Order Type",
            ["MKT", "LMT"],
            index=0,
        )

        limit_price = None

        if order_type == "LMT":
            limit_price = st.number_input(
                "Limit Price",
                min_value=0.01,
                value=100.00,
                step=0.01,
                format="%.2f",
            )
        else:
            st.info("Market order selected. No limit price will be sent.")

        confirm = st.checkbox(
            "I confirm this order should be routed through OMS",
            value=False,
        )

        submit = st.form_submit_button("Submit Manual Order")

    if submit:

        if not confirm:
            st.error("Order blocked: confirmation checkbox is required.")
            return

        if not symbol:
            st.error("Order blocked: symbol is required.")
            return

        signal: Dict[str, Any] = {
            "source": "manual_order_ticket",
            "symbol": symbol,
            "action": side,
            "side": side,
            "qty": int(qty),
            "quantity": int(qty),
            "order_type": order_type,
            "mode": mode,
            "timestamp": now(),
        }

        if order_type == "LMT":
            signal["limit_price"] = float(limit_price)

        try:
            result = oms.execute_signal(signal)

            if result is None:
                st.error("Order blocked or rejected by OMS.")
                st.write("Last OMS error:", getattr(oms, "last_error", ""))
                st.write("Last rejection:", getattr(oms, "last_rejection", None))
                return

            status = str(result.get("status", "")).upper()

            if status in {"WORKING", "SUBMITTED", "ROUTED", "ACKNOWLEDGED"}:
                st.success("Order submitted to OMS / broker path.")
            elif status in {"FILLED", "PARTIAL_FILLED"}:
                st.success("Order filled.")
            else:
                st.warning(f"Order returned status: {status}")

            st.dataframe(
                flatten_for_table(result),
                use_container_width=True,
                hide_index=True,
            )

        except Exception as exc:
            st.error(f"Manual order failed: {exc}")

    st.divider()

    st.subheader("Fill Propagation Check")

    try:
        broker_positions = _extract_broker_positions(gateway)
        oms_fills = _extract_oms_fills(oms)
        execution_registry = _extract_execution_registry(oms)
        last_fill = _extract_last_fill(oms)

        audit_store = _extract_audit_store(oms, gateway)
        audit_fills = _extract_audit_fills(audit_store)

        portfolio_ledger = _extract_portfolio_ledger(portfolio_engine)

        c1, c2, c3, c4, c5 = st.columns(5)

        if mode == "SIM":
            c1.metric("Broker Positions", "SIM N/A")
        else:
            c1.metric("Broker Positions", _safe_len(broker_positions))

        c2.metric("OMS Fills", _safe_len(oms_fills))
        c3.metric("OMS Registry", _safe_len(execution_registry))
        c4.metric("Portfolio Ledger", _safe_len(portfolio_ledger))
        c5.metric("Audit Fills", _safe_len(audit_fills))

        st.write("Last OMS Error:", getattr(oms, "last_error", None))

        if mode == "SIM":
            st.caption(
                "SIM mode uses OMS synthetic fills. Broker positions are not expected "
                "to update until LIVE/paper broker callbacks are tested."
            )

        if last_fill:
            st.write("Last Fill Payload")
            st.dataframe(
                flatten_for_table(last_fill),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No fill detected yet.")

    except Exception as exc:
        st.error(f"Fill propagation diagnostics failed: {exc}")

    st.divider()

    st.subheader("OMS Snapshot")

    try:
        oms_snapshot = oms.snapshot()
        st.dataframe(
            flatten_for_table(oms_snapshot),
            use_container_width=True,
            hide_index=True,
        )
    except Exception as exc:
        st.error(f"OMS snapshot failed: {exc}")

    st.subheader("Gateway Status")

    try:
        if gateway and hasattr(gateway, "connection_status"):
            gateway_status = gateway.connection_status()
            st.dataframe(
                flatten_for_table(gateway_status),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Gateway status unavailable.")
    except Exception as exc:
        st.error(f"Gateway status failed: {exc}")

    st.subheader("Broker Positions")

    try:
        positions = _extract_broker_positions(gateway)

        if positions:
            st.dataframe(
                pd.DataFrame(positions),
                use_container_width=True,
                hide_index=True,
            )
        else:
            if mode == "SIM":
                st.info(
                    "No broker positions expected in SIM mode. "
                    "SIM fills are internal OMS fills."
                )
            else:
                st.info("No broker positions returned.")

    except Exception as exc:
        st.error(f"Broker positions failed: {exc}")

    st.subheader("Broker Open Orders")

    try:
        open_orders = _extract_broker_open_orders(gateway)

        if open_orders:
            open_orders_df = pd.DataFrame(open_orders)

            st.dataframe(
                open_orders_df,
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("### Broker Order Controls")
            st.warning(
                "Cancel controls send cancel requests to the broker gateway. "
                "Use only for test/stale/open orders."
            )

            broker_order_ids = []

            if "broker_order_id" in open_orders_df.columns:
                broker_order_ids = [
                    str(x).strip()
                    for x in open_orders_df["broker_order_id"].tolist()
                    if str(x).strip()
                ]

            broker_order_ids = list(dict.fromkeys(broker_order_ids))

            if broker_order_ids:

                selected_broker_order_id = st.selectbox(
                    "Select broker order to cancel",
                    broker_order_ids,
                    key="manual_ticket_cancel_order_select",
                )

                c1, c2 = st.columns(2)

                confirm_cancel_selected = c1.checkbox(
                    "Confirm cancel selected broker order",
                    key="manual_ticket_confirm_cancel_selected",
                )

                cancel_selected_clicked = c1.button(
                    "Cancel Selected Broker Order",
                    use_container_width=True,
                    disabled=not confirm_cancel_selected,
                )

                confirm_cancel_all = c2.checkbox(
                    "Confirm cancel ALL broker open orders",
                    key="manual_ticket_confirm_cancel_all",
                )

                cancel_all_clicked = c2.button(
                    "Cancel All Broker Orders",
                    use_container_width=True,
                    disabled=not confirm_cancel_all,
                )

                if cancel_selected_clicked:
                    ok = _cancel_broker_order(
                        gateway,
                        selected_broker_order_id,
                    )

                    if ok:
                        st.success(
                            f"Cancel request sent for broker order "
                            f"{selected_broker_order_id}."
                        )
                        st.rerun()
                    else:
                        st.error(
                            "Cancel selected failed. "
                            f"{st.session_state.get('manual_ticket_cancel_error', '')}"
                        )

                if cancel_all_clicked:
                    cancelled = 0
                    failed = 0

                    for broker_order_id in broker_order_ids:
                        ok = _cancel_broker_order(
                            gateway,
                            broker_order_id,
                        )

                        if ok:
                            cancelled += 1
                        else:
                            failed += 1

                    if failed == 0:
                        st.success(
                            f"Cancel requests sent for all {cancelled} broker orders."
                        )
                    else:
                        st.warning(
                            f"Cancel attempted. Sent={cancelled}, Failed={failed}."
                        )

                    st.rerun()

            else:
                st.info("Open orders returned, but no broker_order_id column was found.")

        else:
            st.info("No broker open orders returned.")

    except Exception as exc:
        st.error(f"Broker open orders failed: {exc}")

    st.subheader("Broker Account Summary")

    try:
        account_summary = []

        if gateway and hasattr(gateway, "account_summary"):
            account_summary = gateway.account_summary()
        elif gateway and hasattr(gateway, "get_account_summary"):
            account_summary = gateway.get_account_summary()

        if account_summary:
            st.dataframe(
                pd.DataFrame(account_summary),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No broker account summary returned.")

    except Exception as exc:
        st.error(f"Broker account summary failed: {exc}")


def run_page():
    page()