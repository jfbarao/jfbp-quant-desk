# =========================================================
# 📁 JFBP PORTFOLIO MANAGER v35.10
# PORTFOLIO LEDGER TRUTH + LONG-ONLY ENFORCEMENT
# =========================================================

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set


# =========================================================
# DATA MODELS
# =========================================================

@dataclass
class Fill:
    symbol: str
    side: str
    quantity: float
    price: float


@dataclass
class Lot:
    qty: float
    price: float


@dataclass
class Position:
    symbol: str
    quantity: float = 0.0
    avg_price: float = 0.0
    realized_pnl: float = 0.0


# =========================================================
# PORTFOLIO MANAGER
# =========================================================

class PortfolioManager:
    """
    Institutional portfolio truth layer.

    Responsibilities:
    - Own position truth
    - Own lot truth
    - Own realized / unrealized P&L truth
    - Own portfolio ledger truth
    - Provide compatibility methods for OMS / Risk / UI pages
    """

    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.lots: Dict[str, List[Lot]] = {}
        self.last_prices: Dict[str, float] = {}

        # Canonical portfolio ledger
        self.ledger: List[Dict[str, Any]] = []

        # Compatibility aliases expected by pages / risk / OMS
        self.portfolio_ledger: List[Dict[str, Any]] = self.ledger

        self.last_event: Dict[str, Any] = {}
        self.last_error: str = ""

        self.processed_fill_ids: Set[str] = set()

    # =====================================================
    # CORE FILL ENTRY
    # =====================================================

    def apply_fill(self, fill: Any) -> Dict[str, Any]:
        """
        Apply a broker/OMS/sim fill to portfolio state.

        This is the canonical portfolio mutation entrypoint.
        """

        try:
            f = self._normalize_fill(fill)

            dedupe_key = self._dedupe_key(f)

            if dedupe_key and dedupe_key in self.processed_fill_ids:
                event = {
                    "timestamp": self._now(),
                    "symbol": f.get("symbol"),
                    "status": "DUPLICATE_IGNORED",
                    "fill_id": f.get("fill_id"),
                    "order_id": f.get("order_id"),
                    "dedupe_key": dedupe_key,
                    "source": f.get("source"),
                }

                self.last_event = event
                return event

            symbol = f["symbol"]
            action = f["action"]
            qty = float(f["qty"])
            price = float(f["fill_price"])
            source = str(f.get("source") or "")

            self.positions.setdefault(symbol, Position(symbol=symbol))
            self.lots.setdefault(symbol, [])

            pos = self.positions[symbol]

            old_qty = self._signed_qty(symbol)
            old_avg = self._avg_price(symbol)
            old_side = self._side(old_qty)

            signed_fill_qty = qty if action == "BUY" else -qty

            is_close = self._is_close_or_flatten(f)

            # =================================================
            # LONG-ONLY ENFORCEMENT
            # =================================================
            # Portfolio Manager is the final position-truth guard.
            # SELL may only reduce or close an existing long.
            # It must never create a short position or flip long to short.
            if action == "SELL":
                if old_qty <= 0:
                    event = {
                        "timestamp": f.get("timestamp") or self._now(),
                        "status": "REJECTED",
                        "event_type": "PORTFOLIO_REJECTED",
                        "reason": "REJECTED_LONG_ONLY_NO_POSITION",
                        "symbol": symbol,
                        "action": action,
                        "side": action,
                        "qty": qty,
                        "fill_price": price,
                        "price": price,
                        "old_qty": old_qty,
                        "new_qty": old_qty,
                        "expected_qty": old_qty,
                        "old_side": old_side,
                        "new_side": old_side,
                        "lifecycle_stage": "BLOCKED_OPEN_SHORT",
                        "signed_qty_delta": 0.0,
                        "realized_delta": 0.0,
                        "realized_pnl": round(pos.realized_pnl, 4),
                        "unrealized_pnl": round(self.get_unrealized_pnl(symbol), 4),
                        "total_pnl": round(
                            pos.realized_pnl + self.get_unrealized_pnl(symbol),
                            4,
                        ),
                        "order_id": f.get("order_id"),
                        "fill_id": f.get("fill_id") or f.get("id"),
                        "broker_order_id": f.get("broker_order_id"),
                        "source": source,
                        "mode": f.get("mode"),
                        "dedupe_key": dedupe_key,
                    }

                    self.last_event = event
                    self.last_error = event["reason"]
                    self._append_ledger_event(event)
                    return event

                signed_fill_qty = -min(abs(qty), abs(old_qty))

            elif is_close:
                signed_fill_qty = self._lock_close_signed_qty(
                    fill=f,
                    old_qty=old_qty,
                    action=action,
                    qty=qty,
                )

            expected_qty = old_qty + signed_fill_qty

            lifecycle_stage = self._classify_lifecycle(
                old_qty=old_qty,
                signed_fill_qty=signed_fill_qty,
            )

            realized_delta = self._apply_signed_lifecycle_fill(
                symbol=symbol,
                signed_fill_qty=signed_fill_qty,
                fill_price=price,
            )

            self._normalize_symbol_state(symbol)

            new_qty = self._signed_qty(symbol)
            new_avg = self._avg_price(symbol)
            new_side = self._side(new_qty)

            pos.quantity = new_qty
            pos.avg_price = new_avg
            pos.realized_pnl += realized_delta

            self.last_prices[symbol] = price

            if dedupe_key:
                self.processed_fill_ids.add(dedupe_key)

            event = {
                "timestamp": f.get("timestamp") or self._now(),

                "status": "FILLED",
                "event_type": "PORTFOLIO_FILL",

                "symbol": symbol,
                "action": action,
                "side": action,

                "qty": abs(signed_fill_qty),
                "signed_qty_delta": signed_fill_qty,

                "fill_price": price,
                "price": price,

                "old_qty": old_qty,
                "new_qty": new_qty,
                "expected_qty": expected_qty,

                "old_side": old_side,
                "new_side": new_side,

                "old_avg_price": round(old_avg, 4),
                "new_avg_price": round(new_avg, 4),

                "lifecycle_stage": lifecycle_stage,

                "realized_delta": round(realized_delta, 4),
                "realized_pnl": round(pos.realized_pnl, 4),
                "unrealized_pnl": round(self.get_unrealized_pnl(symbol), 4),
                "total_pnl": round(
                    pos.realized_pnl + self.get_unrealized_pnl(symbol),
                    4,
                ),

                "position_value": round(abs(new_qty) * price, 4),

                "order_id": f.get("order_id"),
                "fill_id": f.get("fill_id") or f.get("id"),
                "broker_order_id": f.get("broker_order_id"),

                "source": source,
                "mode": f.get("mode"),

                "close_request_id": f.get("close_request_id"),
                "flatten_generated": bool(f.get("flatten_generated", False)),
                "close_or_flatten_context": bool(is_close),

                "dedupe_key": dedupe_key,
            }

            self._append_ledger_event(event)

            self.last_event = event
            self.last_error = ""

            return event

        except Exception as exc:
            self.last_error = str(exc)

            event = {
                "timestamp": self._now(),
                "status": "ERROR",
                "event_type": "PORTFOLIO_ERROR",
                "error": str(exc),
            }

            self.last_event = event
            self._append_ledger_event(event)

            return event

    # Compatibility aliases
    process_fill = apply_fill
    record_fill = apply_fill
    update_from_fill = apply_fill
    apply_execution = apply_fill
    record_execution = apply_fill

    # =====================================================
    # PORTFOLIO LEDGER TRUTH
    # =====================================================

    def _append_ledger_event(self, event: Dict[str, Any]) -> None:
        """
        Canonical ledger append.

        Keeps both:
        - self.ledger
        - self.portfolio_ledger

        pointing to the same truth list.
        """

        if not isinstance(event, dict):
            return

        self.ledger.append(event)
        self.ledger = self.ledger[-5000:]

        # Re-bind alias after trimming
        self.portfolio_ledger = self.ledger

    def ledger_snapshot(self) -> List[Dict[str, Any]]:
        return list(self.ledger)

    def portfolio_ledger_snapshot(self) -> List[Dict[str, Any]]:
        return self.ledger_snapshot()

    def get_ledger(self) -> List[Dict[str, Any]]:
        return self.ledger_snapshot()

    def get_portfolio_ledger(self) -> List[Dict[str, Any]]:
        return self.ledger_snapshot()

    def history(self) -> List[Dict[str, Any]]:
        return self.ledger_snapshot()

    def fills_history(self) -> List[Dict[str, Any]]:
        return self.ledger_snapshot()

    def has_ledger(self) -> bool:
        return bool(self.ledger)

    def ledger_count(self) -> int:
        return len(self.ledger)
    
    # =====================================================
    # CLOSE / FLATTEN SIGN LOCK
    # =====================================================

    def _is_close_or_flatten(self, fill: Dict[str, Any]) -> bool:
        source = str(fill.get("source") or "")

        return bool(
            fill.get("flatten_generated")
            or fill.get("close_request_id")
            or fill.get("force_position_context")
            or fill.get("close_or_flatten_context")
            or source.startswith("oms_close")
            or source.startswith("oms_flatten")
            or source.startswith("oms_emergency")
            or source.startswith("risk_close")
            or source.startswith("risk_flatten")
        )

    def _lock_close_signed_qty(
        self,
        fill: Dict[str, Any],
        old_qty: float,
        action: str,
        qty: float,
    ) -> float:
        """
        Close / flatten must reduce existing exposure only.

        Portfolio truth wins over stale OMS context.
        Long-only rule: SELL cannot create or increase a short.
        """

        if abs(old_qty) <= 1e-9:
            context_qty = self._float(fill.get("position_before"))
            old_qty = context_qty

        if action == "SELL":
            if old_qty <= 0:
                return 0.0
            return -min(abs(qty), abs(old_qty))

        if action == "BUY":
            if old_qty >= 0:
                return abs(qty)
            return min(abs(qty), abs(old_qty))

        return qty if action == "BUY" else -qty

    # =====================================================
    # SIGNED POSITION LIFECYCLE
    # =====================================================

    def _apply_signed_lifecycle_fill(
        self,
        symbol: str,
        signed_fill_qty: float,
        fill_price: float,
    ) -> float:

        symbol = self._symbol(symbol)
        lots = self.lots.setdefault(symbol, [])

        remaining = abs(float(signed_fill_qty))

        if remaining <= 0:
            return 0.0

        incoming_sign = 1 if signed_fill_qty > 0 else -1
        realized = 0.0

        while remaining > 1e-9 and lots:
            lot = lots[0]

            if abs(lot.qty) <= 1e-9:
                lots.pop(0)
                continue

            lot_sign = 1 if lot.qty > 0 else -1

            if lot_sign == incoming_sign:
                break

            close_qty = min(abs(lot.qty), remaining)

            if lot.qty > 0 and incoming_sign < 0:
                realized += (fill_price - lot.price) * close_qty

            elif lot.qty < 0 and incoming_sign > 0:
                realized += (lot.price - fill_price) * close_qty

            if abs(lot.qty) <= close_qty + 1e-9:
                lots.pop(0)
            else:
                lot.qty += close_qty * incoming_sign

            remaining -= close_qty

        if remaining > 1e-9:
            lots.append(
                Lot(
                    qty=remaining * incoming_sign,
                    price=fill_price,
                )
            )

        self._normalize_symbol_state(symbol)
        return realized

    def _normalize_symbol_state(self, symbol: str) -> None:
        symbol = self._symbol(symbol)
        lots = self.lots.setdefault(symbol, [])

        cleaned = [lot for lot in lots if abs(lot.qty) > 1e-9]
        net_qty = round(sum(lot.qty for lot in cleaned), 10)

        self.positions.setdefault(symbol, Position(symbol=symbol))

        if abs(net_qty) <= 1e-9:
            self.lots[symbol] = []
            self.positions[symbol].quantity = 0.0
            self.positions[symbol].avg_price = 0.0
            return

        signs = {1 if lot.qty > 0 else -1 for lot in cleaned}

        if len(signs) > 1:
            total_abs = sum(abs(lot.qty) for lot in cleaned)

            avg_price = (
                sum(abs(lot.qty) * lot.price for lot in cleaned) / total_abs
                if total_abs > 0
                else 0.0
            )

            cleaned = [
                Lot(
                    qty=net_qty,
                    price=avg_price,
                )
            ]

        self.lots[symbol] = cleaned
        self.positions[symbol].quantity = self._signed_qty(symbol)
        self.positions[symbol].avg_price = self._avg_price(symbol)

    # =====================================================
    # POSITION ACCESS
    # =====================================================

    def get_position(self, symbol: str) -> float:
        return self._signed_qty(symbol)

    def position(self, symbol: str) -> float:
        return self.get_position(symbol)

    def get_quantity(self, symbol: str) -> float:
        return self.get_position(symbol)

    def get_signed_quantity(self, symbol: str) -> float:
        return self.get_position(symbol)

    def get_all_positions(self) -> Dict[str, float]:
        rows: Dict[str, float] = {}

        symbols = set(self.positions.keys()) | set(self.lots.keys())

        for symbol in symbols:
            qty = self._signed_qty(symbol)

            if abs(qty) > 1e-9:
                rows[symbol] = qty

        return rows

    def positions_dict(self) -> Dict[str, float]:
        return self.get_all_positions()

    def risk_positions(self) -> Dict[str, int]:
        return {
            symbol: int(round(qty))
            for symbol, qty in self.get_all_positions().items()
            if abs(qty) > 1e-9
        }

    def get_position_row(self, symbol: str) -> Dict[str, Any]:
        symbol = self._symbol(symbol)
        self._normalize_symbol_state(symbol)

        pos = self.positions.setdefault(symbol, Position(symbol=symbol))

        qty = self._signed_qty(symbol)
        avg_price = self._avg_price(symbol)
        last_price = self.last_prices.get(symbol, avg_price)

        pos.quantity = qty
        pos.avg_price = avg_price

        return {
            "symbol": symbol,
            "side": self._side(qty),
            "qty": abs(qty),
            "signed_qty": qty,
            "avg_price": round(avg_price, 4),
            "last_price": round(last_price, 4),
            "position_value": round(abs(qty) * last_price, 4),
            "unrealized_pnl": round(self.get_unrealized_pnl(symbol), 4),
            "realized_pnl": round(pos.realized_pnl, 4),
            "total_pnl": round(
                pos.realized_pnl + self.get_unrealized_pnl(symbol),
                4,
            ),
        }

    # =====================================================
    # PRICE FEED
    # =====================================================

    def update_price(self, symbol: str, price: Any) -> bool:
        symbol = self._symbol(symbol)

        try:
            price = float(price)
        except Exception:
            return False

        if not symbol or price <= 0:
            return False

        self.last_prices[symbol] = price
        return True

    def update_prices(self, prices: Dict[str, Any]) -> None:
        if isinstance(prices, dict):
            for symbol, price in prices.items():
                self.update_price(symbol, price)

    mark_price = update_price
    mark_prices = update_prices

    # =====================================================
    # P&L
    # =====================================================

    def get_unrealized_pnl(self, symbol: str) -> float:
        symbol = self._symbol(symbol)
        last_price = self.last_prices.get(symbol)

        if last_price is None:
            last_price = self._avg_price(symbol)

        unrealized = 0.0

        for lot in self.lots.get(symbol, []):
            if lot.qty > 0:
                unrealized += (last_price - lot.price) * lot.qty

            elif lot.qty < 0:
                unrealized += (lot.price - last_price) * abs(lot.qty)

        return unrealized

    def get_realized_pnl(self, symbol: Optional[str] = None) -> float:
        if symbol:
            symbol = self._symbol(symbol)
            pos = self.positions.get(symbol)
            return float(pos.realized_pnl) if pos else 0.0

        return sum(float(pos.realized_pnl) for pos in self.positions.values())

    def get_total_pnl(self) -> float:
        symbols = set(self.positions.keys()) | set(self.lots.keys())

        return sum(
            self.get_unrealized_pnl(symbol) + self.get_realized_pnl(symbol)
            for symbol in symbols
        )

    # =====================================================
    # SNAPSHOTS
    # =====================================================

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        rows: Dict[str, Dict[str, Any]] = {}

        symbols = sorted(set(self.positions.keys()) | set(self.lots.keys()))

        for symbol in symbols:
            self._normalize_symbol_state(symbol)

            pos = self.positions.setdefault(symbol, Position(symbol=symbol))

            qty = self._signed_qty(symbol)
            avg_price = self._avg_price(symbol)

            pos.quantity = qty
            pos.avg_price = avg_price

            if abs(qty) <= 1e-9 and abs(pos.realized_pnl) <= 1e-9:
                continue

            last_price = self.last_prices.get(symbol, avg_price)

            rows[symbol] = {
                "symbol": symbol,
                "side": self._side(qty),
                "qty": abs(qty),
                "signed_qty": qty,
                "avg_price": round(avg_price, 4),
                "last_price": round(last_price, 4),
                "position_value": round(abs(qty) * last_price, 4),
                "unrealized_pnl": round(self.get_unrealized_pnl(symbol), 4),
                "realized_pnl": round(pos.realized_pnl, 4),
                "total_pnl": round(
                    pos.realized_pnl + self.get_unrealized_pnl(symbol),
                    4,
                ),
            }

        return rows

    positions_snapshot = snapshot

    def exposure_snapshot(self) -> Dict[str, Any]:
        positions = self.snapshot()

        long_exposure = 0.0
        short_exposure = 0.0
        unrealized = 0.0
        realized = 0.0

        for row in positions.values():
            value = float(row.get("position_value", 0.0))
            side = row.get("side")

            if side == "LONG":
                long_exposure += value
            elif side == "SHORT":
                short_exposure += value

            unrealized += float(row.get("unrealized_pnl", 0.0))
            realized += float(row.get("realized_pnl", 0.0))

        return {
            "positions": len(positions),
            "gross_exposure": round(long_exposure + short_exposure, 4),
            "long_exposure": round(long_exposure, 4),
            "short_exposure": round(short_exposure, 4),
            "net_exposure": round(long_exposure - short_exposure, 4),
            "unrealized_pnl": round(unrealized, 4),
            "realized_pnl": round(realized, 4),
            "total_pnl": round(unrealized + realized, 4),
        }

    def full_snapshot(self) -> Dict[str, Any]:
        return {
            "positions": self.snapshot(),
            "exposure": self.exposure_snapshot(),
            "ledger": self.ledger_snapshot(),
            "portfolio_ledger": self.portfolio_ledger_snapshot(),
            "last_event": self.last_event,
            "last_error": self.last_error,
            "processed_fills": len(self.processed_fill_ids),
            "manager_version": "35.10",
            "long_only_enforced": True,
        }
    
        # =====================================================
    # AUDIT REPLAY / REBUILD
    # =====================================================

    def replay_fills(
        self,
        fills: List[Dict[str, Any]],
        reset_first: bool = True,
    ) -> Dict[str, Any]:
        """
        Rebuild portfolio state from durable audit/runtime fills.

        Institutional rebuild semantics:
        - Portfolio state is reconstructed only from FILLED events
        - Existing runtime state may optionally be cleared first
        - Dedupe protections remain active
        """

        if reset_first:
            self.clear()

        replayed = 0
        skipped = 0
        errors = 0

        last_error = None

        for fill in fills:

            try:

                if not isinstance(fill, dict):
                    skipped += 1
                    continue

                status = str(fill.get("status") or "").upper()

                if status not in ("FILLED", "COMPLETE"):
                    skipped += 1
                    continue

                symbol = fill.get("symbol")

                if not symbol:
                    skipped += 1
                    continue

                result = self.apply_fill(fill)

                if result.get("status") == "ERROR":
                    errors += 1
                    last_error = result.get("error")
                    continue

                if result.get("status") == "DUPLICATE_IGNORED":
                    skipped += 1
                    continue

                replayed += 1

            except Exception as exc:
                errors += 1
                last_error = str(exc)

        return {
            "status": "OK" if errors == 0 else "PARTIAL",
            "replayed": replayed,
            "skipped": skipped,
            "errors": errors,
            "positions": len(self.snapshot()),
            "ledger": len(self.ledger),
            "last_error": last_error,
        }

    def rebuild_from_audit(
        self,
        audit_rows: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Canonical durable portfolio reconstruction entrypoint.
        """

        return self.replay_fills(
            fills=audit_rows,
            reset_first=True,
        )

    # =====================================================
    # STATE
    # =====================================================

    def clear(self) -> None:
        self.positions.clear()
        self.lots.clear()
        self.last_prices.clear()
        self.ledger.clear()

        # Keep alias synchronized
        self.portfolio_ledger = self.ledger

        self.last_event = {}
        self.last_error = ""
        self.processed_fill_ids.clear()

    reset = clear
    clear_portfolio = clear
    reset_portfolio = clear

    # =====================================================
    # INTERNAL HELPERS
    # =====================================================

    def _dedupe_key(self, fill: Dict[str, Any]) -> str:
        fill_id = fill.get("fill_id") or fill.get("id")
        order_id = fill.get("order_id")
        symbol = fill.get("symbol")
        action = fill.get("action")
        qty = fill.get("qty")
        price = fill.get("fill_price")
        timestamp = fill.get("timestamp")

        if fill_id:
            return f"fill:{fill_id}"

        if order_id:
            return f"order:{order_id}:{symbol}:{action}:{qty}:{price}"

        return f"synthetic:{timestamp}:{symbol}:{action}:{qty}:{price}"

    def _signed_qty(self, symbol: str) -> float:
        symbol = self._symbol(symbol)
        return round(sum(lot.qty for lot in self.lots.get(symbol, [])), 10)

    def _avg_price(self, symbol: str) -> float:
        symbol = self._symbol(symbol)
        lots = self.lots.get(symbol, [])

        total_qty = sum(abs(lot.qty) for lot in lots)

        if total_qty <= 0:
            return 0.0

        return sum(abs(lot.qty) * lot.price for lot in lots) / total_qty

    def _classify_lifecycle(
        self,
        old_qty: float,
        signed_fill_qty: float,
    ) -> str:
        new_qty = old_qty + signed_fill_qty

        if abs(old_qty) <= 1e-9 and new_qty > 0:
            return "OPEN_LONG"

        if abs(old_qty) <= 1e-9 and new_qty < 0:
            return "BLOCKED_OPEN_SHORT"

        if old_qty > 0 and signed_fill_qty > 0:
            return "ADD_LONG"

        if old_qty < 0 and signed_fill_qty < 0:
            return "ADD_SHORT"

        if old_qty > 0 and signed_fill_qty < 0:
            if new_qty > 0:
                return "REDUCE_LONG"
            if abs(new_qty) <= 1e-9:
                return "CLOSE_LONG"
            return "FLIP_LONG_TO_SHORT"

        if old_qty < 0 and signed_fill_qty > 0:
            if new_qty < 0:
                return "REDUCE_SHORT"
            if abs(new_qty) <= 1e-9:
                return "CLOSE_SHORT"
            return "FLIP_SHORT_TO_LONG"

        return "UNKNOWN"

    def _normalize_fill(self, fill: Any) -> Dict[str, Any]:
        if isinstance(fill, Fill):
            return {
                "symbol": self._symbol(fill.symbol),
                "action": self._action(fill.side),
                "qty": self._float(fill.quantity),
                "fill_price": self._float(fill.price),
                "price": self._float(fill.price),
                "source": "FillDataclass",
            }

        if not isinstance(fill, dict):
            raise ValueError("Fill must be Fill dataclass or dict")

        symbol = self._symbol(
            fill.get("symbol")
            or fill.get("ticker")
            or fill.get("data_symbol")
        )

        action = self._action(
            fill.get("action")
            or fill.get("side")
            or fill.get("signal")
        )

        qty = self._float(
            fill.get("qty")
            or fill.get("quantity")
            or fill.get("shares")
            or 1
        )

        price = self._float(
            fill.get("fill_price")
            or fill.get("price")
            or fill.get("avg_fill_price")
            or fill.get("last_price")
        )

        if not symbol:
            raise ValueError("Fill missing symbol")

        if action not in ("BUY", "SELL"):
            raise ValueError(f"Unsupported fill action: {action}")

        if qty <= 0:
            raise ValueError("Fill qty must be > 0")

        if price <= 0:
            raise ValueError("Fill price must be > 0")

        return {
            **fill,
            "symbol": symbol,
            "action": action,
            "side": action,
            "qty": qty,
            "fill_price": price,
            "price": price,
        }

    def _side(self, qty: float) -> str:
        if qty > 0:
            return "LONG"
        if qty < 0:
            return "SHORT"
        return "FLAT"

    def _symbol(self, symbol: Any) -> str:
        return str(symbol or "").upper().strip()

    def _action(self, action: Any) -> str:
        action = str(action or "").upper().strip()

        if action in ("LONG", "BUY_LONG"):
            return "BUY"

        if action in ("SHORT", "SELL_SHORT"):
            return "SELL"

        return action

    def _float(self, value: Any) -> float:
        try:
            return float(value)
        except Exception:
            return 0.0

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()        