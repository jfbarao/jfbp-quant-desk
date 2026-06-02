# =========================================================
# 🧠 IBKR GATEWAY v3.4 — REAL IBKR CONNECTION + CALLBACKS
# LIVE MARKET DATA SUBSCRIPTION FIX
# LIVE-READY SAFE
# =========================================================

from __future__ import annotations

import time
from typing import Dict, Any, Optional, List, Callable

import pandas as pd


# =========================================================
# MODES
# =========================================================

SIM = "SIM"
LIVE = "LIVE"
BACKTEST = "BACKTEST"


# =========================================================
# 🧠 IBKR GATEWAY
# =========================================================

class IBKRGateway:

    def __init__(self, mode: str = SIM):

        self.mode = str(mode).upper()

        self.ui_connected = False
        self.broker_connected = False

        self.host: Optional[str] = None
        self.port: Optional[int] = None
        self.client_id: int = 7

        self.last_error: Optional[str] = None
        self.ib_client = None

        self.market_data = None

        self.positions: Dict[str, float] = {}
        self.last_quotes: Dict[str, Dict[str, Any]] = {}
        self.market_subscriptions: Dict[str, Any] = {}

        self.fill_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.order_callbacks: List[Callable[[Dict[str, Any]], None]] = []

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
        if callable(callback):
            self.fill_callbacks.append(callback)

    def on_order_update(self, callback):
        if callable(callback):
            self.order_callbacks.append(callback)

    def _emit_fill(self, fill: Dict[str, Any]) -> None:
        for callback in list(self.fill_callbacks):
            try:
                callback(fill)
            except Exception as exc:
                self.last_error = f"Fill callback failed: {exc}"

    def _emit_order_update(self, event: Dict[str, Any]) -> None:
        for callback in list(self.order_callbacks):
            try:
                callback(event)
            except Exception as exc:
                self.last_error = f"Order callback failed: {exc}"

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

        # =====================================================
    # CONNECTION
    # =====================================================

    def connect(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 7,
    ) -> bool:

        try:
            from ib_insync import IB

            self.host = host
            self.port = int(port)
            self.client_id = int(client_id)

            if self.ib_client is None:
                self.ib_client = IB()

            if not self.ib_client.isConnected():
                self.ib_client.connect(
                    host=self.host,
                    port=self.port,
                    clientId=self.client_id,
                    timeout=10,
                )

            # Prefer delayed market data, but do not request quotes here.
            # Connect must stay fast and socket-only.
            try:
                self.ib_client.reqMarketDataType(3)
                self.market_data_type = 3
            except Exception as exc:
                self.last_error = f"Delayed market data request failed: {exc}"

            self.ui_connected = True
            self.broker_connected = self.verify_connection()

            self._bind_ib_events()

            # IMPORTANT:
            # Do NOT call refresh_all() during connect.
            # refresh_all() may request market/account/position data and can make
            # Live IBKR / Portfolio pages hang while IBKR resolves tickers.
            self.last_error = ""

            return self.broker_connected

        except Exception as exc:
            self.last_error = str(exc)
            self.ui_connected = False
            self.broker_connected = False
            return False

    def disconnect(self) -> bool:

        try:
            if self.ib_client is not None and self.ib_client.isConnected():

                for symbol, ticker in list(self.market_subscriptions.items()):
                    try:
                        self.ib_client.cancelMktData(ticker.contract)
                    except Exception:
                        pass

                self.market_subscriptions = {}
                self.ib_client.disconnect()

        except Exception:
            pass

        self.ui_connected = False
        self.broker_connected = False
        self.host = None
        self.port = None
        self.client_id = None
        self.last_error = ""
        return True

    def verify_connection(self) -> bool:
        try:
            if self.ib_client is None:
                return False

            is_connected = getattr(self.ib_client, "isConnected", None)

            if callable(is_connected):
                return bool(is_connected())

            return False

        except Exception:
            return False

    def _bind_ib_events(self) -> None:

        if self.ib_client is None:
            return

        try:
            self.ib_client.execDetailsEvent -= self._on_exec_details
        except Exception:
            pass

        try:
            self.ib_client.orderStatusEvent -= self._on_order_status
        except Exception:
            pass

        try:
            self.ib_client.positionEvent -= self._on_position
        except Exception:
            pass

        try:
            self.ib_client.execDetailsEvent += self._on_exec_details
            self.ib_client.orderStatusEvent += self._on_order_status
            self.ib_client.positionEvent += self._on_position
        except Exception as exc:
            self.last_error = f"IB event bind failed: {exc}"

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

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value or default)
        except Exception:
            return default

    def _safe_str(self, value: Any) -> str:
        try:
            return str(value or "").strip()
        except Exception:
            return ""

    def _on_exec_details(self, trade, fill):

        try:
            contract = getattr(fill, "contract", None)
            execution = getattr(fill, "execution", None)

            if execution is None:
                self.last_error = "execDetails ignored: missing execution object"
                return

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
                "symbol": symbol,
                "action": action,
                "side": action,
                "qty": qty,
                "filled_qty": qty,
                "fill_qty": qty,
                "price": price,
                "fill_price": price,
                "execution_price": price,
                "avg_fill_price": price,
                "execution_id": exec_id,
                "exec_id": exec_id,
                "order_id": order_id,
                "broker_order_id": order_id,
                "perm_id": perm_id,
                "account": account,
                "exchange": exchange,
                "currency": currency,
                "sec_type": sec_type,
                "status": "FILLED",
                "execution_status": "FILLED",
                "ib_time": str(fill_time or ""),
                "source": "ibkr_execDetailsEvent",
                "mode": self.mode,
                "timestamp": time.time(),
            }

            if not row["symbol"]:
                self.last_error = f"execDetails ignored: missing symbol | exec_id={exec_id}"
                return

            if row["side"] not in ("BUY", "SELL"):
                self.last_error = f"execDetails ignored: invalid side {row['side']} | exec_id={exec_id}"
                return

            if row["qty"] <= 0:
                self.last_error = f"execDetails ignored: invalid qty {row['qty']} | exec_id={exec_id}"
                return

            if row["price"] <= 0:
                self.last_error = f"execDetails ignored: invalid price {row['price']} | exec_id={exec_id}"
                return

            self.update_quote(symbol, price)
            self._emit_fill(row)

            try:
                self.refresh_positions()
                self.subscribe_market_data(list(self.positions.keys()))
                self.refresh_market_data()
            except Exception as exc:
                self.last_error = f"fill emitted but refresh_positions failed: {exc}"

        except Exception as exc:
            self.last_error = f"execDetails handler failed: {exc}"

    def _on_order_status(self, trade):

        try:
            order = getattr(trade, "order", None)
            status = getattr(trade, "orderStatus", None)
            contract = getattr(trade, "contract", None)

            event = {
                "symbol": self._safe_str(getattr(contract, "symbol", "")).upper(),
                "order_id": self._safe_str(getattr(order, "orderId", "")),
                "broker_order_id": self._safe_str(getattr(order, "orderId", "")),
                "perm_id": self._safe_str(getattr(order, "permId", "")),
                "status": self._safe_str(getattr(status, "status", "")).upper(),
                "filled_qty": self._safe_float(getattr(status, "filled", 0)),
                "remaining_qty": self._safe_float(getattr(status, "remaining", 0)),
                "avg_fill_price": self._safe_float(getattr(status, "avgFillPrice", 0)),
                "source": "ibkr_orderStatusEvent",
                "mode": self.mode,
                "timestamp": time.time(),
            }

            self._emit_order_update(event)

        except Exception as exc:
            self.last_error = f"orderStatus handler failed: {exc}"

    def _on_position(self, position):

        try:
            contract = getattr(position, "contract", None)

            symbol = self._safe_str(getattr(contract, "symbol", "")).upper()
            qty = self._safe_float(getattr(position, "position", 0))
            avg_cost = self._safe_float(getattr(position, "avgCost", 0))

            if symbol:
                self.positions[symbol] = qty

            self._sync_positions()

            if symbol and abs(qty) > 0:
                self.subscribe_market_data([symbol])
                self.refresh_market_data()

        except Exception as exc:
            self.last_error = f"position handler failed: {exc}"

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

        symbol = symbol.upper()
        side = side.upper()

        if not self.ui_connected:
            raise RuntimeError("Gateway not connected")

        if side not in ["BUY", "SELL"]:
            raise ValueError("Invalid side")

        if qty <= 0:
            raise ValueError("Invalid qty")

        if self.mode == SIM:

            current = self.positions.get(symbol, 0)

            if side == "BUY":
                current += qty
            else:
                current -= qty

            self.positions[symbol] = current

            self._sync_positions()
            self._sync_pnl()

            return {
                "status": "SIM_FILLED",
                "symbol": symbol,
                "qty": qty,
                "side": side,
                "price": self.get_quote(symbol),
                "time": time.time(),
                "mode": self.mode,
            }

        if self.mode == LIVE:

            if self.ib_client is None:
                raise RuntimeError("IBKR client unavailable")

            if not self.verify_connection():
                raise RuntimeError("IBKR client not connected")

            from ib_insync import Stock, MarketOrder

            contract = Stock(symbol, "SMART", "USD")

            action = "BUY" if side == "BUY" else "SELL"

            order = MarketOrder(
                action=action,
                totalQuantity=int(qty),
            )

            trade = self.ib_client.placeOrder(contract, order)

            self.subscribe_market_data([symbol])
            self.refresh_market_data()

            self.last_error = None

            return {
                "status": "LIVE_SENT",
                "symbol": symbol,
                "qty": qty,
                "side": side,
                "trade": str(trade),
                "time": time.time(),
                "mode": self.mode,
            }

        if self.mode == BACKTEST:

            return {
                "status": "BACKTEST_RECORDED",
                "symbol": symbol,
                "qty": qty,
                "side": side,
                "price": self.get_quote(symbol),
                "time": time.time(),
                "mode": self.mode,
            }

        raise RuntimeError(f"Unsupported mode: {self.mode}")

    # =====================================================
    # POSITION / ACCOUNT READS
    # =====================================================

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

                    qty = float(getattr(p, "position", 0) or 0)
                    avg_cost = float(getattr(p, "avgCost", 0) or 0)
                    account = str(getattr(p, "account", "") or "")

                    if not symbol or abs(qty) <= 0:
                        continue

                    self.positions[symbol] = qty

                    rows.append({
                        "account": account,
                        "symbol": symbol,
                        "sec_type": getattr(contract, "secType", ""),
                        "exchange": getattr(contract, "exchange", ""),
                        "currency": getattr(contract, "currency", ""),
                        "position": qty,
                        "avg_cost": avg_cost,
                    })

                self.last_positions_df = pd.DataFrame(rows)

                # Broker snapshot sync must remain position-only.
                # Do NOT subscribe to market data or refresh quotes here.
                # Market data refresh belongs to a separate manual action.

                return rows

            self._sync_positions()
            return self.last_positions_df.to_dict("records")

        except Exception as exc:
            self.last_error = f"refresh_positions failed: {exc}"
            return []

    def get_positions(self):
        return self.refresh_positions()

    def refresh_all(self):

        if self.mode == LIVE and self.verify_connection():

            self.refresh_positions()

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
                "avg_cost": 0.0,
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

        return {
            "connected": self.ui_connected or self.broker_connected,
            "ui_connected": self.ui_connected,
            "broker_connected": self.broker_connected,
            "mode": self.mode,
            "host": self.host,
            "port": self.port,
            "client_id": self.client_id,
            "error": self.last_error,
        }