# =========================================================
# 🚦 JFBP EXECUTION PIPELINE v35.8
# INSTITUTIONAL EXECUTION RETURN TRUTH LAYER
# =========================================================

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import uuid
import time

try:
    import streamlit as st
except Exception:
    st = None


class TradingPipeline:

    VALID_MODES = {"SIM", "LIVE", "BACKTEST", "REPLAY"}

    EXECUTION_STATES = {
        "INIT",
        "ORDER_CREATED",
        "PREFLIGHT_OK",
        "RISK_APPROVED",
        "ORDER_ROUTED",
        "BROKER_ACK",
        "PARTIAL_FILLED",
        "ORDER_FILLED",
        "PORTFOLIO_SYNCED",
        "COMPLETE",
        "PARTIAL",
        "REJECTED",
        "TIMEOUT",
        "BLOCKED",
        "ERROR",
    }

    TERMINAL_STATUSES = {
        "COMPLETE",
        "PARTIAL",
        "REJECTED",
        "TIMEOUT",
        "BLOCKED",
        "ERROR",
    }

    OMS_TIMEOUT_SECONDS = 10
    MAX_CONSECUTIVE_FAILURES = 5
    PROCESSED_SIGNAL_TTL_SECONDS = 3600
    MAX_PROCESSED_SIGNAL_IDS = 2000

    def __init__(
        self,
        gateway=None,
        market=None,
        market_data=None,
        oms=None,
        risk_engine=None,
        risk=None,
        audit_store=None,
        audit=None,
        portfolio_engine=None,
        portfolio=None,
        mode: str = "SIM",
        **kwargs,
    ):
        self.gateway = gateway
        self.market = market or market_data
        self.market_data = self.market
        self.oms = oms

        self.risk_engine = risk_engine or risk
        self.risk = self.risk_engine

        self.audit_store = audit_store or audit
        self.audit = self.audit_store

        self.portfolio_engine = portfolio_engine or portfolio
        self.portfolio = self.portfolio_engine

        self.mode = self._normalize_mode(mode)

        self.last_result: Optional[Dict[str, Any]] = None
        self.results: List[Dict[str, Any]] = []
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.last_error = ""

        self.processed_signal_ids: Dict[str, float] = {}
        self.consecutive_failures = 0
        self.audit_snapshots: List[Dict[str, Any]] = []

    # =====================================================
    # RUNTIME REFRESH
    # =====================================================

    def _refresh_runtime_refs(self) -> None:
        if st is None:
            return

        try:
            self.gateway = st.session_state.get("gateway", self.gateway)

            self.market = (
                st.session_state.get("market", None)
                or st.session_state.get("market_data", None)
                or self.market
            )
            self.market_data = self.market

            self.oms = st.session_state.get("oms", self.oms)

            self.risk_engine = (
                st.session_state.get("risk_engine", None)
                or st.session_state.get("risk", None)
                or self.risk_engine
            )
            self.risk = self.risk_engine

            self.audit_store = (
                st.session_state.get("audit_store", None)
                or st.session_state.get("audit", None)
                or self.audit_store
            )
            self.audit = self.audit_store

            self.portfolio_engine = (
                st.session_state.get("portfolio_engine", None)
                or st.session_state.get("portfolio", None)
                or self.portfolio_engine
            )
            self.portfolio = self.portfolio_engine

        except Exception:
            pass

    # =====================================================
    # CONFIG
    # =====================================================

    def set_mode(self, mode: str) -> None:
        self.mode = self._normalize_mode(mode)

        for obj in (self.gateway, self.oms, self.risk_engine):
            if obj is not None and hasattr(obj, "set_mode"):
                try:
                    obj.set_mode(self.mode)
                except Exception:
                    pass

    def attach(
        self,
        gateway=None,
        market=None,
        market_data=None,
        oms=None,
        risk_engine=None,
        risk=None,
        audit_store=None,
        audit=None,
        portfolio_engine=None,
        portfolio=None,
    ) -> None:

        if gateway is not None:
            self.gateway = gateway

        if market is not None or market_data is not None:
            self.market = market or market_data
            self.market_data = self.market

        if oms is not None:
            self.oms = oms

        if risk_engine is not None or risk is not None:
            self.risk_engine = risk_engine or risk
            self.risk = self.risk_engine

        if audit_store is not None or audit is not None:
            self.audit_store = audit_store or audit
            self.audit = self.audit_store

        if portfolio_engine is not None or portfolio is not None:
            self.portfolio_engine = portfolio_engine or portfolio
            self.portfolio = self.portfolio_engine

    # =====================================================
    # HELPERS
    # =====================================================

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _new_id(self, prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4().hex[:10]}"

    def _safe_float(self, value: Any) -> float:
        try:
            if value is None:
                return 0.0
            return float(value)
        except Exception:
            return 0.0

    def _normalize_mode(self, value: Any) -> str:
        mode = str(value or "SIM").upper().strip()
        return mode if mode in self.VALID_MODES else "SIM"
    
    def _kill_switch_active(self) -> bool:
        if st is None:
            return False

        try:
            return bool(st.session_state.get("risk_kill_switch", False))
        except Exception:
            return False

    def _live_trading_armed(self) -> bool:
        if st is None:
            return False

        try:
            return bool(st.session_state.get("live_trading_armed", False))
        except Exception:
            return False

    # =====================================================
    # SIGNAL NORMALIZATION
    # =====================================================

    def _normalize_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:

        if not isinstance(signal, dict):
            signal = {}

        symbol = str(
            signal.get("symbol")
            or signal.get("ticker")
            or signal.get("data_symbol")
            or ""
        ).upper().strip()

        action = str(
            signal.get("action")
            or signal.get("side")
            or ""
        ).upper().strip()

        action_map = {
            "LONG": "BUY",
            "BUY_LONG": "BUY",
            "ENTER_LONG": "BUY",
            "SHORT": "SELL",
            "SELL_SHORT": "SELL",
            "ENTER_SHORT": "SELL",
        }

        action = action_map.get(action, action)

        qty = abs(self._safe_float(
            signal.get("qty")
            or signal.get("quantity")
            or signal.get("shares")
            or 0
        ))

        price = self._safe_float(
            signal.get("price")
            or signal.get("fill_price")
            or signal.get("last_price")
        )

        return {
            **signal,
            "symbol": symbol,
            "action": action,
            "side": action,
            "qty": qty,
            "price": price,
            "mode": self._normalize_mode(
                signal.get("mode", self.mode)
            ),
        }

    # =====================================================
    # BASE RESULT
    # =====================================================

    def _base_result(
        self,
        signal: Dict[str, Any],
        signal_id: str,
        order_id: str,
        pipeline_id: str,
    ) -> Dict[str, Any]:

        return {
            "timestamp": self._now(),
            "updated_at": self._now(),
            "signal_id": signal_id,
            "order_id": order_id,
            "pipeline_id": pipeline_id,
            "batch_id": signal.get("batch_id"),
            "symbol": signal.get("symbol"),
            "action": signal.get("action"),
            "qty": signal.get("qty"),
            "price": signal.get("price"),
            "status": "INIT",
            "execution_status": "INIT",
            "order_status": "INIT",
            "stage": "INIT",
            "reason": "",
            "risk_approved": False,
            "has_fill": False,
            "partial_fill": False,
            "source": signal.get("source"),
            "mode": signal.get("mode"),
        }

    def _record_order_state(
        self,
        order_id: str,
        result: Dict[str, Any],
        state: str,
    ) -> None:

        self.orders[order_id] = {
            **result,
            "state": state,
        }

    # =====================================================
    # FAILURE CONTROL
    # =====================================================

    def _trip_failure(self) -> None:
        self.consecutive_failures += 1

    def _reset_failures(self) -> None:
        self.consecutive_failures = 0

    def _purge_processed_signal_ids(self) -> None:

        now_ts = time.time()
        cutoff = now_ts - self.PROCESSED_SIGNAL_TTL_SECONDS

        stale = [
            sig_id
            for sig_id, ts in self.processed_signal_ids.items()
            if ts < cutoff
        ]

        for sig_id in stale:
            self.processed_signal_ids.pop(sig_id, None)

        if len(self.processed_signal_ids) > self.MAX_PROCESSED_SIGNAL_IDS:
            ordered = sorted(
                self.processed_signal_ids.items(),
                key=lambda x: x[1]
            )

            excess = len(self.processed_signal_ids) - self.MAX_PROCESSED_SIGNAL_IDS

            for sig_id, _ in ordered[:excess]:
                self.processed_signal_ids.pop(sig_id, None)

    # =====================================================
    # EXECUTION ENTRYPOINT
    # =====================================================

    def execute(self, signal: Dict[str, Any]) -> Dict[str, Any]:

        exec_start = time.time()

        self._refresh_runtime_refs()
        self._purge_processed_signal_ids()

        signal = self._normalize_signal(signal)
        signal = self._reconcile_signal_with_position(signal)

        signal_id = signal.get("signal_id") or self._new_id("SIG")
        order_id = signal.get("order_id") or self._new_id("ORD")
        pipeline_id = signal.get("pipeline_id") or self._new_id("PIPE")

        signal["signal_id"] = signal_id
        signal["order_id"] = order_id
        signal["pipeline_id"] = pipeline_id

        if signal_id in self.processed_signal_ids:
            return self._finalize({
                "timestamp": self._now(),
                "updated_at": self._now(),
                "status": "BLOCKED",
                "execution_status": "BLOCKED",
                "order_status": "BLOCKED",
                "stage": "IDEMPOTENCY",
                "reason": "Duplicate signal blocked",
                "signal_id": signal_id,
                "order_id": order_id,
                "pipeline_id": pipeline_id,
                "symbol": signal.get("symbol"),
                "action": signal.get("action"),
                "qty": signal.get("qty"),
                "price": signal.get("price"),
            })

        self.processed_signal_ids[signal_id] = time.time()

        result = self._base_result(
            signal,
            signal_id,
            order_id,
            pipeline_id,
        )

        self._transition(result, "ORDER_CREATED")
        self._record_order_state(order_id, result, "ORDER_CREATED")

        emergency_exit = bool(
            signal.get("emergency_flatten")
            or signal.get("flatten_generated")
            or signal.get("force_position_context")
            or signal.get("close_or_flatten_context")
            or str(signal.get("execution_type", "")).upper() == "EMERGENCY"
        )

        if self._kill_switch_active() and not emergency_exit:
            result.update({
                "status": "BLOCKED",
                "execution_status": "BLOCKED",
                "order_status": "BLOCKED",
                "stage": "BLOCKED",
                "reason": "PIPELINE_KILL_SWITCH_ACTIVE",
                "risk_approved": False,
                "has_fill": False,
                "partial_fill": False,
                "total_execution_ms": round(
                    (time.time() - exec_start) * 1000,
                    2,
                ),
            })
            self._transition(result, "BLOCKED")
            return self._finalize(result)

        if self._kill_switch_active() and emergency_exit:
            result.update({
                "kill_switch_bypassed_for_exit": True,
                "emergency_exit": True,
                "reason": "Emergency exit allowed while kill switch active",
            })

        preflight_start = time.time()
        ok, reason = self._preflight(signal)

        result["preflight_ms"] = round(
            (time.time() - preflight_start) * 1000,
            2,
        )

        if not ok:
            result.update({
                "status": "REJECTED",
                "reason": reason,
            })
            self._transition(result, "REJECTED")
            return self._finalize(result)

        self._transition(result, "PREFLIGHT_OK")

        if not self._position_truth_check(signal):
            result.update({
                "status": "BLOCKED",
                "reason": "Position drift detected",
            })
            self._transition(result, "BLOCKED")
            return self._finalize(result)

        risk_start = time.time()
        ok, reason = self._risk_check(signal)

        result["risk_check_ms"] = round(
            (time.time() - risk_start) * 1000,
            2,
        )

        if not ok:
            result.update({
                "status": "REJECTED",
                "reason": reason,
                "risk_approved": False,
            })
            self._transition(result, "REJECTED")
            return self._finalize(result)

        result["risk_approved"] = True
        self._transition(result, "RISK_APPROVED")

        oms_start = time.time()
        raw_oms_result = self._route_to_oms_with_timeout(signal)

        result["oms_route_ms"] = round(
            (time.time() - oms_start) * 1000,
            2,
        )

        oms_status = self._extract_status(raw_oms_result)

        if raw_oms_result is None:
            result.update({
                "status": "TIMEOUT",
                "reason": self.last_error or "OMS timeout",
                "has_fill": False,
            })
            self._transition(result, "TIMEOUT")
            return self._finalize(result)

        if oms_status in ("REJECTED", "BLOCKED", "ERROR", "TIMEOUT"):
            reason = "OMS rejected order"

            if isinstance(raw_oms_result, dict):
                reason = (
                    raw_oms_result.get("reason")
                    or raw_oms_result.get("message")
                    or reason
                )

            result.update({
                "status": oms_status,
                "reason": reason,
                "has_fill": False,
                "raw_oms_result": raw_oms_result,
            })
            self._transition(result, oms_status)
            return self._finalize(result)

        self._transition(result, "BROKER_ACK")

        fill = self._normalize_fill(raw_oms_result, signal)

        if not fill:
            result.update({
                "status": "ERROR",
                "reason": "OMS returned unusable fill payload",
                "has_fill": False,
                "raw_oms_result": raw_oms_result,
            })
            self._transition(result, "ERROR")
            return self._finalize(result)

        is_partial = bool(fill.get("partial_fill"))

        if is_partial:
            self._transition(result, "PARTIAL_FILLED")

        sync_start = time.time()
        lifecycle_event = self._sync_portfolio(fill)

        result["portfolio_sync_ms"] = round(
            (time.time() - sync_start) * 1000,
            2,
        )

        self._record_risk_trade(signal, fill, lifecycle_event)

        terminal_status = "PARTIAL" if is_partial else "COMPLETE"

        if is_partial:
            self._transition(result, "PARTIAL")
        else:
            self._transition(result, "ORDER_FILLED")
            self._transition(result, "PORTFOLIO_SYNCED")
            self._transition(result, "COMPLETE")

        result.update({
            "status": terminal_status,
            "execution_status": terminal_status,
            "order_status": terminal_status,
            "stage": terminal_status,
            "reason": "Partial fill" if is_partial else "Execution complete",
            "fill": fill,
            "fill_id": fill.get("fill_id"),
            "broker_order_id": fill.get("broker_order_id"),
            "fill_price": fill.get("fill_price"),
            "has_fill": True,
            "partial_fill": is_partial,
            "lifecycle_stage": lifecycle_event.get("lifecycle_stage"),
            "realized_delta": lifecycle_event.get("realized_delta"),
            "realized_pnl": lifecycle_event.get("realized_pnl"),
            "old_qty": lifecycle_event.get("old_qty"),
            "new_qty": lifecycle_event.get("new_qty"),
            "old_side": lifecycle_event.get("old_side"),
            "new_side": lifecycle_event.get("new_side"),
            "total_execution_ms": round(
                (time.time() - exec_start) * 1000,
                2,
            ),
        })

        self._reset_failures()
        return self._finalize(result)

        # =====================================================
    # BATCH EXECUTION
    # =====================================================

    def execute_batch(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:

        self._refresh_runtime_refs()

        if not isinstance(signals, list):
            return []

        batch_id = self._new_id("BATCH")
        results = []

        for signal in signals:

            if isinstance(signal, dict):
                signal["batch_id"] = batch_id

            if self._kill_switch_active():
                blocked = {
                    "timestamp": self._now(),
                    "updated_at": self._now(),
                    "status": "BLOCKED",
                    "execution_status": "BLOCKED",
                    "order_status": "BLOCKED",
                    "stage": "BLOCKED",
                    "reason": "PIPELINE_KILL_SWITCH_ACTIVE",
                    "batch_id": batch_id,
                    "signal_id": signal.get("signal_id") if isinstance(signal, dict) else None,
                    "order_id": signal.get("order_id") if isinstance(signal, dict) else None,
                    "pipeline_id": signal.get("pipeline_id") if isinstance(signal, dict) else None,
                    "symbol": signal.get("symbol") if isinstance(signal, dict) else None,
                    "action": signal.get("action") if isinstance(signal, dict) else None,
                    "qty": signal.get("qty") if isinstance(signal, dict) else None,
                    "price": signal.get("price") if isinstance(signal, dict) else None,
                    "risk_approved": False,
                    "has_fill": False,
                    "partial_fill": False,
                    "source": signal.get("source") if isinstance(signal, dict) else None,
                    "mode": signal.get("mode", self.mode) if isinstance(signal, dict) else self.mode,
                }

                results.append(self._finalize(blocked))
                continue

            results.append(self.execute(signal))

        return results

    route = execute
    run = execute
    process_signal = execute
    process = execute
    execute_signal = execute

    # =====================================================
    # PREFLIGHT
    # =====================================================

    def _preflight(
        self,
        signal: Dict[str, Any],
    ) -> tuple:

        if self.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
            return False, "Pipeline failure lockout"

        if self.mode == "LIVE" and not self._live_trading_armed():
            return False, "LIVE trading not armed"

        if not signal.get("symbol"):
            return False, "Missing symbol"

        if signal.get("action") not in ("BUY", "SELL"):
            return False, "Invalid action"

        if self._safe_float(signal.get("qty")) <= 0:
            return False, "Invalid quantity"

        return True, "OK"

    # =====================================================
    # POSITION TRUTH
    # =====================================================

    def _position_truth_check(
        self,
        signal: Dict[str, Any],
    ) -> bool:

        self._refresh_runtime_refs()

        if self.portfolio_engine is None:
            return True

        if hasattr(self.portfolio_engine, "reconcile_positions"):
            try:
                self.portfolio_engine.reconcile_positions()
            except Exception:
                pass

        return True


    def _reconcile_signal_with_position(
        self,
        signal: Dict[str, Any],
    ) -> Dict[str, Any]:

        if self.portfolio_engine is None:
            return signal

        if not hasattr(self.portfolio_engine, "get_position"):
            return signal

        try:
            pos = self.portfolio_engine.get_position(signal.get("symbol"))
        except Exception:
            return signal

        if not pos:
            return signal

        signal["existing_position"] = pos
        return signal

    # =====================================================
    # RISK
    # =====================================================

    def _risk_check(self, signal: Dict[str, Any]) -> tuple:

        emergency_exit = bool(
            signal.get("emergency_flatten")
            or signal.get("flatten_generated")
            or signal.get("force_position_context")
            or signal.get("close_or_flatten_context")
            or str(signal.get("execution_type", "")).upper() == "EMERGENCY"
        )

        if emergency_exit:
            return True, "OK_EMERGENCY_EXIT_REDUCES_RISK"

        if self.risk_engine is None:
            return True, "OK_NO_RISK_ENGINE"

        try:
            if (
                self.portfolio_engine is not None
                and hasattr(self.portfolio_engine, "risk_positions")
                and hasattr(self.risk_engine, "sync_positions")
            ):
                self.risk_engine.sync_positions(
                    self.portfolio_engine.risk_positions()
                )
        except Exception:
            pass

        for method_name in (
            "check",
            "check_order",
            "validate",
            "approve",
        ):
            if not hasattr(self.risk_engine, method_name):
                continue

            try:
                result = getattr(self.risk_engine, method_name)(signal)
                return self._normalize_risk_result(result)

            except Exception as exc:
                return False, str(exc)

        return True, "OK"


    def _normalize_risk_result(self, result: Any) -> tuple:

        if isinstance(result, tuple) and len(result) >= 2:
            return bool(result[0]), str(result[1])

        if isinstance(result, bool):
            return result, "OK" if result else "Risk rejected"

        if isinstance(result, dict):
            approved = bool(
                result.get("approved")
                or result.get("ok")
                or result.get("allowed")
                or result.get("risk_approved")
            )

            reason = str(
                result.get("reason")
                or result.get("message")
                or ("OK" if approved else "Risk rejected")
            )

            return approved, reason

        if result is None:
            return False, "Risk returned no result"

        return bool(result), "OK" if bool(result) else "Risk rejected"


    def _record_risk_trade(
        self,
        signal: Dict[str, Any],
        fill: Dict[str, Any],
        lifecycle_event: Optional[Dict[str, Any]] = None,
    ) -> None:

        if self.risk_engine is None:
            return

        try:
            if hasattr(self.risk_engine, "record_trade"):
                self.risk_engine.record_trade(signal)

            pnl = None

            if isinstance(lifecycle_event, dict):
                pnl = lifecycle_event.get("realized_delta")
                if pnl is None:
                    pnl = lifecycle_event.get("realized_pnl")

            if pnl is None:
                pnl = fill.get("realized_delta")

            if pnl is None:
                pnl = fill.get("realized_pnl")

            if pnl is not None and hasattr(
                self.risk_engine,
                "record_pnl"
            ):
                self.risk_engine.record_pnl(pnl)

        except Exception:
            pass

        # =====================================================
    # OMS ROUTING
    # =====================================================

    def _route_to_oms_with_timeout(
        self,
        signal: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:

        if self.oms is None:
            self.last_error = "OMS unavailable"
            return None

        start = time.time()

        for method_name in (
            "execute_signal",
            "execute",
            "route",
            "process_signal",
            "process",
        ):
            if not hasattr(self.oms, method_name):
                continue

            try:
                result = getattr(self.oms, method_name)(signal)

                elapsed = time.time() - start

                if elapsed > self.OMS_TIMEOUT_SECONDS:
                    self.last_error = "OMS timeout exceeded"
                    return None

                return result

            except Exception as exc:
                self.last_error = str(exc)
                return {
                    "status": "ERROR",
                    "reason": str(exc),
                    "symbol": signal.get("symbol"),
                    "action": signal.get("action"),
                    "qty": signal.get("qty"),
                    "price": signal.get("price"),
                    "order_id": signal.get("order_id"),
                    "pipeline_id": signal.get("pipeline_id"),
                    "signal_id": signal.get("signal_id"),
                }

        self.last_error = "OMS execution method unavailable"

        return {
            "status": "ERROR",
            "reason": "OMS execution method unavailable",
            "symbol": signal.get("symbol"),
            "action": signal.get("action"),
            "qty": signal.get("qty"),
            "price": signal.get("price"),
            "order_id": signal.get("order_id"),
            "pipeline_id": signal.get("pipeline_id"),
            "signal_id": signal.get("signal_id"),
        }


    def _extract_status(self, payload: Any) -> str:

        if payload is None:
            return "TIMEOUT"

        if not isinstance(payload, dict):
            return "ERROR"

        raw_status = str(
            payload.get("status")
            or payload.get("execution_status")
            or payload.get("order_status")
            or ""
        ).upper().strip()

        status_map = {
            "FILLED": "COMPLETE",
            "ORDER_FILLED": "COMPLETE",
            "COMPLETE": "COMPLETE",
            "DONE": "COMPLETE",
            "SUCCESS": "COMPLETE",
            "PARTIAL_FILLED": "PARTIAL",
            "PARTIALLY_FILLED": "PARTIAL",
            "PARTIAL": "PARTIAL",
            "REJECTED": "REJECTED",
            "BLOCKED": "BLOCKED",
            "TIMEOUT": "TIMEOUT",
            "ERROR": "ERROR",
        }

        return status_map.get(raw_status, raw_status or "COMPLETE")


    def _normalize_fill(
        self,
        fill: Dict[str, Any],
        signal: Dict[str, Any],
    ) -> Dict[str, Any]:

        if not isinstance(fill, dict):
            return {}

        status = self._extract_status(fill)

        if status in ("REJECTED", "BLOCKED", "ERROR", "TIMEOUT"):
            return {}

        order_id = (
            fill.get("order_id")
            or signal.get("order_id")
            or self._new_id("ORD")
        )

        broker_order_id = (
            fill.get("broker_order_id")
            or fill.get("ib_order_id")
            or fill.get("perm_id")
            or fill.get("broker_id")
        )

        fill_id = (
            fill.get("fill_id")
            or fill.get("execution_id")
            or fill.get("exec_id")
            or fill.get("id")
            or self._new_id("FILL")
        )

        fill_price = self._safe_float(
            fill.get("fill_price")
            or fill.get("avg_fill_price")
            or fill.get("average_price")
            or fill.get("price")
            or signal.get("price")
        )

        fill_qty = abs(self._safe_float(
            fill.get("qty")
            or fill.get("filled_qty")
            or fill.get("quantity")
            or signal.get("qty")
        ))

        remaining_qty = abs(self._safe_float(
            fill.get("remaining_qty")
            or max(
                0.0,
                self._safe_float(signal.get("qty")) - fill_qty
            )
        ))

        partial_fill = bool(
            fill.get("partial_fill")
            or status == "PARTIAL"
            or remaining_qty > 0
        )

        return {
            **fill,
            "signal_id": signal.get("signal_id"),
            "pipeline_id": signal.get("pipeline_id"),
            "batch_id": signal.get("batch_id"),
            "symbol": fill.get("symbol") or signal.get("symbol"),
            "data_symbol": fill.get("data_symbol") or signal.get("data_symbol"),
            "action": signal.get("action"),
            "side": signal.get("action"),
            "qty": fill_qty,
            "filled_qty": fill_qty,
            "remaining_qty": remaining_qty,
            "price": fill_price,
            "fill_price": fill_price,
            "avg_fill_price": fill.get("avg_fill_price") or fill_price,
            "mode": fill.get("mode") or signal.get("mode") or self.mode,
            "source": fill.get("source") or signal.get("source"),
            "order_id": order_id,
            "broker_order_id": broker_order_id,
            "fill_id": fill_id,
            "position_action": signal.get("position_action"),
            "partial_fill": partial_fill,
            "status": "PARTIAL" if partial_fill else "COMPLETE",
        }

       # =====================================================
    # PORTFOLIO SYNC
    # =====================================================

    def _sync_portfolio(
        self,
        fill: Dict[str, Any],
    ) -> Dict[str, Any]:

        self._refresh_runtime_refs()

        if self.portfolio_engine is None:
            self.last_error = "Portfolio sync failed: portfolio_engine unavailable"
            return {
                "status": "ERROR",
                "reason": self.last_error,
            }

        sync_fill = dict(fill or {})

        for method_name in (
            "apply_fill",
            "process_fill",
            "record_fill",
            "update_from_fill",
        ):
            if not hasattr(self.portfolio_engine, method_name):
                continue

            try:
                event = getattr(
                    self.portfolio_engine,
                    method_name,
                )(sync_fill)

                if isinstance(event, dict):
                    status = str(event.get("status", "")).upper().strip()

                    if status in ("COMPLETE", "PARTIAL", "SKIPPED"):
                        self.last_error = ""
                        return event

                    self.last_error = (
                        event.get("reason")
                        or f"Portfolio sync returned {status or 'UNKNOWN'}"
                    )
                    return event

                self.last_error = (
                    f"Portfolio sync method {method_name} returned non-dict result"
                )
                return {
                    "status": "ERROR",
                    "reason": self.last_error,
                }

            except Exception as exc:
                self.last_error = f"Portfolio sync failed via {method_name}: {exc}"
                continue

        return {
            "status": "ERROR",
            "reason": "No portfolio sync method available",
        }

    # =====================================================
    # FINALIZATION
    # =====================================================

    def _transition(
        self,
        result: Dict[str, Any],
        state: str,
    ) -> None:

        result["stage"] = state
        result["execution_status"] = state
        result["updated_at"] = self._now()

    def _finalize(
        self,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:

        self.last_result = result
        self.results.append(result)
        self.results = self.results[-500:]

        if result.get("status") in ("COMPLETE", "PARTIAL"):
            self._reset_failures()
            self.last_error = ""
        else:
            self._trip_failure()
            self.last_error = result.get("reason", "")

        self._audit_result(result)

        return result

    def _audit_result(
        self,
        result: Dict[str, Any],
    ) -> None:

        if self.audit_store is None:
            return

        try:
            if hasattr(self.audit_store, "record_pipeline_result"):
                self.audit_store.record_pipeline_result(result)

            elif hasattr(self.audit_store, "record_event"):
                self.audit_store.record_event("PIPELINE_RESULT", result)

        except Exception:
            pass

    # =====================================================
    # ACCESSORS
    # =====================================================

    def snapshot(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "consecutive_failures": self.consecutive_failures,
            "orders_tracked": len(self.orders),
            "results_tracked": len(self.results),
            "last_error": self.last_error,
        }

    def clear_runtime(self) -> None:
        self.last_result = None
        self.results = []
        self.orders = {}
        self.last_error = ""
        self.processed_signal_ids = {}
        self.consecutive_failures = 0
        self.audit_snapshots = []                                              