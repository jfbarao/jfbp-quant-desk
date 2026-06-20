# =========================================================
# 🧠 IBKR GATEWAY v3.8 — HARD RECONNECT + SAFE CALLBACKS
# LIVE MARKET DATA SUBSCRIPTION FIX
# EXECUTION RECOVERY HARD DEDUPE
# LIVE-READY SAFE
# =========================================================

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import pandas as pd


# =========================================================
# MODES
# =========================================================

SIM = "SIM"
LIVE = "LIVE"
BACKTEST = "BACKTEST"

TRUTH_SOURCE = "ibkr_gateway_v3_8"


# =========================================================
# 🧠 IBKR GATEWAY
# =========================================================

class IBKRGateway:

    def __init__(self, mode: str = SIM):

        self.mode = str(mode or SIM).upper().strip()

        self.ui_connected = False
        self.broker_connected = False

        self.host: Optional[str] = None
        self.port: Optional[int] = None
        self.client_id: Optional[int] = 7

        self.last_error: str = ""
        self.ib_client = None

        self.market_data = None
        self.market_data_type = 3

        self.positions: Dict[str, float] = {}
        self.last_quotes: Dict[str, Dict[str, Any]] = {}
        self.market_subscriptions: Dict[str, Any] = {}

        self.fill_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.order_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.error_callbacks: List[Callable[[Dict[str, Any]], None]] = []

        self.execution_cache: Dict[str, Dict[str, Any]] = {}
        self.execution_detail_cache: List[Dict[str, Any]] = []
        self._seen_exec_ids: set[str] = set()
        self._execution_recovery_running = False
        self.last_execution_recovery_report: Dict[str, Any] = {}

        self.open_orders_cache: List[Dict[str, Any]] = []
        self.account_summary_cache: List[Dict[str, Any]] = []

        self.last_positions_refresh: Optional[str] = None
        self.last_open_orders_refresh: Optional[str] = None
        self.last_account_refresh: Optional[str] = None
        self.last_execution_recovery_refresh: Optional[str] = None

        self._lock = threading.RLock()
        self._events_bound = False

        self.last_quotes_df = pd.DataFrame(
            columns=["symbol", "price", "time"]
        )

        self.last_positions_df = pd.DataFrame(
            columns=[
                "account",
                "symbol",
                "sec_type",
                "exchange",
                "currency",
                "position",
                "avg_cost",
            ]
        )

        self.last_pnl_df = pd.DataFrame(
            columns=["symbol", "pnl"]
        )

        self.ensure_runtime_fields()

    # =====================================================
    # ATTACHMENTS / CALLBACKS
    # =====================================================

    def attach_market_data(self, market_data):
        self.market_data = market_data

    def on_fill(self, callback):
        if callable(callback) and callback not in self.fill_callbacks:
            self.fill_callbacks.append(callback)

    def on_order_update(self, callback):
        if callable(callback) and callback not in self.order_callbacks:
            self.order_callbacks.append(callback)

    def on_error(self, callback):
        if callable(callback) and callback not in self.error_callbacks:
            self.error_callbacks.append(callback)

    def _emit_fill(self, fill: Dict[str, Any]) -> bool:
        """
        Emits a fill once per exec_id.

        This is the hard gate that prevents recovered historical IBKR executions
        from being replayed into OMS/runtime over and over.
        """

        exec_id = self._execution_id(fill)

        if exec_id:
            with self._lock:
                if exec_id in self._seen_exec_ids:
                    self.last_error = f"Duplicate execution ignored: {exec_id}"
                    return False

                self._seen_exec_ids.add(exec_id)
                self.execution_cache[exec_id] = dict(fill)

                if not any(
                    self._execution_id(row) == exec_id
                    for row in self.execution_detail_cache
                ):
                    self.execution_detail_cache.append(dict(fill))

        for callback in list(self.fill_callbacks):
            try:
                callback(dict(fill))
            except Exception as exc:
                self.last_error = f"Fill callback failed: {exc}"

        return True

    def _emit_order_update(self, event: Dict[str, Any]) -> None:
        for callback in list(self.order_callbacks):
            try:
                callback(dict(event))
            except Exception as exc:
                self.last_error = f"Order callback failed: {exc}"

    def _emit_error(self, event: Dict[str, Any]) -> None:
        for callback in list(self.error_callbacks):
            try:
                callback(dict(event))
            except Exception as exc:
                self.last_error = f"Error callback failed: {exc}"

    # =====================================================
    # RUNTIME SAFETY
    # =====================================================

    def ensure_runtime_fields(self):

        if self.last_quotes is None:
            self.last_quotes = {}

        if self.positions is None:
            self.positions = {}

        if not hasattr(self, "market_subscriptions") or self.market_subscriptions is None:
            self.market_subscriptions = {}

        if not hasattr(self, "fill_callbacks") or self.fill_callbacks is None:
            self.fill_callbacks = []

        if not hasattr(self, "order_callbacks") or self.order_callbacks is None:
            self.order_callbacks = []

        if not hasattr(self, "error_callbacks") or self.error_callbacks is None:
            self.error_callbacks = []

        if not hasattr(self, "execution_cache") or self.execution_cache is None:
            self.execution_cache = {}

        if not hasattr(self, "execution_detail_cache") or self.execution_detail_cache is None:
            self.execution_detail_cache = []

        if not hasattr(self, "_seen_exec_ids") or self._seen_exec_ids is None:
            self._seen_exec_ids = set()

        for row in list(self.execution_detail_cache):
            exec_id = self._execution_id(row)
            if exec_id:
                self._seen_exec_ids.add(exec_id)
                self.execution_cache.setdefault(exec_id, dict(row))

        if not hasattr(self, "open_orders_cache") or self.open_orders_cache is None:
            self.open_orders_cache = []

        if not hasattr(self, "account_summary_cache") or self.account_summary_cache is None:
            self.account_summary_cache = []

        if not hasattr(self, "_lock") or self._lock is None:
            self._lock = threading.RLock()

        if not hasattr(self, "_execution_recovery_running"):
            self._execution_recovery_running = False

        if not hasattr(self, "_events_bound"):
            self._events_bound = False

        if self.last_quotes_df is None:
            self.last_quotes_df = pd.DataFrame(
                columns=["symbol", "price", "time"]
            )

        if self.last_positions_df is None:
            self.last_positions_df = pd.DataFrame(
                columns=[
                    "account",
                    "symbol",
                    "sec_type",
                    "exchange",
                    "currency",
                    "position",
                    "avg_cost",
                ]
            )

        if self.last_pnl_df is None:
            self.last_pnl_df = pd.DataFrame(
                columns=["symbol", "pnl"]
            )

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value if value is not None else default)
        except Exception:
            return default

    def _safe_str(self, value: Any) -> str:
        try:
            return str(value or "").strip()
        except Exception:
            return ""

    def _execution_id(self, row: Any) -> str:
        if not isinstance(row, dict):
            return ""

        return self._safe_str(
            row.get("exec_id")
            or row.get("execution_id")
            or row.get("execution_key")
            or row.get("dedupe_key")
            or ""
        )

    # =====================================================
    # CONNECTION
    # =====================================================

    def connect(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 7,
        timeout: float = 10.0,
    ) -> bool:
        """Connect to IBKR with a hard reconnect fallback.

        Why this exists:
        - After a manual disconnect, ib_insync / TWS can keep the old client
          socket/clientId in a stale state for a short period.
        - Reusing the same IB() object may return False even though TWS/Gateway
          is healthy.
        - Restarting Streamlit works because it creates a fresh IB() object.

        This method recreates the IB() client for every manual connect attempt
        and retries once with alternate client IDs if the requested client ID is
        still being held by TWS/Gateway.
        """

        from ib_insync import IB

        self.ensure_runtime_fields()

        requested_host = str(host or "127.0.0.1")
        requested_port = int(port or 7497)
        requested_client_id = int(client_id or 7)

        self.host = requested_host
        self.port = requested_port
        self.client_id = requested_client_id

        self.ui_connected = False
        self.broker_connected = False
        self.last_error = ""

        # Always start manual connect from a clean IB() object. This is the
        # important reconnect fix.
        self._hard_reset_ib_client()

        candidate_client_ids = []
        for cid in (
            requested_client_id,
            requested_client_id + 1,
            requested_client_id + 2,
            requested_client_id + 10,
            7 if requested_client_id != 7 else 11,
        ):
            if cid not in candidate_client_ids:
                candidate_client_ids.append(cid)

        errors: List[str] = []

        for cid in candidate_client_ids:

            try:
                self.ib_client = IB()
                self._events_bound = False
                self.client_id = int(cid)

                self.ib_client.connect(
                    host=self.host,
                    port=self.port,
                    clientId=self.client_id,
                    timeout=timeout,
                )

                if not self.verify_connection():
                    errors.append(f"clientId {cid}: connect returned but isConnected=False")
                    self._hard_reset_ib_client()
                    time.sleep(0.35)
                    continue

                self._bind_ib_events()

                try:
                    self.ib_client.reqMarketDataType(3)
                    self.market_data_type = 3
                except Exception as exc:
                    # Non-fatal: connection is still valid.
                    self.last_error = f"Delayed market data request failed: {exc}"

                self.ui_connected = True
                self.broker_connected = True

                if not self.last_error:
                    self.last_error = ""

                return True

            except Exception as exc:
                errors.append(f"clientId {cid}: {exc}")
                self._hard_reset_ib_client()
                time.sleep(0.35)

        self.ui_connected = False
        self.broker_connected = False
        self.last_error = "Reconnect failed after fresh-client attempts: " + " | ".join(errors)
        return False

    def _hard_reset_ib_client(self) -> None:
        """Fully tear down the ib_insync client object before reconnecting."""

        try:
            if self.ib_client is not None:
                try:
                    if self.ib_client.isConnected():
                        self.ib_client.disconnect()
                except Exception:
                    pass
        finally:
            self.ib_client = None
            self._events_bound = False

    def disconnect(self) -> bool:

        try:
            if self.ib_client is not None and self.ib_client.isConnected():

                for _, ticker in list(self.market_subscriptions.items()):
                    try:
                        self.ib_client.cancelMktData(ticker.contract)
                    except Exception:
                        pass

                self.market_subscriptions = {}
                self.ib_client.disconnect()

        except Exception as exc:
            self.last_error = f"Disconnect warning: {exc}"

        # Fully reset the client object so the next Connect Gateway action
        # creates a fresh socket/client session instead of reusing a stale IB().
        self.ib_client = None
        self._events_bound = False

        self.ui_connected = False
        self.broker_connected = False
        self.host = None
        self.port = None
        self.client_id = None
        return True

    def verify_connection(self) -> bool:

        try:
            if self.ib_client is None:
                return False

            is_connected = getattr(
                self.ib_client,
                "isConnected",
                None,
            )

            if callable(is_connected):
                return bool(is_connected())

            return False

        except Exception:
            return False

    def is_connected(self) -> bool:
        return self.verify_connection()

    @property
    def connected(self) -> bool:
        return self.verify_connection()

    # =====================================================
    # IBKR EVENT BINDING
    # =====================================================

    def _bind_ib_events(self) -> None:

        if self.ib_client is None:
            return

        if getattr(self, "_events_bound", False):
            return

        bindings = (
            ("execDetailsEvent", self._on_exec_details),
            ("orderStatusEvent", self._on_order_status),
            ("positionEvent", self._on_position),
            ("errorEvent", self._on_error),
            ("disconnectedEvent", self._on_disconnect),
        )

        for event_name, handler in bindings:
            try:
                event_obj = getattr(self.ib_client, event_name, None)

                if event_obj is None:
                    continue

                try:
                    event_obj -= handler
                except Exception:
                    pass

                event_obj += handler

            except Exception as exc:
                self.last_error = f"IBKR event bind failed {event_name}: {exc}"

        self._events_bound = True

    # =====================================================
    # EXECUTION RECOVERY
    # =====================================================

    def recover_broker_executions(
        self,
        timeout_seconds: float = 5.0,
    ) -> List[Dict[str, Any]]:
        """
        Safe broker execution recovery.

        - Calls IBKR reqExecutions().
        - Normalizes returned executions.
        - Emits only executions whose exec_id has not already been seen.
        - Never replays historical duplicate fills into runtime.
        - Runs in a daemon worker so Streamlit does not freeze forever.
        """

        self.ensure_runtime_fields()

        if getattr(
            self,
            "_execution_recovery_running",
            False,
        ):
            self.last_error = "Execution recovery already running."
            return []

        if not self.verify_connection():
            self.last_error = "IBKR broker connection unavailable."
            return []

        if self.ib_client is None:
            self.last_error = "IBKR client missing."
            return []

        self._execution_recovery_running = True
        self.last_error = ""

        recovered_events: List[Dict[str, Any]] = []
        errors: List[str] = []
        counts = {
            "recovered": 0,
            "new": 0,
            "duplicates": 0,
        }

        lock = threading.RLock()

        def worker() -> None:
            try:
                executions = self.ib_client.reqExecutions()

                if executions is None:
                    executions = []

                for fill in list(executions):
                    row = self._normalize_ib_fill(
                        trade=None,
                        fill=fill,
                        source="ibkr_execution_recovery",
                    )

                    exec_id = self._execution_id(row)

                    if not exec_id:
                        errors.append("Recovered execution ignored: missing exec_id")
                        continue

                    with lock:
                        counts["recovered"] += 1

                    # Hard dedupe BEFORE emit/persist/replay.
                    emitted = self._emit_fill(row)

                    with lock:
                        if emitted:
                            counts["new"] += 1
                            recovered_events.append(row)
                        else:
                            counts["duplicates"] += 1

            except Exception as exc:
                errors.append(str(exc))

        thread = threading.Thread(
            target=worker,
            daemon=True,
        )

        try:
            thread.start()
            thread.join(timeout_seconds)

            if thread.is_alive():
                errors.append("Execution recovery timed out.")

            report = {
                "status": "OK" if not errors else "ERROR",
                "timestamp": self._now(),
                "recovered": counts["recovered"],
                "new": counts["new"],
                "duplicates": counts["duplicates"],
                "errors": list(errors),
                "cache_count": len(self.execution_cache),
                "truth_source": TRUTH_SOURCE,
            }

            self.last_execution_recovery_report = dict(report)
            self.last_execution_recovery_refresh = self._now()

            if errors:
                self.last_error = "Execution recovery failed: " + "; ".join(errors)
            else:
                self.last_error = (
                    "Execution recovery OK: "
                    f"recovered={counts['recovered']} "
                    f"new={counts['new']} "
                    f"duplicates={counts['duplicates']}"
                )

            return list(recovered_events)

        except Exception as exc:
            self.last_error = f"Execution recovery failed: {exc}"
            self.last_execution_recovery_report = {
                "status": "ERROR",
                "timestamp": self._now(),
                "recovered": counts["recovered"],
                "new": counts["new"],
                "duplicates": counts["duplicates"],
                "errors": [str(exc)],
                "truth_source": TRUTH_SOURCE,
            }
            return []

        finally:
            self._execution_recovery_running = False

    def recover_executions_from_broker(
        self,
        timeout_seconds: float = 5.0,
    ) -> Dict[str, Any]:

        before = len(self.execution_cache)

        events = self.recover_broker_executions(
            timeout_seconds=timeout_seconds,
        )

        report = dict(self.last_execution_recovery_report or {})
        report.setdefault("events", events)
        report.setdefault("before_cache_count", before)
        report.setdefault("after_cache_count", len(self.execution_cache))

        return report

    def get_execution_cache(self) -> List[Dict[str, Any]]:
        self.ensure_runtime_fields()
        return list(self.execution_detail_cache)

    def execution_snapshot(self) -> List[Dict[str, Any]]:
        return self.get_execution_cache()

    # =====================================================
    # IBKR EVENT HANDLERS — EXECUTION INGESTION SAFE
    # =====================================================

    def _normalize_ib_action(self, action: Any) -> str:
        action = str(action or "").upper().strip()

        if action in ("BOT", "BUY"):
            return "BUY"

        if action in ("SLD", "SELL"):
            return "SELL"

        return action

    def _normalize_ib_fill(
        self,
        trade: Any,
        fill: Any,
        source: str = "ibkr_execDetailsEvent",
    ) -> Dict[str, Any]:

        contract = getattr(fill, "contract", None)
        execution = getattr(fill, "execution", None)

        if execution is None:
            return {
                "status": "REJECTED",
                "reason": "Missing execution object",
                "source": source,
                "mode": self.mode,
                "timestamp": self._now(),
                "truth_source": TRUTH_SOURCE,
            }

        symbol = self._safe_str(getattr(contract, "symbol", "")).upper()
        action = self._normalize_ib_action(getattr(execution, "side", ""))

        qty = self._safe_float(
            getattr(execution, "shares", None)
            or getattr(execution, "cumQty", None)
            or 0
        )

        price = self._safe_float(
            getattr(execution, "price", None)
            or getattr(execution, "avgPrice", None)
            or 0
        )

        exec_id = self._safe_str(getattr(execution, "execId", ""))
        order_id = self._safe_str(getattr(execution, "orderId", ""))
        perm_id = self._safe_str(getattr(execution, "permId", ""))
        account = self._safe_str(getattr(execution, "acctNumber", ""))

        exchange = self._safe_str(getattr(execution, "exchange", ""))
        currency = self._safe_str(getattr(contract, "currency", ""))
        sec_type = self._safe_str(getattr(contract, "secType", ""))

        fill_time = getattr(execution, "time", None)

        row = {
            "event": "EXECUTION_FILL",
            "symbol": symbol,
            "action": action,
            "side": action,
            "qty": qty,
            "quantity": qty,
            "filled_qty": qty,
            "fill_qty": qty,
            "execution_qty": qty,
            "price": price,
            "fill_price": price,
            "execution_price": price,
            "avg_fill_price": price,
            "execution_id": exec_id,
            "exec_id": exec_id,
            "broker_order_id": order_id,
            "broker_id": order_id,
            "order_id": order_id,
            "perm_id": perm_id,
            "permId": perm_id,
            "account": account,
            "exchange": exchange,
            "currency": currency,
            "sec_type": sec_type,
            "status": "FILLED",
            "execution_status": "FILLED",
            "order_status": "FILLED",
            "ib_time": str(fill_time or ""),
            "source": source,
            "mode": self.mode,
            "is_true_fill": True,
            "truth_source": TRUTH_SOURCE,
            "dedupe_key": exec_id,
            "timestamp": str(fill_time or self._now()),
            "cached_at": self._now(),
        }

        if not row["symbol"]:
            row["status"] = "REJECTED"
            row["reason"] = f"Missing symbol | exec_id={exec_id}"

        elif row["side"] not in ("BUY", "SELL"):
            row["status"] = "REJECTED"
            row["reason"] = f"Invalid side {row['side']} | exec_id={exec_id}"

        elif row["qty"] <= 0:
            row["status"] = "REJECTED"
            row["reason"] = f"Invalid qty {row['qty']} | exec_id={exec_id}"

        elif row["price"] <= 0:
            row["status"] = "REJECTED"
            row["reason"] = f"Invalid price {row['price']} | exec_id={exec_id}"

        return row

    def _on_exec_details(self, *args):

        try:
            trade = None
            fill = None

            for arg in args:
                if hasattr(arg, "execution") and hasattr(arg, "contract"):
                    fill = arg
                elif hasattr(arg, "order") and hasattr(arg, "contract"):
                    trade = arg

            if fill is None and len(args) >= 2:
                trade = args[0]
                fill = args[1]

            if fill is None:
                self.last_error = "execDetails ignored: missing fill object"
                return

            row = self._normalize_ib_fill(
                trade=trade,
                fill=fill,
                source="ibkr_execDetailsEvent",
            )

            if row.get("status") == "REJECTED":
                self.last_error = row.get("reason", "execDetails rejected")
                return

            self.update_quote(row["symbol"], row["price"])

            # Hard dedupe happens inside _emit_fill().
            self._emit_fill(row)

            # IMPORTANT:
            # Do NOT refresh positions, subscribe market data, or request account
            # data inside the execution callback. That can hang Streamlit and can
            # mutate runtime repeatedly during recovery.

        except Exception as exc:
            self.last_error = f"execDetails handler failed: {exc}"

    def _on_order_status(self, *args):

        try:
            trade = args[0] if args else None

            order = getattr(trade, "order", None)
            status = getattr(trade, "orderStatus", None)
            contract = getattr(trade, "contract", None)

            event = {
                "symbol": self._safe_str(getattr(contract, "symbol", "")).upper(),
                "order_id": self._safe_str(getattr(order, "orderId", "")),
                "broker_order_id": self._safe_str(getattr(order, "orderId", "")),
                "broker_id": self._safe_str(getattr(order, "orderId", "")),
                "perm_id": self._safe_str(getattr(order, "permId", "")),
                "permId": self._safe_str(getattr(order, "permId", "")),
                "status": self._safe_str(getattr(status, "status", "")).upper(),
                "filled_qty": self._safe_float(getattr(status, "filled", 0)),
                "remaining_qty": self._safe_float(getattr(status, "remaining", 0)),
                "avg_fill_price": self._safe_float(getattr(status, "avgFillPrice", 0)),
                "source": "ibkr_orderStatusEvent",
                "mode": self.mode,
                "timestamp": self._now(),
                "truth_source": TRUTH_SOURCE,
            }

            self._emit_order_update(event)

        except Exception as exc:
            self.last_error = f"orderStatus handler failed: {exc}"

    def _on_position(self, *args):

        try:
            position = args[-1] if args else None
            contract = getattr(position, "contract", None)

            symbol = self._safe_str(getattr(contract, "symbol", "")).upper()
            qty = self._safe_float(getattr(position, "position", 0))

            if symbol:
                if abs(qty) > 0:
                    self.positions[symbol] = qty
                elif symbol in self.positions:
                    self.positions.pop(symbol, None)

            self._sync_positions()

            # Do NOT request market data here. Position callbacks should remain
            # cache-only.

        except Exception as exc:
            self.last_error = f"position handler failed: {exc}"

    def _on_error(self, *args):

        try:
            event = {
                "event": "IBKR_ERROR",
                "args": [str(arg) for arg in args],
                "timestamp": self._now(),
                "truth_source": TRUTH_SOURCE,
            }

            if len(args) >= 3:
                event["req_id"] = args[0]
                event["error_code"] = args[1]
                event["error"] = str(args[2])
                self.last_error = str(args[2])
            else:
                self.last_error = "IBKR error event: " + " | ".join(event["args"])

            self._emit_error(event)

        except Exception as exc:
            self.last_error = f"error handler failed: {exc}"

    def _on_disconnect(self, *args, **kwargs):

        self.ui_connected = False
        self.broker_connected = False

        event = {
            "event": "DISCONNECTED",
            "timestamp": self._now(),
            "truth_source": TRUTH_SOURCE,
        }

        self._emit_error(event)

    # =====================================================
    # MARKET DATA / QUOTES
    # =====================================================

    def get_quote(self, symbol: str) -> Optional[float]:

        symbol = str(symbol).upper().strip()
        data = self.last_quotes.get(symbol)

        if data is None:
            return None

        return float(data["price"])

    def get_price(self, symbol: str) -> Optional[float]:
        return self.get_quote(symbol)

    def latest_price(self, symbol: str) -> Optional[float]:
        return self.get_quote(symbol)

    def get_last_price(self, symbol: str) -> Optional[float]:
        return self.get_quote(symbol)

    def last_price(self, symbol: str) -> Optional[float]:
        return self.get_quote(symbol)

    def market_price(self, symbol: str) -> Optional[float]:
        return self.get_quote(symbol)

    def update_quote(self, symbol: str, price: float):

        symbol = str(symbol).upper().strip()
        price = self._safe_float(price)

        if not symbol or price <= 0:
            return

        self.last_quotes[symbol] = {
            "price": float(price),
            "time": time.time(),
        }

        if self.market_data is not None:
            fn = getattr(self.market_data, "update_price", None)

            if callable(fn):
                fn(symbol, price)

        self._sync_quotes()

    def subscribe_market_data(
        self,
        symbols: List[str],
    ) -> None:

        if self.ib_client is None:
            return

        if not self.verify_connection():
            return

        try:
            from ib_insync import Stock
        except Exception as exc:
            self.last_error = f"ib_insync import failed: {exc}"
            return

        self.ensure_runtime_fields()

        for raw_symbol in symbols:

            try:
                symbol = str(raw_symbol).upper().strip()

                if not symbol:
                    continue

                if symbol in self.market_subscriptions:
                    continue

                contract = Stock(symbol, "SMART", "USD")

                ticker = self.ib_client.reqMktData(
                    contract,
                    "",
                    False,
                    False,
                )

                self.market_subscriptions[symbol] = ticker

            except Exception as exc:
                self.last_error = f"Market subscription failed {raw_symbol}: {exc}"

    def refresh_market_data(self) -> None:

        self.ensure_runtime_fields()

        if not self.market_subscriptions:
            return

        for symbol, ticker in list(self.market_subscriptions.items()):

            try:
                price = None

                for field in (
                    "marketPrice",
                    "last",
                    "close",
                    "midpoint",
                ):

                    value = getattr(ticker, field, None)

                    if callable(value):
                        try:
                            value = value()
                        except Exception:
                            value = None

                    value = self._safe_float(value)

                    if value > 0:
                        price = value
                        break

                if price is None:
                    continue

                self.update_quote(symbol, price)

            except Exception as exc:
                self.last_error = f"refresh_market_data failed {symbol}: {exc}"

    def load_demo_data(self):

        demo = {
            "AAPL": 192.44,
            "MSFT": 421.11,
            "NVDA": 118.72,
            "TSLA": 177.88,
            "AMZN": 183.55,
            "META": 512.20,
            "GOOGL": 176.30,
            "AMD": 164.90,
        }

        for s, p in demo.items():
            self.update_quote(s, p)

    # =====================================================
    # ORDERS
    # =====================================================

    def place_order(
        self,
        symbol: str,
        qty: int,
        side: str,
    ) -> dict:

        return self.submit_order(
            symbol=symbol,
            qty=qty,
            side=side,
            order_type="MKT",
        )

    def submit_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        order_type: str = "MKT",
        limit_price: Optional[float] = None,
        order_id: Optional[str] = None,
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> Dict[str, Any]:

        symbol = str(symbol or "").upper().strip()
        side = str(side or "").upper().strip()
        order_type = str(order_type or "MKT").upper().strip()
        qty = int(qty)

        if not symbol:
            raise ValueError("Missing symbol")

        if side not in ["BUY", "SELL"]:
            raise ValueError("Invalid side")

        if qty <= 0:
            raise ValueError("Invalid qty")

        if self.mode == SIM:

            current = self.positions.get(symbol, 0.0)

            if side == "BUY":
                current += qty
            else:
                current -= qty

            if abs(current) > 0:
                self.positions[symbol] = current
            else:
                self.positions.pop(symbol, None)

            self._sync_positions()
            self._sync_pnl()

            return {
                "status": "SIM_FILLED",
                "symbol": symbol,
                "qty": qty,
                "quantity": qty,
                "side": side,
                "action": side,
                "price": self.get_quote(symbol),
                "time": time.time(),
                "timestamp": self._now(),
                "mode": self.mode,
                "truth_source": TRUTH_SOURCE,
            }

        if self.mode == LIVE:

            if self.ib_client is None:
                raise RuntimeError("IBKR client unavailable")

            if not self.verify_connection():
                raise RuntimeError("IBKR client not connected")

            from ib_insync import LimitOrder, MarketOrder, Stock

            contract = Stock(symbol, exchange, currency)

            if order_type == "MKT":
                ib_order = MarketOrder(
                    action=side,
                    totalQuantity=int(qty),
                )

            elif order_type == "LMT":
                if limit_price is None or float(limit_price) <= 0:
                    raise ValueError("Limit order requires positive limit_price")

                ib_order = LimitOrder(
                    action=side,
                    totalQuantity=int(qty),
                    lmtPrice=float(limit_price),
                )

            else:
                raise ValueError(f"Unsupported order_type: {order_type}")

            trade = self.ib_client.placeOrder(contract, ib_order)

            try:
                self.ib_client.sleep(0.25)
            except Exception:
                pass

            broker_order_id = self._safe_str(
                getattr(getattr(trade, "order", None), "orderId", "")
            )

            perm_id = self._safe_str(
                getattr(getattr(trade, "order", None), "permId", "")
            )

            self.last_error = ""

            return {
                "status": "LIVE_SENT",
                "order_status": self._safe_str(
                    getattr(getattr(trade, "orderStatus", None), "status", "")
                ).upper() or "SUBMITTED",
                "order_id": order_id or broker_order_id,
                "broker_order_id": broker_order_id,
                "broker_id": broker_order_id,
                "perm_id": perm_id,
                "permId": perm_id,
                "symbol": symbol,
                "qty": qty,
                "quantity": qty,
                "side": side,
                "action": side,
                "order_type": order_type,
                "limit_price": limit_price,
                "trade": str(trade),
                "time": time.time(),
                "timestamp": self._now(),
                "mode": self.mode,
                "truth_source": TRUTH_SOURCE,
            }

        if self.mode == BACKTEST:

            return {
                "status": "BACKTEST_RECORDED",
                "symbol": symbol,
                "qty": qty,
                "quantity": qty,
                "side": side,
                "action": side,
                "price": self.get_quote(symbol),
                "time": time.time(),
                "timestamp": self._now(),
                "mode": self.mode,
                "truth_source": TRUTH_SOURCE,
            }

        raise RuntimeError(f"Unsupported mode: {self.mode}")

    def cancel_order(self, broker_order_id: str) -> bool:

        if not self.verify_connection():
            raise RuntimeError("IBKR broker is not connected")

        broker_order_id = self._safe_str(broker_order_id)

        if not broker_order_id:
            return False

        try:
            candidates = []

            try:
                candidates.extend(list(self.ib_client.openTrades()))
            except Exception:
                pass

            try:
                candidates.extend(list(self.ib_client.trades()))
            except Exception:
                pass

            seen = set()

            for trade in candidates:
                order = getattr(trade, "order", None)

                if order is None:
                    continue

                oid = self._safe_str(getattr(order, "orderId", ""))
                perm_id = self._safe_str(getattr(order, "permId", ""))

                key = (oid, perm_id)

                if key in seen:
                    continue

                seen.add(key)

                if broker_order_id in {oid, perm_id}:
                    self.ib_client.cancelOrder(order)

                    try:
                        self.ib_client.sleep(0.25)
                    except Exception:
                        pass

                    self.refresh_open_orders()
                    return True

            self.refresh_open_orders()
            return False

        except Exception as exc:
            self.last_error = str(exc)
            return False

    # =====================================================
    # POSITION / ACCOUNT READS
    # =====================================================

    def _position_market_price(
        self,
        symbol: str,
        contract: Any = None,
        avg_cost: float = 0.0,
    ) -> float:
        symbol = str(symbol or "").upper().strip()

        price = 0.0

        # Prefer cached quote/market data if available.
        for cache_name in (
            "quotes_cache",
            "market_data_cache",
            "last_prices",
            "prices",
            "snapshot_cache",
        ):
            try:
                cache = getattr(self, cache_name, None)

                if not isinstance(cache, dict):
                    continue

                raw = cache.get(symbol)

                if isinstance(raw, dict):
                    for key in (
                        "last_price",
                        "market_price",
                        "marketPrice",
                        "last",
                        "price",
                        "close",
                    ):
                        price = self._safe_float(raw.get(key))

                        if price > 0:
                            return price

                else:
                    price = self._safe_float(raw)

                    if price > 0:
                        return price

            except Exception:
                pass

        # Fallback to ib_insync market price when a contract is available.
        try:
            if (
                self.ib_client is not None
                and contract is not None
                and self.verify_connection()
            ):
                ticker = self.ib_client.reqMktData(
                    contract,
                    "",
                    False,
                    False,
                )

                try:
                    self.ib_client.sleep(0.25)
                except Exception:
                    pass

                for attr in (
                    "marketPrice",
                    "last",
                    "close",
                ):
                    value = getattr(ticker, attr, None)

                    if callable(value):
                        value = value()

                    price = self._safe_float(value)

                    if price > 0:
                        return price

                bid = self._safe_float(getattr(ticker, "bid", 0.0))
                ask = self._safe_float(getattr(ticker, "ask", 0.0))

                if bid > 0 and ask > 0:
                    return (bid + ask) / 2.0

        except Exception:
            pass

        return self._safe_float(avg_cost)

    def refresh_positions(self):

        try:
            if self.ib_client is not None and self.verify_connection():

                ib_positions = self.ib_client.positions()

                rows = []
                self.positions = {}

                for p in ib_positions:

                    contract = getattr(p, "contract", None)

                    symbol = str(
                        getattr(contract, "symbol", "") or ""
                    ).upper().strip()

                    qty = self._safe_float(
                        getattr(p, "position", 0)
                    )

                    avg_cost = self._safe_float(
                        getattr(p, "avgCost", 0)
                    )

                    account = str(
                        getattr(p, "account", "") or ""
                    )

                    if not symbol or abs(qty) <= 0:
                        continue

                    last_price = self._position_market_price(
                        symbol=symbol,
                        contract=contract,
                        avg_cost=avg_cost,
                    )

                    market_value = abs(qty) * last_price

                    unrealized_pnl = 0.0

                    if avg_cost > 0 and last_price > 0:
                        unrealized_pnl = (
                            (last_price - avg_cost) * qty
                        )

                    self.positions[symbol] = qty

                    rows.append({
                        "account": account,
                        "symbol": symbol,
                        "sec_type": getattr(contract, "secType", ""),
                        "exchange": getattr(contract, "exchange", ""),
                        "currency": getattr(contract, "currency", ""),
                        "position": qty,
                        "qty": qty,
                        "quantity": qty,
                        "signed_qty": qty,
                        "avg_cost": avg_cost,
                        "avgCost": avg_cost,
                        "avg_price": avg_cost,
                        "last_price": last_price,
                        "market_price": last_price,
                        "marketPrice": last_price,
                        "position_value": market_value,
                        "market_value": market_value,
                        "marketValue": market_value,
                        "unrealized_pnl": unrealized_pnl,
                        "realized_pnl": 0.0,
                        "total_pnl": unrealized_pnl,
                        "con_id": getattr(contract, "conId", ""),
                        "timestamp": self._now(),
                        "truth_source": TRUTH_SOURCE,
                    })

                self.last_positions_df = pd.DataFrame(rows)
                self.last_positions_refresh = self._now()

                return rows

            self._sync_positions()
            return self.last_positions_df.to_dict("records")

        except Exception as exc:
            self.last_error = f"refresh_positions failed: {exc}"
            return []

    def positions_snapshot(self) -> List[Dict[str, Any]]:
        return self.last_positions_df.to_dict("records")

    def get_positions(self):
        return self.refresh_positions()

    def refresh_open_orders(self) -> List[Dict[str, Any]]:

        rows: List[Dict[str, Any]] = []

        try:
            if self.ib_client is not None and self.verify_connection():
                try:
                    trades = list(self.ib_client.openTrades())
                except Exception:
                    trades = []

                for trade in trades:
                    order = getattr(trade, "order", None)
                    status = getattr(trade, "orderStatus", None)
                    contract = getattr(trade, "contract", None)

                    action = self._safe_str(
                        getattr(order, "action", "")
                    ).upper()

                    qty = self._safe_float(
                        getattr(order, "totalQuantity", 0)
                    )

                    filled = self._safe_float(
                        getattr(status, "filled", 0)
                    )

                    remaining = self._safe_float(
                        getattr(status, "remaining", 0)
                    )

                    rows.append({
                        "broker_order_id": self._safe_str(
                            getattr(order, "orderId", "")
                        ),
                        "broker_id": self._safe_str(
                            getattr(order, "orderId", "")
                        ),
                        "perm_id": self._safe_str(
                            getattr(order, "permId", "")
                        ),
                        "permId": self._safe_str(
                            getattr(order, "permId", "")
                        ),
                        "symbol": self._safe_str(
                            getattr(contract, "symbol", "")
                        ).upper(),
                        "action": action,
                        "side": action,
                        "qty": qty,
                        "quantity": qty,
                        "filled_qty": filled,
                        "remaining_qty": remaining,
                        "order_type": self._safe_str(
                            getattr(order, "orderType", "")
                        ),
                        "limit_price": self._safe_float(
                            getattr(order, "lmtPrice", 0)
                        ),
                        "avg_fill_price": self._safe_float(
                            getattr(status, "avgFillPrice", 0)
                        ),
                        "status": self._safe_str(
                            getattr(status, "status", "")
                        ).upper(),
                        "timestamp": self._now(),
                        "truth_source": TRUTH_SOURCE,
                    })

            self.open_orders_cache = list(rows)
            self.last_open_orders_refresh = self._now()
            return list(self.open_orders_cache)

        except Exception as exc:
            self.last_error = f"refresh_open_orders failed: {exc}"
            return list(self.open_orders_cache)

    def open_orders(self) -> List[Dict[str, Any]]:
        return list(self.open_orders_cache)

    def get_open_orders(self) -> List[Dict[str, Any]]:
        return self.refresh_open_orders()

    def refresh_account_summary(self) -> List[Dict[str, Any]]:

        rows: List[Dict[str, Any]] = []

        try:
            if self.ib_client is not None and self.verify_connection():
                try:
                    values = list(self.ib_client.accountValues())
                except Exception:
                    values = []

                for item in values:
                    rows.append({
                        "account": getattr(item, "account", ""),
                        "tag": getattr(item, "tag", ""),
                        "value": getattr(item, "value", ""),
                        "currency": getattr(item, "currency", ""),
                        "model_code": getattr(item, "modelCode", ""),
                        "timestamp": self._now(),
                        "truth_source": TRUTH_SOURCE,
                    })

            self.account_summary_cache = list(rows)
            self.last_account_refresh = self._now()
            return list(self.account_summary_cache)

        except Exception as exc:
            self.last_error = f"refresh_account_summary failed: {exc}"
            return list(self.account_summary_cache)

    def account_summary(self) -> List[Dict[str, Any]]:
        return list(self.account_summary_cache)

    def get_account_summary(self) -> List[Dict[str, Any]]:
        return self.refresh_account_summary()

    def account_values(self) -> Dict[str, Any]:

        values: Dict[str, Any] = {}

        try:
            rows = list(self.account_summary_cache)

            if not rows:
                rows = self.refresh_account_summary()

            for row in rows:

                if not isinstance(row, dict):
                    continue

                tag = str(
                    row.get("tag", "")
                ).strip()

                if not tag:
                    continue

                raw_value = row.get("value")

                try:
                    value = float(raw_value)
                except Exception:
                    value = raw_value

                values[tag] = value

                currency = str(
                    row.get("currency", "")
                ).strip()

                if currency:
                    values[f"{tag}_{currency}"] = value

        except Exception as exc:
            self.last_error = (
                f"account_values failed: {exc}"
            )

        return values

    def account_snapshot(self) -> Dict[str, Any]:

        values = self.account_values()

        def first_value(keys: List[str]) -> float:
            for key in keys:
                value = self._safe_float(values.get(key), 0.0)

                if value > 0:
                    return float(value)

            return 0.0

        net_liquidation = first_value([
            "NetLiquidation",
            "NetLiquidation_USD",
            "NetLiquidation_CAD",
            "FullAvailableFunds",
            "FullAvailableFunds_USD",
            "FullAvailableFunds_CAD",
        ])

        available_funds = first_value([
            "AvailableFunds",
            "AvailableFunds_USD",
            "AvailableFunds_CAD",
            "FullAvailableFunds",
            "FullAvailableFunds_USD",
            "FullAvailableFunds_CAD",
        ])

        buying_power = first_value([
            "BuyingPower",
            "BuyingPower_USD",
            "BuyingPower_CAD",
        ])

        total_cash = first_value([
            "TotalCashValue",
            "TotalCashValue_USD",
            "TotalCashValue_CAD",
            "CashBalance",
            "CashBalance_USD",
            "CashBalance_CAD",
            "SettledCash",
            "SettledCash_USD",
            "SettledCash_CAD",
            "AvailableFunds",
            "AvailableFunds_USD",
            "AvailableFunds_CAD",
        ])

        excess_liquidity = first_value([
            "ExcessLiquidity",
            "ExcessLiquidity_USD",
            "ExcessLiquidity_CAD",
        ])

        return {
            "account_equity": net_liquidation,
            "net_liquidation": net_liquidation,
            "NetLiquidation": net_liquidation,
            "available_funds": available_funds,
            "AvailableFunds": available_funds,
            "buying_power": buying_power,
            "BuyingPower": buying_power,
            "cash": total_cash,
            "available_cash": total_cash,
            "TotalCashValue": total_cash,
            "excess_liquidity": excess_liquidity,
            "ExcessLiquidity": excess_liquidity,
            "raw": values,
            "timestamp": self._now(),
            "truth_source": TRUTH_SOURCE,
        }

    def pull_broker_snapshot(self) -> Dict[str, Any]:

        positions = self.refresh_positions()
        open_orders = self.refresh_open_orders()
        account_summary = self.refresh_account_summary()
        account_values = self.account_values()
        account_snapshot = self.account_snapshot()
        fills = self.get_execution_cache()

        return {
            "positions": positions,
            "open_orders": open_orders,
            "account_summary": account_summary,
            "account_values": account_values,
            "account_snapshot": account_snapshot,
            "fills": fills,
            "timestamp": self._now(),
            "truth_source": TRUTH_SOURCE,
        }

    def broker_snapshot(self) -> Dict[str, Any]:
        return self.pull_broker_snapshot()

    def refresh_all(self):

        if self.mode == LIVE and self.verify_connection():

            self.refresh_positions()
            self.refresh_account_summary()

            symbols = list(self.positions.keys())

            if symbols:
                self.subscribe_market_data(symbols)

            self.refresh_market_data()

        else:
            if self.last_quotes_df.empty:
                self.load_demo_data()

            self._sync_quotes()
            self._sync_positions()
            self._sync_pnl()
                        
    # =====================================================
    # SYNC HELPERS
    # =====================================================

    def _sync_quotes(self):

        self.last_quotes_df = pd.DataFrame([
            {
                "symbol": s,
                "price": v["price"],
                "time": v["time"],
            }
            for s, v in self.last_quotes.items()
        ])

    def _sync_positions(self):

        self.last_positions_df = pd.DataFrame([
            {
                "symbol": s,
                "position": p,
                "qty": p,
                "quantity": p,
                "avg_cost": 0.0,
                "avg_price": 0.0,
            }
            for s, p in self.positions.items()
            if abs(float(p or 0)) > 0
        ])

    def _sync_pnl(self):

        self.last_pnl_df = pd.DataFrame([
            {
                "symbol": s,
                "pnl": 0.0,
            }
            for s in self.positions.keys()
        ])

    # =====================================================
    # STATUS
    # =====================================================

    def connection_status(self) -> dict:

        broker_connected = self.verify_connection()
        self.broker_connected = broker_connected

        return {
            "connected": self.ui_connected or broker_connected,
            "ui_connected": self.ui_connected,
            "broker_connected": broker_connected,
            "status": "CONNECTED" if broker_connected else "DISCONNECTED",
            "mode": self.mode,
            "host": self.host,
            "port": self.port,
            "client_id": self.client_id,
            "error": self.last_error,
            "positions_count": len(self.positions),
            "open_orders_count": len(self.open_orders_cache),
            "account_summary_rows": len(self.account_summary_cache),
            "execution_cache_count": len(self.execution_cache),
            "last_positions_refresh": self.last_positions_refresh,
            "last_open_orders_refresh": self.last_open_orders_refresh,
            "last_account_refresh": self.last_account_refresh,
            "last_execution_recovery_refresh": self.last_execution_recovery_refresh,
            "truth_source": TRUTH_SOURCE,
        }


# Backward-compatible aliases
IBKRGatewayLive = IBKRGateway
IBKRLiveGateway = IBKRGateway
