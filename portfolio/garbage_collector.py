# =========================================================
# 🧹 JFBP PORTFOLIO GARBAGE COLLECTOR v32.9
# ZERO-QTY PURGE + POSITION STATE NORMALIZER
# SAFE EMPTY-LOTS POSITION PRESERVATION
# =========================================================

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


class PortfolioGarbageCollector:
    """
    Portfolio state sanitizer.

    Purpose:
    - purge zero-qty stale positions
    - remove orphan lots
    - normalize symbol casing
    - repair signed qty drift
    - preserve realized P&L
    - preserve recovered positions when lots are unavailable
    - keep snapshots institutional-clean

    This class does NOT execute trades.
    It only cleans portfolio runtime state.
    """

    EPSILON = 1e-9

    def __init__(self, portfolio_engine=None):
        self.portfolio_engine = portfolio_engine
        self.last_report: Dict[str, Any] = {}
        self.last_error = ""

    # =====================================================
    # PUBLIC API
    # =====================================================

    def attach(self, portfolio_engine) -> None:
        self.portfolio_engine = portfolio_engine

    def run(self, portfolio_engine=None) -> Dict[str, Any]:
        """
        Main garbage collection entry point.
        """

        if portfolio_engine is not None:
            self.portfolio_engine = portfolio_engine

        if self.portfolio_engine is None:
            self.last_error = "Portfolio engine unavailable"
            self.last_report = self._report(
                status="ERROR",
                reason=self.last_error,
            )
            return self.last_report

        try:
            report = self._collect(self.portfolio_engine)
            self.last_report = report
            self.last_error = ""
            return report

        except Exception as exc:
            self.last_error = str(exc)
            self.last_report = self._report(
                status="ERROR",
                reason=str(exc),
            )
            return self.last_report

    collect = run
    cleanup = run
    clean = run
    sanitize = run

    def snapshot(self) -> Dict[str, Any]:
        return dict(self.last_report)

    # =====================================================
    # CORE CLEANUP
    # =====================================================

    def _collect(self, portfolio) -> Dict[str, Any]:

        before = self._portfolio_counts(portfolio)

        actions: List[Dict[str, Any]] = []

        self._ensure_runtime_fields(portfolio)

        actions.extend(self._normalize_lot_symbols(portfolio))
        actions.extend(self._normalize_position_symbols(portfolio))
        actions.extend(self._purge_empty_lots(portfolio))
        actions.extend(self._repair_positions_from_lots(portfolio))
        actions.extend(self._purge_zero_positions(portfolio))
        actions.extend(self._normalize_last_prices(portfolio))
        actions.extend(self._trim_processed_fill_ids(portfolio))
        actions.extend(self._trim_ledger(portfolio))

        after = self._portfolio_counts(portfolio)

        if hasattr(portfolio, "snapshot"):
            try:
                portfolio.snapshot()
            except Exception:
                pass

        report = self._report(
            status="OK",
            reason="Portfolio garbage collection complete",
            before=before,
            after=after,
            actions=actions,
        )

        return report

    # =====================================================
    # FIELD SAFETY
    # =====================================================

    def _ensure_runtime_fields(self, portfolio) -> None:

        if not hasattr(portfolio, "positions") or portfolio.positions is None:
            portfolio.positions = {}

        if not hasattr(portfolio, "lots") or portfolio.lots is None:
            portfolio.lots = {}

        if not hasattr(portfolio, "last_prices") or portfolio.last_prices is None:
            portfolio.last_prices = {}

        if not hasattr(portfolio, "ledger") or portfolio.ledger is None:
            portfolio.ledger = []

        if (
            not hasattr(portfolio, "processed_fill_ids")
            or portfolio.processed_fill_ids is None
        ):
            portfolio.processed_fill_ids = {}

        if not hasattr(portfolio, "last_event"):
            portfolio.last_event = {}

        if not hasattr(portfolio, "last_error"):
            portfolio.last_error = ""

    # =====================================================
    # SYMBOL NORMALIZATION
    # =====================================================

    def _normalize_lot_symbols(self, portfolio) -> List[Dict[str, Any]]:
        actions = []

        normalized = {}

        for symbol, lots in list(portfolio.lots.items()):
            clean_symbol = self._symbol(symbol)

            if not clean_symbol:
                actions.append(self._action("DROP_LOTS_EMPTY_SYMBOL", symbol=symbol))
                continue

            if clean_symbol not in normalized:
                normalized[clean_symbol] = []

            if isinstance(lots, list):
                normalized[clean_symbol].extend(lots)

            if clean_symbol != symbol:
                actions.append(
                    self._action(
                        "NORMALIZE_LOT_SYMBOL",
                        symbol=symbol,
                        new_symbol=clean_symbol,
                    )
                )

        portfolio.lots = normalized
        return actions

    def _normalize_position_symbols(self, portfolio) -> List[Dict[str, Any]]:
        actions = []

        normalized = {}

        for symbol, position in list(portfolio.positions.items()):
            clean_symbol = self._symbol(symbol)

            if not clean_symbol:
                actions.append(
                    self._action(
                        "DROP_POSITION_EMPTY_SYMBOL",
                        symbol=symbol,
                    )
                )
                continue

            if hasattr(position, "symbol"):
                position.symbol = clean_symbol

            if clean_symbol in normalized:
                existing = normalized[clean_symbol]

                existing_realized = self._get_attr(existing, "realized_pnl", 0.0)
                incoming_realized = self._get_attr(position, "realized_pnl", 0.0)

                self._set_attr(
                    existing,
                    "realized_pnl",
                    float(existing_realized or 0.0) + float(incoming_realized or 0.0),
                )

                actions.append(
                    self._action(
                        "MERGE_DUPLICATE_POSITION",
                        symbol=symbol,
                        new_symbol=clean_symbol,
                    )
                )

            else:
                normalized[clean_symbol] = position

            if clean_symbol != symbol:
                actions.append(
                    self._action(
                        "NORMALIZE_POSITION_SYMBOL",
                        symbol=symbol,
                        new_symbol=clean_symbol,
                    )
                )

        portfolio.positions = normalized
        return actions

    def _normalize_last_prices(self, portfolio) -> List[Dict[str, Any]]:
        actions = []

        normalized = {}

        for symbol, price in list(portfolio.last_prices.items()):
            clean_symbol = self._symbol(symbol)

            if not clean_symbol:
                actions.append(self._action("DROP_PRICE_EMPTY_SYMBOL", symbol=symbol))
                continue

            try:
                price = float(price)
            except Exception:
                actions.append(
                    self._action(
                        "DROP_BAD_PRICE",
                        symbol=symbol,
                        price=price,
                    )
                )
                continue

            if price <= 0:
                actions.append(
                    self._action(
                        "DROP_NONPOSITIVE_PRICE",
                        symbol=symbol,
                        price=price,
                    )
                )
                continue

            normalized[clean_symbol] = price

            if clean_symbol != symbol:
                actions.append(
                    self._action(
                        "NORMALIZE_PRICE_SYMBOL",
                        symbol=symbol,
                        new_symbol=clean_symbol,
                    )
                )

        portfolio.last_prices = normalized
        return actions

    # =====================================================
    # LOT / POSITION CLEANUP
    # =====================================================

    def _purge_empty_lots(self, portfolio) -> List[Dict[str, Any]]:
        actions = []

        for symbol, lots in list(portfolio.lots.items()):
            if not isinstance(lots, list):
                portfolio.lots[symbol] = []
                actions.append(
                    self._action(
                        "RESET_BAD_LOTS_CONTAINER",
                        symbol=symbol,
                    )
                )
                continue

            cleaned = []

            for lot in lots:
                qty = self._get_attr(lot, "qty", 0.0)
                price = self._get_attr(lot, "price", 0.0)

                try:
                    qty = float(qty)
                    price = float(price)
                except Exception:
                    actions.append(self._action("DROP_BAD_LOT", symbol=symbol))
                    continue

                if abs(qty) <= self.EPSILON:
                    actions.append(self._action("DROP_ZERO_LOT", symbol=symbol))
                    continue

                if price <= 0:
                    actions.append(
                        self._action(
                            "DROP_BAD_PRICE_LOT",
                            symbol=symbol,
                            qty=qty,
                            price=price,
                        )
                    )
                    continue

                self._set_attr(lot, "qty", qty)
                self._set_attr(lot, "price", price)

                cleaned.append(lot)

            portfolio.lots[symbol] = cleaned

        return actions

    def _repair_positions_from_lots(self, portfolio) -> List[Dict[str, Any]]:
        """
        Repair position quantity/average price from lots.

        Safety rule:
        Empty lots are NOT authoritative when a valid non-zero position exists.
        Runtime replay/recovery can restore positions and ledger before lot-level
        reconstruction is available. In that state, GC must preserve positions,
        not flatten them to zero.
        """

        actions = []

        all_symbols = set(portfolio.positions.keys()) | set(portfolio.lots.keys())

        for symbol in sorted(all_symbols):
            lots = portfolio.lots.get(symbol, [])
            position = portfolio.positions.get(symbol)

            if not isinstance(lots, list):
                lots = []

            # =================================================
            # HARD SAFETY GUARD
            # Never destroy valid positions because lots are empty.
            # Empty lots can occur after runtime replay/recovery.
            # =================================================

            if position is not None and len(lots) == 0:
                existing_qty = float(
                    self._get_attr(position, "quantity", 0.0) or 0.0
                )
                existing_avg = float(
                    self._get_attr(position, "avg_price", 0.0) or 0.0
                )
                existing_realized = float(
                    self._get_attr(position, "realized_pnl", 0.0) or 0.0
                )

                clean_symbol = self._symbol(symbol)

                self._set_attr(position, "symbol", clean_symbol)
                self._set_attr(position, "quantity", existing_qty)
                self._set_attr(position, "avg_price", existing_avg)
                self._set_attr(position, "realized_pnl", existing_realized)

                if abs(existing_qty) > self.EPSILON:
                    actions.append(
                        self._action(
                            "PRESERVE_POSITION_WITHOUT_LOTS",
                            symbol=clean_symbol,
                            quantity=existing_qty,
                            avg_price=existing_avg,
                            realized_pnl=existing_realized,
                        )
                    )

                    continue

            realized = (
                self._get_attr(position, "realized_pnl", 0.0)
                if position
                else 0.0
            )

            signed_qty = round(
                sum(
                    float(self._get_attr(lot, "qty", 0.0) or 0.0)
                    for lot in lots
                ),
                10,
            )

            avg_price = self._weighted_avg_price(lots)

            if position is None:
                if abs(signed_qty) <= self.EPSILON:
                    continue

                position = self._new_position_like(portfolio, symbol)
                portfolio.positions[symbol] = position

                actions.append(
                    self._action(
                        "CREATE_POSITION_FROM_LOTS",
                        symbol=symbol,
                    )
                )

            old_qty = float(
                self._get_attr(position, "quantity", 0.0) or 0.0
            )

            old_avg = float(
                self._get_attr(position, "avg_price", 0.0) or 0.0
            )

            if abs(old_qty - signed_qty) > self.EPSILON:
                actions.append(
                    self._action(
                        "REPAIR_POSITION_QTY",
                        symbol=symbol,
                        old_qty=old_qty,
                        new_qty=signed_qty,
                    )
                )

            if abs(old_avg - avg_price) > self.EPSILON:
                actions.append(
                    self._action(
                        "REPAIR_POSITION_AVG_PRICE",
                        symbol=symbol,
                        old_avg_price=old_avg,
                        new_avg_price=avg_price,
                    )
                )

            self._set_attr(position, "symbol", symbol)
            self._set_attr(position, "quantity", signed_qty)
            self._set_attr(position, "avg_price", avg_price)
            self._set_attr(position, "realized_pnl", float(realized or 0.0))

        return actions

    def _purge_zero_positions(self, portfolio) -> List[Dict[str, Any]]:
        actions = []

        for symbol, position in list(portfolio.positions.items()):
            qty = float(self._get_attr(position, "quantity", 0.0) or 0.0)
            realized = float(self._get_attr(position, "realized_pnl", 0.0) or 0.0)
            lots = portfolio.lots.get(symbol, [])

            no_lots = not lots or len(lots) == 0
            flat_qty = abs(qty) <= self.EPSILON
            no_realized = abs(realized) <= self.EPSILON

            if flat_qty and no_lots and no_realized:
                portfolio.positions.pop(symbol, None)
                portfolio.lots.pop(symbol, None)
                actions.append(
                    self._action(
                        "PURGE_ZERO_POSITION",
                        symbol=symbol,
                    )
                )

            elif flat_qty and no_lots and not no_realized:
                self._set_attr(position, "quantity", 0.0)
                self._set_attr(position, "avg_price", 0.0)
                portfolio.lots[symbol] = []
                actions.append(
                    self._action(
                        "KEEP_FLAT_REALIZED_POSITION",
                        symbol=symbol,
                        realized_pnl=realized,
                    )
                )

        return actions

    # =====================================================
    # MEMORY LIMITS
    # =====================================================

    def _trim_processed_fill_ids(
        self,
        portfolio,
        max_ids: int = 10000,
    ) -> List[Dict[str, Any]]:
        actions = []

        fill_ids = getattr(portfolio, "processed_fill_ids", {})

        if fill_ids is None:
            fill_ids = {}

        if isinstance(fill_ids, dict):
            normalized = {}

            for key, meta in fill_ids.items():
                if isinstance(meta, dict):
                    normalized[str(key)] = meta
                else:
                    normalized[str(key)] = {
                        "timestamp": 0,
                        "legacy_meta": meta,
                    }

            fill_ids = normalized

        elif isinstance(fill_ids, (set, list, tuple)):
            fill_ids = {
                str(key): {
                    "timestamp": 0,
                    "legacy_source": "converted_by_portfolio_gc",
                }
                for key in fill_ids
            }

            actions.append(self._action("REPAIR_PROCESSED_FILL_ID_DICT"))

        else:
            fill_ids = {}
            actions.append(self._action("RESET_BAD_PROCESSED_FILL_IDS"))

        portfolio.processed_fill_ids = fill_ids

        if len(fill_ids) > max_ids:
            keys = list(fill_ids.keys())[-max_ids:]
            trimmed = {key: fill_ids[key] for key in keys}
            portfolio.processed_fill_ids = trimmed

            actions.append(
                self._action(
                    "TRIM_PROCESSED_FILL_IDS",
                    before=len(fill_ids),
                    after=len(portfolio.processed_fill_ids),
                )
            )

        return actions

    def _trim_ledger(
        self,
        portfolio,
        max_rows: int = 5000,
    ) -> List[Dict[str, Any]]:
        actions = []

        ledger = getattr(portfolio, "ledger", [])

        if not isinstance(ledger, list):
            portfolio.ledger = []
            actions.append(self._action("RESET_BAD_LEDGER"))
            return actions

        if len(ledger) > max_rows:
            before = len(ledger)
            portfolio.ledger = ledger[-max_rows:]

            actions.append(
                self._action(
                    "TRIM_LEDGER",
                    before=before,
                    after=len(portfolio.ledger),
                )
            )

        return actions

    # =====================================================
    # REPORTING
    # =====================================================

    def _portfolio_counts(self, portfolio) -> Dict[str, Any]:
        positions = getattr(portfolio, "positions", {}) or {}
        lots = getattr(portfolio, "lots", {}) or {}
        last_prices = getattr(portfolio, "last_prices", {}) or {}
        ledger = getattr(portfolio, "ledger", []) or []
        processed = getattr(portfolio, "processed_fill_ids", {}) or {}

        nonzero_positions = 0
        total_lots = 0

        for position in positions.values():
            qty = float(self._get_attr(position, "quantity", 0.0) or 0.0)

            if abs(qty) > self.EPSILON:
                nonzero_positions += 1

        for lot_list in lots.values():
            if isinstance(lot_list, list):
                total_lots += len(lot_list)

        return {
            "positions": len(positions),
            "nonzero_positions": nonzero_positions,
            "symbols_with_lots": len(lots),
            "lots": total_lots,
            "prices": len(last_prices),
            "ledger": len(ledger),
            "processed_fills": len(processed),
        }

    def _report(
        self,
        status: str,
        reason: str,
        before: Dict[str, Any] | None = None,
        after: Dict[str, Any] | None = None,
        actions: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:

        actions = actions or []

        return {
            "timestamp": self._now(),
            "status": status,
            "reason": reason,
            "before": before or {},
            "after": after or {},
            "actions": actions,
            "actions_count": len(actions),
        }

    def _action(self, action: str, **kwargs) -> Dict[str, Any]:
        return {
            "timestamp": self._now(),
            "action": action,
            **kwargs,
        }

    # =====================================================
    # DATA HELPERS
    # =====================================================

    def _weighted_avg_price(self, lots: List[Any]) -> float:
        total_qty = 0.0
        total_cost = 0.0

        for lot in lots:
            qty = abs(float(self._get_attr(lot, "qty", 0.0) or 0.0))
            price = float(self._get_attr(lot, "price", 0.0) or 0.0)

            if qty <= self.EPSILON or price <= 0:
                continue

            total_qty += qty
            total_cost += qty * price

        if total_qty <= self.EPSILON:
            return 0.0

        return total_cost / total_qty

    def _new_position_like(self, portfolio, symbol: str):
        """
        Create a Position object compatible with the portfolio engine.
        """

        position_cls = None

        for existing in getattr(portfolio, "positions", {}).values():
            position_cls = existing.__class__
            break

        if position_cls is None:
            try:
                from portfolio.engine import Position as EnginePosition

                position_cls = EnginePosition
            except Exception:
                position_cls = None

        if position_cls is not None:
            try:
                return position_cls(
                    symbol=symbol,
                    quantity=0.0,
                    avg_price=0.0,
                    realized_pnl=0.0,
                )
            except Exception:
                pass

        return {
            "symbol": symbol,
            "quantity": 0.0,
            "avg_price": 0.0,
            "realized_pnl": 0.0,
        }

    def _get_attr(self, obj: Any, key: str, default=None):
        if obj is None:
            return default

        if isinstance(obj, dict):
            return obj.get(key, default)

        return getattr(obj, key, default)

    def _set_attr(self, obj: Any, key: str, value: Any) -> None:
        if isinstance(obj, dict):
            obj[key] = value
        else:
            setattr(obj, key, value)

    def _symbol(self, symbol: Any) -> str:
        return str(symbol or "").upper().strip()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()