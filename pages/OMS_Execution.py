# =========================================================
# ⚡ OMS EXECUTION PAGE v34.6
# INSTITUTIONAL EXECUTION SAFETY
# + IDEMPOTENT REPLAY
# + DUPLICATE EXECUTION LOCK
# =========================================================

from __future__ import annotations

from datetime import datetime, timezone
import uuid
import time
import hashlib
import json

import pandas as pd
import streamlit as st

from core.bootstrap import init_core


def run_page():

    gateway, market, oms, portfolio_engine = init_core()

    risk_engine = st.session_state.get("risk_engine")
    pipeline = st.session_state.get("pipeline")
    audit_store = st.session_state.get("audit_store")

    st.session_state.setdefault("mode", "SIM")
    st.session_state.setdefault("live_trading_armed", False)
    st.session_state.setdefault("risk_kill_switch", False)
    st.session_state.setdefault("last_close_verification", [])
    st.session_state.setdefault("flatten_lock_active", False)
    st.session_state.setdefault("flatten_lock_ts", 0.0)
    st.session_state.setdefault("live_execute_phrase", "")
    st.session_state.setdefault("oms_emergency_ack", False)
    st.session_state.setdefault("last_replay_report", {})

    # v34.6 duplicate execution lock state
    st.session_state.setdefault("oms_execution_lock_active", False)
    st.session_state.setdefault("oms_execution_lock_ts", 0.0)
    st.session_state.setdefault("oms_last_execution_fingerprint", "")
    st.session_state.setdefault("oms_last_execution_ts", 0.0)
    st.session_state.setdefault("oms_last_execution_report", {})
    st.session_state.setdefault("oms_execution_history", [])

    # =====================================================
    # HELPERS
    # =====================================================

    def now():
        return datetime.now(timezone.utc).isoformat()

    def new_id(prefix: str):
        return f"{prefix}-{uuid.uuid4().hex[:10]}"

    def refresh_refs():
        nonlocal gateway, market, oms, portfolio_engine, risk_engine, pipeline, audit_store

        gateway = st.session_state.get("gateway", gateway)
        market = st.session_state.get("market", market)
        oms = st.session_state.get("oms", oms)
        portfolio_engine = st.session_state.get("portfolio_engine", portfolio_engine)
        risk_engine = st.session_state.get("risk_engine", risk_engine)
        pipeline = st.session_state.get("pipeline", pipeline)
        audit_store = st.session_state.get("audit_store", audit_store)

    def safe_snapshot(obj):
        if obj and hasattr(obj, "snapshot"):
            try:
                snap = obj.snapshot()
                return snap if isinstance(snap, dict) else {}
            except Exception:
                return {}
        return {}

    def force_portfolio_refresh():
        refresh_refs()

        if portfolio_engine and hasattr(portfolio_engine, "snapshot"):
            try:
                snap = portfolio_engine.snapshot()
                return snap if isinstance(snap, dict) else {}
            except Exception:
                return {}

        return {}

    def get_positions():
        return force_portfolio_refresh()

    def get_position_row(symbol: str):
        return get_positions().get(str(symbol or "").upper().strip(), {})

    def get_signed_qty(symbol: str):
        row = get_position_row(symbol)

        try:
            return float(row.get("signed_qty", row.get("qty", 0)) or 0)
        except Exception:
            return 0.0

    def sync_risk():
        refresh_refs()

        try:
            if (
                portfolio_engine
                and risk_engine
                and hasattr(portfolio_engine, "risk_positions")
                and hasattr(risk_engine, "sync_positions")
            ):
                positions = portfolio_engine.risk_positions()

                try:
                    risk_engine.sync_positions(positions, historical=True)
                except TypeError:
                    risk_engine.sync_positions(positions)

                return True
        except Exception:
            return False

        return False

    def full_truth_sync():
        force_portfolio_refresh()
        sync_risk()
        return {
            "portfolio": force_portfolio_refresh(),
            "risk": safe_snapshot(risk_engine),
        }

    def get_pipeline_results():
        refresh_refs()

        if pipeline and hasattr(pipeline, "results_snapshot"):
            try:
                rows = pipeline.results_snapshot()
                return rows if isinstance(rows, list) else []
            except Exception:
                return []

        if pipeline and hasattr(pipeline, "results"):
            try:
                return list(pipeline.results)
            except Exception:
                return []

        return []

    def get_fills():
        refresh_refs()

        if oms and hasattr(oms, "fills_snapshot"):
            try:
                rows = oms.fills_snapshot()
                return rows if isinstance(rows, list) else []
            except Exception:
                return []

        if oms and hasattr(oms, "fills"):
            try:
                return list(oms.fills)
            except Exception:
                return []

        return []

    def get_portfolio_ledger():
        refresh_refs()

        if portfolio_engine and hasattr(portfolio_engine, "ledger_snapshot"):
            try:
                rows = portfolio_engine.ledger_snapshot()
                return rows if isinstance(rows, list) else []
            except Exception:
                return []

        return []

    def get_audit_events(limit=500):
        refresh_refs()

        for method in ("events", "recent_events"):
            if audit_store and hasattr(audit_store, method):
                try:
                    rows = getattr(audit_store, method)(limit=limit)
                    return rows if isinstance(rows, list) else []
                except Exception:
                    return []

        return []

    def get_audit_fills(limit=500):
        refresh_refs()

        for method in ("fills", "recent_fills"):
            if audit_store and hasattr(audit_store, method):
                try:
                    rows = getattr(audit_store, method)(limit=limit)
                    return rows if isinstance(rows, list) else []
                except Exception:
                    return []

        return []

    def get_audit_stats():
        refresh_refs()

        if audit_store and hasattr(audit_store, "stats"):
            try:
                stats = audit_store.stats()
                return stats if isinstance(stats, dict) else {}
            except Exception:
                return {}

        events = get_audit_events(limit=5000)

        fills = [
            e for e in events
            if isinstance(e, dict)
            and str(e.get("event_type", "")).upper() == "FILL"
        ]

        return {
            "audit_events": len(events),
            "audit_fills": len(fills),
        }

    def audit_event(event_type: str, payload: dict):
        refresh_refs()

        if audit_store is None:
            return

        payload = {
            **payload,
            "event_type": event_type,
            "timestamp": payload.get("timestamp") or now(),
        }

        try:
            if hasattr(audit_store, "record_event"):
                audit_store.record_event(event_type, payload)
            elif hasattr(audit_store, "record_pipeline_result"):
                audit_store.record_pipeline_result(payload)
        except Exception:
            pass

    # =====================================================
    # RUNTIME CONTROL
    # =====================================================

    def reset_risk_counters_only():
        refresh_refs()

        if risk_engine is None:
            return False

        try:
            if hasattr(risk_engine, "daily_trades"):
                risk_engine.daily_trades = 0

            if hasattr(risk_engine, "daily_pnl"):
                risk_engine.daily_pnl = 0.0

            if hasattr(risk_engine, "risk_state"):
                risk_engine.risk_state = "NORMAL"

            if hasattr(risk_engine, "risk_state_reason"):
                risk_engine.risk_state_reason = "COUNTERS_RESET"

            if hasattr(risk_engine, "last_error"):
                risk_engine.last_error = ""

            sync_risk()

            audit_event(
                "RISK_COUNTER_RESET",
                {
                    "source": "oms_execution_v34_6",
                },
            )

            return True

        except Exception:
            return False

    def clear_runtime():
        """
        HARD runtime clear.

        Clears:
        - OMS runtime fills/orders
        - portfolio runtime state
        - risk runtime state

        Preserves:
        - persistent audit history
        """

        refresh_refs()

        if oms and hasattr(oms, "clear"):
            try:
                oms.clear()
            except Exception:
                pass

        if portfolio_engine and hasattr(portfolio_engine, "clear"):
            try:
                portfolio_engine.clear()
            except Exception:
                pass

        if risk_engine and hasattr(risk_engine, "reset"):
            try:
                risk_engine.reset()
            except Exception:
                pass

        st.session_state["last_close_verification"] = []
        st.session_state["flatten_lock_active"] = False
        st.session_state["flatten_lock_ts"] = 0.0

        st.session_state["oms_execution_lock_active"] = False
        st.session_state["oms_execution_lock_ts"] = 0.0

        audit_event(
            "RUNTIME_CLEAR",
            {
                "source": "oms_execution_v34_6",
            },
        )

    def replay_runtime():
        """
        Institutional replay rebuild.

        Source of truth = persistent audit fills.

        IMPORTANT:
        runtime MUST be empty before replay.
        """

        refresh_refs()

        clear_runtime()

        runtime_before = len(get_fills())
        ledger_before = len(get_portfolio_ledger())
        audit_fills = get_audit_fills(limit=10000)

        if not audit_fills:
            st.session_state["last_replay_report"] = {
                "status": "NO_AUDIT_FILLS",
                "runtime_before": runtime_before,
                "ledger_before": ledger_before,
                "audit_fills": 0,
            }
            return False

        replay_ok = False

        if audit_store and hasattr(audit_store, "replay_fills"):
            try:
                audit_store.replay_fills(
                    oms=oms,
                    portfolio=portfolio_engine,
                    risk=risk_engine,
                )
                replay_ok = True
            except Exception:
                replay_ok = False

        elif audit_store and hasattr(audit_store, "rebuild_runtime_state"):
            try:
                audit_store.rebuild_runtime_state(
                    oms=oms,
                    portfolio=portfolio_engine,
                    risk=risk_engine,
                )
                replay_ok = True
            except Exception:
                replay_ok = False

        if not replay_ok:
            st.session_state["last_replay_report"] = {
                "status": "REPLAY_FAILED",
                "runtime_before": runtime_before,
                "ledger_before": ledger_before,
                "audit_fills": len(audit_fills),
            }
            return False

        full_truth_sync()

        runtime_after = len(get_fills())
        ledger_after = len(get_portfolio_ledger())
        positions_after = len(get_positions())

        st.session_state["last_replay_report"] = {
            "status": "OK",
            "runtime_before": runtime_before,
            "ledger_before": ledger_before,
            "audit_fills": len(audit_fills),
            "runtime_after": runtime_after,
            "ledger_after": ledger_after,
            "positions_after": positions_after,
        }

        audit_event(
            "RUNTIME_REPLAY",
            {
                "source": "oms_execution_v34_6",
                "runtime_after": runtime_after,
                "ledger_after": ledger_after,
                "positions_after": positions_after,
            },
        )

        return True
    
    # =====================================================
    # EMERGENCY FLATTEN ENGINE v36.0
    # =====================================================

    def flatten_locked():
        ts = st.session_state.get("flatten_lock_ts", 0.0)

        if not ts:
            return False

        age = time.time() - ts

        if age > 30:
            st.session_state["flatten_lock_active"] = False
            st.session_state["flatten_lock_ts"] = 0.0
            return False

        return bool(st.session_state.get("flatten_lock_active", False))

    def lock_flatten():
        st.session_state["flatten_lock_active"] = True
        st.session_state["flatten_lock_ts"] = time.time()

    def unlock_flatten():
        st.session_state["flatten_lock_active"] = False
        st.session_state["flatten_lock_ts"] = 0.0

    def normalize_position_rows():
        """
        Returns normalized active positions from PortfolioEngine snapshot.

        Output:
        {
            "AAPL": {
                "symbol": "AAPL",
                "signed_qty": 35.0,
                "qty": 35.0,
                "side": "LONG",
                "last_price": 190.0,
            }
        }
        """

        rows = get_positions()

        normalized = {}

        if not isinstance(rows, dict):
            return normalized

        for symbol, row in rows.items():

            symbol = str(symbol or "").upper().strip()

            if not symbol:
                continue

            if isinstance(row, dict):
                raw_qty = (
                    row.get("signed_qty")
                    if row.get("signed_qty") is not None
                    else row.get("qty", 0)
                )

                try:
                    signed_qty = float(raw_qty or 0)
                except Exception:
                    signed_qty = 0.0

                side = str(row.get("side") or "").upper().strip()

                if side == "SHORT" and signed_qty > 0:
                    signed_qty = -abs(signed_qty)

                elif side == "LONG" and signed_qty < 0:
                    signed_qty = abs(signed_qty)

                price = (
                    row.get("last_price")
                    or row.get("price")
                    or row.get("avg_price")
                    or row.get("fill_price")
                    or 0
                )

                try:
                    price = float(price or 0)
                except Exception:
                    price = 0.0

            else:
                try:
                    signed_qty = float(row or 0)
                except Exception:
                    signed_qty = 0.0

                price = 0.0

            if abs(signed_qty) <= 1e-9:
                continue

            normalized[symbol] = {
                "symbol": symbol,
                "signed_qty": signed_qty,
                "qty": abs(signed_qty),
                "side": "LONG" if signed_qty > 0 else "SHORT",
                "last_price": price,
            }

        return normalized

    def build_emergency_flatten_signals():
        """
        Builds opposite-side liquidation orders from current portfolio truth.
        Long  +35 -> SELL 35
        Short -10 -> BUY  10
        """

        refresh_refs()
        full_truth_sync()

        positions = normalize_position_rows()

        request_id = new_id("EMERG-FLAT")

        signals = []

        for symbol, row in positions.items():

            signed_qty = float(row.get("signed_qty", 0) or 0)
            qty = abs(signed_qty)

            if qty <= 0:
                continue

            action = "SELL" if signed_qty > 0 else "BUY"

            price = float(row.get("last_price", 0) or 0)

            if price <= 0:
                try:
                    risk_snap = safe_snapshot(risk_engine)
                    last_prices = risk_snap.get("last_prices", {})
                    price = float(last_prices.get(symbol, 0) or 0)
                except Exception:
                    price = 0.0

            if price <= 0:
                price = 1.0

            signals.append(
                {
                    "timestamp": now(),
                    "symbol": symbol,
                    "action": action,
                    "side": action,
                    "qty": qty,
                    "price": price,
                    "mode": st.session_state.get("mode", "SIM"),
                    "source": "oms_emergency_flatten_v36_0",
                    "execution_type": "EMERGENCY",
                    "emergency_flatten": True,
                    "flatten_generated": True,
                    "force_position_context": True,
                    "close_or_flatten_context": True,
                    "flatten_request_id": request_id,
                    "position_before": signed_qty,
                    "position_after_expected": 0.0,
                    "position_action": (
                        "CLOSE_LONG"
                        if signed_qty > 0
                        else "CLOSE_SHORT"
                    ),
                }
            )

        return request_id, signals

    def route_emergency_signal(signal):
        """
        Routes emergency flatten signal through pipeline if available,
        otherwise directly through OMS.
        """

        refresh_refs()

        if pipeline is not None:
            for method_name in (
                "execute_emergency",
                "execute",
                "route",
                "process_signal",
            ):
                if hasattr(pipeline, method_name):
                    try:
                        return getattr(pipeline, method_name)(signal)
                    except Exception as exc:
                        return {
                            "status": "ERROR",
                            "reason": str(exc),
                            "symbol": signal.get("symbol"),
                            "action": signal.get("action"),
                            "qty": signal.get("qty"),
                        }

        if oms is not None:
            for method_name in (
                "execute_signal",
                "execute",
                "route",
                "process_signal",
            ):
                if hasattr(oms, method_name):
                    try:
                        return getattr(oms, method_name)(signal)
                    except Exception as exc:
                        return {
                            "status": "ERROR",
                            "reason": str(exc),
                            "symbol": signal.get("symbol"),
                            "action": signal.get("action"),
                            "qty": signal.get("qty"),
                        }

        return {
            "status": "ERROR",
            "reason": "No execution route available",
            "symbol": signal.get("symbol"),
            "action": signal.get("action"),
            "qty": signal.get("qty"),
        }
    
    def emergency_flatten_all():
        """
        Executes emergency flatten for every active portfolio position.

        Safety:
        - duplicate locked
        - audit-start / audit-complete events
        - routes through pipeline where possible
        - final reconciliation sync
        """

        refresh_refs()

        if flatten_locked():
            report = {
                "timestamp": now(),
                "status": "BLOCKED",
                "reason": "Emergency flatten lock active",
            }

            audit_event("EMERGENCY_FLATTEN_BLOCKED", report)
            return report

        request_id, signals = build_emergency_flatten_signals()

        if not signals:
            report = {
                "timestamp": now(),
                "status": "SKIPPED",
                "reason": "No active positions to flatten",
                "flatten_request_id": request_id,
            }

            audit_event("EMERGENCY_FLATTEN_SKIPPED", report)
            return report

        lock_flatten()

        if risk_engine is not None:
            try:
                if hasattr(risk_engine, "risk_state"):
                    risk_engine.risk_state = "EMERGENCY_FLATTEN"

                if hasattr(risk_engine, "risk_state_reason"):
                    risk_engine.risk_state_reason = "MANUAL_EMERGENCY_FLATTEN"

            except Exception:
                pass

        start_payload = {
            "timestamp": now(),
            "status": "STARTED",
            "flatten_request_id": request_id,
            "signals": len(signals),
            "symbols": [s.get("symbol") for s in signals],
            "mode": st.session_state.get("mode", "SIM"),
            "source": "oms_emergency_flatten_v36_0",
        }

        audit_event("EMERGENCY_FLATTEN_START", start_payload)

        results = []

        try:
            for signal in signals:
                audit_event(
                    "EMERGENCY_FLATTEN_ORDER_CREATED",
                    {
                        **signal,
                        "flatten_request_id": request_id,
                    },
                )

                result = route_emergency_signal(signal)

                if not isinstance(result, dict):
                    result = {
                        "status": "ERROR",
                        "reason": "Emergency route returned non-dict result",
                        "symbol": signal.get("symbol"),
                        "action": signal.get("action"),
                        "qty": signal.get("qty"),
                    }

                result = {
                    **result,
                    "flatten_request_id": request_id,
                    "emergency_flatten": True,
                    "source": "oms_emergency_flatten_v36_0",
                }

                audit_event(
                    "EMERGENCY_FLATTEN_ORDER_RESULT",
                    result,
                )

                results.append(result)

        finally:
            unlock_flatten()

        full_truth_sync()

        after_positions = normalize_position_rows()

        completed = [
            r for r in results
            if str(r.get("status", "")).upper() in (
                "COMPLETE",
                "FILLED",
                "ORDER_FILLED",
                "SUCCESS",
            )
        ]

        failed = [
            r for r in results
            if str(r.get("status", "")).upper() in (
                "ERROR",
                "REJECTED",
                "BLOCKED",
                "TIMEOUT",
            )
        ]

        residual_symbols = list(after_positions.keys())

        final_status = (
            "COMPLETE"
            if not residual_symbols and not failed
            else "PARTIAL_OR_FAILED"
        )

        complete_payload = {
            "timestamp": now(),
            "status": final_status,
            "flatten_request_id": request_id,
            "orders_attempted": len(signals),
            "orders_complete": len(completed),
            "orders_failed": len(failed),
            "residual_positions": len(residual_symbols),
            "residual_symbols": residual_symbols,
            "runtime_fills": len(get_fills()),
            "portfolio_ledger": len(get_portfolio_ledger()),
            "audit_fills": int(get_audit_stats().get("audit_fills", 0) or 0),
            "mode": st.session_state.get("mode", "SIM"),
            "source": "oms_emergency_flatten_v36_0",
        }

        audit_event("EMERGENCY_FLATTEN_COMPLETE", complete_payload)

        st.session_state["last_emergency_flatten_report"] = {
            **complete_payload,
            "results": results,
        }

        return st.session_state["last_emergency_flatten_report"]    

    # =====================================================
    # EXECUTION SAFETY
    # =====================================================

    def execution_fingerprint(rows):
        """
        Stable fingerprint for duplicate execution prevention.
        """

        if not rows:
            return ""

        normalized = []

        for row in rows:
            if not isinstance(row, dict):
                continue

            normalized.append(
                {
                    "symbol": str(row.get("symbol", "")),
                    "action": str(row.get("execution_action", "")),
                    "qty": float(row.get("qty", 0) or 0),
                    "price": float(row.get("price", 0) or 0),
                }
            )

        payload = json.dumps(normalized, sort_keys=True)

        return hashlib.sha256(payload.encode()).hexdigest()

    def execution_locked():
        ts = st.session_state.get("oms_execution_lock_ts", 0.0)

        if not ts:
            return False

        age = time.time() - ts

        if age > 30:
            st.session_state["oms_execution_lock_active"] = False
            st.session_state["oms_execution_lock_ts"] = 0.0
            return False

        return st.session_state.get("oms_execution_lock_active", False)

    def lock_execution():
        st.session_state["oms_execution_lock_active"] = True
        st.session_state["oms_execution_lock_ts"] = time.time()

    def unlock_execution():
        st.session_state["oms_execution_lock_active"] = False
        st.session_state["oms_execution_lock_ts"] = 0.0

    def get_risk_positions():
        refresh_refs()

        if risk_engine is None:
            return {}

        if hasattr(risk_engine, "positions_snapshot"):
            try:
                rows = risk_engine.positions_snapshot()
                return rows if isinstance(rows, dict) else {}
            except Exception:
                return {}

        if hasattr(risk_engine, "positions"):
            try:
                rows = risk_engine.positions
                return rows if isinstance(rows, dict) else {}
            except Exception:
                return {}

        snapshot = safe_snapshot(risk_engine)

        if isinstance(snapshot, dict):
            positions = snapshot.get("positions", {})
            return positions if isinstance(positions, dict) else {}

        return {}

    # =====================================================
    # EXECUTION PANEL
    # =====================================================

    st.subheader("⚡ OMS Execution")
    st.caption("🛡️ Execution Safety Panel v34.8 — LIVE Infrastructure Lock")

    st.session_state.setdefault("mode", "SIM")
    st.session_state.setdefault("live_trading_armed", False)
    st.session_state.setdefault("risk_kill_switch", False)
    st.session_state.setdefault("oms_live_unlocked_v34_8", False)

    current_mode = str(
        st.session_state.get("mode", "SIM")
    ).upper().strip()

    if current_mode not in ("SIM", "LIVE"):
        current_mode = "SIM"

    requested_mode = st.selectbox(
        "Mode",
        ["SIM", "LIVE"],
        index=0 if current_mode == "SIM" else 1,
        key="oms_requested_mode_v34_8",
    )

    requested_mode = str(requested_mode).upper().strip()

    live_unlocked = bool(
        st.session_state.get("oms_live_unlocked_v34_8", False)
    )

    if requested_mode == "LIVE":

        st.error("🚨 OMS LIVE MODE REQUESTED — REAL BROKER ORDERS MAY BE ROUTED")

        live_master_ack = st.checkbox(
            "I understand OMS LIVE can route REAL broker orders",
            value=bool(st.session_state.get("oms_live_master_ack_v34_8", False)),
            key="oms_live_master_ack_v34_8",
        )

        live_master_phrase = st.text_input(
            "Type ARM OMS LIVE to unlock OMS LIVE mode",
            value=st.session_state.get("oms_live_master_phrase_v34_8", ""),
            key="oms_live_master_phrase_v34_8",
        )

        live_master_phrase_ok = (
            str(live_master_phrase).strip().upper() == "ARM OMS LIVE"
        )

        if live_master_ack and live_master_phrase_ok:
            live_unlocked = True
            st.session_state["oms_live_unlocked_v34_8"] = True

        if live_unlocked:
            mode = "LIVE"
            st.error("🚨 OMS LIVE INFRASTRUCTURE MODE ENABLED")
        else:
            mode = "SIM"
            st.warning("OMS LIVE request blocked. System remains in SIM mode.")

    else:
        mode = "SIM"
        live_unlocked = False

        st.session_state["oms_live_unlocked_v34_8"] = False
        st.session_state["oms_live_master_ack_v34_8"] = False
        st.session_state["oms_live_master_phrase_v34_8"] = ""
        st.session_state["live_trading_armed"] = False

    # =====================================================
    # PROPAGATE MODE TO REAL RUNTIME OBJECTS
    # =====================================================

    st.session_state["mode"] = mode

    refresh_refs()

    for obj in (gateway, oms, risk_engine, pipeline):
        if obj is not None and hasattr(obj, "set_mode"):
            try:
                obj.set_mode(mode)
            except Exception:
                pass

    for obj in (gateway, oms, risk_engine, pipeline):
        if obj is not None and hasattr(obj, "mode"):
            try:
                obj.mode = mode
            except Exception:
                pass

    refresh_refs()

    live_armed = False

    if mode == "LIVE":

        live_armed = st.checkbox(
            "LIVE Trading Armed",
            value=bool(st.session_state.get("live_trading_armed", False)),
            key="oms_live_trading_armed_v34_8",
        )

        if live_armed:
            st.error("🚨 LIVE TRADING ARMED — ORDERS MAY ROUTE TO BROKER")
        else:
            st.warning("OMS is LIVE, but trading is not armed.")

    else:
        st.session_state["live_trading_armed"] = False
        st.info("SIM mode active. LIVE trading is locked.")

    st.session_state["live_trading_armed"] = live_armed

    kill_switch = st.checkbox(
        "Kill Switch",
        value=bool(st.session_state.get("risk_kill_switch", False)),
        key="oms_kill_switch_v34_8",
    )

    st.session_state["risk_kill_switch"] = kill_switch

    if risk_engine and hasattr(risk_engine, "kill_switch"):
        risk_engine.kill_switch = kill_switch

    # =====================================================
    # RECONCILIATION CENTER
    # =====================================================

    runtime_fills = get_fills()
    portfolio_ledger = get_portfolio_ledger()
    audit_fills = get_audit_fills(limit=10000)
    positions = get_positions()
    risk_positions = get_risk_positions()

    if isinstance(runtime_fills, dict):
        runtime_fills = list(runtime_fills.values())

    if isinstance(portfolio_ledger, dict):
        portfolio_ledger = list(portfolio_ledger.values())

    if isinstance(audit_fills, dict):
        audit_fills = list(audit_fills.values())

    if isinstance(positions, dict):
        positions_count = len(positions)
    elif isinstance(positions, list):
        positions_count = len(positions)
    elif isinstance(positions, set):
        positions_count = len(positions)
    else:
        positions_count = 0

    if isinstance(risk_positions, dict):
        risk_positions_count = len(risk_positions)
    elif isinstance(risk_positions, list):
        risk_positions_count = len(risk_positions)
    elif isinstance(risk_positions, set):
        risk_positions_count = len(risk_positions)
    else:
        risk_positions_count = 0

    st.markdown("### 🏛 Institutional Reconciliation Center")

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Runtime Fills", len(runtime_fills))
    c2.metric("Portfolio Ledger", len(portfolio_ledger))
    c3.metric("Audit Fills", len(audit_fills))
    c4.metric("Portfolio Positions", positions_count)
    c5.metric("Risk Positions", risk_positions_count)

    ledger_match = (
        len(portfolio_ledger) == len(audit_fills)
    )

    position_match = (
        positions_count == risk_positions_count
    )

    runtime_empty_after_restart = (
        len(runtime_fills) == 0
        and len(audit_fills) > 0
        and len(portfolio_ledger) == len(audit_fills)
    )

    full_runtime_match = (
        len(runtime_fills) == len(portfolio_ledger)
        and len(runtime_fills) == len(audit_fills)
    )

    if ledger_match and position_match:

        if runtime_empty_after_restart:
            st.success(
                "Institutional reconciliation: MATCH "
                "(runtime cache empty after restart)"
            )

        elif full_runtime_match:
            st.success("Institutional reconciliation: MATCH")

        else:
            st.success(
                "Institutional reconciliation: MATCH "
                "(audit/portfolio/risk aligned; runtime cache is non-authoritative)"
            )

    else:
        st.error(
            "Institutional reconciliation drift: "
            "FILL_LEDGER_AUDIT_MISMATCH"
        )

        if portfolio_engine and hasattr(
            portfolio_engine,
            "reconcile_runtime_vs_portfolio",
        ):
            try:
                drift_report = portfolio_engine.reconcile_runtime_vs_portfolio(
                    runtime_fills=runtime_fills,
                    audit_fills=audit_fills,
                )

                st.session_state["last_portfolio_reconcile_report"] = drift_report

                if isinstance(drift_report, dict) and drift_report.get("status") == "OK":
                    st.success("Portfolio ledger repaired from runtime/audit truth.")
                    st.rerun()

                else:
                    st.warning(
                        "Portfolio repair attempted. Review reconcile report below."
                    )

            except Exception as exc:
                st.warning(f"Portfolio repair failed: {exc}")

        if st.session_state.get("last_portfolio_reconcile_report"):
            with st.expander("Last Portfolio Reconcile Report"):
                st.json(st.session_state["last_portfolio_reconcile_report"])

    # =====================================================
    # OPERATIONAL CONTROLS
    # =====================================================

    st.markdown("### Operational Controls")

    oc1, oc2, oc3 = st.columns(3)

    confirm_replay = oc1.checkbox("Confirm runtime rebuild from audit")
    replay_clicked = oc1.button("Replay Audit / Rebuild Runtime")

    confirm_reset = oc2.checkbox("Confirm risk counter reset")
    reset_clicked = oc2.button("Reset Risk Counters")

    confirm_test = oc3.checkbox("Confirm OMS test fill")
    test_clicked = oc3.button("Test OMS Fill")

    if replay_clicked:
        if not confirm_replay:
            st.warning("Replay requires confirmation.")
        else:
            ok = replay_runtime()

            if ok:
                st.success("Runtime rebuilt from audit truth.")
                st.rerun()
            else:
                st.error("Replay failed.")

    if reset_clicked:
        if not confirm_reset:
            st.warning("Risk reset requires confirmation.")
        else:
            ok = reset_risk_counters_only()

            if ok:
                st.success("Risk counters reset.")
                st.rerun()
            else:
                st.error("Risk reset failed.")

    if test_clicked:
        if not confirm_test:
            st.warning("OMS fill test requires confirmation.")
        else:
            st.info("OMS test fill not enabled in this build.")

    # =====================================================
    # RUNTIME CLEAR
    # =====================================================

    st.markdown("### Runtime Clear Zone")

    confirm_clear = st.checkbox("Confirm runtime clear")

    if st.button("Clear Runtime OMS"):
        if not confirm_clear:
            st.warning("Runtime clear requires confirmation.")
        else:
            clear_runtime()
            st.success("Runtime cleared.")
            st.rerun()


    # =====================================================
    # EMERGENCY FLATTEN CONTROL
    # =====================================================

    st.markdown("### 🚨 Emergency Flatten")

    emergency_positions = normalize_position_rows()
    emergency_mode = st.session_state.get("mode", "SIM")

    ef1, ef2, ef3 = st.columns(3)

    ef1.metric("Positions To Flatten", len(emergency_positions))
    ef2.metric("Flatten Lock", "ACTIVE" if flatten_locked() else "CLEAR")
    ef3.metric("Mode", emergency_mode)

    if emergency_positions:
        st.warning(
            "Emergency Flatten will send opposite-side orders for every active position. "
            "Use only when you want the system flat."
        )
    else:
        st.success("No active positions to flatten.")

    confirm_flatten_1 = st.checkbox(
        "Confirm emergency flatten all positions"
    )

    confirm_flatten_2 = st.checkbox(
        "I understand this will attempt to close every active position"
    )

    live_phrase_ok = True

    if emergency_mode == "LIVE":
        phrase = st.text_input(
            "LIVE emergency phrase",
            placeholder="Type EMERGENCY FLATTEN",
            key="live_emergency_flatten_phrase_v36_0",
        )

        live_phrase_ok = phrase.strip().upper() == "EMERGENCY FLATTEN"

    flatten_btn = st.button(
        "🚨 EMERGENCY FLATTEN ALL POSITIONS",
        use_container_width=True,
        disabled=(
            not emergency_positions
            or flatten_locked()
            or not confirm_flatten_1
            or not confirm_flatten_2
            or not live_phrase_ok
        ),
    )

    if flatten_btn:
        report = emergency_flatten_all()
        status = str(report.get("status", "UNKNOWN"))

        if status == "COMPLETE":
            st.success("Emergency flatten completed. Book is flat.")
        elif status == "SKIPPED":
            st.info(report.get("reason", "Emergency flatten skipped."))
        else:
            st.warning(
                f"Emergency flatten finished with status: {status}. "
                "Check residual positions and audit trail."
            )

        st.rerun()

    last_flatten = st.session_state.get("last_emergency_flatten_report", {})

    if last_flatten:
        with st.expander("Last Emergency Flatten Report"):
            st.json(last_flatten)            

    # =====================================================
    # DUPLICATE EXECUTION LOCK
    # =====================================================

    def route_signal(signal):
        refresh_refs()

        if not isinstance(signal, dict):
            return {
                "status": "ERROR",
                "reason": "Invalid signal",
            }

        if pipeline is not None:
            for method_name in (
                "execute",
                "route",
                "process_signal",
                "process",
            ):
                if hasattr(pipeline, method_name):
                    try:
                        return getattr(pipeline, method_name)(signal)
                    except Exception as exc:
                        return {
                            "status": "ERROR",
                            "reason": str(exc),
                            "symbol": signal.get("symbol"),
                            "action": signal.get("action"),
                            "qty": signal.get("qty"),
                        }

        return {
            "status": "ERROR",
            "reason": "Pipeline unavailable",
            "symbol": signal.get("symbol"),
            "action": signal.get("action"),
            "qty": signal.get("qty"),
        }

    def execute_scanner_plan():
        refresh_refs()

        if pipeline is None:
            report = {
                "timestamp": now(),
                "status": "REJECTED",
                "reason": "Pipeline unavailable",
            }
            st.session_state["oms_last_execution_report"] = report
            return report

        if execution_locked():
            report = {
                "timestamp": now(),
                "status": "REJECTED",
                "reason": "Execution lock active",
            }
            st.session_state["oms_last_execution_report"] = report
            return report

        scanner_plan = st.session_state.get("scanner_last_risk_plan", [])

        if not scanner_plan:
            report = {
                "timestamp": now(),
                "status": "REJECTED",
                "reason": "No approved scanner plan available",
            }
            st.session_state["oms_last_execution_report"] = report
            return report

        approved = []

        for row in scanner_plan:
            if not isinstance(row, dict):
                continue

            risk_approved = bool(row.get("risk_approved", False))

            execution_action = str(
                row.get("execution_action")
                or row.get("action")
                or ""
            ).upper().strip()

            if execution_action in ("BUY", "SELL") and risk_approved:
                approved.append(row)

        if not approved:
            report = {
                "timestamp": now(),
                "status": "REJECTED",
                "reason": "Scanner plan contains no approved executable BUY/SELL rows",
            }
            st.session_state["oms_last_execution_report"] = report
            return report

        fp = execution_fingerprint(approved)
        last_fp = st.session_state.get("oms_last_execution_fingerprint", "")

        if fp and fp == last_fp:
            report = {
                "timestamp": now(),
                "status": "REJECTED_DUPLICATE_PLAN",
                "fingerprint": fp,
                "approved_signals": len(approved),
            }

            st.session_state["oms_last_execution_report"] = report
            audit_event("EXECUTION_DUPLICATE_BLOCKED", report)
            return report

        lock_execution()

        results = []

        try:
            for row in approved:
                execution_action = str(
                    row.get("execution_action")
                    or row.get("action")
                    or ""
                ).upper().strip()

                signal = {
                    "symbol": row.get("symbol"),
                    "action": execution_action,
                    "qty": row.get("qty", 1),
                    "price": row.get("price"),
                    "mode": st.session_state.get("mode", "SIM"),
                    "source": "oms_execute_scanner_plan",
                }

                result = route_signal(signal)

                if isinstance(result, dict):
                    results.append(result)
                else:
                    results.append({
                        "status": "ERROR",
                        "reason": "Invalid pipeline result",
                        "symbol": signal.get("symbol"),
                        "action": signal.get("action"),
                        "qty": signal.get("qty"),
                    })

        finally:
            unlock_execution()

        executed_count = sum(
            1 for r in results
            if isinstance(r, dict)
            and str(r.get("status", "")).upper() in (
                "COMPLETE",
                "PARTIAL",
                "EXECUTED",
            )
        )

        blocked_count = sum(
            1 for r in results
            if isinstance(r, dict)
            and str(r.get("status", "")).upper() == "BLOCKED"
        )

        failed_count = sum(
            1 for r in results
            if isinstance(r, dict)
            and str(r.get("status", "")).upper() in (
                "ERROR",
                "REJECTED",
                "TIMEOUT",
            )
        )

        report = {
            "timestamp": now(),
            "status": f"EXECUTED_{executed_count}_BLOCKED_{blocked_count}_FAILED_{failed_count}",
            "fingerprint": fp,
            "approved_signals": len(approved),
            "executed": executed_count,
            "blocked": blocked_count,
            "failed": failed_count,
            "results": results,
        }

        st.session_state["oms_last_execution_report"] = report
        st.session_state["oms_last_execution_fingerprint"] = fp
        st.session_state["oms_last_execution_ts"] = time.time()
        st.session_state["oms_execution_history"] = (
            [report] + st.session_state.get("oms_execution_history", [])
        )[:50]

        audit_event("EXECUTION_PLAN_EXECUTED", report)

        full_truth_sync()

        return report

    # =====================================================
    # EXECUTE APPROVED SIGNALS
    # =====================================================

    st.markdown("### 🎯 Execution")

    confirm_execute = st.checkbox("Confirm execution of approved signals")

    execute_clicked = st.button(
        "Execute Approved Signals Only",
        use_container_width=True,
    )

    if execute_clicked:
        if not confirm_execute:
            st.warning("Execution requires confirmation.")
        else:
            report = execute_scanner_plan()

            status = str(report.get("status", "UNKNOWN"))

            if status.startswith("EXECUTED_"):
                executed = report.get("executed", 0)
                blocked = report.get("blocked", 0)
                failed = report.get("failed", 0)

                if blocked and not executed and not failed:
                    st.warning(
                        f"Pipeline blocked all approved signals: {status}"
                    )
                elif failed:
                    st.error(
                        f"Execution completed with failures: {status}"
                    )
                else:
                    st.success(
                        f"Execution completed: {status}"
                    )

            elif status == "REJECTED_DUPLICATE_PLAN":
                st.warning(
                    "Duplicate execution blocked: same approved scanner plan already executed."
                )

            else:
                st.warning(report.get("reason", status))

            st.rerun()

    # =====================================================
    # OBSERVABILITY
    # =====================================================

    st.markdown("### 📊 OMS Diagnostics")

    last_exec = st.session_state.get("oms_last_execution_report", {})

    if last_exec:
        st.json(last_exec)

    # =====================================================
    # OMS ORDER BLOTTER (FIXED)
    # =====================================================

    st.markdown("### 📋 OMS Order Blotter")

    blotter_rows = []

    refresh_refs()

    if oms:
        for attr in (
            "orders",
            "completed_orders",
            "working_orders",
            "rejected_orders",
        ):
            if hasattr(oms, attr):
                try:
                    rows = getattr(oms, attr)

                    if isinstance(rows, list):
                        blotter_rows.extend(rows)

                    elif isinstance(rows, dict):
                        blotter_rows.extend(rows.values())

                except Exception:
                    pass

        if hasattr(oms, "orders_snapshot"):
            try:
                rows = oms.orders_snapshot()
                if isinstance(rows, list):
                    blotter_rows.extend(rows)
                elif isinstance(rows, dict):
                    blotter_rows.extend(rows.values())
            except Exception:
                pass

    if not blotter_rows:
        blotter_rows = get_pipeline_results()

    if not blotter_rows:
        blotter_rows = get_fills()

    if blotter_rows:
        cleaned_rows = [
            row for row in blotter_rows
            if isinstance(row, dict)
        ]

        df = pd.DataFrame(cleaned_rows)

        preferred_cols = [
            "timestamp",
            "symbol",
            "action",
            "side",
            "execution_action",
            "qty",
            "price",
            "fill_price",
            "avg_fill_price",
            "status",
            "execution_status",
            "order_status",
            "reason",
            "risk_approved",
            "position_action",
            "position_before",
            "position_after_expected",
            "lifecycle_stage",
            "realized_delta",
            "realized_pnl",
            "mode",
            "order_id",
            "fill_id",
            "execution_id",
            "exec_id",
            "broker_order_id",
            "source",
            "emergency_flatten",
        ]

        visible_cols = [
            col for col in preferred_cols
            if col in df.columns
        ]

        if visible_cols:
            df = df[visible_cols]

        st.dataframe(df, use_container_width=True)

    else:
        st.info("No OMS blotter entries yet.")

    # =====================================================
    # PORTFOLIO
    # =====================================================

    positions = get_positions()

    st.markdown("### 📦 Portfolio Snapshot")

    if positions:
        st.dataframe(
            pd.DataFrame.from_dict(
                positions,
                orient="index",
            ),
            use_container_width=True,
        )
    else:
        st.info("No active positions.")

    # =====================================================
    # FILLS
    # =====================================================

    fills = get_fills()

    st.markdown("### 🧾 Runtime Fills")

    if fills:
        st.dataframe(
            pd.DataFrame(fills),
            use_container_width=True,
        )
    else:
        st.info("No runtime fills.")

    # =====================================================
    # AUDIT
    # =====================================================

    audit_events = get_audit_events(limit=200)

    st.markdown("### 🏛 Audit Trail")

    if audit_events:
        st.dataframe(
            pd.DataFrame(audit_events),
            use_container_width=True,
        )
    else:
        st.info("No audit events.")

    # =====================================================
    # RISK SNAPSHOT
    # =====================================================

    st.markdown("### 🔍 Risk Snapshot")

    risk_snap = safe_snapshot(risk_engine)

    if risk_snap and isinstance(risk_snap, dict):

        excluded = {
            "positions",
            "last_prices",
            "last_check",
        }

        rows = []

        for k, v in risk_snap.items():
            if k in excluded:
                continue

            rows.append(
                {
                    "Metric": str(k),
                    "Value": str(v),
                }
            )

        if rows:
            risk_df = pd.DataFrame(rows)

            risk_df["Metric"] = risk_df["Metric"].astype(str)
            risk_df["Value"] = risk_df["Value"].astype(str)

            st.dataframe(
                risk_df,
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("No risk snapshot available.")

    else:
        st.info("No risk snapshot available.")