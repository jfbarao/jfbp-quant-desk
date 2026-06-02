# =========================================================
# 🛡️ JFBP RISK ENGINE v34.7.1
# INSTITUTIONAL RISK TRUTH LAYER — FULL FIXED FILE
# =========================================================

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List


class RiskEngine:

    VALID_MODES = {"SIM", "LIVE", "BACKTEST", "REPLAY"}
    EPSILON = 1e-9

    def __init__(
        self,
        max_daily_trades: int = 25,
        max_open_positions: int = 25,
        max_gross_exposure: float = 100000.0,
        max_single_order_value: float = 10000.0,
        max_daily_loss: float = 1000.0,
        mode: str = "SIM",
    ):
        self.mode = self._normalize_mode(mode)

        # Hard guards:
        # max_open_positions must never silently become 0.
        self.max_daily_trades = max(0, int(max_daily_trades))
        self.max_open_positions = max(1, int(max_open_positions))
        self.max_gross_exposure = max(0.0, float(max_gross_exposure))
        self.max_single_order_value = max(0.0, float(max_single_order_value))
        self.max_daily_loss = max(0.0, float(max_daily_loss))

        self.daily_trades = 0
        self.daily_pnl = 0.0

        self.positions: Dict[str, float] = {}
        self.last_prices: Dict[str, float] = {}

        self.risk_state = "NORMAL"
        self.risk_state_reason = "OK"

        self.last_error = ""
        self.last_check: Dict[str, Any] = {}
        self.last_sync: Dict[str, Any] = {}
        self.last_batch_check: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []

        # v34.7 truth metadata
        self.sync_generation = 0
        self.last_reconciliation_source = "INIT"
        self.last_reconciliation_warning = ""

    # =====================================================
    # CONFIG
    # =====================================================

    def set_mode(self, mode: str):
        self.mode = self._normalize_mode(mode)

    def set_limits(
        self,
        max_daily_trades: Optional[int] = None,
        max_open_positions: Optional[int] = None,
        max_gross_exposure: Optional[float] = None,
        max_single_order_value: Optional[float] = None,
        max_daily_loss: Optional[float] = None,
    ):
        if max_daily_trades is not None:
            self.max_daily_trades = max(0, int(max_daily_trades))

        if max_open_positions is not None:
            # Scanner / UI bugs must not silently set this to 0.
            self.max_open_positions = max(1, int(max_open_positions))

        if max_gross_exposure is not None:
            self.max_gross_exposure = max(0.0, float(max_gross_exposure))

        if max_single_order_value is not None:
            self.max_single_order_value = max(0.0, float(max_single_order_value))

        if max_daily_loss is not None:
            self.max_daily_loss = max(0.0, float(max_daily_loss))

        self._update_risk_state()

    # =====================================================
    # PORTFOLIO RECONCILIATION TRUTH
    # =====================================================

    def reconcile_with_portfolio(
        self,
        portfolio: Any = None,
        historical: bool = False,
    ):
        if portfolio is None:
            self.last_reconciliation_source = "NONE"
            return self.sync_positions(
                {},
                historical=historical,
                source="NONE",
            )

        rows = {}
        source = "NONE"

        for method_name in ("snapshot", "positions_snapshot"):
            if rows:
                break

            try:
                if hasattr(portfolio, method_name):
                    snap = getattr(portfolio, method_name)()
                    extracted = self._extract_positions_from_snapshot(snap)

                    if isinstance(extracted, (dict, list)):
                        rows = extracted
                        source = f"portfolio.{method_name}"

                        if rows:
                            break

            except Exception as exc:
                self.last_error = f"portfolio.{method_name} failed: {exc}"

        if not rows:
            try:
                if hasattr(portfolio, "risk_positions"):
                    snap = portfolio.risk_positions()
                    extracted = self._extract_positions_from_snapshot(snap)

                    if isinstance(extracted, (dict, list)):
                        rows = extracted
                        source = "portfolio.risk_positions"

            except Exception as exc:
                self.last_error = f"portfolio.risk_positions failed: {exc}"

        if not rows:
            try:
                raw = getattr(portfolio, "positions", {})
                extracted = self._extract_positions_from_snapshot(raw)

                if isinstance(extracted, (dict, list)):
                    rows = extracted
                    source = "portfolio.positions"

            except Exception as exc:
                self.last_error = f"portfolio.positions failed: {exc}"

        self.last_reconciliation_source = source

        return self.sync_positions(
            rows,
            historical=historical,
            source=source,
        )

    def sync_positions(
        self,
        positions: Any = None,
        historical: bool = False,
        source: str = "DIRECT",
    ):
        clean_positions: Dict[str, float] = {}
        clean_prices: Dict[str, float] = {}
        rejected = []

        if positions is None:
            positions = {}

        items = []

        if isinstance(positions, dict):
            items = list(positions.items())

        elif isinstance(positions, list):
            for row in positions:
                if isinstance(row, dict):
                    items.append((
                        row.get("symbol")
                        or row.get("ticker")
                        or row.get("data_symbol"),
                        row,
                    ))
                else:
                    rejected.append({
                        "reason": "UNSUPPORTED_LIST_ROW",
                        "type": type(row).__name__,
                    })

        else:
            rejected.append({
                "reason": "UNSUPPORTED_POSITIONS_TYPE",
                "type": type(positions).__name__,
            })

        for symbol, value in items:
            symbol = self._symbol(symbol)

            if not symbol:
                rejected.append({
                    "reason": "EMPTY_SYMBOL",
                    "value": str(value)[:120],
                })
                continue

            qty = self._extract_signed_qty(value)

            if abs(qty) <= self.EPSILON:
                continue

            clean_positions[symbol] = clean_positions.get(symbol, 0.0) + qty

            price = self._extract_price(value)
            if price > 0:
                clean_prices[symbol] = price

        clean_positions = {
            symbol: qty
            for symbol, qty in clean_positions.items()
            if abs(qty) > self.EPSILON
        }

        # Institutional truth:
        # portfolio sync is authoritative. If external book is flat,
        # risk inventory must become flat. No stale ghost positions.
        preserved_prices = dict(self.last_prices)

        self.positions = clean_positions
        self.last_prices = {
            symbol: clean_prices.get(symbol, preserved_prices.get(symbol, 0.0))
            for symbol in self.positions.keys()
        }

        self._purge_stale_inventory()
        self.sync_generation += 1
        self._update_risk_state()

        missing_prices = [
            symbol
            for symbol, price in self.last_prices.items()
            if not price or price <= 0
        ]

        self.last_reconciliation_warning = (
            "MISSING_PRICES_FOR_EXPOSURE"
            if missing_prices
            else ""
        )

        self.last_sync = {
            "timestamp": self._now(),
            "event": "SYNC_POSITIONS",
            "historical": historical,
            "source": source,
            "sync_generation": self.sync_generation,
            "received_type": type(positions).__name__,
            "positions_loaded": len(self.positions),
            "open_positions": self.open_positions_count(),
            "max_open_positions": self.max_open_positions,
            "gross_exposure": self.gross_exposure(),
            "max_gross_exposure": self.max_gross_exposure,
            "net_exposure": self.net_exposure(),
            "long_exposure": self.long_exposure(),
            "short_exposure": self.short_exposure(),
            "risk_state": self.risk_state,
            "risk_state_reason": self.risk_state_reason,
            "missing_prices": missing_prices,
            "rejected": rejected,
            "positions": dict(self.positions),
            "last_prices": dict(self.last_prices),
            "warning": self.last_reconciliation_warning,
        }

        self.last_check = dict(self.last_sync)
        self.last_error = ""

        return True

    def _extract_positions_from_snapshot(self, snap: Any) -> Any:
        if snap is None:
            return {}

        if isinstance(snap, dict):
            for key in (
                "positions",
                "portfolio_positions",
                "risk_positions",
                "book",
                "holdings",
            ):
                value = snap.get(key)
                if isinstance(value, (dict, list)):
                    return value

            return snap

        if isinstance(snap, list):
            return snap

        return {}

    # =====================================================
    # RISK STATE INTELLIGENCE
    # =====================================================

    def _update_risk_state(self):
        if self.risk_state == "LOCKDOWN":
            return self.risk_state

        if self.daily_pnl <= -abs(self.max_daily_loss):
            self.risk_state = "LOCKDOWN"
            self.risk_state_reason = "DAILY_LOSS_LIMIT_REACHED"
            return self.risk_state

        gross = self.gross_exposure()
        open_positions = self.open_positions_count()

        over_gross = gross > self.max_gross_exposure + self.EPSILON
        over_positions = open_positions > self.max_open_positions

        if over_gross and over_positions:
            self.risk_state = "OVER_LIMIT"
            self.risk_state_reason = (
                "GROSS_AND_POSITION_LIMIT_EXCEEDED "
                f"(gross={gross:.2f}, limit={self.max_gross_exposure:.2f}; "
                f"open_positions={open_positions}, limit={self.max_open_positions})"
            )

        elif over_gross:
            self.risk_state = "OVER_LIMIT"
            self.risk_state_reason = (
                "GROSS_EXPOSURE_LIMIT_EXCEEDED "
                f"(gross={gross:.2f}, limit={self.max_gross_exposure:.2f})"
            )

        elif over_positions:
            self.risk_state = "OVER_LIMIT"
            self.risk_state_reason = (
                "OPEN_POSITION_LIMIT_EXCEEDED "
                f"(open_positions={open_positions}, limit={self.max_open_positions})"
            )

        else:
            self.risk_state = "NORMAL"
            self.risk_state_reason = "OK"

        return self.risk_state
    
    # =====================================================
    # PRICE UPDATES
    # =====================================================

    def update_price(self, symbol: str, price: Any):
        symbol = self._symbol(symbol)
        price = self._float(price)

        if not symbol or price <= 0:
            return False

        self.last_prices[symbol] = price
        self._purge_stale_inventory()
        self._update_risk_state()
        return True

    def update_prices(self, prices: Dict[str, Any]):
        if isinstance(prices, dict):
            for symbol, price in prices.items():
                self.update_price(symbol, price)

    # =====================================================
    # SINGLE ORDER CHECK
    # =====================================================

    def check(self, signal: Dict[str, Any]):
        self._purge_stale_inventory()
        self._update_risk_state()

        signal = self._normalize_signal(signal)
        approved, reason = self._check_single(signal)

        self._update_risk_state()

        self.last_check = {
            "timestamp": self._now(),
            "approved": approved,
            "reason": reason,
            "symbol": signal.get("symbol"),
            "action": signal.get("action"),
            "qty": signal.get("qty"),
            "price": signal.get("price"),
            "mode": signal.get("mode"),
            "position_before": self.get_position(signal.get("symbol")),
            "position_after": self.projected_position(signal),
            "gross_before": self.gross_exposure(),
            "gross_after": self.projected_gross_exposure(signal),
            "net_before": self.net_exposure(),
            "net_after": self.projected_net_exposure(signal),
            "open_positions_before": self.open_positions_count(),
            "open_positions_after": self.projected_open_positions(signal),
            "position_action": self.classify_position_action(signal),
            "risk_state": self.risk_state,
            "risk_state_reason": self.risk_state_reason,
            "book_positions": dict(self.positions),
            "book_prices": dict(self.last_prices),
            "rotation_context": self._is_rotation_or_flatten_context(signal),
        }

        self.history.append(self.last_check)
        self.history = self.history[-500:]
        self.last_error = "" if approved else reason

        return approved, reason

    approve = check
    validate = check
    risk_check = check

    def _check_single(self, signal: Dict[str, Any]):
        base_ok, base_reason = self._basic_signal_validation(signal)

        if not base_ok:
            return False, base_reason

        position_action = self.classify_position_action(signal)

        if self._is_risk_reducing(position_action):
            return self._check_exit_safety(signal)

        if self.risk_state == "OVER_LIMIT":
            gross_after = self.projected_gross_exposure(signal)
            open_after = self.projected_open_positions(signal)

            return False, (
                "REJECTED_RISK_STATE_OVER_LIMIT "
                f"reason={self.risk_state_reason}; "
                f"projected_gross={gross_after:.2f}; "
                f"projected_open_positions={open_after}"
            )

        if self.daily_trades >= self.max_daily_trades:
            return False, (
                "REJECTED_RISK_DAILY_TRADE_LIMIT "
                f"(daily_trades={self.daily_trades}, "
                f"limit={self.max_daily_trades})"
            )

        order_value = abs(
            self._float(signal.get("qty"))
            * self._float(signal.get("price"))
        )

        if order_value > self.max_single_order_value:
            return False, (
                "REJECTED_RISK_SINGLE_ORDER_VALUE "
                f"(order_value={order_value:.2f}, "
                f"limit={self.max_single_order_value:.2f})"
            )

        if self.projected_open_positions(signal) > self.max_open_positions:
            return False, (
                "REJECTED_RISK_OPEN_POSITION_LIMIT "
                f"(projected={self.projected_open_positions(signal)}, "
                f"limit={self.max_open_positions})"
            )

        if self.projected_gross_exposure(signal) > self.max_gross_exposure:
            return False, (
                "REJECTED_RISK_GROSS_EXPOSURE "
                f"(projected={self.projected_gross_exposure(signal):.2f}, "
                f"limit={self.max_gross_exposure:.2f})"
            )

        return True, "OK"

    # =====================================================
    # BATCH CHECK
    # =====================================================

    def check_batch(self, signals: List[Dict[str, Any]]):
        self._purge_stale_inventory()
        self._update_risk_state()

        normalized = [
            self._normalize_signal(signal)
            for signal in signals
            if isinstance(signal, dict)
        ]

        gross_before = self.gross_exposure()
        open_before = self.open_positions_count()

        projected_positions = dict(self.positions)
        projected_prices = dict(self.last_prices)

        rows = []
        malformed = []

        for signal in normalized:
            base_ok, base_reason = self._basic_signal_validation(signal)

            if not base_ok:
                malformed.append({
                    **signal,
                    "approved": False,
                    "reason": base_reason,
                    "position_action": "INVALID",
                })
                continue

            symbol = signal.get("symbol")
            action = signal.get("action")
            qty = self._float(signal.get("qty"))
            price = self._float(signal.get("price"))

            if price > 0:
                projected_prices[symbol] = price

            signed = qty if action == "BUY" else -qty
            old_qty = projected_positions.get(symbol, 0.0)
            new_qty = old_qty + signed

            if abs(new_qty) <= self.EPSILON:
                projected_positions.pop(symbol, None)
            else:
                projected_positions[symbol] = new_qty

        gross_after = self._gross_from_positions(
            projected_positions,
            projected_prices,
        )

        open_after = len(projected_positions)

        batch_reduces_gross = gross_after <= gross_before + self.EPSILON
        batch_reduces_positions = open_after <= open_before

        if self.risk_state == "OVER_LIMIT":
            batch_ok = batch_reduces_gross or batch_reduces_positions
            batch_reason = (
                "OK_BATCH_REDUCES_OVER_LIMIT_RISK"
                if batch_ok
                else "REJECTED_BATCH_INCREASES_OVER_LIMIT"
            )
        else:
            batch_ok = (
                gross_after <= self.max_gross_exposure + self.EPSILON
                and open_after <= self.max_open_positions
            )

            batch_reason = (
                "OK_BATCH"
                if batch_ok
                else "REJECTED_BATCH_LIMIT"
            )

        if self.risk_state == "LOCKDOWN":
            batch_ok = False
            batch_reason = "RISK_LOCKDOWN"

        if self.daily_trades + len(normalized) > self.max_daily_trades:
            batch_ok = False
            batch_reason = "REJECTED_RISK_DAILY_TRADE_LIMIT"

    # =====================================================
    # POSITION CLASSIFICATION
    # =====================================================

    def classify_position_action(self, signal: Dict[str, Any]) -> str:
        signal = self._normalize_signal(signal)

        symbol = signal.get("symbol")
        action = signal.get("action")
        qty = self._float(signal.get("qty"))
        old_qty = self.get_position(symbol)

        if self._is_rotation_or_flatten_context(signal):
            if old_qty > 0 and action == "SELL":
                return "CLOSE_LONG" if qty >= abs(old_qty) else "REDUCE_LONG"

            if old_qty < 0 and action == "BUY":
                return "CLOSE_SHORT" if qty >= abs(old_qty) else "REDUCE_SHORT"

        signed = qty if action == "BUY" else -qty
        new_qty = old_qty + signed

        if abs(old_qty) <= self.EPSILON:
            if new_qty > 0:
                return "OPEN_LONG"
            if new_qty < 0:
                return "OPEN_SHORT"
            return "NO_CHANGE"

        if old_qty > 0:
            if signed > 0:
                return "ADD_LONG"
            if new_qty > 0:
                return "REDUCE_LONG"
            if abs(new_qty) <= self.EPSILON:
                return "CLOSE_LONG"
            return "FLIP_LONG_TO_SHORT"

        if old_qty < 0:
            if signed < 0:
                return "ADD_SHORT"
            if new_qty < 0:
                return "REDUCE_SHORT"
            if abs(new_qty) <= self.EPSILON:
                return "CLOSE_SHORT"
            return "FLIP_SHORT_TO_LONG"

        return "UNKNOWN"

    # =====================================================
    # EXPOSURE
    # =====================================================

    def get_position(self, symbol: str) -> float:
        return float(self.positions.get(self._symbol(symbol), 0.0) or 0.0)

    def projected_position(self, signal: Dict[str, Any]) -> float:
        signal = self._normalize_signal(signal)

        old_qty = self.get_position(signal.get("symbol"))
        signed = (
            self._float(signal.get("qty"))
            if signal.get("action") == "BUY"
            else -self._float(signal.get("qty"))
        )

        return old_qty + signed

    def open_positions_count(self) -> int:
        return len([
            qty for qty in self.positions.values()
            if abs(float(qty or 0.0)) > self.EPSILON
        ])

    def projected_open_positions(self, signal: Dict[str, Any]) -> int:
        positions = dict(self.positions)
        symbol = signal.get("symbol")
        projected = self.projected_position(signal)

        if abs(projected) <= self.EPSILON:
            positions.pop(symbol, None)
        else:
            positions[symbol] = projected

        return len([
            qty for qty in positions.values()
            if abs(float(qty or 0.0)) > self.EPSILON
        ])

    def gross_exposure(self) -> float:
        return self._gross_from_positions(self.positions, self.last_prices)

    def projected_gross_exposure(self, signal: Dict[str, Any]) -> float:
        positions = dict(self.positions)
        prices = dict(self.last_prices)

        symbol = signal.get("symbol")
        projected = self.projected_position(signal)
        price = self._float(signal.get("price"))

        if abs(projected) <= self.EPSILON:
            positions.pop(symbol, None)
        else:
            positions[symbol] = projected

        if price > 0:
            prices[symbol] = price

        return self._gross_from_positions(positions, prices)

    def net_exposure(self) -> float:
        total = 0.0
        for symbol, qty in self.positions.items():
            total += qty * self._float(self.last_prices.get(symbol, 0.0))
        return total

    def projected_net_exposure(self, signal: Dict[str, Any]) -> float:
        positions = dict(self.positions)
        prices = dict(self.last_prices)

        symbol = signal.get("symbol")
        projected = self.projected_position(signal)
        price = self._float(signal.get("price"))

        if abs(projected) <= self.EPSILON:
            positions.pop(symbol, None)
        else:
            positions[symbol] = projected

        if price > 0:
            prices[symbol] = price

        total = 0.0
        for s, qty in positions.items():
            total += qty * self._float(prices.get(s, 0.0))

        return total

    def long_exposure(self) -> float:
        total = 0.0
        for symbol, qty in self.positions.items():
            if qty > 0:
                total += qty * self._float(self.last_prices.get(symbol, 0.0))
        return total

    def short_exposure(self) -> float:
        total = 0.0
        for symbol, qty in self.positions.items():
            if qty < 0:
                total += abs(qty) * self._float(self.last_prices.get(symbol, 0.0))
        return total

    def _gross_from_positions(self, positions, prices):
        total = 0.0
        for symbol, qty in positions.items():
            total += abs(qty) * self._float(prices.get(symbol, 0.0))
        return total

    # =====================================================
    # RECORDING / STATE
    # =====================================================

    def record_trade(self, signal=None):
        self.daily_trades += 1
        self._update_risk_state()
        return True

    def record_fill(self, fill):
        return self.record_trade(fill)

    def record_pnl(self, pnl):
        self.daily_pnl += self._float(pnl)
        self._update_risk_state()
        return True

    def reset(self):
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.positions = {}
        self.last_prices = {}
        self.risk_state = "NORMAL"
        self.risk_state_reason = "OK"
        self.last_error = ""
        self.last_check = {}
        self.last_sync = {}
        self.last_batch_check = {}
        self.history = []
        self.sync_generation = 0
        self.last_reconciliation_source = "RESET"
        self.last_reconciliation_warning = ""
        return True

    clear = reset

    def unlock(self):
        self.risk_state = "NORMAL"
        self.risk_state_reason = "MANUAL_UNLOCK"
        self._update_risk_state()
        return True

    def lockdown(self, reason="MANUAL_LOCKDOWN"):
        self.risk_state = "LOCKDOWN"
        self.risk_state_reason = reason
        self.last_error = reason
        return True

    # =====================================================
    # SNAPSHOT
    # =====================================================

    def snapshot(self):
        self._purge_stale_inventory()
        self._update_risk_state()

        return {
            "mode": self.mode,
            "risk_state": self.risk_state,
            "risk_state_reason": self.risk_state_reason,
            "daily_trades": self.daily_trades,
            "max_daily_trades": self.max_daily_trades,
            "daily_pnl": round(self.daily_pnl, 4),
            "max_daily_loss": self.max_daily_loss,
            "open_positions": self.open_positions_count(),
            "max_open_positions": self.max_open_positions,
            "gross_exposure": round(self.gross_exposure(), 4),
            "net_exposure": round(self.net_exposure(), 4),
            "long_exposure": round(self.long_exposure(), 4),
            "short_exposure": round(self.short_exposure(), 4),
            "max_gross_exposure": self.max_gross_exposure,
            "max_single_order_value": self.max_single_order_value,
            "positions": dict(self.positions),
            "last_prices": dict(self.last_prices),
            "last_check": dict(self.last_check),
            "last_sync": dict(self.last_sync),
            "last_batch_check": dict(self.last_batch_check),
            "last_error": self.last_error,
            "sync_generation": self.sync_generation,
            "last_reconciliation_source": self.last_reconciliation_source,
            "last_reconciliation_warning": self.last_reconciliation_warning,
        }

    def history_snapshot(self):
        return list(self.history)

    # =====================================================
    # HELPERS
    # =====================================================

    def _purge_stale_inventory(self):
        stale = [
            s for s, q in self.positions.items()
            if abs(q) <= self.EPSILON
        ]
        for s in stale:
            self.positions.pop(s, None)
            self.last_prices.pop(s, None)

    def _is_rotation_or_flatten_context(self, signal):
        return any([
            signal.get("close_or_flatten_context"),
            signal.get("flatten_generated"),
            signal.get("force_position_context"),
            signal.get("close_request_id"),
        ])

    def _check_exit_safety(self, signal):
        return True, "OK_EXIT_REDUCES_RISK"

    def _is_risk_reducing(self, action):
        return action in {
            "REDUCE_LONG",
            "REDUCE_SHORT",
            "CLOSE_LONG",
            "CLOSE_SHORT",
        }

    def _basic_signal_validation(self, signal):
        if self.risk_state == "LOCKDOWN":
            return False, "RISK_LOCKDOWN"

        if not signal.get("symbol"):
            return False, "MISSING_SYMBOL"

        if signal.get("action") not in ("BUY", "SELL"):
            return False, "INVALID_ACTION"

        if self._float(signal.get("qty")) <= 0:
            return False, "INVALID_QTY"

        if self._float(signal.get("price")) <= 0:
            return False, "INVALID_PRICE"

        return True, "OK"

    def _normalize_signal(self, signal):
        if not isinstance(signal, dict):
            return {}

        action = str(
            signal.get("action")
            or signal.get("side")
            or ""
        ).upper().strip()

        return {
            **signal,
            "symbol": self._symbol(
                signal.get("symbol")
                or signal.get("ticker")
                or signal.get("data_symbol")
            ),
            "action": action,
            "qty": abs(self._float(signal.get("qty"))),
            "price": self._float(signal.get("price")),
            "mode": self._normalize_mode(signal.get("mode", self.mode)),
        }

    def _extract_signed_qty(self, value):
        if isinstance(value, dict):
            if "signed_qty" in value:
                return self._float(value["signed_qty"])

            qty = self._float(
                value.get("qty", value.get("quantity", 0))
            )

            side = str(value.get("side", "")).upper()

            if side == "SHORT":
                return -abs(qty)

            if side == "LONG":
                return abs(qty)

            return qty

        return self._float(value)

    def _extract_price(self, value):
        if isinstance(value, dict):
            for key in ("last_price", "avg_price", "price", "fill_price"):
                p = self._float(value.get(key))
                if p > 0:
                    return p
        return 0.0

    def _symbol(self, symbol):
        return str(symbol or "").upper().strip()

    def _float(self, value):
        try:
            if value is None:
                return 0.0
            return float(value)
        except Exception:
            return 0.0

    def _normalize_mode(self, mode):
        mode = str(mode or "SIM").upper().strip()
        return mode if mode in self.VALID_MODES else "SIM"

    def _now(self):
        return datetime.now(timezone.utc).isoformat()                