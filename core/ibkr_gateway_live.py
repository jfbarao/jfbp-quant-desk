# =========================================================
# 📡 IBKR LIVE GATEWAY — INSTITUTIONAL TRUTH ADAPTER v1.5
# LIVE CONNECTIVITY + ACCOUNT / POSITIONS / ORDER TRUTH
# =========================================================

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
import threading
import asyncio


# =========================================================
# STREAMLIT / IB_INSYNC EVENT LOOP FIX
# Must happen BEFORE importing ib_insync.
# =========================================================

try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())


try:
    from ib_insync import IB, Stock, MarketOrder, LimitOrder
    IB_IMPORT_ERROR = ""
except Exception as exc:
    IB = None
    Stock = None
    MarketOrder = None
    LimitOrder = None
    IB_IMPORT_ERROR = str(exc)


SIM = "SIM"
LIVE = "LIVE"
BACKTEST = "BACKTEST"

TRUTH_SOURCE = "ibkr_live_gateway.v1_5"


class IBKRLiveGateway:
    """
    Institutional LIVE-only IBKR gateway.

    Rules:
    - No fake fills.
    - No demo quotes.
    - No UI-connected shortcut.
    - Broker connection truth comes only from ib.isConnected().
    - Orders are submitted to IBKR and fills must come back through callbacks.
    """

    def __init__(self, mode: str = LIVE):
        self.mode = str(mode or LIVE).upper()

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

        self.last_positions_refresh: str = ""
        self.last_account_refresh: str = ""
        self.last_open_orders_refresh: str = ""

        self._lock = threading.RLock()

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
                raise RuntimeError(
                    "Current asyncio event loop is closed"
                )

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

                    if hasattr(self, "_bind_events"):
                        self._bind_events()

                if self.ib.isConnected():
                    self.last_status = "CONNECTED"
                    self.last_error = ""
                    return True

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

                self.last_status = "CONNECTED"
                self.last_error = ""

                try:
                    self.refresh_positions()
                except Exception as exc:
                    self.last_error = f"Position refresh failed after connect: {exc}"

                try:
                    self.refresh_account_summary()
                except Exception as exc:
                    self.last_error = f"Account summary refresh failed after connect: {exc}"

                try:
                    self.refresh_open_orders()
                except Exception as exc:
                    self.last_error = f"Open orders refresh failed after connect: {exc}"

                return True

            except Exception as exc:
                self.last_status = "ERROR"
                self.last_error = str(exc)
                return False

    def disconnect(self) -> bool:
        with self._lock:
            try:
                if self.ib is not None and self.ib.isConnected():
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
            return bool(self.ib is not None and self.ib.isConnected())
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
            "error": self.last_error,
            "ib_import_error": IB_IMPORT_ERROR,
            "ib_available": IB is not None,
            "positions_count": len(self.positions_cache),
            "account_summary_rows": len(self.account_summary_cache),
            "open_orders_count": len(self.open_orders_cache),
            "last_positions_refresh": self.last_positions_refresh,
            "last_account_refresh": self.last_account_refresh,
            "last_open_orders_refresh": self.last_open_orders_refresh,
            "truth_source": TRUTH_SOURCE,
        }

    # =====================================================
    # CALLBACK REGISTRATION
    # =====================================================

    def on_order_update(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        if callable(callback):
            self.order_callbacks.append(callback)

    def on_fill(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        if callable(callback):
            self.fill_callbacks.append(callback)

    def on_error(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        if callable(callback):
            self.error_callbacks.append(callback)

        # =====================================================
    # ORDERS
    # =====================================================

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

        if self.mode != LIVE:
            raise RuntimeError("IBKRLiveGateway only submits orders in LIVE mode")

        if not self.verify_connection():
            raise RuntimeError("IBKR broker is not connected")

        self._ensure_event_loop()

        symbol = str(symbol or "").upper().strip()
        side = str(side or "").upper().strip()
        order_type = str(order_type or "MKT").upper().strip()

        qty = int(qty)

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

        # Let IBKR assign a stable broker order id before mapping it.
        try:
            self.ib.sleep(0.75)
        except Exception:
            pass

        broker_order_id = str(
            getattr(trade.order, "orderId", "") or ""
        ).strip()

        perm_id = str(
            getattr(trade.order, "permId", "") or ""
        ).strip()

        if not broker_order_id:
            raise RuntimeError(
                "IBKR failed to assign broker order id"
            )

        response = {
            "status": "SUBMITTED",
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
            "order_type": order_type,
            "limit_price": limit_price,
            "mode": self.mode,
            "timestamp": self._now(),
            "trade": trade,
            "truth_source": TRUTH_SOURCE,
        }

        with self._lock:
            self.submitted_orders[broker_order_id] = response

            if order_id:
                self.broker_order_map[broker_order_id] = order_id

        # Critical for Streamlit + ib_insync:
        # allow orderStatusEvent / execDetailsEvent callbacks to flush.
        try:
            self.ib.sleep(2.0)
        except Exception:
            pass

        self.refresh_positions()
        self.refresh_open_orders()

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
                    getattr(order, "orderId", "")
                    or ""
                ).strip()

                perm_id = str(
                    getattr(order, "permId", "")
                    or ""
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

                    self.refresh_open_orders()
                    return True

            self.refresh_open_orders()
            return False

        except Exception as exc:
            self.last_error = str(exc)
            return False

def refresh_positions(self) -> Dict[str, float]:

    if not self.verify_connection():
        return dict(self.positions_cache)

    self._ensure_event_loop()

    positions: Dict[str, float] = {}
    details: List[Dict[str, Any]] = []

    try:

        # =====================================================
        # FORCE IB SYNC
        # =====================================================

        ib_positions = []

        try:
            ib_positions = list(self.ib.reqPositions())
        except Exception as exc:
            self.last_error = f"Direct IB position request failed: {exc}"
            ib_positions = []

        if not ib_positions:
            try:
                self.ib.sleep(3.0)
                ib_positions = list(self.ib.positions())
            except Exception as exc:
                self.last_error = f"Cached IB position read failed: {exc}"
                ib_positions = []

        # =====================================================
        # DEBUG TRACE
        # =====================================================

        self.last_positions_raw_count = len(ib_positions)

        try:
            self.last_positions_raw_debug = [
                {
                    "account": getattr(pos, "account", ""),
                    "symbol": str(
                        getattr(getattr(pos, "contract", None), "symbol", "")
                        or ""
                    ).upper().strip(),
                    "sec_type": getattr(
                        getattr(pos, "contract", None),
                        "secType",
                        "",
                    ),
                    "exchange": getattr(
                        getattr(pos, "contract", None),
                        "exchange",
                        "",
                    ),
                    "currency": getattr(
                        getattr(pos, "contract", None),
                        "currency",
                        "",
                    ),
                    "position": float(getattr(pos, "position", 0.0) or 0.0),
                    "avg_cost": float(getattr(pos, "avgCost", 0.0) or 0.0),
                }
                for pos in ib_positions
            ]

            print("IB_POSITIONS_COUNT:", self.last_positions_raw_count)
            print("IB_POSITIONS_RAW:", self.last_positions_raw_debug)

        except Exception as exc:
            self.last_error = f"IB position debug trace failed: {exc}"

        # =====================================================
        # PARSE POSITIONS
        # =====================================================

        for pos in ib_positions:

            contract = getattr(pos, "contract", None)

            symbol = str(
                getattr(contract, "symbol", "") or ""
            ).upper().strip()

            if not symbol:
                continue

            quantity = float(
                getattr(pos, "position", 0.0) or 0.0
            )

            avg_cost = float(
                getattr(pos, "avgCost", 0.0) or 0.0
            )

            positions[symbol] = quantity

            details.append({
                "account": getattr(pos, "account", ""),
                "symbol": symbol,
                "sec_type": getattr(contract, "secType", ""),
                "exchange": getattr(contract, "exchange", ""),
                "currency": getattr(contract, "currency", ""),
                "position": quantity,
                "avg_cost": avg_cost,
                "con_id": getattr(contract, "conId", ""),
                "timestamp": self._now(),
                "truth_source": TRUTH_SOURCE,
            })

        # =====================================================
        # CACHE UPDATE
        # =====================================================

        self.positions_cache = dict(positions)
        self.positions_detail_cache = list(details)
        self.last_positions_refresh = self._now()

        return dict(self.positions_cache)

    except Exception as exc:

        self.last_error = str(exc)

        return dict(self.positions_cache)
    # =====================================================
    # IBKR EVENT BINDING
    # =====================================================

    def _bind_events(self) -> None:
        if self.ib is None:
            return

        # Remove stale/dead callbacks before rebinding.
        # This prevents shutdown errors from old weakrefs after Streamlit reloads.
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
                self.last_error = f"IB event bind failed for {event_name}: {exc}"

    def _handle_order_status(self, trade) -> None:
        try:
            order = getattr(trade, "order", None)
            status = getattr(trade, "orderStatus", None)
            contract = getattr(trade, "contract", None)

            broker_order_id = str(
                getattr(order, "orderId", "")
                or ""
            ).strip()

            perm_id = str(
                getattr(order, "permId", "")
                or ""
            ).strip()

            symbol = str(
                getattr(contract, "symbol", "")
                or ""
            ).upper().strip()

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

                "status": str(
                    getattr(status, "status", "")
                    or ""
                ).upper().strip(),

                "filled_qty": self._safe_float(
                    getattr(status, "filled", 0)
                ),
                "remaining_qty": self._safe_float(
                    getattr(status, "remaining", 0)
                ),
                "avg_fill_price": self._safe_float(
                    getattr(status, "avgFillPrice", 0)
                ),

                "timestamp": self._now(),
                "truth_source": TRUTH_SOURCE,
            }

            self.last_error = (
                f"ORDER STATUS CALLBACK FIRED: "
                f"{symbol} {event.get('status')} "
                f"broker_order_id={broker_order_id}"
            )

            self.refresh_open_orders()

            for callback in list(self.order_callbacks):
                try:
                    callback(event)
                except Exception as cb_exc:
                    self.last_error = (
                        f"Order status callback failed: {cb_exc}"
                    )

        except Exception as exc:
            self.last_error = f"orderStatus handler failed: {exc}"

    def _handle_exec_details(self, trade, fill) -> None:
        try:
            execution = getattr(fill, "execution", None)
            contract = getattr(fill, "contract", None)
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
                getattr(execution, "execId", "")
                or ""
            ).strip()

            symbol = str(
                getattr(contract, "symbol", "")
                or ""
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

            shares = self._safe_int(
                getattr(execution, "shares", 0)
            )

            price = self._safe_float(
                getattr(execution, "price", 0)
            )

            event = {
                "event": "EXECUTION_FILL",

                "execution_id": exec_id,
                "exec_id": exec_id,

                "broker_order_id": broker_order_id,
                "broker_id": broker_order_id,

                "perm_id": perm_id,
                "permId": perm_id,

                "order_id": self.broker_order_map.get(broker_order_id),

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

                "timestamp": self._now(),
                "mode": LIVE,
                "source": "ibkr_live_gateway",
                "is_true_fill": True,
                "truth_source": TRUTH_SOURCE,
            }

            self.last_error = (
                f"EXEC CALLBACK FIRED: "
                f"{symbol} {side} {shares} @ {price} "
                f"exec_id={exec_id} "
                f"broker_order_id={broker_order_id}"
            )

            self.refresh_positions()
            self.refresh_open_orders()

            for callback in list(self.fill_callbacks):
                try:
                    callback(event)
                except Exception as cb_exc:
                    self.last_error = f"Fill callback failed: {cb_exc}"

        except Exception as exc:
            self.last_error = f"execDetails handler failed: {exc}"

    def _handle_error(
        self,
        req_id,
        error_code,
        error_string,
        contract=None,
        *args,
    ) -> None:
        event = {
            "event": "IBKR_ERROR",
            "req_id": req_id,
            "error_code": error_code,
            "error": error_string,
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

    def _handle_disconnect(self, *args, **kwargs) -> None:
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

    # =====================================================
    # HELPERS
    # =====================================================

    def _safe_float(self, value: Any) -> float:
        try:
            if value is None:
                return 0.0
            return float(value)
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


# Backward-compatible alias
IBKRGatewayLive = IBKRLiveGateway