# =========================================================
# 📡 IBKR LIVE GATEWAY — INSTITUTIONAL TRUTH ADAPTER v1.7
# LIVE CONNECTIVITY + ACCOUNT / POSITIONS / ORDER TRUTH
# BROKER EXECUTION RECOVERY + EXECUTION CACHE
# =========================================================

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
import asyncio
import threading


# =========================================================
# STREAMLIT / IB_INSYNC EVENT LOOP FIX
# Must happen BEFORE importing ib_insync.
# =========================================================

try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())


try:
    from ib_insync import IB, Stock, MarketOrder, LimitOrder, ExecutionFilter
    IB_IMPORT_ERROR = ""
except Exception as exc:
    IB = None
    Stock = None
    MarketOrder = None
    LimitOrder = None
    ExecutionFilter = None
    IB_IMPORT_ERROR = str(exc)


SIM = "SIM"
LIVE = "LIVE"
BACKTEST = "BACKTEST"

TRUTH_SOURCE = "ibkr_live_gateway.v1_7"


class IBKRLiveGateway:
    """
    Institutional LIVE-only IBKR gateway.

    Rules:
    - No fake fills.
    - No demo quotes.
    - No UI-connected shortcut.
    - Broker connection truth comes only from ib.isConnected().
    - Orders are submitted to IBKR.
    - Fills are persisted only from broker callbacks / broker recovery.
    """

    def __init__(self, mode: str = LIVE):
        self.mode = str(mode or LIVE).upper().strip()

        self.ib = None
        self.host: Optional[str] = None
        self.port: Optional[int] = None
        self.client_id: Optional[int] = None

        self.last_error: str = (
            f"IB import error: {IB_IMPORT_ERROR}"
            if IB_IMPORT_ERROR
            else ""
        )
        self.last_status: str = "DISCONNECTED"

        self.order_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.fill_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.error_callbacks: List[Callable[[Dict[str, Any]], None]] = []

        self.submitted_orders: Dict[str, Dict[str, Any]] = {}
        self.broker_order_map: Dict[str, str] = {}

        self.positions_cache: Dict[str, float] = {}
        self.positions_detail_cache: List[Dict[str, Any]] = []

        self.account_summary_cache: List[Dict[str, Any]] = []
        self.open_orders_cache: List[Dict[str, Any]] = []

        self.execution_cache: Dict[str, Dict[str, Any]] = {}
        self.execution_detail_cache: List[Dict[str, Any]] = []
        self.fills_cache: List[Dict[str, Any]] = []
        self.executions_cache: List[Dict[str, Any]] = []

        self.last_positions_refresh: str = ""
        self.last_account_refresh: str = ""
        self.last_open_orders_refresh: str = ""
        self.last_execution_recovery_report: Dict[str, Any] = {}

        self._execution_recovery_running: bool = False
        self._events_bound: bool = False
        self._lock = threading.RLock()

        self._load_persisted_executions()

    # =====================================================
    # HELPERS
    # =====================================================

    def _safe_float(self, value: Any) -> float:
        try:
            if value is None:
                return 0.0

            value = float(value)

            if value != value:
                return 0.0

            return value

        except Exception:
            return 0.0

    def _safe_int(self, value: Any) -> int:
        try:
            if value is None:
                return 0

            return int(float(value))

        except Exception:
            return 0

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _broker_now(self) -> str:
        return self._now()

    # =====================================================
    # EVENT LOOP
    # =====================================================

    def _ensure_event_loop(self) -> None:
        """
        Streamlit runs inside ScriptRunner.scriptThread, which often has
        no default asyncio event loop. ib_insync requires one.
        """

        try:
            loop = asyncio.get_event_loop()

            if loop.is_closed():
                raise RuntimeError("Current asyncio event loop is closed")

        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            from ib_insync import util
            util.patchAsyncio()
        except Exception:
            pass

    # =====================================================
    # CONNECTION
    # =====================================================

    def connect(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 7,
        timeout: float = 5.0,
    ) -> bool:

        if IB is None:
            self.host = host
            self.port = int(port)
            self.client_id = int(client_id)
            self.last_error = (
                "ib_insync is not installed or could not be imported: "
                f"{IB_IMPORT_ERROR}"
            )
            self.last_status = "ERROR"
            return False

        with self._lock:
            try:
                self._ensure_event_loop()

                self.host = host
                self.port = int(port)
                self.client_id = int(client_id)

                if self.ib is None:
                    self.ib = IB()

                if not self.ib.isConnected():
                    self.ib.connect(
                        host=self.host,
                        port=self.port,
                        clientId=self.client_id,
                        timeout=timeout,
                    )

                if not self.ib.isConnected():
                    self.last_status = "DISCONNECTED"
                    self.last_error = (
                        "IBKR connection failed: "
                        "ib.isConnected() returned False"
                    )
                    return False

                # Bind events only after the socket is live.
                self._bind_events()

                # -------------------------------------------------
                # ACCOUNT / POSITION SYNC KICK
                # -------------------------------------------------
                try:
                    accounts = []

                    try:
                        accounts = list(self.ib.managedAccounts() or [])
                    except Exception:
                        accounts = []

                    if accounts:
                        self.account_id = str(accounts[0])

                        try:
                            self.ib.reqAccountUpdates(
                                True,
                                self.account_id,
                            )
                        except Exception as acct_exc:
                            self.last_error = (
                                f"Account update subscription failed: "
                                f"{acct_exc}"
                            )

                    try:
                        self.ib.reqPositions()
                    except Exception as pos_req_exc:
                        self.last_error = (
                            f"Position request failed after connect: "
                            f"{pos_req_exc}"
                        )

                    try:
                        self.ib.reqOpenOrders()
                    except Exception:
                        pass

                    try:
                        self.ib.sleep(2.0)
                    except Exception:
                        pass

                except Exception as sync_exc:
                    self.last_error = (
                        f"IBKR post-connect sync failed: {sync_exc}"
                    )

                # -------------------------------------------------
                # CACHE WARM-UP
                # -------------------------------------------------
                try:
                    self.refresh_positions()
                except Exception as exc:
                    self.last_error = (
                        f"Position refresh failed after connect: {exc}"
                    )

                try:
                    self.refresh_account_summary()
                except Exception as exc:
                    self.last_error = (
                        f"Account summary refresh failed after connect: {exc}"
                    )

                try:
                    self.refresh_open_orders()
                except Exception as exc:
                    self.last_error = (
                        f"Open orders refresh failed after connect: {exc}"
                    )

                self.last_status = "CONNECTED"

                if self.last_error and "failed after connect" not in self.last_error.lower():
                    pass
                else:
                    self.last_error = ""

                return True

            except Exception as exc:
                self.last_status = "ERROR"
                self.last_error = str(exc)
                return False

    def disconnect(self) -> bool:

        with self._lock:
            try:
                if self.ib is not None and self.ib.isConnected():

                    try:
                        account_id = getattr(self, "account_id", None)

                        if account_id:
                            self.ib.reqAccountUpdates(
                                False,
                                account_id,
                            )
                    except Exception:
                        pass

                    self.ib.disconnect()

                self.last_status = "DISCONNECTED"
                self.last_error = ""
                return True

            except Exception as exc:
                self.last_status = "ERROR"
                self.last_error = str(exc)
                return False

    def verify_connection(self) -> bool:
        try:
            return bool(
                self.ib is not None
                and self.ib.isConnected()
            )
        except Exception:
            return False

    def is_connected(self) -> bool:
        return self.verify_connection()

    @property
    def connected(self) -> bool:
        return self.verify_connection()

    def connection_status(self) -> Dict[str, Any]:

        broker_connected = self.verify_connection()

        status = "CONNECTED" if broker_connected else self.last_status

        if not status:
            status = "DISCONNECTED"

        return {
            "connected": broker_connected,
            "broker_connected": broker_connected,
            "ui_connected": False,
            "status": status,
            "mode": self.mode,
            "host": self.host,
            "port": self.port,
            "client_id": self.client_id,
            "account_id": getattr(self, "account_id", None),
            "error": self.last_error,
            "ib_import_error": IB_IMPORT_ERROR,
            "ib_available": IB is not None,
            "positions_count": len(self.positions_cache),
            "account_summary_rows": len(self.account_summary_cache),
            "open_orders_count": len(self.open_orders_cache),
            "execution_cache_count": len(self.execution_cache),
            "last_positions_refresh": self.last_positions_refresh,
            "last_account_refresh": self.last_account_refresh,
            "last_open_orders_refresh": self.last_open_orders_refresh,
            "truth_source": TRUTH_SOURCE,
        }
    
    # =====================================================
    # ORDERS
    # =====================================================

    def submit_order(
        self,
        order: Optional[Dict[str, Any]] = None,
        symbol: Optional[str] = None,
        qty: Optional[int] = None,
        side: Optional[str] = None,
        action: Optional[str] = None,
        order_type: str = "MKT",
        limit_price: Optional[float] = None,
        order_id: Optional[str] = None,
        exchange: str = "SMART",
        currency: str = "USD",
        **kwargs,
    ) -> Dict[str, Any]:

        if isinstance(order, dict):
            symbol = order.get("symbol", symbol)
            side = order.get("side") or order.get("action") or side or action
            qty = order.get("qty") or order.get("quantity") or qty
            order_type = order.get("order_type", order_type)
            limit_price = order.get("limit_price", limit_price)
            order_id = order.get("order_id", order_id)
            exchange = order.get("exchange", exchange)
            currency = order.get("currency", currency)

        if self.mode != LIVE:
            raise RuntimeError("IBKRLiveGateway only submits orders in LIVE mode")

        if not self.verify_connection():
            raise RuntimeError("IBKR broker is not connected")

        self._ensure_event_loop()

        symbol = str(symbol or "").upper().strip()
        side = str(side or action or "").upper().strip()
        order_type = str(order_type or "MKT").upper().strip()

        if order_type == "MARKET":
            order_type = "MKT"

        if order_type == "LIMIT":
            order_type = "LMT"

        qty = int(qty or 0)

        if not symbol:
            raise ValueError("Missing symbol")

        if side not in {"BUY", "SELL"}:
            raise ValueError(f"Invalid side: {side}")

        if qty <= 0:
            raise ValueError(f"Invalid qty: {qty}")

        contract = Stock(symbol, exchange, currency)

        if order_type == "MKT":
            ib_order = MarketOrder(side, qty)

        elif order_type == "LMT":
            if limit_price is None or float(limit_price) <= 0:
                raise ValueError("Limit order requires positive limit_price")

            ib_order = LimitOrder(side, qty, float(limit_price))

        else:
            raise ValueError(f"Unsupported order_type: {order_type}")

        trade = self.ib.placeOrder(contract, ib_order)

        try:
            self.ib.sleep(1.0)
        except Exception:
            pass

        broker_order_id = str(
            getattr(trade.order, "orderId", "") or ""
        ).strip()

        perm_id = str(
            getattr(trade.order, "permId", "") or ""
        ).strip()

        trade_status = getattr(trade, "orderStatus", None)

        raw_status = str(
            getattr(trade_status, "status", "") or "SUBMITTED"
        ).upper().strip()

        filled_qty = self._safe_float(
            getattr(trade_status, "filled", 0.0)
        )

        remaining_qty = self._safe_float(
            getattr(trade_status, "remaining", 0.0)
        )

        if filled_qty > 0 and remaining_qty == 0:
            broker_status = "FILLED"
        elif filled_qty > 0 and remaining_qty > 0:
            broker_status = "PARTIALLY_FILLED"
        else:
            broker_status = raw_status or "SUBMITTED"

        if not broker_order_id:
            raise RuntimeError("IBKR failed to assign broker order id")

        response = {
            "status": broker_status,
            "raw_status": raw_status,
            "order_id": order_id,
            "broker_order_id": broker_order_id,
            "broker_id": broker_order_id,
            "perm_id": perm_id,
            "permId": perm_id,
            "symbol": symbol,
            "action": side,
            "side": side,
            "qty": qty,
            "quantity": qty,
            "filled_qty": filled_qty,
            "remaining_qty": remaining_qty,
            "order_type": order_type,
            "limit_price": limit_price if order_type == "LMT" else None,
            "mode": self.mode,
            "timestamp": self._now(),
            "truth_source": TRUTH_SOURCE,
        }

        with self._lock:
            self.submitted_orders[broker_order_id] = response

            if order_id:
                self.broker_order_map[broker_order_id] = order_id

        return response

    def cancel_order(self, broker_order_id: str) -> bool:

        if not self.verify_connection():
            raise RuntimeError("IBKR broker is not connected")

        self._ensure_event_loop()

        broker_order_id = str(broker_order_id or "").strip()

        if not broker_order_id:
            return False

        try:
            candidates = []

            try:
                candidates.extend(list(self.ib.openTrades()))
            except Exception:
                pass

            try:
                candidates.extend(list(self.ib.trades()))
            except Exception:
                pass

            seen = set()

            for trade in candidates:
                order = getattr(trade, "order", None)

                if order is None:
                    continue

                oid = str(
                    getattr(order, "orderId", "") or ""
                ).strip()

                perm_id = str(
                    getattr(order, "permId", "") or ""
                ).strip()

                key = (oid, perm_id)

                if key in seen:
                    continue

                seen.add(key)

                if broker_order_id in {oid, perm_id}:
                    self.ib.cancelOrder(order)

                    try:
                        self.ib.sleep(1.0)
                    except Exception:
                        pass

                    try:
                        self.refresh_open_orders()
                    except Exception:
                        pass

                    return True

            try:
                self.refresh_open_orders()
            except Exception:
                pass

            return False

        except Exception as exc:
            self.last_error = str(exc)
            return False

    def refresh_open_orders(self) -> List[Dict[str, Any]]:
        """
        Refresh live IBKR order state into gateway cache.
        Includes freshly filled trades still present in ib.trades().
        """

        if not self.verify_connection():
            return list(self.open_orders_cache)

        self._ensure_event_loop()

        open_orders: List[Dict[str, Any]] = []

        try:
            candidates = []

            try:
                candidates.extend(list(self.ib.openTrades()))
            except Exception:
                pass

            try:
                candidates.extend(list(self.ib.trades()))
            except Exception:
                pass

            seen = set()

            for trade in candidates:
                try:
                    order = getattr(trade, "order", None)
                    contract = getattr(trade, "contract", None)
                    order_status = getattr(trade, "orderStatus", None)

                    if order is None:
                        continue

                    broker_order_id = str(
                        getattr(order, "orderId", "") or ""
                    ).strip()

                    perm_id = str(
                        getattr(order, "permId", "") or ""
                    ).strip()

                    symbol = str(
                        getattr(contract, "symbol", "") or ""
                    ).upper().strip()

                    action = str(
                        getattr(order, "action", "") or ""
                    ).upper().strip()

                    order_type = str(
                        getattr(order, "orderType", "") or ""
                    ).upper().strip()

                    total_qty = self._safe_float(
                        getattr(order, "totalQuantity", 0.0)
                    )

                    filled_qty = self._safe_float(
                        getattr(order_status, "filled", 0.0)
                    )

                    remaining_qty = self._safe_float(
                        getattr(order_status, "remaining", 0.0)
                    )

                    limit_price = self._safe_float(
                        getattr(order, "lmtPrice", 0.0)
                    )

                    avg_fill_price = self._safe_float(
                        getattr(order_status, "avgFillPrice", 0.0)
                    )

                    raw_status = str(
                        getattr(order_status, "status", "") or ""
                    ).upper().strip()

                    if filled_qty > 0 and remaining_qty == 0:
                        status = "FILLED"
                    elif filled_qty > 0 and remaining_qty > 0:
                        status = "PARTIALLY_FILLED"
                    elif raw_status:
                        status = raw_status
                    else:
                        status = "UNKNOWN"

                    if status in {
                        "CANCELLED",
                        "INACTIVE",
                        "API_CANCELLED",
                    }:
                        continue

                    key = (
                        broker_order_id,
                        perm_id,
                        symbol,
                        action,
                        total_qty,
                        filled_qty,
                        remaining_qty,
                    )

                    if key in seen:
                        continue

                    seen.add(key)

                    open_orders.append({
                        "broker_order_id": broker_order_id,
                        "broker_id": broker_order_id,
                        "perm_id": perm_id,
                        "permId": perm_id,
                        "symbol": symbol,
                        "action": action,
                        "side": action,
                        "qty": total_qty,
                        "quantity": total_qty,
                        "filled_qty": filled_qty,
                        "remaining_qty": remaining_qty,
                        "order_type": order_type,
                        "limit_price": limit_price,
                        "avg_fill_price": avg_fill_price,
                        "status": status,
                        "raw_status": raw_status,
                        "timestamp": self._now(),
                        "truth_source": TRUTH_SOURCE,
                    })

                except Exception:
                    pass

            self.open_orders_cache = list(open_orders)
            self.last_open_orders_refresh = self._now()

            return list(self.open_orders_cache)

        except Exception as exc:
            self.last_error = f"Open orders refresh failed: {exc}"
            return list(self.open_orders_cache)

    def open_orders(self) -> List[Dict[str, Any]]:
        try:
            return self.refresh_open_orders()
        except Exception:
            return list(self.open_orders_cache)

    def get_open_orders(self) -> List[Dict[str, Any]]:
        return self.open_orders()

    # =====================================================
    # POSITIONS / ACCOUNT
    # =====================================================

    def refresh_positions(self) -> Dict[str, float]:
        """
        Refresh IBKR positions into cache.

        Important:
        - First tries cached ib.positions()
        - Then requests positions if cache is empty
        - Sleeps briefly to let ib_insync process position callbacks
        - Never blocks the order submit path
        """

        if not self.verify_connection():
            return dict(self.positions_cache)

        self._ensure_event_loop()

        positions: Dict[str, float] = {}
        details: List[Dict[str, Any]] = []

        try:
            ib_positions = []

            # ---------------------------------------------
            # 1) READ CURRENT IB_INSYNC CACHE
            # ---------------------------------------------

            try:
                ib_positions = list(self.ib.positions() or [])
            except Exception as exc:
                self.last_error = f"Cached IB position read failed: {exc}"
                ib_positions = []

            # ---------------------------------------------
            # 2) FORCE POSITION REQUEST ONLY IF CACHE EMPTY
            # ---------------------------------------------

            if not ib_positions:
                try:
                    self.ib.reqPositions()

                    try:
                        self.ib.sleep(2.0)
                    except Exception:
                        pass

                    ib_positions = list(self.ib.positions() or [])

                except Exception as exc:
                    self.last_error = f"IB position request failed: {exc}"
                    ib_positions = []

            self.last_positions_raw_count = len(ib_positions)

            self.last_positions_raw_debug = []

            # ---------------------------------------------
            # 3) NORMALIZE
            # ---------------------------------------------

            for pos in ib_positions:
                try:
                    contract = getattr(pos, "contract", None)

                    symbol = str(
                        getattr(contract, "symbol", "") or ""
                    ).upper().strip()

                    if not symbol:
                        continue

                    quantity = self._safe_float(
                        getattr(pos, "position", 0.0)
                    )

                    avg_cost = self._safe_float(
                        getattr(pos, "avgCost", 0.0)
                    )

                    if abs(quantity) <= 0.000001:
                        continue

                    positions[symbol] = quantity

                    row = {
                        "account": getattr(pos, "account", ""),
                        "symbol": symbol,
                        "sec_type": getattr(contract, "secType", ""),
                        "exchange": getattr(contract, "exchange", ""),
                        "currency": getattr(contract, "currency", ""),
                        "position": quantity,
                        "qty": quantity,
                        "quantity": quantity,
                        "signed_qty": quantity,
                        "avg_cost": avg_cost,
                        "avgCost": avg_cost,
                        "con_id": getattr(contract, "conId", ""),
                        "timestamp": self._now(),
                        "truth_source": TRUTH_SOURCE,
                    }

                    details.append(row)
                    self.last_positions_raw_debug.append(row)

                except Exception as pos_exc:
                    self.last_error = f"Position normalize failed: {pos_exc}"

            # ---------------------------------------------
            # 4) CACHE UPDATE
            # ---------------------------------------------

            self.positions_cache = dict(positions)
            self.positions_detail_cache = list(details)
            self.last_positions_refresh = self._now()

            return dict(self.positions_cache)

        except Exception as exc:
            self.last_error = str(exc)
            return dict(self.positions_cache)

    def positions_snapshot(self) -> List[Dict[str, Any]]:
        try:
            if not self.positions_detail_cache:
                self.refresh_positions()

            return list(self.positions_detail_cache)

        except Exception:
            return list(self.positions_detail_cache)

    def get_positions(self) -> Dict[str, float]:
        try:
            if not self.positions_cache:
                self.refresh_positions()

            return dict(self.positions_cache)

        except Exception:
            return dict(self.positions_cache)

    def refresh_account_summary(self) -> List[Dict[str, Any]]:

        if not self.verify_connection():
            return list(self.account_summary_cache)

        self._ensure_event_loop()

        rows: List[Dict[str, Any]] = []

        try:
            try:
                account_values = list(self.ib.accountValues() or [])
            except Exception:
                account_values = []

            if not account_values:
                try:
                    self.ib.reqAccountSummary()
                    self.ib.sleep(2.0)
                    account_values = list(self.ib.accountValues() or [])
                except Exception:
                    account_values = []

            for item in account_values:
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
            self.last_error = f"Account summary refresh failed: {exc}"
            return list(self.account_summary_cache)

    def account_summary(self) -> List[Dict[str, Any]]:
        return list(self.account_summary_cache)

    def get_account_summary(self) -> List[Dict[str, Any]]:
        try:
            if not self.account_summary_cache:
                self.refresh_account_summary()

            return list(self.account_summary_cache)

        except Exception:
            return list(self.account_summary_cache)

    # =====================================================
    # EXECUTION CACHE / PERSISTENCE
    # =====================================================

    def _execution_cache_path(self) -> str:
        try:
            import os

            root = os.path.join(
                os.getcwd(),
                "runtime_state",
            )

            os.makedirs(
                root,
                exist_ok=True,
            )

            return os.path.join(
                root,
                "broker_execution_cache.json",
            )

        except Exception:
            return "broker_execution_cache.json"

    def _load_persisted_executions(self) -> None:
        try:
            import json
            import os

            path = self._execution_cache_path()

            if not os.path.exists(path):
                self.execution_detail_cache = list(
                    self.execution_cache.values()
                )
                self.fills_cache = list(self.execution_detail_cache)
                self.executions_cache = list(self.execution_detail_cache)
                return

            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)

            rows = payload.get("executions", [])

            if isinstance(rows, list):
                for row in rows:
                    if not isinstance(row, dict):
                        continue

                    exec_id = str(
                        row.get("exec_id")
                        or row.get("execution_id")
                        or ""
                    ).strip()

                    if not exec_id:
                        continue

                    self.execution_cache[exec_id] = dict(row)

            self.execution_detail_cache = list(
                self.execution_cache.values()
            )
            self.fills_cache = list(self.execution_detail_cache)
            self.executions_cache = list(self.execution_detail_cache)

        except Exception as exc:
            self.last_error = f"Load persisted executions failed: {exc}"

    def _persist_executions(self) -> None:
        try:
            import json

            payload = {
                "saved_at": self._now(),
                "truth_source": TRUTH_SOURCE,
                "count": len(self.execution_cache),
                "executions": list(self.execution_cache.values()),
            }

            with open(
                self._execution_cache_path(),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    payload,
                    handle,
                    indent=2,
                    default=str,
                )

        except Exception as exc:
            self.last_error = f"Persist executions failed: {exc}"

    def _cache_execution_event(self, event: Dict[str, Any]) -> bool:
        try:
            if not isinstance(event, dict):
                return False

            exec_id = str(
                event.get("exec_id")
                or event.get("execution_id")
                or ""
            ).strip()

            if not exec_id:
                exec_id = (
                    f"{event.get('symbol')}|"
                    f"{event.get('side')}|"
                    f"{event.get('qty')}|"
                    f"{event.get('price')}|"
                    f"{event.get('timestamp')}"
                )

                event["exec_id"] = exec_id
                event["execution_id"] = exec_id

            already_seen = exec_id in self.execution_cache

            event["dedupe_key"] = exec_id
            event["persisted"] = True
            event["cached_at"] = event.get("cached_at") or self._now()

            self.execution_cache[exec_id] = dict(event)

            self.execution_detail_cache = list(
                self.execution_cache.values()
            )
            self.fills_cache = list(self.execution_detail_cache)
            self.executions_cache = list(self.execution_detail_cache)

            self._persist_executions()

            return not already_seen

        except Exception as exc:
            self.last_error = f"Execution cache update failed: {exc}"
            return False

    # =====================================================
    # EXECUTION NORMALIZATION
    # =====================================================

    def _normalize_ib_fill_event(
        self,
        trade,
        fill=None,
    ) -> Dict[str, Any]:

        if fill is None:
            fill = trade
            trade = None

        execution = getattr(fill, "execution", None)
        contract = getattr(fill, "contract", None)

        order = None

        if trade is not None:
            order = getattr(trade, "order", None)

        broker_order_id = str(
            getattr(execution, "orderId", "")
            or getattr(order, "orderId", "")
            or ""
        ).strip()

        perm_id = str(
            getattr(execution, "permId", "")
            or getattr(order, "permId", "")
            or ""
        ).strip()

        exec_id = str(
            getattr(execution, "execId", "") or ""
        ).strip()

        symbol = str(
            getattr(contract, "symbol", "") or ""
        ).upper().strip()

        side = str(
            getattr(execution, "side", "")
            or getattr(order, "action", "")
            or ""
        ).upper().strip()

        if side == "BOT":
            side = "BUY"
        elif side == "SLD":
            side = "SELL"

        shares = self._safe_float(
            getattr(execution, "shares", 0)
        )

        price = self._safe_float(
            getattr(execution, "price", 0)
        )

        timestamp = (
            str(getattr(execution, "time", "") or "")
            or self._now()
        )

        return {
            "event": "EXECUTION_FILL",
            "execution_id": exec_id,
            "exec_id": exec_id,
            "broker_order_id": broker_order_id,
            "broker_id": broker_order_id,
            "perm_id": perm_id,
            "permId": perm_id,
            "order_id": self.broker_order_map.get(
                broker_order_id,
                broker_order_id,
            ),
            "symbol": symbol,
            "action": side,
            "side": side,
            "qty": shares,
            "quantity": shares,
            "filled_qty": shares,
            "fill_qty": shares,
            "execution_qty": shares,
            "price": price,
            "fill_price": price,
            "execution_price": price,
            "avg_fill_price": price,
            "status": "FILLED",
            "execution_status": "FILLED",
            "order_status": "FILLED",
            "timestamp": timestamp,
            "cached_at": self._now(),
            "mode": LIVE,
            "source": "ibkr_live_gateway",
            "is_true_fill": True,
            "truth_source": TRUTH_SOURCE,
        }

    def _normalize_recovered_execution(
        self,
        recovered_fill,
    ) -> Dict[str, Any]:

        if isinstance(recovered_fill, dict):
            return dict(recovered_fill)

        return self._normalize_ib_fill_event(
            recovered_fill,
            None,
        )

    # =====================================================
    # EVENT BINDING
    # =====================================================

    def _bind_events(self) -> None:
        if self.ib is None:
            return

        bindings = (
            ("orderStatusEvent", self._handle_order_status),
            ("execDetailsEvent", self._handle_exec_details),
            ("errorEvent", self._handle_error),
            ("disconnectedEvent", self._handle_disconnect),
        )

        for event_name, handler in bindings:
            try:
                event = getattr(self.ib, event_name)
                event -= handler
            except Exception:
                pass

        for event_name, handler in bindings:
            try:
                event = getattr(self.ib, event_name)
                event += handler
            except Exception as exc:
                self.last_error = (
                    f"IB event bind failed for {event_name}: {exc}"
                )

        self._events_bound = True

    def _handle_order_status(self, *args) -> None:
        try:
            trade = args[0] if args else None

            order = getattr(trade, "order", None)
            status = getattr(trade, "orderStatus", None)
            contract = getattr(trade, "contract", None)

            broker_order_id = str(
                getattr(order, "orderId", "") or ""
            ).strip()

            perm_id = str(
                getattr(order, "permId", "") or ""
            ).strip()

            symbol = str(
                getattr(contract, "symbol", "") or ""
            ).upper().strip()

            filled_qty = self._safe_float(
                getattr(status, "filled", 0)
            )

            remaining_qty = self._safe_float(
                getattr(status, "remaining", 0)
            )

            raw_status = str(
                getattr(status, "status", "") or ""
            ).upper().strip()

            if filled_qty > 0 and remaining_qty == 0:
                order_status = "FILLED"
            elif filled_qty > 0 and remaining_qty > 0:
                order_status = "PARTIALLY_FILLED"
            else:
                order_status = raw_status

            event = {
                "event": "ORDER_STATUS",
                "broker_order_id": broker_order_id,
                "broker_id": broker_order_id,
                "perm_id": perm_id,
                "permId": perm_id,
                "order_id": self.broker_order_map.get(
                    broker_order_id,
                    broker_order_id,
                ),
                "symbol": symbol,
                "status": order_status,
                "raw_status": raw_status,
                "filled_qty": filled_qty,
                "remaining_qty": remaining_qty,
                "avg_fill_price": self._safe_float(
                    getattr(status, "avgFillPrice", 0)
                ),
                "timestamp": self._now(),
                "truth_source": TRUTH_SOURCE,
            }

            try:
                self.refresh_open_orders()
            except Exception:
                pass

            for callback in list(self.order_callbacks):
                try:
                    callback(event)
                except Exception as cb_exc:
                    self.last_error = (
                        f"Order status callback failed: {cb_exc}"
                    )

        except Exception as exc:
            self.last_error = f"orderStatus handler failed: {exc}"

    def _handle_exec_details(self, *args) -> None:
        try:
            trade = None
            fill = None

            for arg in args:
                if hasattr(arg, "execution") and hasattr(arg, "contract"):
                    fill = arg
                elif hasattr(arg, "order") and hasattr(arg, "contract"):
                    trade = arg

            if fill is None:
                return

            event = self._normalize_ib_fill_event(
                trade,
                fill,
            )

            is_new_execution = self._cache_execution_event(event)

            if not is_new_execution:
                return

            self.last_error = (
                f"EXEC CALLBACK FIRED + PERSISTED: "
                f"{event.get('symbol')} "
                f"{event.get('side')} "
                f"{event.get('qty')} @ {event.get('price')} "
                f"exec_id={event.get('exec_id')} "
                f"broker_order_id={event.get('broker_order_id')}"
            )

            for callback in list(self.fill_callbacks):
                try:
                    callback(event)
                except Exception as cb_exc:
                    self.last_error = f"Fill callback failed: {cb_exc}"

        except Exception as exc:
            self.last_error = f"execDetails handler failed: {exc}"

    # =====================================================
    # EXECUTION RECOVERY
    # =====================================================

    def recover_broker_executions(
        self,
        timeout_seconds: float = 8.0,
    ) -> List[Dict[str, Any]]:

        report = self.recover_executions_from_broker(
            timeout_seconds=timeout_seconds,
        )

        self.last_execution_recovery_report = dict(report)

        return list(
            getattr(self, "execution_detail_cache", [])
        )

    def recover_executions_from_broker(
        self,
        timeout_seconds: float = 8.0,
    ) -> Dict[str, Any]:

        report = {
            "status": "STARTED",
            "requested_at": self._now(),
            "recovered": 0,
            "new": 0,
            "duplicates": 0,
            "errors": [],
            "truth_source": TRUTH_SOURCE,
        }

        if self._execution_recovery_running:
            report["status"] = "ALREADY_RUNNING"
            report["errors"].append("Execution recovery already running")
            self.last_execution_recovery_report = dict(report)
            return report

        if ExecutionFilter is None:
            report["status"] = "UNSUPPORTED"
            report["errors"].append("ExecutionFilter unavailable")
            self.last_execution_recovery_report = dict(report)
            return report

        if not self.verify_connection():
            report["status"] = "DISCONNECTED"
            report["errors"].append("IBKR gateway not connected")
            self.last_execution_recovery_report = dict(report)
            return report

        self._execution_recovery_running = True
        self.last_error = ""

        try:
            recovered_events: List[Dict[str, Any]] = []
            seen_exec_ids = set()

            # =====================================================
            # FIRST: READ IB'S CURRENT LOCAL FILL CACHE
            # This catches fills already delivered to this client.
            # =====================================================

            try:
                cached_fills = list(self.ib.fills() or [])

                for fill in cached_fills:
                    try:
                        event = self._normalize_ib_fill_event(
                            None,
                            fill,
                        )

                        exec_id = str(
                            event.get("exec_id")
                            or event.get("execution_id")
                            or ""
                        ).strip()

                        if exec_id and exec_id in seen_exec_ids:
                            continue

                        if exec_id:
                            seen_exec_ids.add(exec_id)

                        recovered_events.append(event)

                    except Exception as exc:
                        report["errors"].append(
                            f"cached_fill_normalize: {exc}"
                        )

            except Exception as exc:
                report["errors"].append(
                    f"ib.fills cache read failed: {exc}"
                )

            # =====================================================
            # SECOND: REQUEST BROKER EXECUTIONS BY CALLBACK
            # Do not block on ib.reqExecutions().
            # =====================================================

            done = threading.Event()
            worker_error = {"value": ""}

            def on_exec_details(*args) -> None:
                try:
                    trade = None
                    fill = None

                    for arg in args:
                        if hasattr(arg, "execution") and hasattr(arg, "contract"):
                            fill = arg
                        elif hasattr(arg, "order") and hasattr(arg, "contract"):
                            trade = arg

                    if fill is None:
                        return

                    event = self._normalize_ib_fill_event(
                        trade,
                        fill,
                    )

                    exec_id = str(
                        event.get("exec_id")
                        or event.get("execution_id")
                        or ""
                    ).strip()

                    if exec_id and exec_id in seen_exec_ids:
                        return

                    if exec_id:
                        seen_exec_ids.add(exec_id)

                    recovered_events.append(event)

                except Exception as exc:
                    report["errors"].append(
                        f"execDetails normalize: {exc}"
                    )

            try:
                self.ib.execDetailsEvent += on_exec_details
            except Exception as exc:
                report["status"] = "ERROR"
                report["errors"].append(
                    f"Could not attach execDetailsEvent: {exc}"
                )
                self.last_execution_recovery_report = dict(report)
                return report

            def worker() -> None:
                try:
                    execution_filter = ExecutionFilter()
                    req_id = self.ib.client.getReqId()

                    self.ib.client.reqExecutions(
                        req_id,
                        execution_filter,
                    )

                    done.wait(timeout_seconds)

                except Exception as exc:
                    worker_error["value"] = str(exc)

            thread = threading.Thread(
                target=worker,
                daemon=True,
            )

            thread.start()
            thread.join(timeout_seconds + 1.0)

            done.set()

            try:
                self.ib.execDetailsEvent -= on_exec_details
            except Exception:
                pass

            if worker_error["value"]:
                report["errors"].append(worker_error["value"])

            # =====================================================
            # CACHE EVERYTHING RECOVERED
            # =====================================================

            for event in recovered_events:
                try:
                    is_new = self._cache_execution_event(event)

                    report["recovered"] += 1

                    if is_new:
                        report["new"] += 1
                    else:
                        report["duplicates"] += 1

                    for callback in list(self.fill_callbacks):
                        try:
                            callback(event)
                        except Exception as cb_exc:
                            report["errors"].append(
                                f"fill_callback: {cb_exc}"
                            )

                except Exception as exc:
                    report["errors"].append(
                        f"cache_recovered_execution: {exc}"
                    )

            report["status"] = "OK"
            report["cache_count"] = len(self.execution_cache)
            report["completed_at"] = self._now()

            self.execution_detail_cache = list(
                self.execution_cache.values()
            )
            self.fills_cache = list(self.execution_detail_cache)
            self.executions_cache = list(self.execution_detail_cache)

            self.last_execution_recovery_report = dict(report)

            self.last_error = (
                f"Execution recovery OK: "
                f"recovered={report['recovered']} "
                f"new={report['new']} "
                f"duplicates={report['duplicates']}"
            )

            return report

        except Exception as exc:
            report["status"] = "ERROR"
            report["errors"].append(str(exc))
            report["completed_at"] = self._now()

            self.last_execution_recovery_report = dict(report)
            self.last_error = f"Execution recovery failed: {exc}"

            return report

        finally:
            self._execution_recovery_running = False

    # =====================================================
    # EXECUTION GETTERS
    # =====================================================

    def get_executions(self) -> List[Dict[str, Any]]:
        try:
            if not self.execution_cache:
                self._load_persisted_executions()

            return list(self.execution_cache.values())

        except Exception as exc:
            self.last_error = f"Execution cache read failed: {exc}"
            return []

    def fills_snapshot(self) -> List[Dict[str, Any]]:
        return self.get_executions()

    def execution_cache_status(self) -> Dict[str, Any]:
        try:
            executions = self.get_executions()

            return {
                "status": "READY",
                "count": len(executions),
                "path": self._execution_cache_path(),
                "last_recovery": self.last_execution_recovery_report,
                "truth_source": TRUTH_SOURCE,
                "checked_at": self._now(),
            }

        except Exception as exc:
            return {
                "status": "ERROR",
                "count": 0,
                "error": str(exc),
                "truth_source": TRUTH_SOURCE,
                "checked_at": self._now(),
            }

    # =====================================================
    # CALLBACK REGISTRATION
    # =====================================================

    def on_order_update(
        self,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        if callable(callback):
            self.order_callbacks.append(callback)

    def on_fill(
        self,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        if callable(callback):
            self.fill_callbacks.append(callback)

    def on_error(
        self,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        if callable(callback):
            self.error_callbacks.append(callback)

    # =====================================================
    # ERROR / DISCONNECT HANDLERS
    # =====================================================

    def _handle_error(
        self,
        req_id=None,
        error_code=None,
        error_string="",
        contract=None,
        *args,
        **kwargs,
    ) -> None:

        event = {
            "event": "IBKR_ERROR",
            "req_id": req_id,
            "error_code": error_code,
            "error": str(error_string),
            "contract": str(contract) if contract is not None else "",
            "timestamp": self._now(),
            "truth_source": TRUTH_SOURCE,
        }

        self.last_error = str(error_string)

        for callback in list(self.error_callbacks):
            try:
                callback(event)
            except Exception as cb_exc:
                self.last_error = f"Error callback failed: {cb_exc}"

    def _handle_disconnect(
        self=None,
        *args,
        **kwargs,
    ) -> None:

        if self is None:
            return

        try:
            self.last_status = "DISCONNECTED"

            event = {
                "event": "DISCONNECTED",
                "timestamp": self._now(),
                "truth_source": TRUTH_SOURCE,
            }

            for callback in list(self.error_callbacks):
                try:
                    callback(event)
                except Exception as cb_exc:
                    self.last_error = f"Disconnect callback failed: {cb_exc}"

        except Exception:
            pass


# Backward-compatible alias
IBKRGatewayLive = IBKRLiveGateway