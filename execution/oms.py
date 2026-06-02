# =========================================================
# ⚡ JFBP OMS ENGINE v21.2
# INSTITUTIONAL EXECUTION SAFETY HARDENED
#
# v21.2 upgrades:
#   - REMOVED fake 100.00 fallback price
#   - no synthetic execution price in SIM / REPLAY / BACKTEST
#   - missing price now rejects execution safely
#   - prevents audit DB contamination
# =========================================================

from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import List, Dict, Optional, Any, Tuple


try:
    import streamlit as st
except Exception:
    st = None


from audit.store import AuditStore


class OMS:

    VALID_MODES = {"SIM", "LIVE", "BACKTEST", "REPLAY"}
    EXECUTABLE_ACTIONS = {"BUY", "SELL"}
    NON_EXECUTABLE_ACTIONS = {"HOLD", "NO TRADE", "NONE", "FLAT", ""}

    def __init__(
        self,
        gateway=None,
        portfolio_engine=None,
        audit_store=None,
        mode: str = "SIM",
    ):

        self.gateway = gateway
        self.portfolio_engine = portfolio_engine
        self.audit_store = audit_store or AuditStore()

        self.mode = self._normalize_mode(mode)

        self.fills: List[Dict[str, Any]] = []
        self.last_fill: Optional[Dict[str, Any]] = None
        self.last_error: str = ""
        self.last_audit_error: str = ""
        self.last_rejection: Optional[Dict[str, Any]] = None

        self.orders: Dict[str, Dict[str, Any]] = {}
        self.working_orders: Dict[str, Dict[str, Any]] = {}
        self.completed_orders: Dict[str, Dict[str, Any]] = {}
        self.rejected_orders: Dict[str, Dict[str, Any]] = {}

        self.execution_registry: Dict[str, Dict[str, Any]] = {}
        self.fill_identity_registry: Dict[str, Dict[str, Any]] = {}

        self.broker_order_registry: Dict[str, str] = {}

        self.last_order: Optional[Dict[str, Any]] = None

        self.pending_timeout_seconds = 120

        self.sim_slippage_bps = 5
        self.sim_latency_seconds = 0.0

        self.enable_sim_partial_fills = False
        self.partial_fill_ratio = 0.5

        self.TRUTH_SOURCE = "OMS_RUNTIME"

    # =====================================================
    # CONFIG
    # =====================================================

    def set_mode(self, mode: str) -> None:
        self.mode = self._normalize_mode(mode)

        if self.gateway is not None and hasattr(self.gateway, "set_mode"):
            try:
                self.gateway.set_mode(self.mode)
            except Exception as exc:
                self.last_error = f"Gateway mode propagation failed: {exc}"

    def attach_gateway(self, gateway) -> None:
        self.gateway = gateway

    def attach_portfolio_engine(self, portfolio_engine) -> None:
        self.portfolio_engine = portfolio_engine

    def attach_audit_store(self, audit_store) -> None:
        self.audit_store = audit_store

    # =====================================================
    # CORE EXECUTION
    # =====================================================

    def execute_signal(self, signal: dict) -> Optional[dict]:

        gate_ok, rejection = self._execution_gate(signal)

        if not gate_ok:
            self.last_rejection = rejection
            self.last_error = rejection.get("reason", "OMS execution blocked")
            return None

        signal = dict(signal)

        symbol = self._normalize_symbol(
            signal.get("symbol")
            or signal.get("ticker")
            or signal.get("signal_symbol")
        )

        action = self._normalize_action(
            signal.get("action")
            or signal.get("side")
            or signal.get("signal_action")
        )

        qty = self._safe_int(
            signal.get("qty")
            or signal.get("quantity")
            or signal.get("shares")
            or 1
        )

        mode = self._normalize_mode(signal.get("mode", self.mode))

        try:
            price = self._resolve_execution_price(signal, symbol)

            fill = {
                "id": str(uuid.uuid4())[:8],
                "fill_id": None,
                "order_id": signal.get("order_id"),
                "symbol": symbol,
                "action": action,
                "side": action,
                "qty": qty,
                "fill_price": price,
                "price": price,
                "timestamp": self._now(),
                "source": signal.get("source", "oms"),
                "mode": mode,
                "status": "FILLED",
            }

            fill["fill_id"] = fill["id"]

            self.fills.append(fill)
            self.fills = self.fills[-1000:]

            self.last_fill = fill
            self.last_error = ""
            self.last_rejection = None

            self._apply_portfolio(fill)
            self._record_fill(fill)

            return fill

        except Exception as exc:
            self.last_error = str(exc)
            self.last_rejection = {
                "status": "REJECTED",
                "stage": "price_resolution",
                "reason": str(exc),
                "symbol": symbol,
                "action": action,
                "timestamp": self._now(),
                "mode": mode,
            }
            return None

    # =====================================================
    # OMS HELPERS
    # =====================================================

    def _normalize_symbol(self, symbol) -> str:
        return str(symbol or "").upper().strip()

    def _normalize_action(self, action) -> str:

        action = str(action or "").upper().strip()

        if action in {"BOT", "BUY", "LONG"}:
            return "BUY"

        if action in {"SLD", "SELL", "SHORT"}:
            return "SELL"

        return action

    def _normalize_mode(self, mode) -> str:

        mode = str(mode or self.mode).upper().strip()

        if mode not in self.VALID_MODES:
            return self.mode

        return mode

    def _safe_float(self, value) -> float:

        try:
            if value is None:
                return 0.0

            value = float(value)

            if value != value:
                return 0.0

            return value

        except Exception:
            return 0.0

    def _safe_int(self, value) -> int:

        try:
            if value is None:
                return 0

            return int(float(value))

        except Exception:
            return 0

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _new_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:10].upper()}"

    def _fill_identity_key(
        self,
        execution_id,
        broker_order_id,
        symbol,
        action,
        fill_qty,
        price,
        partial_sequence,
    ) -> str:

        if execution_id:
            return f"EXEC::{execution_id}"

        return (
            f"{broker_order_id}|"
            f"{symbol}|"
            f"{action}|"
            f"{fill_qty}|"
            f"{round(price, 4)}|"
            f"{partial_sequence}"
        )

    def _is_true_fill(self, fill: Dict[str, Any]) -> bool:

        if not isinstance(fill, dict):
            return False

        qty = self._safe_float(
            fill.get("filled_qty")
            or fill.get("fill_qty")
            or fill.get("qty")
        )

        price = self._safe_float(
            fill.get("fill_price")
            or fill.get("price")
        )

        action = self._normalize_action(
            fill.get("action")
            or fill.get("side")
        )

        symbol = self._normalize_symbol(
            fill.get("symbol")
        )

        return (
            bool(symbol)
            and action in {"BUY", "SELL"}
            and qty > 0
            and price > 0
        )

    # =====================================================
    # BROKER FILL INGESTION
    # =====================================================

    def ingest_broker_fill(
        self,
        broker_fill: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:

        if not isinstance(broker_fill, dict):
            self.last_error = "Broker fill must be a dict"
            return None

        broker_fill = dict(broker_fill)

        symbol = self._normalize_symbol(
            broker_fill.get("symbol")
            or broker_fill.get("ticker")
        )

        action = self._normalize_action(
            broker_fill.get("action")
            or broker_fill.get("side")
        )

        qty = self._safe_int(
            broker_fill.get("filled_qty")
            or broker_fill.get("fill_qty")
            or broker_fill.get("qty")
            or broker_fill.get("quantity")
            or broker_fill.get("shares")
        )

        price = self._safe_float(
            broker_fill.get("fill_price")
            or broker_fill.get("execution_price")
            or broker_fill.get("price")
            or broker_fill.get("avg_fill_price")
        )

        execution_id = str(
            broker_fill.get("execution_id")
            or broker_fill.get("exec_id")
            or ""
        ).strip()

        if not symbol or action not in {"BUY", "SELL"} or qty <= 0 or price <= 0:
            self.last_error = f"Invalid broker fill: {broker_fill}"
            return None

        if execution_id and execution_id in self.execution_registry:
            self.last_error = f"Duplicate execution ignored: {execution_id}"
            return None

        fill = {
            "id": execution_id or str(uuid.uuid4())[:8],
            "fill_id": execution_id or str(uuid.uuid4())[:8],
            "order_id": broker_fill.get("order_id"),
            "broker_order_id": broker_fill.get("broker_order_id"),
            "perm_id": broker_fill.get("perm_id"),
            "execution_id": execution_id,
            "exec_id": execution_id,
            "symbol": symbol,
            "action": action,
            "side": action,
            "qty": qty,
            "filled_qty": qty,
            "fill_qty": qty,
            "fill_price": price,
            "price": price,
            "execution_price": price,
            "avg_fill_price": price,
            "timestamp": broker_fill.get("timestamp", self._now()),
            "source": broker_fill.get("source", "broker_fill_ingestion"),
            "mode": self.mode,
            "status": "FILLED",
            "is_true_fill": True,
        }

        if execution_id:
            self.execution_registry[execution_id] = dict(fill)

        self.fills.append(fill)
        self.fills = self.fills[-1000:]

        self.last_fill = fill
        self.last_error = ""
        self.last_rejection = None

        self._apply_portfolio(fill)
        self._record_fill(fill)

        return fill

    def ingest_broker_order_status(
        self,
        broker_status: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:

        if not isinstance(broker_status, dict):
            return None

        return dict(broker_status)

    # =====================================================
    # BATCH
    # =====================================================

    def execute_batch(self, signals: List[dict]) -> List[dict]:

        results: List[dict] = []

        if not isinstance(signals, list):
            self.last_error = "Signals must be a list"
            return results

        for signal in signals:

            if self._kill_switch_active():
                self.last_error = "Kill switch active during OMS batch"
                break

            fill = self.execute_signal(signal)

            if fill:
                results.append(fill)

        return results

    # =====================================================
    # OMS ALIASES
    # =====================================================

    route = execute_signal
    execute = execute_signal
    process = execute_signal
    process_signal = execute_signal

    route_batch = execute_batch
    run_batch = execute_batch
    process_batch = execute_batch
    execute_signals = execute_batch

    # =====================================================
    # SAFETY GATES
    # =====================================================

    def _execution_gate(self, signal: Any) -> Tuple[bool, Dict[str, Any]]:

        if not isinstance(signal, dict):
            return False, self._rejection(
                stage="input",
                reason="Signal must be a dict",
                signal=signal,
            )

        symbol = self._normalize_symbol(
            signal.get("symbol")
            or signal.get("ticker")
            or signal.get("signal_symbol")
        )

        action = self._normalize_action(
            signal.get("action")
            or signal.get("side")
            or signal.get("signal_action")
        )

        mode = self._normalize_mode(signal.get("mode", self.mode))

        if self._kill_switch_active():
            return False, self._rejection(
                stage="safety_gate",
                reason="Kill switch active",
                signal=signal,
                symbol=symbol,
                action=action,
                mode=mode,
            )

        if mode == "LIVE" and not self._live_trading_armed():
            return False, self._rejection(
                stage="safety_gate",
                reason="LIVE mode requires live_trading_armed=True",
                signal=signal,
                symbol=symbol,
                action=action,
                mode=mode,
            )

        if not symbol:
            return False, self._rejection(
                stage="validation",
                reason="Missing symbol",
                signal=signal,
                symbol=symbol,
                action=action,
                mode=mode,
            )

        if action in self.NON_EXECUTABLE_ACTIONS:
            return False, self._rejection(
                stage="validation",
                reason=f"Non-executable action: {action or 'EMPTY'}",
                signal=signal,
                symbol=symbol,
                action=action,
                mode=mode,
            )

        if action not in self.EXECUTABLE_ACTIONS:
            return False, self._rejection(
                stage="validation",
                reason=f"Unsupported action: {action}",
                signal=signal,
                symbol=symbol,
                action=action,
                mode=mode,
            )

        qty = self._safe_int(
            signal.get("qty")
            or signal.get("quantity")
            or signal.get("shares")
            or 1
        )

        if qty <= 0:
            return False, self._rejection(
                stage="validation",
                reason=f"Invalid qty: {qty}",
                signal=signal,
                symbol=symbol,
                action=action,
                mode=mode,
            )

        return True, {}

    def _kill_switch_active(self) -> bool:

        if st is not None:
            try:
                return bool(st.session_state.get("risk_kill_switch", False))
            except Exception:
                pass

        return False

    def _live_trading_armed(self) -> bool:

        if st is not None:
            try:
                return bool(st.session_state.get("live_trading_armed", False))
            except Exception:
                pass

        return False

    # =====================================================
    # PORTFOLIO / AUDIT
    # =====================================================

    def _apply_portfolio(self, fill: Dict[str, Any]) -> None:

        if (
            self.portfolio_engine is not None
            and hasattr(self.portfolio_engine, "apply_fill")
        ):
            try:
                self.portfolio_engine.apply_fill(fill)
            except Exception as exc:
                self.last_error = f"Portfolio update failed: {exc}"

    def _record_fill(self, fill: Dict[str, Any]) -> None:

        if self.audit_store is None:
            self.last_audit_error = "No audit store available"
            return

        try:
            ok = self.audit_store.record_fill(fill)

            if ok is False:
                self.last_audit_error = (
                    getattr(self.audit_store, "last_error", "")
                    or "Audit record_fill returned False"
                )

        except Exception as exc:
            self.last_audit_error = f"Audit record_fill failed: {exc}"

    # =====================================================
    # SNAPSHOT
    # =====================================================

    def snapshot(self) -> Dict[str, Any]:

        audit_count = 0

        if self.audit_store is not None:
            try:
                audit_count = self.audit_store.count()
            except Exception:
                audit_count = 0

        return {
            "fills": len(self.fills),
            "audit_events": audit_count,
            "last_fill": self.last_fill,
            "last_error": self.last_error,
            "last_audit_error": self.last_audit_error,
            "last_rejection": self.last_rejection,
            "mode": self.mode,
        }

    def fills_snapshot(self) -> List[Dict[str, Any]]:
        return list(self.fills)

    # =====================================================
    # AUDIT HELPERS
    # =====================================================

    def audit_fills(self, limit: int = 100):

        if self.audit_store is None:
            return []

        if hasattr(self.audit_store, "fills"):
            try:
                return self.audit_store.fills(limit=limit)
            except Exception as exc:
                self.last_audit_error = f"audit_fills failed: {exc}"
                return []

        if hasattr(self.audit_store, "recent_fills"):
            try:
                return self.audit_store.recent_fills(limit=limit)
            except Exception as exc:
                self.last_audit_error = f"audit_fills failed: {exc}"
                return []

        return []

    # =====================================================
    # RESET
    # =====================================================

    def clear(self) -> None:
        self.fills = []
        self.last_fill = None
        self.last_error = ""
        self.last_audit_error = ""
        self.last_rejection = None

    reset = clear

    # =====================================================
    # PRICE RESOLUTION
    # =====================================================

    def _resolve_execution_price(
        self,
        signal: Dict[str, Any],
        symbol: str,
    ) -> float:

        for key in (
            "fill_price",
            "price",
            "last_price",
            "execution_price",
            "avg_price",
            "snapshot_price",
            "mark",
            "close",
            "limit_price",
        ):
            if key in signal:
                value = self._safe_float(signal.get(key))
                if value > 0:
                    return value

        if self.gateway is not None:

            for method_name in (
                "get_price",
                "latest_price",
                "get_last_price",
                "last_price",
                "market_price",
            ):
                if hasattr(self.gateway, method_name):
                    try:
                        value = self._safe_float(
                            getattr(self.gateway, method_name)(symbol)
                        )
                        if value > 0:
                            return value
                    except Exception:
                        pass

            if hasattr(self.gateway, "last_quotes"):
                try:
                    quote = self.gateway.last_quotes.get(symbol)

                    if isinstance(quote, dict):
                        for key in ("price", "last", "mark", "close", "bid", "ask"):
                            value = self._safe_float(quote.get(key))
                            if value > 0:
                                return value
                except Exception:
                    pass

            if hasattr(self.gateway, "last_quotes_df"):
                try:
                    df = self.gateway.last_quotes_df

                    if df is not None and not df.empty:
                        rows = df[df["symbol"].astype(str).str.upper() == symbol]

                        if not rows.empty:
                            for key in ("price", "last", "mark", "close", "bid", "ask"):
                                if key in rows.columns:
                                    value = self._safe_float(rows.iloc[-1][key])
                                    if value > 0:
                                        return value
                except Exception:
                    pass

            if hasattr(self.gateway, "market_data"):
                md = self.gateway.market_data

                if md is not None:

                    for method_name in (
                        "get_price",
                        "latest_price",
                        "get_last_price",
                        "last_price",
                        "market_price",
                    ):
                        if hasattr(md, method_name):
                            try:
                                value = self._safe_float(
                                    getattr(md, method_name)(symbol)
                                )
                                if value > 0:
                                    return value
                            except Exception:
                                pass

                    if hasattr(md, "snapshot"):
                        try:
                            snapshot = md.snapshot()

                            if isinstance(snapshot, dict):
                                row = snapshot.get(symbol)

                                if isinstance(row, dict):
                                    for key in (
                                        "price",
                                        "last",
                                        "mark",
                                        "close",
                                        "bid",
                                        "ask",
                                    ):
                                        value = self._safe_float(row.get(key))
                                        if value > 0:
                                            return value
                        except Exception:
                            pass

        raise ValueError(f"No executable price available for {symbol}")

    # =====================================================
    # HELPERS
    # =====================================================

    def _rejection(
        self,
        stage: str,
        reason: str,
        signal: Any = None,
        symbol: str = "",
        action: str = "",
        mode: str = "SIM",
    ) -> Dict[str, Any]:

        return {
            "status": "BLOCKED" if stage == "safety_gate" else "REJECTED",
            "stage": stage,
            "reason": reason,
            "symbol": symbol,
            "action": action,
            "timestamp": self._now(),
            "mode": mode,
            "raw_signal": str(signal)[:500],
        }