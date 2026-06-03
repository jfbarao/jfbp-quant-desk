# =========================================================
# 📡 LIVE IBKR PAGE v23.2
# LIVE CONNECTIVITY + MANUAL BROKER SNAPSHOT SYNC
# OPERATOR INTENT RESET HARDENING — STREAMLIT-SAFE
# =========================================================

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from core.bootstrap import init_core


def page():

    gateway, market, oms, portfolio_engine = init_core()

    pipeline = st.session_state.get("pipeline")
    stream_engine = st.session_state.get("stream_engine")
    risk_engine = st.session_state.get("risk_engine")

    st.session_state.setdefault("mode", "SIM")
    st.session_state.setdefault("live_trading_armed", False)
    st.session_state.setdefault("risk_kill_switch", False)
    st.session_state.setdefault("live_ibkr_last_refresh", "")
    st.session_state.setdefault("live_ibkr_intent_reset_id", 0)

    mode = st.session_state.get("mode", "SIM")
    live_armed = st.session_state.get("live_trading_armed", False)
    kill_switch = st.session_state.get("risk_kill_switch", False)

    # =====================================================
    # HELPERS
    # =====================================================

    def now():
        return datetime.now(timezone.utc).isoformat()

    def safe_bool(value):
        try:
            return bool(value)
        except Exception:
            return False

    def _safe_len(value):
        try:
            return len(value)
        except Exception:
            return 0

    def _as_list(value):
        if value is None:
            return []

        if isinstance(value, list):
            return value

        if isinstance(value, dict):
            return list(value.values())

        try:
            return list(value)
        except Exception:
            return []

    def reset_operator_intent():
        st.session_state["live_ibkr_intent_reset_id"] = (
            int(st.session_state.get("live_ibkr_intent_reset_id", 0) or 0) + 1
        )

    def _cached_gateway_status(ttl_seconds: int = 5):
        import time

        current_ts = time.time()

        cached_at = float(
            st.session_state.get("live_ibkr_status_cached_at", 0.0)
            or 0.0
        )

        cached_status = st.session_state.get("live_ibkr_cached_status")

        if (
            isinstance(cached_status, dict)
            and current_ts - cached_at < ttl_seconds
        ):
            return cached_status

        if gateway is None:
            status = {
                "connected": False,
                "status": "MISSING",
                "detail": "Gateway missing",
            }

        else:
            connected = False

            for attr in (
                "broker_connected",
                "ui_connected",
                "connected",
            ):
                if hasattr(gateway, attr):
                    value = getattr(gateway, attr)
                    connected = safe_bool(value)
                    break

            status = {
                "connected": connected,
                "status": "CONNECTED" if connected else "DISCONNECTED",
                "detail": "attribute-only status; no broker probe during render",
            }

        st.session_state["live_ibkr_cached_status"] = status
        st.session_state["live_ibkr_status_cached_at"] = current_ts

        return status

    def gateway_connected():
        return safe_bool(
            _cached_gateway_status().get("connected")
        )

    def gateway_status():
        return _cached_gateway_status()

    def stream_running():
        if stream_engine is None:
            return False

        if hasattr(stream_engine, "running"):
            return safe_bool(stream_engine.running)

        if hasattr(stream_engine, "is_running"):
            try:
                return safe_bool(stream_engine.is_running())
            except Exception:
                return False

        return False

    def market_snapshot_count():
        # Attribute/cache-only count.
        # Do NOT call market.snapshot() here.

        if market is None:
            return 0

        for attr in (
            "prices",
            "last_prices",
            "data",
            "snapshot_cache",
            "cache",
            "last_snapshot",
        ):
            try:
                value = getattr(market, attr, None)

                if isinstance(value, dict):
                    return len(value)

            except Exception:
                pass

        try:
            universe = st.session_state.get("universe", {})

            if isinstance(universe, dict):
                return len(universe)

            if isinstance(universe, list):
                return len(universe)

        except Exception:
            pass

        return 0

    def call_if_exists(obj, method_name):
        if obj is None or not hasattr(obj, method_name):
            return False, f"{method_name} unavailable"

        try:
            getattr(obj, method_name)()
            st.session_state["live_ibkr_cached_status"] = None
            st.session_state["live_ibkr_status_cached_at"] = 0.0
            return True, "OK"
        except Exception as exc:
            return False, str(exc)

    # =====================================================
    # HEADER
    # =====================================================

    st.title("📡 Live IBKR")
    st.subheader("🛡 Live Connectivity Safety Panel")

    status = gateway_status()
    connected = status.get("connected", False)
    streaming = stream_running()

    # =====================================================
    # LIVE STATUS BANNER
    # =====================================================

    if kill_switch:

        st.error(
            "🛑 KILL SWITCH ACTIVE — execution is blocked."
        )

    elif mode == "LIVE":

        if live_armed and connected:

            st.success(
                "🟢 LIVE MODE ACTIVE — broker connected and live execution armed."
            )

        elif live_armed and not connected:

            st.warning(
                "🟡 LIVE MODE ARMED — broker disconnected."
            )

        else:

            st.warning(
                "🟠 LIVE MODE SELECTED — live trading is not armed."
            )

    else:

        st.info(
            f"🔵 {mode} MODE ACTIVE — live execution is not armed."
        )

    # =====================================================
    # STATUS STRIP
    # =====================================================

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Gateway",
        "CONNECTED" if connected else "DISCONNECTED",
    )

    c2.metric(
        "Stream",
        "RUNNING" if streaming else "STOPPED",
    )

    c3.metric(
        "Market Symbols",
        market_snapshot_count(),
    )

    c4.metric(
        "Mode",
        mode,
    )

    st.divider()

    # =====================================================
    # LIVE SAFETY CONTROLS
    # =====================================================

    st.subheader("Live Safety Controls")

    s1, s2, s3 = st.columns(3)

    with s1:
        st.session_state["live_trading_armed"] = st.toggle(
            "LIVE Trading Armed",
            value=live_armed,
            disabled=mode != "LIVE",
        )

    with s2:
        st.session_state["risk_kill_switch"] = st.toggle(
            "Kill Switch",
            value=kill_switch,
        )

    with s3:
        refresh = st.button(
            "Refresh Status",
            width="stretch",
        )

    if refresh:
        reset_operator_intent()

        st.session_state["live_ibkr_cached_status"] = None
        st.session_state["live_ibkr_status_cached_at"] = 0.0
        st.session_state["live_ibkr_last_refresh"] = now()

        st.rerun()

    st.divider()

    # =====================================================
    # CONNECTION CONTROLS
    # =====================================================

    st.subheader("Connection Controls")

    st.warning(
        "This page manages connectivity only. It does not execute trades."
    )

    intent_key = st.session_state.get("live_ibkr_intent_reset_id", 0)

    connect_col, disconnect_col, stream_col = st.columns(3)

    with connect_col:
        confirm_connect = st.checkbox(
            "Confirm IBKR connect",
            value=False,
            key=f"confirm_ibkr_connect_{intent_key}",
        )

        connect_btn = st.button(
            "Connect Gateway",
            width="stretch",
            disabled=connected or not confirm_connect,
        )

    with disconnect_col:
        confirm_disconnect = st.checkbox(
            "Confirm IBKR disconnect",
            value=False,
            key=f"confirm_ibkr_disconnect_{intent_key}",
        )

        disconnect_btn = st.button(
            "Disconnect Gateway",
            width="stretch",
            disabled=not connected or not confirm_disconnect,
        )

    with stream_col:
        confirm_stream_stop = st.checkbox(
            "Confirm stream stop",
            value=False,
            key=f"confirm_stream_stop_{intent_key}",
        )

        stop_stream_btn = st.button(
            "Stop Stream",
            width="stretch",
            disabled=not streaming or not confirm_stream_stop,
        )

    if connect_btn:
        if gateway is None:
            ok = False
            reason = "Gateway object missing"

        elif not hasattr(gateway, "connect"):
            ok = False
            reason = "Gateway has no connect() method"

        else:
            try:
                result = gateway.connect(
                    host="127.0.0.1",
                    port=7497,
                    client_id=1,
                )

                ok = bool(result)

                if ok:
                    reason = "OK"
                else:
                    reason = (
                        getattr(gateway, "last_error", "")
                        or getattr(gateway, "error", "")
                        or "gateway.connect() returned False"
                    )

            except Exception as exc:
                ok = False
                reason = str(exc)

        if ok:
            reset_operator_intent()

            st.session_state["live_ibkr_cached_status"] = {
                "connected": True,
                "status": "CONNECTED",
                "detail": "connected after manual gateway connect",
            }
            st.session_state["live_ibkr_status_cached_at"] = 0.0
            st.session_state["live_ibkr_last_refresh"] = now()

            st.success("Gateway connected.")
            st.rerun()
        else:
            st.error(f"Gateway connect failed: {reason}")

    if disconnect_btn:
        ok, reason = call_if_exists(gateway, "disconnect")

        if ok:
            reset_operator_intent()

            st.session_state["live_ibkr_cached_status"] = {
                "connected": False,
                "status": "DISCONNECTED",
                "detail": "disconnected after manual gateway disconnect",
            }
            st.session_state["live_ibkr_status_cached_at"] = 0.0
            st.session_state["live_ibkr_last_refresh"] = now()

            st.success("Gateway disconnect requested.")
            st.rerun()
        else:
            st.error(f"Gateway disconnect failed: {reason}")

    if stop_stream_btn:
        ok, reason = call_if_exists(stream_engine, "stop")

        if ok:
            reset_operator_intent()

            st.success("Stream stop requested.")
            st.rerun()
        else:
            st.error(f"Stream stop failed: {reason}")

    st.divider()

    # =====================================================
    # BROKER SNAPSHOT SYNC
    # =====================================================

    st.subheader("Broker Snapshot Sync")

    st.info(
        "Manual read-only broker snapshot pull. "
        "This does NOT mutate portfolio runtime automatically."
    )

    sync_col1, sync_col2 = st.columns(2)

    with sync_col1:
        confirm_snapshot_pull = st.checkbox(
            "Confirm broker snapshot pull",
            value=False,
            key=f"confirm_snapshot_pull_{intent_key}",
        )

        pull_snapshot_btn = st.button(
            "Pull Broker Snapshot",
            width="stretch",
            disabled=(
                not connected
                or not confirm_snapshot_pull
            ),
        )

    with sync_col2:
        st.caption(
            "Pulls broker positions, open orders, "
            "and account summary into session cache."
        )

    if pull_snapshot_btn:

        broker_positions = []
        broker_open_orders = []
        broker_account_summary = []

        errors = []

        # ---------------------------------------------
        # POSITIONS
        # ---------------------------------------------

        try:

            # ---------------------------------
            # HARD REFRESH
            # ---------------------------------

            if hasattr(gateway, "refresh_positions"):

                refreshed_positions = gateway.refresh_positions()

                broker_positions = _as_list(
                    refreshed_positions
                )

            # ---------------------------------
            # SNAPSHOT CACHE
            # ---------------------------------

            if (
                not broker_positions
                and hasattr(gateway, "positions_snapshot")
            ):

                snapshot_positions = (
                    gateway.positions_snapshot()
                )

                broker_positions = _as_list(
                    snapshot_positions
                )

            # ---------------------------------
            # GENERIC ACCESSOR
            # ---------------------------------

            if (
                not broker_positions
                and hasattr(gateway, "get_positions")
            ):

                fetched_positions = (
                    gateway.get_positions()
                )

                broker_positions = _as_list(
                    fetched_positions
                )

            # ---------------------------------
            # RAW IBKR FALLBACK
            # ---------------------------------

            if (
                not broker_positions
                and hasattr(gateway, "ib")
                and gateway.ib is not None
            ):

                try:

                    raw_positions = gateway.ib.positions()

                    broker_positions = _as_list(
                        raw_positions
                    )

                except Exception as raw_exc:

                    errors.append(
                        f"ib.positions(): {raw_exc}"
                    )

            # ---------------------------------
            # NORMALIZE
            # ---------------------------------

            normalized_positions = []

            for p in broker_positions:

                try:

                    if isinstance(p, dict):

                        symbol = (
                            p.get("symbol")
                            or p.get("localSymbol")
                            or ""
                        )

                        qty = (
                            p.get("position")
                            or p.get("qty")
                            or p.get("quantity")
                            or 0
                        )

                        avg_cost = (
                            p.get("avgCost")
                            or p.get("avg_cost")
                            or p.get("average_cost")
                            or 0
                        )

                    else:

                        contract = getattr(
                            p,
                            "contract",
                            None,
                        )

                        symbol = getattr(
                            contract,
                            "symbol",
                            "",
                        )

                        qty = getattr(
                            p,
                            "position",
                            0,
                        )

                        avg_cost = getattr(
                            p,
                            "avgCost",
                            0,
                        )

                    qty = float(qty)

                    if abs(qty) <= 0.000001:
                        continue

                    normalized_positions.append(
                        {
                            "symbol": str(symbol).upper().strip(),
                            "qty": qty,
                            "avg_cost": float(avg_cost),
                        }
                    )

                except Exception as pos_exc:

                    errors.append(
                        f"normalize_position: {pos_exc}"
                    )

            broker_positions = normalized_positions

        except Exception as exc:

            errors.append(f"positions: {exc}")

        # ---------------------------------------------
        # OPEN ORDERS
        # ---------------------------------------------

        try:
            if hasattr(gateway, "refresh_open_orders"):
                broker_open_orders = _as_list(
                    gateway.refresh_open_orders()
                )

            elif hasattr(gateway, "get_open_orders"):
                broker_open_orders = _as_list(
                    gateway.get_open_orders()
                )

        except Exception as exc:
            errors.append(f"open_orders: {exc}")

        # ---------------------------------------------
        # ACCOUNT SUMMARY
        # ---------------------------------------------

        try:
            if hasattr(gateway, "refresh_account_summary"):
                broker_account_summary = _as_list(
                    gateway.refresh_account_summary()
                )

            elif hasattr(gateway, "get_account_summary"):
                broker_account_summary = _as_list(
                    gateway.get_account_summary()
                )

        except Exception as exc:
            errors.append(f"account_summary: {exc}")

        # ---------------------------------------------
        # EXECUTIONS / FILLS
        # ---------------------------------------------

        broker_fills = []

        try:

            raw_fills = []

            if (
                hasattr(gateway, "ib")
                and gateway.ib is not None
            ):

                try:

                    raw_fills = _as_list(
                        gateway.ib.fills()
                    )

                except Exception as fills_exc:

                    errors.append(
                        f"ib.fills(): {fills_exc}"
                    )

            normalized_fills = []

            for fill in raw_fills:

                try:

                    execution = getattr(
                        fill,
                        "execution",
                        None,
                    )

                    contract = getattr(
                        fill,
                        "contract",
                        None,
                    )

                    if execution is None:
                        continue

                    symbol = getattr(
                        contract,
                        "symbol",
                        "",
                    )

                    side = getattr(
                        execution,
                        "side",
                        "",
                    )

                    shares = getattr(
                        execution,
                        "shares",
                        0,
                    )

                    price = getattr(
                        execution,
                        "price",
                        0,
                    )

                    exec_id = getattr(
                        execution,
                        "execId",
                        "",
                    )

                    timestamp = getattr(
                        execution,
                        "time",
                        "",
                    )

                    normalized_fills.append(
                        {
                            "exec_id": str(exec_id),
                            "symbol": str(symbol).upper().strip(),
                            "action": str(side).upper().strip(),
                            "qty": float(shares),
                            "price": float(price),
                            "timestamp": str(timestamp),
                            "source": "ibkr_live_execution_snapshot",
                        }
                    )

                except Exception as fill_exc:

                    errors.append(
                        f"normalize_fill: {fill_exc}"
                    )

            broker_fills = normalized_fills

        except Exception as exc:

            errors.append(f"broker_fills: {exc}")

        # ---------------------------------------------
        # STORE SNAPSHOTS
        # ---------------------------------------------

        st.session_state["broker_snapshot_positions"] = broker_positions
        st.session_state["broker_snapshot_open_orders"] = broker_open_orders
        st.session_state["broker_snapshot_account_summary"] = broker_account_summary
        st.session_state["broker_snapshot_fills"] = broker_fills
        st.session_state["broker_snapshot_timestamp"] = now()
        st.session_state["broker_snapshot_errors"] = errors

        reset_operator_intent()

        if errors:
            st.warning(
                "Broker snapshot completed with partial errors: "
                + " | ".join(errors)
            )

        else:
            st.success(
                "Broker snapshot pull completed successfully."
            )

        st.rerun()

    # =====================================================
    # SNAPSHOT STATUS
    # =====================================================

    broker_snapshot_positions = st.session_state.get(
        "broker_snapshot_positions",
        [],
    )

    broker_snapshot_open_orders = st.session_state.get(
        "broker_snapshot_open_orders",
        [],
    )

    broker_snapshot_account_summary = st.session_state.get(
        "broker_snapshot_account_summary",
        [],
    )

    broker_snapshot_fills = st.session_state.get(
        "broker_snapshot_fills",
        [],
    )

    broker_snapshot_timestamp = st.session_state.get(
        "broker_snapshot_timestamp",
        "",
    )

    broker_snapshot_errors = st.session_state.get(
        "broker_snapshot_errors",
        [],
    )

    snap1, snap2, snap3, snap4, snap5 = st.columns(5)

    snap1.metric(
        "Broker Positions",
        _safe_len(broker_snapshot_positions),
    )

    snap2.metric(
        "Broker Open Orders",
        _safe_len(broker_snapshot_open_orders),
    )

    snap3.metric(
        "Account Summary Rows",
        _safe_len(broker_snapshot_account_summary),
    )

    snap4.metric(
        "Broker Fills",
        _safe_len(broker_snapshot_fills),
    )

    snap5.metric(
        "Snapshot Cached",
        "YES" if broker_snapshot_timestamp else "NO",
    )

    if broker_snapshot_timestamp:
        st.caption(
            f"Last broker snapshot: {broker_snapshot_timestamp}"
        )

    if broker_snapshot_errors:
        st.warning(
            "Last broker snapshot warnings: "
            + " | ".join(str(e) for e in broker_snapshot_errors)
        )

    st.divider()

    # =====================================================
    # COMPONENT STATUS
    # =====================================================

    st.subheader("Component Status")

    stream_status = "ONLINE" if stream_engine else "NOT CONFIGURED"
    stream_running_status = "YES" if streaming else "N/A"

    status_rows = {
        "Gateway Object": "ONLINE" if gateway else "MISSING",
        "Gateway Connected": "YES" if connected else "NO",
        "Gateway Status": status.get("status"),
        "Stream Engine": stream_status,
        "Stream Running": stream_running_status,
        "Market Hub": "ONLINE" if market else "MISSING",
        "OMS": "ONLINE" if oms else "MISSING",
        "Pipeline": "READY" if pipeline else "MISSING",
        "Risk Engine": "ONLINE" if risk_engine else "MISSING",
        "Mode": mode,
        "LIVE Armed": "YES" if st.session_state.get("live_trading_armed") else "NO",
        "Kill Switch": "ON" if st.session_state.get("risk_kill_switch") else "OFF",
        "Last Refresh": st.session_state.get("live_ibkr_last_refresh", ""),
    }

    st.table(
        {
            "Component": list(status_rows.keys()),
            "Status": list(status_rows.values()),
        }
    )

    # =====================================================
    # RAW STATUS
    # =====================================================

    with st.expander("Gateway detail"):
        st.write(status.get("detail"))

    with st.expander("Live execution guard summary"):
        st.write(
            {
                "mode": mode,
                "live_trading_armed": st.session_state.get("live_trading_armed"),
                "risk_kill_switch": st.session_state.get("risk_kill_switch"),
                "pipeline_ready": pipeline is not None,
                "oms_ready": oms is not None,
                "gateway_connected": connected,
                "streaming": streaming,
            }
        )

    with st.expander("Cached broker snapshot detail"):
        st.write(
            {
                "positions": broker_snapshot_positions,
                "open_orders": broker_snapshot_open_orders,
                "account_summary": broker_snapshot_account_summary,
                "timestamp": broker_snapshot_timestamp,
                "errors": broker_snapshot_errors,
            }
        )


def run_page():
    page()