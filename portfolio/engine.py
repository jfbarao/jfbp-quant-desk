# =========================================================
# 📊 JFBP PORTFOLIO ENGINE v37.1
# BROKER AUTHORITY REPAIR LAYER + REPLAY TRUTH
# + SUPABASE PORTFOLIO POSITIONS PERSISTENCE
# =========================================================

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import math
import time

try:
    from core.portfolio_db import upsert_position, delete_position
except Exception:  # pragma: no cover
    upsert_position = None
    delete_position = None

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None


@dataclass
class Position:
    symbol: str
    quantity: float = 0.0
    avg_price: float = 0.0
    realized_pnl: float = 0.0


@dataclass
class Lot:
    symbol: str
    qty: float
    price: float
    fill_id: Optional[str] = None
    timestamp: Optional[str] = None


class PortfolioEngine:

    EPSILON = 1e-9
    MAX_LEDGER_ROWS = 10000
    MAX_PROCESSED_FILL_IDS = 25000
    PROCESSED_FILL_TTL_SECONDS = 60 * 60 * 24 * 7

    VALID_ACTIONS = {"BUY", "SELL"}

    COMPLETE_STATUSES = {
        "COMPLETE",
        "FILLED",
        "ORDER_FILLED",
        "DONE",
        "SUCCESS",
        "EXECUTED",
        "EXECUTION_COMPLETE",
    }

    PARTIAL_STATUSES = {
        "PARTIAL",
        "PARTIAL_FILLED",
        "PARTIALLY_FILLED",
        "PARTIAL_FILL",
    }

    NON_FILL_STATUSES = {
        "REJECTED",
        "BLOCKED",
        "ERROR",
        "TIMEOUT",
        "CANCELLED",
        "CANCELED",
        "UNKNOWN",
        "INIT",
        "NEW",
        "ROUTED",
        "ACKNOWLEDGED",
        "WORKING",
        "SKIPPED",
        "",
    }

    TRUTH_SOURCE = "portfolio_engine.v37_1"

    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.lots: Dict[str, List[Lot]] = {}
        self.last_prices: Dict[str, float] = {}
        self.ledger: List[Dict[str, Any]] = []

        self.processed_fill_ids: Dict[str, Dict[str, Any]] = {}
        self.applied_fill_registry: Dict[str, Dict[str, Any]] = {}
        self.execution_registry: Dict[str, Dict[str, Any]] = {}
        self.order_registry: Dict[str, List[str]] = {}

        self.identity_registry: Dict[str, Dict[str, Any]] = {}
        self.broker_order_registry: Dict[str, List[str]] = {}
        self.sequence_registry: Dict[str, Dict[str, Any]] = {}

        self.dedupe_collision_log: List[Dict[str, Any]] = []
        self.rejection_trace: List[Dict[str, Any]] = []
        self.commit_trace: List[Dict[str, Any]] = []

        self.last_event: Dict[str, Any] = {}
        self.last_error = ""
        self.last_reconcile: Dict[str, Any] = {}
        self.last_missing_fill_report: Dict[str, Any] = {}
        self.last_drift_report: Dict[str, Any] = {}
        self.last_identity_report: Dict[str, Any] = {}

        self.last_broker_snapshot_report: Dict[str, Any] = {}
        self.last_broker_drift_report: Dict[str, Any] = {}
        self.last_broker_repair_report: Dict[str, Any] = {}
        self.last_broker_execution_report: Dict[str, Any] = {}

        self.user_id: Optional[str] = None
        self.last_supabase_sync_report: Dict[str, Any] = {}
        self.supabase_sync_trace: List[Dict[str, Any]] = []

    # =====================================================
    # CORE FILL ENTRY
    # =====================================================

    def apply_fill(self, fill: Any) -> Dict[str, Any]:

        self._purge_processed_fill_ids()

        row = self._normalize_fill(fill)

        if not self._is_true_fill(row):
            return self._reject(
                row.get("status") or "REJECTED",
                row,
                reason=row.get("reason") or "Not executable fill",
            )

        symbol = self._symbol(row.get("symbol"))
        action = str(row.get("action") or "").upper().strip()
        qty = self._float(row.get("qty"))
        price = self._float(row.get("price"))

        if not symbol:
            return self._reject(
                "REJECTED",
                row,
                reason="Missing executable symbol",
            )

        if action not in ("BUY", "SELL"):
            return self._reject(
                "REJECTED",
                row,
                reason=f"Unsupported executable action: {action}",
            )

        if qty <= self.EPSILON:
            return self._reject(
                "REJECTED",
                row,
                reason=f"Invalid executable quantity: {qty}",
            )

        if price <= self.EPSILON:
            return self._reject(
                "REJECTED",
                row,
                reason=f"Invalid executable price: {price}",
            )

        row["symbol"] = symbol
        row["action"] = action
        row["qty"] = qty
        row["price"] = price

        mode = str(row.get("mode") or "").upper().strip()
        source = str(row.get("source") or "").lower().strip()
        replay_mode = self._is_replay_mode(row)

        broker_repair = bool(
            row.get("broker_repair")
            or row.get("source") == "broker_execution_repair"
        )

        broker_origin = (
            mode == "LIVE"
            and (
                "ibkr" in source
                or "broker" in source
                or row.get("is_true_fill") is True
            )
        )

        identity_key = row.get("identity_key")
        fill_key = row.get("fill_key")
        execution_key = row.get("execution_key")
        order_key = row.get("order_key")

        # =====================================================
        # HARD LIVE / SIM PARTITION
        # =====================================================

        if mode == "LIVE":
            row["mode"] = "LIVE"

        # Broker-origin LIVE executions must not be replayed as SIM,
        # and SIM/replay fills must not masquerade as broker fills.
        if broker_origin:
            row["source"] = row.get("source") or "ibkr_live_gateway"
            row["is_true_fill"] = True

        # =====================================================
        # DEDUPE
        # =====================================================

        existing = self._find_existing_fill(row)

        if existing:
            result = {
                **row,
                "status": "SKIPPED",
                "execution_status": "SKIPPED",
                "reason": (
                    "Replay fill already applied"
                    if replay_mode
                    else "Fill already applied"
                ),
                "truth_source": self.TRUTH_SOURCE,
                "existing_fill": existing,
                "dedupe_truth": {
                    "identity_key": identity_key,
                    "fill_key": fill_key,
                    "execution_key": execution_key,
                    "order_key": order_key,
                    "identity_source": row.get("identity_source"),
                    "replay_mode": replay_mode,
                    "mode": mode,
                    "broker_origin": broker_origin,
                },
            }

            self.last_event = result
            self.last_error = ""
            return result

        collision = self._detect_identity_collision(row)

        if collision and not replay_mode and not broker_repair:
            self.dedupe_collision_log.append(collision)
            self.last_identity_report = collision

            return self._reject(
                "DUPLICATE_COLLISION",
                row,
                reason="Fill identity collision detected",
            )

        old_pos = self.positions.get(symbol)

        old_qty = self._float(old_pos.quantity) if old_pos else 0.0
        old_avg = self._float(old_pos.avg_price) if old_pos else 0.0
        old_realized = self._float(old_pos.realized_pnl) if old_pos else 0.0

        signed_fill_qty = qty if action == "BUY" else -qty

        (
            new_qty,
            new_avg,
            realized_delta,
            lifecycle_stage,
        ) = self._apply_position_math(
            old_qty=old_qty,
            old_avg=old_avg,
            fill_qty=signed_fill_qty,
            fill_price=price,
        )

        new_qty = self._clean_zero(new_qty)
        new_avg = self._float(new_avg)
        realized_delta = self._float(realized_delta)
        new_realized = self._float(old_realized + realized_delta)

        source_status = str(
            row.get("status")
            or row.get("execution_status")
            or ""
        ).upper().strip()

        terminal_status = (
            "PARTIAL"
            if source_status in self.PARTIAL_STATUSES or row.get("partial_fill")
            else "COMPLETE"
        )

        ledger_row = {
            **row,
            "symbol": symbol,
            "action": action,
            "side": action,
            "qty": qty,
            "quantity": qty,
            "price": price,
            "fill_price": price,
            "execution_price": price,
            "position_before": old_qty,
            "position_after": new_qty,
            "avg_before": old_avg,
            "avg_after": new_avg,
            "realized_delta": realized_delta,
            "realized_total": new_realized,
            "lifecycle_stage": lifecycle_stage,
            "execution_status": terminal_status,
            "status": terminal_status,
            "mode": mode or row.get("mode"),
            "source": row.get("source"),
            "broker_origin": broker_origin,
            "broker_repair": broker_repair,
            "replay_mode": replay_mode,
            "truth_source": self.TRUTH_SOURCE,
        }

        # =====================================================
        # COMMIT MUTATION
        # =====================================================

        self._set_position(
            symbol=symbol,
            quantity=new_qty,
            avg_price=new_avg,
            realized_pnl=new_realized,
        )

        # Persist the authoritative position snapshot to Supabase.
        # This keeps core.portfolio_positions aligned after OMS fills.
        self.persist_symbol_position(symbol=symbol, source_row=ledger_row)

        self.last_prices[symbol] = price

        self._update_lots(
            symbol=symbol,
            action=action,
            qty=qty,
            price=price,
            fill_id=identity_key,
            timestamp=row["timestamp"],
        )

        self.ledger.append(ledger_row)

        if len(self.ledger) > self.MAX_LEDGER_ROWS:
            self.ledger = self.ledger[-self.MAX_LEDGER_ROWS:]

        meta = {
            "symbol": symbol,
            "action": action,
            "side": action,
            "qty": qty,
            "quantity": qty,
            "price": price,
            "timestamp": row["timestamp"],
            "timestamp_epoch": time.time(),
            "execution_key": execution_key,
            "identity_key": identity_key,
            "fill_key": fill_key,
            "order_key": order_key,
            "identity_source": row.get("identity_source"),
            "broker_order_id": row.get("broker_order_id"),
            "order_id": row.get("order_id"),
            "perm_id": row.get("perm_id"),
            "partial_fill": row.get("partial_fill"),
            "partial_sequence": row.get("partial_sequence"),
            "cumulative_filled_qty": row.get("cumulative_filled_qty"),
            "remaining_qty": row.get("remaining_qty"),
            "mode": mode or row.get("mode"),
            "source": row.get("source"),
            "broker_origin": broker_origin,
            "broker_repair": broker_repair,
            "status": terminal_status,
            "replay_mode": replay_mode,
            "truth_source": self.TRUTH_SOURCE,
        }

        self._register_fill_identity(row, meta)

        self.commit_trace.append({
            "timestamp": self._now(),
            "status": "COMMITTED",
            "symbol": symbol,
            "action": action,
            "qty": qty,
            "price": price,
            "execution_key": execution_key,
            "identity_key": identity_key,
            "ledger_count": len(self.ledger),
            "mode": mode or row.get("mode"),
            "source": row.get("source"),
            "broker_origin": broker_origin,
            "broker_repair": broker_repair,
            "replay_mode": replay_mode,
            "truth_source": self.TRUTH_SOURCE,
        })

        self.last_event = ledger_row
        self.last_error = ""

        return ledger_row

    def process_fill(self, fill: Any) -> Dict[str, Any]:
        return self.apply_fill(fill)
    
    # =====================================================
    # POSITION MATH
    # =====================================================

    def _apply_position_math(
        self,
        old_qty: float,
        old_avg: float,
        fill_qty: float,
        fill_price: float,
    ) -> Tuple[float, float, float, str]:

        old_qty = self._float(old_qty)
        old_avg = self._float(old_avg)
        fill_qty = self._float(fill_qty)
        fill_price = self._float(fill_price)

        if abs(old_qty) < self.EPSILON:
            return fill_qty, fill_price, 0.0, "OPEN_NEW"

        if old_qty * fill_qty > 0:
            new_qty = old_qty + fill_qty
            total_cost = abs(old_qty) * old_avg + abs(fill_qty) * fill_price
            new_avg = total_cost / abs(new_qty)

            return new_qty, new_avg, 0.0, "ADD_SAME_DIRECTION"

        close_qty = min(abs(old_qty), abs(fill_qty))

        if old_qty > 0:
            realized = (fill_price - old_avg) * close_qty
        else:
            realized = (old_avg - fill_price) * close_qty

        remaining = old_qty + fill_qty

        if abs(remaining) < self.EPSILON:
            return 0.0, 0.0, realized, "FULL_CLOSE"

        if old_qty * remaining > 0:
            return remaining, old_avg, realized, "PARTIAL_REDUCTION"

        return remaining, fill_price, realized, "FLIP_POSITION"

    # =====================================================
    # LOT ENGINE
    # =====================================================

    def _update_lots(
        self,
        symbol: str,
        action: str,
        qty: float,
        price: float,
        fill_id: Optional[str],
        timestamp: Optional[str],
    ):

        pos = self.positions.get(symbol)

        if pos is None or abs(pos.quantity) < self.EPSILON:
            self.lots[symbol] = []
            return

        self.lots[symbol] = [
            Lot(
                symbol=symbol,
                qty=pos.quantity,
                price=pos.avg_price,
                fill_id=fill_id,
                timestamp=timestamp or self._now(),
            )
        ]

    def _set_position(
        self,
        symbol: str,
        quantity: float,
        avg_price: float,
        realized_pnl: float,
    ) -> None:

        quantity = self._clean_zero(quantity)
        avg_price = self._float(avg_price)
        realized_pnl = self._float(realized_pnl)

        if abs(quantity) < self.EPSILON:
            if abs(realized_pnl) < self.EPSILON:
                self.positions.pop(symbol, None)
                self.lots[symbol] = []
                return

            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=0.0,
                avg_price=0.0,
                realized_pnl=realized_pnl,
            )
            self.lots[symbol] = []
            return

        self.positions[symbol] = Position(
            symbol=symbol,
            quantity=quantity,
            avg_price=avg_price,
            realized_pnl=realized_pnl,
        )

    # =====================================================
    # SNAPSHOTS
    # =====================================================

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        self.reconcile_positions()

        rows: Dict[str, Dict[str, Any]] = {}

        for symbol, pos in sorted(self.positions.items()):
            qty = self._clean_zero(pos.quantity)

            if abs(qty) < self.EPSILON and abs(pos.realized_pnl) < self.EPSILON:
                continue

            last_price = self.last_prices.get(symbol, pos.avg_price)

            if last_price <= 0:
                last_price = pos.avg_price

            unrealized = self.get_unrealized_pnl(symbol)
            realized = pos.realized_pnl
            total = realized + unrealized

            rows[symbol] = {
                "symbol": symbol,
                "side": self._side_from_qty(qty),
                "qty": abs(qty),
                "signed_qty": qty,
                "avg_price": round(pos.avg_price, 6),
                "last_price": round(last_price, 6),
                "position_value": round(abs(qty) * last_price, 6),
                "unrealized_pnl": round(unrealized, 6),
                "realized_pnl": round(realized, 6),
                "total_pnl": round(total, 6),
            }

        return rows

    def positions_snapshot(self):
        return self.snapshot()

    def ledger_snapshot(self):
        return list(self.ledger)

    def lots_snapshot(self):
        return {
            symbol: [
                asdict(lot) if isinstance(lot, Lot) else dict(lot)
                for lot in lots
            ]
            for symbol, lots in self.lots.items()
        }

    def applied_fills_snapshot(self):
        return dict(self.applied_fill_registry)

    def identity_snapshot(self):
        return dict(self.identity_registry)

    def collision_snapshot(self):
        return list(self.dedupe_collision_log)

    def rejection_snapshot(self):
        return list(self.rejection_trace)

    def commit_snapshot(self):
        return list(self.commit_trace)

    def broker_snapshot_report(self):
        return dict(self.last_broker_snapshot_report)

    def broker_drift_report(self):
        return dict(self.last_broker_drift_report)

    def broker_repair_report(self):
        return dict(self.last_broker_repair_report)

    def broker_execution_report(self):
        return dict(self.last_broker_execution_report)

    def supabase_sync_report(self):
        return dict(self.last_supabase_sync_report)

    def supabase_sync_snapshot(self):
        return list(self.supabase_sync_trace)

    def set_user_id(self, user_id: Any):
        self.user_id = str(user_id or "").strip() or None
        return self.user_id

    def _resolve_user_id(self, row: Optional[Dict[str, Any]] = None) -> Optional[str]:
        row = row if isinstance(row, dict) else {}

        for key in (
            "user_id",
            "supabase_user_id",
            "auth_user_id",
            "account_user_id",
            "owner_id",
        ):
            value = row.get(key)
            if value:
                return str(value).strip()

        if self.user_id:
            return str(self.user_id).strip()

        if st is not None:
            try:
                session_state = getattr(st, "session_state", {})
                for key in (
                    "user_id",
                    "supabase_user_id",
                    "auth_user_id",
                    "jfbp_user_id",
                    "current_user_id",
                    "account_user_id",
                ):
                    value = session_state.get(key)
                    if value:
                        return str(value).strip()

                for key in ("user", "current_user", "auth_user", "session_user"):
                    value = session_state.get(key)
                    if isinstance(value, dict):
                        for subkey in ("id", "user_id", "sub", "uuid"):
                            subvalue = value.get(subkey)
                            if subvalue:
                                return str(subvalue).strip()
                    elif value is not None:
                        subvalue = getattr(value, "id", None)
                        if subvalue:
                            return str(subvalue).strip()
            except Exception:
                return None

        return None

    def persist_symbol_position(
        self,
        symbol: str,
        source_row: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        symbol = self._symbol(symbol)
        source_row = source_row if isinstance(source_row, dict) else {}

        user_id = self._resolve_user_id(source_row)

        if not user_id:
            report = {
                "timestamp": self._now(),
                "status": "SKIPPED",
                "reason": "Missing user_id for Supabase portfolio persistence",
                "symbol": symbol,
                "truth_source": self.TRUTH_SOURCE,
            }
            self.last_supabase_sync_report = report
            self.supabase_sync_trace.append(report)
            self.supabase_sync_trace = self.supabase_sync_trace[-250:]
            return report

        pos = self.positions.get(symbol)
        last_price = self._float(
            self.last_prices.get(symbol)
            or source_row.get("price")
            or source_row.get("fill_price")
            or source_row.get("execution_price")
            or (pos.avg_price if pos else 0.0)
        )

        if pos is None or abs(self._float(pos.quantity)) < self.EPSILON:
            if delete_position is None:
                report = {
                    "timestamp": self._now(),
                    "status": "SKIPPED",
                    "reason": "core.portfolio_db.delete_position unavailable",
                    "user_id": user_id,
                    "symbol": symbol,
                    "truth_source": self.TRUTH_SOURCE,
                }
            else:
                try:
                    delete_position(user_id=user_id, symbol=symbol)
                    report = {
                        "timestamp": self._now(),
                        "status": "DELETED",
                        "user_id": user_id,
                        "symbol": symbol,
                        "shares": 0.0,
                        "truth_source": self.TRUTH_SOURCE,
                    }
                except Exception as exc:
                    report = {
                        "timestamp": self._now(),
                        "status": "ERROR",
                        "reason": str(exc),
                        "user_id": user_id,
                        "symbol": symbol,
                        "truth_source": self.TRUTH_SOURCE,
                    }

            self.last_supabase_sync_report = report
            self.supabase_sync_trace.append(report)
            self.supabase_sync_trace = self.supabase_sync_trace[-250:]
            return report

        shares = self._float(pos.quantity)
        avg_price = self._float(pos.avg_price)
        realized_pnl = self._float(pos.realized_pnl)

        if last_price <= 0:
            last_price = avg_price

        cost_basis = shares * avg_price
        market_value = shares * last_price

        if upsert_position is None:
            report = {
                "timestamp": self._now(),
                "status": "SKIPPED",
                "reason": "core.portfolio_db.upsert_position unavailable",
                "user_id": user_id,
                "symbol": symbol,
                "shares": shares,
                "truth_source": self.TRUTH_SOURCE,
            }
        else:
            try:
                print("SUPABASE POSITION SAVE:", user_id, symbol, shares, avg_price)
                upsert_position(
                    user_id=user_id,
                    symbol=symbol,
                    shares=shares,
                    cost_basis=cost_basis,
                    market_value=market_value,
                    avg_price=avg_price,
                    realized_pnl=realized_pnl,
                )
                report = {
                    "timestamp": self._now(),
                    "status": "UPSERTED",
                    "user_id": user_id,
                    "symbol": symbol,
                    "shares": shares,
                    "cost_basis": cost_basis,
                    "market_value": market_value,
                    "avg_price": avg_price,
                    "realized_pnl": realized_pnl,
                    "truth_source": self.TRUTH_SOURCE,
                }
            except Exception as exc:

                print("SUPABASE POSITION SAVE ERROR:", repr(exc))

                report = {
                    "timestamp": self._now(),
                    "status": "ERROR",
                    "reason": str(exc),
                    "user_id": user_id,
                    "symbol": symbol,
                    "shares": shares,
                    "truth_source": self.TRUTH_SOURCE,
                }

        self.last_supabase_sync_report = report
        self.supabase_sync_trace.append(report)
        self.supabase_sync_trace = self.supabase_sync_trace[-250:]
        return report

    def persist_all_positions(self, user_id: Optional[Any] = None) -> Dict[str, Any]:
        if user_id:
            self.set_user_id(user_id)

        self.reconcile_positions()

        reports = []
        for symbol in sorted(self.positions.keys()):
            reports.append(self.persist_symbol_position(symbol=symbol))

        final = {
            "timestamp": self._now(),
            "status": "OK" if not any(r.get("status") == "ERROR" for r in reports) else "PARTIAL_ERROR",
            "positions": len(reports),
            "reports": reports,
            "truth_source": self.TRUTH_SOURCE,
        }
        self.last_supabase_sync_report = final
        return final

    def risk_positions(self):
        self.reconcile_positions()
        return self.risk_positions_no_reconcile()

    def risk_positions_no_reconcile(self):
        return {
            symbol: pos.quantity
            for symbol, pos in self.positions.items()
            if abs(pos.quantity) > self.EPSILON
        }

    def get_position(self, symbol):
        symbol = self._symbol(symbol)
        return self.positions.get(symbol)

    def position_qty(self, symbol):
        pos = self.get_position(symbol)
        return pos.quantity if pos else 0.0

    def get_all_positions(self):
        return self.risk_positions()

    def open_positions_count(self):
        return len(self.risk_positions_no_reconcile())

    # =====================================================
    # BROKER AUTHORITY REPAIR LAYER
    # =====================================================

    def _broker_rows(self, data: Any) -> List[Dict[str, Any]]:

        if data is None:
            return []

        if hasattr(data, "to_dict"):
            try:
                return list(data.to_dict("records"))
            except Exception:
                pass

        if isinstance(data, dict):
            rows = []

            for key, value in data.items():
                if isinstance(value, dict):
                    row = dict(value)
                    row.setdefault("symbol", key)
                    rows.append(row)
                else:
                    rows.append({
                        "symbol": key,
                        "position": value,
                    })

            return rows

        try:
            return [
                dict(row) if isinstance(row, dict) else dict(vars(row))
                for row in list(data)
            ]
        except Exception:
            return []

    def _is_broker_live_fill(self, row: Dict[str, Any]) -> bool:

        if not isinstance(row, dict):
            return False

        source = str(row.get("source") or "").lower().strip()
        mode = str(row.get("mode") or "").upper().strip()

        exec_id = str(
            row.get("exec_id")
            or row.get("execution_id")
            or row.get("execution_key")
            or ""
        ).strip()

        if mode and mode != "LIVE":
            return False

        if not exec_id:
            return False

        return (
            "ibkr" in source
            or "broker" in source
            or row.get("is_true_fill") is True
        )

    def normalize_broker_positions(
        self,
        broker_positions: Any,
    ) -> Dict[str, Dict[str, Any]]:

        normalized: Dict[str, Dict[str, Any]] = {}

        for row in self._broker_rows(broker_positions):
            if not isinstance(row, dict):
                continue

            symbol = self._symbol(row.get("symbol"))

            if not symbol:
                continue

            qty = self._float(
                row.get("signed_qty")
                if row.get("signed_qty") is not None
                else row.get("position")
                if row.get("position") is not None
                else row.get("quantity")
                if row.get("quantity") is not None
                else row.get("qty")
                if row.get("qty") is not None
                else 0.0
            )

            avg_price = self._float(
                row.get("avg_price")
                if row.get("avg_price") is not None
                else row.get("avg_cost")
                if row.get("avg_cost") is not None
                else row.get("avgCost")
                if row.get("avgCost") is not None
                else row.get("price")
                if row.get("price") is not None
                else 0.0
            )

            if abs(qty) <= self.EPSILON:
                continue

            normalized[symbol] = {
                "symbol": symbol,
                "side": self._side_from_qty(qty),
                "qty": abs(qty),
                "quantity": abs(qty),
                "signed_qty": qty,
                "position": qty,
                "avg_price": avg_price,
                "avg_cost": avg_price,
                "account": row.get("account", ""),
                "currency": row.get("currency", ""),
                "exchange": row.get("exchange", ""),
                "sec_type": row.get("sec_type") or row.get("secType") or "",
                "con_id": row.get("con_id") or row.get("conId") or "",
                "source": row.get("source") or "broker_snapshot",
                "truth_source": row.get("truth_source") or "broker",
            }

        return normalized

    def detect_broker_drift(
        self,
        broker_positions: Any,
        tolerance: float = 1e-6,
    ) -> Dict[str, Any]:

        self.reconcile_positions()

        broker = self.normalize_broker_positions(broker_positions)
        runtime = self.snapshot()

        broker_symbols = set(broker.keys())
        runtime_symbols = set(runtime.keys())

        drift_rows = []

        for symbol in sorted(runtime_symbols - broker_symbols):
            runtime_qty = self._float(runtime[symbol].get("signed_qty"))

            if abs(runtime_qty) > tolerance:
                drift_rows.append({
                    "type": "MISSING_IN_BROKER",
                    "symbol": symbol,
                    "broker_qty": 0.0,
                    "runtime_qty": runtime_qty,
                    "delta": -runtime_qty,
                    "severity": "HIGH",
                })

        for symbol in sorted(broker_symbols - runtime_symbols):
            broker_qty = self._float(broker[symbol].get("signed_qty"))

            if abs(broker_qty) > tolerance:
                drift_rows.append({
                    "type": "UNEXPECTED_IN_BROKER",
                    "symbol": symbol,
                    "broker_qty": broker_qty,
                    "runtime_qty": 0.0,
                    "delta": broker_qty,
                    "severity": "HIGH",
                })

        for symbol in sorted(broker_symbols & runtime_symbols):
            broker_qty = self._float(broker[symbol].get("signed_qty"))
            runtime_qty = self._float(runtime[symbol].get("signed_qty"))

            if abs(broker_qty - runtime_qty) > tolerance:
                drift_rows.append({
                    "type": "QTY_MISMATCH",
                    "symbol": symbol,
                    "broker_qty": broker_qty,
                    "runtime_qty": runtime_qty,
                    "delta": broker_qty - runtime_qty,
                    "severity": "HIGH",
                })

        report = {
            "timestamp": self._now(),
            "status": "MATCH" if not drift_rows else "DRIFT",
            "broker_positions": len(broker),
            "runtime_positions": len(runtime),
            "drift_rows": drift_rows,
            "drift_count": len(drift_rows),
            "broker_truth": broker,
            "runtime_truth": runtime,
            "truth_source": self.TRUTH_SOURCE,
        }

        self.last_broker_drift_report = report
        return report

    def rebuild_from_broker_snapshot(
        self,
        broker_positions: Any,
        dry_run: bool = True,
        preserve_realized_pnl: bool = True,
        preserve_ledger: bool = True,
    ) -> Dict[str, Any]:

        broker = self.normalize_broker_positions(broker_positions)
        before = self.snapshot()

        if not broker:
            report = {
                "timestamp": self._now(),
                "status": "ABORTED",
                "reason": "Empty broker snapshot. Runtime rebuild refused.",
                "before": before,
                "after": before,
                "dry_run": dry_run,
                "truth_source": self.TRUTH_SOURCE,
            }

            self.last_broker_repair_report = report
            return report

        realized_by_symbol = {
            symbol: self._float(pos.realized_pnl)
            for symbol, pos in self.positions.items()
        }

        actions = []

        for symbol, row in sorted(broker.items()):
            old = before.get(symbol, {})

            actions.append({
                "action": "REBUILD_POSITION_FROM_BROKER",
                "symbol": symbol,
                "old_qty": self._float(old.get("signed_qty")),
                "new_qty": self._float(row.get("signed_qty")),
                "old_avg_price": self._float(old.get("avg_price")),
                "new_avg_price": self._float(row.get("avg_price")),
            })

        for symbol in sorted(set(before.keys()) - set(broker.keys())):
            actions.append({
                "action": "DROP_RUNTIME_POSITION_NOT_IN_BROKER",
                "symbol": symbol,
                "old_qty": self._float(before[symbol].get("signed_qty")),
                "new_qty": 0.0,
            })

        if not dry_run:
            old_ledger = list(self.ledger)

            self.positions = {}
            self.lots = {}

            if not preserve_ledger:
                self.ledger = []

            for symbol, row in sorted(broker.items()):
                qty = self._float(row.get("signed_qty"))
                avg_price = self._float(row.get("avg_price"))

                realized = (
                    realized_by_symbol.get(symbol, 0.0)
                    if preserve_realized_pnl
                    else 0.0
                )

                self._set_position(
                    symbol=symbol,
                    quantity=qty,
                    avg_price=avg_price,
                    realized_pnl=realized,
                )

                self.lots[symbol] = [
                    Lot(
                        symbol=symbol,
                        qty=qty,
                        price=avg_price,
                        fill_id="BROKER_REBUILD",
                        timestamp=self._now(),
                    )
                ]

                if avg_price > 0:
                    self.last_prices[symbol] = avg_price

            if preserve_ledger:
                self.ledger = old_ledger

            self.reconcile_positions()

        after = self.snapshot() if not dry_run else before

        report = {
            "timestamp": self._now(),
            "status": "DRY_RUN" if dry_run else "APPLIED",
            "broker_positions": len(broker),
            "actions": actions,
            "actions_count": len(actions),
            "before": before,
            "after": after,
            "dry_run": dry_run,
            "preserve_realized_pnl": preserve_realized_pnl,
            "preserve_ledger": preserve_ledger,
            "truth_source": self.TRUTH_SOURCE,
        }

        self.last_broker_repair_report = report
        return report

    def flatten_runtime_orphans(
        self,
        broker_positions: Any = None,
        dry_run: bool = True,
        preserve_realized_pnl: bool = True,
        preserve_ledger: bool = True,
        tolerance: float = 1e-6,
        **kwargs,
    ) -> Dict[str, Any]:

        broker = self.normalize_broker_positions(broker_positions)
        before = self.snapshot()

        if not broker:
            report = {
                "timestamp": self._now(),
                "status": "ABORTED",
                "reason": "Empty broker snapshot. Runtime orphan flatten refused.",
                "before": before,
                "after": before,
                "dry_run": dry_run,
                "preserve_realized_pnl": preserve_realized_pnl,
                "preserve_ledger": preserve_ledger,
                "orphan_count": 0,
                "actions": [],
                "truth_source": self.TRUTH_SOURCE,
            }

            self.last_broker_repair_report = report
            return report

        broker_symbols = set(broker.keys())
        orphan_symbols = []

        for symbol, row in sorted(before.items()):
            runtime_qty = self._float(row.get("signed_qty"))

            if symbol not in broker_symbols and abs(runtime_qty) > tolerance:
                orphan_symbols.append(symbol)

        actions = []

        for symbol in orphan_symbols:
            old = before.get(symbol, {})
            pos = self.positions.get(symbol)
            realized = self._float(pos.realized_pnl) if pos else 0.0

            actions.append({
                "action": "FLATTEN_RUNTIME_ORPHAN",
                "symbol": symbol,
                "old_qty": self._float(old.get("signed_qty")),
                "new_qty": 0.0,
                "old_avg_price": self._float(old.get("avg_price")),
                "realized_pnl_preserved": realized if preserve_realized_pnl else 0.0,
            })

        if not dry_run:
            old_ledger = list(self.ledger)

            for symbol in orphan_symbols:
                pos = self.positions.get(symbol)

                realized = (
                    self._float(pos.realized_pnl)
                    if pos and preserve_realized_pnl
                    else 0.0
                )

                self._set_position(
                    symbol=symbol,
                    quantity=0.0,
                    avg_price=0.0,
                    realized_pnl=realized,
                )

                self.lots[symbol] = []

            if preserve_ledger:
                self.ledger = old_ledger

            self.reconcile_positions()

        after = self.snapshot() if not dry_run else before

        report = {
            "timestamp": self._now(),
            "status": "DRY_RUN" if dry_run else "APPLIED",
            "before": before,
            "after": after,
            "dry_run": dry_run,
            "preserve_realized_pnl": preserve_realized_pnl,
            "preserve_ledger": preserve_ledger,
            "broker_positions": len(broker),
            "runtime_positions": len(before),
            "orphan_count": len(orphan_symbols),
            "orphan_symbols": orphan_symbols,
            "actions": actions,
            "actions_count": len(actions),
            "truth_source": self.TRUTH_SOURCE,
        }

        self.last_broker_repair_report = report
        return report

    def _append_broker_fill_to_ledger_only(
        self,
        row: Dict[str, Any],
    ) -> Dict[str, Any]:

        replay = dict(row)

        replay["mode"] = "LIVE"
        replay["broker_repair"] = True
        replay["ledger_repair"] = True
        replay["runtime_rebuild"] = False
        replay["audit_rebuild"] = True
        replay["replay_mode"] = False
        replay["force_apply"] = True
        replay["source"] = replay.get("source") or "broker_execution_repair"

        replay.setdefault("timestamp", self._now())
        replay.setdefault("status", replay.get("execution_status") or "FILLED")
        replay.setdefault("execution_status", replay.get("status") or "FILLED")

        symbol = self._symbol(replay.get("symbol"))
        action = str(replay.get("action") or replay.get("side") or "").upper().strip()

        qty = self._float(
            replay.get("qty")
            if replay.get("qty") is not None
            else replay.get("quantity")
            if replay.get("quantity") is not None
            else replay.get("filled_qty")
            if replay.get("filled_qty") is not None
            else 0.0
        )

        price = self._float(
            replay.get("price")
            if replay.get("price") is not None
            else replay.get("fill_price")
            if replay.get("fill_price") is not None
            else replay.get("execution_price")
            if replay.get("execution_price") is not None
            else 0.0
        )

        replay["symbol"] = symbol
        replay["action"] = action
        replay["side"] = action
        replay["qty"] = qty
        replay["quantity"] = qty
        replay["filled_qty"] = qty
        replay["price"] = price
        replay["fill_price"] = price
        replay["execution_price"] = price

        identity_key = str(
            replay.get("identity_key")
            or replay.get("execution_key")
            or replay.get("fill_key")
            or replay.get("exec_id")
            or replay.get("execution_id")
            or ""
        ).strip()

        if not identity_key:
            identity_key = f"{symbol}:{action}:{qty}:{price}:{replay.get('timestamp')}"

        replay["identity_key"] = identity_key

        self.ledger.append(replay)

        return {
            "status": "COMPLETE",
            "repair_type": "LEDGER_ONLY",
            "identity_key": identity_key,
            "symbol": symbol,
            "action": action,
            "qty": qty,
            "price": price,
            "reason": "Broker fill restored to portfolio ledger without mutating positions.",
        }

    def broker_execution_repair(
        self,
        broker_fills: Any,
        audit_fills: Optional[List[Dict[str, Any]]] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:

        broker_rows = []

        for fill in self._broker_rows(broker_fills):
            row = self._normalize_fill(fill)

            if self._is_broker_live_fill(row):
                broker_rows.append(row)

        ledger_rows = [
            self._normalize_fill(row)
            for row in self.ledger
            if self._is_broker_live_fill(self._normalize_fill(row))
        ]

        broker_map = self._identity_map(broker_rows)
        ledger_map = self._identity_map(ledger_rows)

        missing = []
        applied = []
        skipped = []
        rejected = []

        for key, row in sorted(broker_map.items()):

            if key in ledger_map:
                skipped.append({
                    "identity_key": key,
                    "symbol": row.get("symbol"),
                    "reason": "Already in LIVE portfolio ledger",
                })
                continue

            missing.append(row)

            if dry_run:
                continue

            try:
                result = self._append_broker_fill_to_ledger_only(row)

                if result.get("status") in ("COMPLETE", "PARTIAL"):
                    applied.append(result)
                elif result.get("status") == "SKIPPED":
                    skipped.append(result)
                else:
                    rejected.append(result)

            except Exception as exc:
                rejected.append({
                    "identity_key": key,
                    "symbol": row.get("symbol"),
                    "status": "ERROR",
                    "reason": str(exc),
                })

        report = {
            "timestamp": self._now(),
            "status": (
                "DRY_RUN"
                if dry_run
                else "APPLIED"
                if not rejected
                else "PARTIAL_REPAIR"
            ),
            "broker_fills": len(broker_rows),
            "ledger_fills": len(ledger_rows),
            "missing_in_ledger": missing,
            "missing_count": len(missing),
            "applied": applied,
            "applied_count": len(applied),
            "skipped": skipped,
            "skipped_count": len(skipped),
            "rejected": rejected,
            "rejected_count": len(rejected),
            "dry_run": dry_run,
            "repair_mode": "LEDGER_ONLY",
            "truth_source": self.TRUTH_SOURCE,
        }

        self.last_broker_execution_report = report
        return report

    def repair_from_broker_truth(
        self,
        broker_positions: Any,
        broker_fills: Optional[Any] = None,
        audit_fills: Optional[List[Dict[str, Any]]] = None,
        dry_run: bool = True,
        mode: str = "HYBRID_CONSENSUS",
    ) -> Dict[str, Any]:

        mode = str(mode or "HYBRID_CONSENSUS").upper().strip()

        broker = self.normalize_broker_positions(broker_positions)
        before = self.snapshot()

        if not broker and mode != "BROKER_EXECUTIONS_ONLY":
            report = {
                "timestamp": self._now(),
                "status": "ABORTED",
                "mode": mode,
                "dry_run": dry_run,
                "reason": "Empty broker snapshot. Broker repair refused.",
                "before": before,
                "after": before,
                "truth_source": self.TRUTH_SOURCE,
            }

            self.last_broker_repair_report = report
            return report

        execution_report = {}

        if broker_fills is not None:
            execution_report = self.broker_execution_repair(
                broker_fills=broker_fills,
                audit_fills=audit_fills,
                dry_run=dry_run,
            )

        drift_report = self.detect_broker_drift(broker)

        position_report = {
            "status": "SKIPPED",
            "reason": "No position rebuild requested",
        }

        if mode in ("BROKER_POSITIONS_ONLY", "HYBRID_CONSENSUS"):
            if drift_report.get("status") == "MATCH":
                position_report = {
                    "status": "SKIPPED",
                    "reason": "Broker/runtime positions already match",
                }
            else:
                position_report = self.rebuild_from_broker_snapshot(
                    broker_positions=broker,
                    dry_run=dry_run,
                    preserve_realized_pnl=True,
                    preserve_ledger=True,
                )

        elif mode == "BROKER_EXECUTIONS_ONLY":
            position_report = {
                "status": "SKIPPED",
                "reason": "Mode is BROKER_EXECUTIONS_ONLY",
            }

        else:
            position_report = {
                "status": "ERROR",
                "reason": f"Unsupported repair mode: {mode}",
            }

        after = self.snapshot()

        final_status = "DRY_RUN" if dry_run else "APPLIED"

        if position_report.get("status") in ("ERROR", "ABORTED"):
            final_status = position_report.get("status")

        report = {
            "timestamp": self._now(),
            "status": final_status,
            "mode": mode,
            "dry_run": dry_run,
            "before": before,
            "after": after,
            "drift_report": drift_report,
            "execution_report": execution_report,
            "position_report": position_report,
            "truth_source": self.TRUTH_SOURCE,
        }

        self.last_broker_repair_report = report
        return report

    # =====================================================
    # P&L
    # =====================================================

    def get_unrealized_pnl(self, symbol):
        symbol = self._symbol(symbol)
        pos = self.positions.get(symbol)

        if not pos or abs(pos.quantity) < self.EPSILON:
            return 0.0

        last_price = self.last_prices.get(symbol, pos.avg_price)

        if last_price <= 0:
            last_price = pos.avg_price

        if last_price <= 0:
            return 0.0

        return (last_price - pos.avg_price) * pos.quantity

    def get_total_pnl(self, symbol=None):

        if symbol:
            symbol = self._symbol(symbol)
            pos = self.positions.get(symbol)

            if not pos:
                return 0.0

            return pos.realized_pnl + self.get_unrealized_pnl(symbol)

        return sum(
            pos.realized_pnl + self.get_unrealized_pnl(symbol)
            for symbol, pos in self.positions.items()
        )

    def realized_pnl(self):
        return sum(
            self._float(pos.realized_pnl)
            for pos in self.positions.values()
        )

    def unrealized_pnl(self):
        return sum(
            self.get_unrealized_pnl(symbol)
            for symbol in self.positions
        )

    # =====================================================
    # EXPOSURE SNAPSHOT
    # =====================================================

    def exposure_snapshot(self):

        self.reconcile_positions()

        gross_exposure = 0.0
        long_exposure = 0.0
        short_exposure = 0.0

        realized_pnl = 0.0
        unrealized_pnl = 0.0

        long_positions = 0
        short_positions = 0

        for symbol, pos in self.positions.items():

            qty = self._float(pos.quantity)

            if abs(qty) < self.EPSILON:
                continue

            avg_price = self._float(pos.avg_price)

            last_price = self._float(
                self.last_prices.get(symbol, avg_price)
            )

            if last_price <= 0:
                last_price = avg_price

            if last_price <= 0:
                continue

            market_value = abs(qty) * last_price

            gross_exposure += market_value

            if qty > 0:
                long_exposure += market_value
                long_positions += 1

            elif qty < 0:
                short_exposure += market_value
                short_positions += 1

            realized_pnl += self._float(pos.realized_pnl)
            unrealized_pnl += self.get_unrealized_pnl(symbol)

        net_exposure = long_exposure - short_exposure
        total_pnl = realized_pnl + unrealized_pnl

        return {
            "positions": long_positions + short_positions,
            "open_positions": long_positions + short_positions,

            "gross_exposure": round(gross_exposure, 6),
            "long_exposure": round(long_exposure, 6),
            "short_exposure": round(short_exposure, 6),
            "net_exposure": round(net_exposure, 6),

            "realized_pnl": round(realized_pnl, 6),
            "unrealized_pnl": round(unrealized_pnl, 6),
            "total_pnl": round(total_pnl, 6),

            "long_positions": long_positions,
            "short_positions": short_positions,

            "ledger_entries": len(self.ledger),
            "truth_source": self.TRUTH_SOURCE,
        }

    metrics = exposure_snapshot
    calculate_exposure = exposure_snapshot

    # =====================================================
    # RECONCILIATION
    # =====================================================

    def reconcile_positions(self):

        actions = []

        for symbol, pos in list(self.positions.items()):
            clean_symbol = self._symbol(symbol)

            if clean_symbol != symbol:
                self.positions.pop(symbol, None)
                pos.symbol = clean_symbol
                self.positions[clean_symbol] = pos

                actions.append({
                    "action": "NORMALIZE_SYMBOL",
                    "from": symbol,
                    "to": clean_symbol,
                })

            pos.quantity = self._clean_zero(pos.quantity)
            pos.avg_price = self._float(pos.avg_price)
            pos.realized_pnl = self._float(pos.realized_pnl)

            if abs(pos.quantity) < self.EPSILON:
                pos.avg_price = 0.0
                self.lots[clean_symbol] = []

                if abs(pos.realized_pnl) < self.EPSILON:
                    self.positions.pop(clean_symbol, None)

                    actions.append({
                        "action": "PURGE_ZERO_POSITION",
                        "symbol": clean_symbol,
                    })

        self.last_reconcile = {
            "timestamp": self._now(),
            "status": "OK",
            "actions": actions,
            "open_positions": len(self.risk_positions_no_reconcile()),
            "positions": len(self.positions),
            "ledger_fills": len(self.ledger),
            "applied_fills": len(self.applied_fill_registry),
            "execution_fills": len(self.execution_registry),
            "identity_fills": len(self.identity_registry),
            "broker_order_groups": len(self.broker_order_registry),
            "dedupe_collisions": len(self.dedupe_collision_log),
            "rejections": len(self.rejection_trace),
            "commits": len(self.commit_trace),
            "truth_source": self.TRUTH_SOURCE,
        }

        return self.last_reconcile

    reconcile = reconcile_positions

    # =====================================================
    # FILL FORENSICS / REPLAY
    # =====================================================

    def reconcile_fill_identity(
        self,
        runtime_fills,
        audit_fills=None,
    ):

        runtime_fills = runtime_fills if isinstance(runtime_fills, list) else []
        audit_fills = audit_fills if isinstance(audit_fills, list) else []

        runtime_rows = []
        for x in runtime_fills:
            row = self._normalize_fill(x)
            if self._is_true_fill(row):
                runtime_rows.append(row)

        audit_rows = []
        for x in audit_fills:
            row = self._normalize_fill(x)
            if self._is_true_fill(row):
                audit_rows.append(row)

        ledger_rows = []
        for x in self.ledger:
            row = self._normalize_fill(x)
            if self._is_true_fill(row):
                ledger_rows.append(row)

        runtime_map = self._identity_map(runtime_rows)
        audit_map = self._identity_map(audit_rows)
        ledger_map = self._identity_map(ledger_rows)

        all_keys = sorted(
            set(runtime_map.keys())
            | set(audit_map.keys())
            | set(ledger_map.keys())
        )

        mismatches = []
        missing_in_portfolio = []

        for key in all_keys:
            r = runtime_map.get(key)
            a = audit_map.get(key)
            l = ledger_map.get(key)

            if r and not l:
                missing_in_portfolio.append(
                    self._forensic_row(key, r, a, l)
                )

            if r and l:
                mismatch = self._compare_fill_rows(
                    key,
                    r,
                    l,
                    "runtime",
                    "portfolio",
                )

                if mismatch:
                    mismatches.append(mismatch)

        report = {
            "timestamp": self._now(),
            "status": (
                "OK"
                if not mismatches and not missing_in_portfolio
                else "MISMATCH_DETECTED"
            ),
            "runtime_truth": len(runtime_rows),
            "audit_truth": len(audit_rows),
            "portfolio_truth": len(ledger_rows),
            "missing_in_portfolio": missing_in_portfolio,
            "mismatches": mismatches,
            "dedupe_collisions": list(self.dedupe_collision_log),
            "rejections": list(self.rejection_trace),
            "commits": list(self.commit_trace),
            "truth_source": self.TRUTH_SOURCE,
        }

        self.last_identity_report = report
        return report

    def reconcile_missing_fills(
        self,
        runtime_fills,
        audit_fills=None,
    ):

        runtime_fills = runtime_fills if isinstance(runtime_fills, list) else []
        audit_fills = audit_fills if isinstance(audit_fills, list) else []

        candidate_fills = runtime_fills + audit_fills

        missing = []
        skipped = 0
        rejected = 0
        applied = 0

        seen_candidate_keys = set()
        forensic_trace = []

        # =====================================================
        # REBUILD IDENTITY REGISTRIES FROM EXISTING LEDGER
        # =====================================================
        #
        # Important:
        # Runtime recovery can restore ledger rows before the
        # in-memory identity registries exist. If we do not rebuild
        # those registries first, replay can double-append the same
        # audit fills into the portfolio ledger.
        #

        for existing in list(self.ledger):

            existing_row = self._normalize_fill(existing)

            if not self._is_true_fill(existing_row):
                continue

            existing_key = (
                existing_row.get("execution_key")
                or existing_row.get("identity_key")
                or existing_row.get("fill_key")
            )

            if not existing_key:
                continue

            self._register_fill_identity(
                existing_row,
                {
                    "symbol": existing_row.get("symbol"),
                    "action": existing_row.get("action"),
                    "qty": existing_row.get("qty"),
                    "price": existing_row.get("price"),
                    "timestamp": existing_row.get("timestamp"),
                    "timestamp_epoch": time.time(),
                    "execution_key": existing_row.get("execution_key"),
                    "identity_key": existing_row.get("identity_key"),
                    "fill_key": existing_row.get("fill_key"),
                    "order_key": existing_row.get("order_key"),
                    "identity_source": existing_row.get("identity_source"),
                    "broker_order_id": existing_row.get("broker_order_id"),
                    "order_id": existing_row.get("order_id"),
                    "perm_id": existing_row.get("perm_id"),
                    "status": existing_row.get("status"),
                    "truth_source": self.TRUTH_SOURCE,
                }
            )

        # =====================================================
        # DETECT CANDIDATE FILLS MISSING FROM PORTFOLIO
        # =====================================================

        for fill in candidate_fills:

            row = self._normalize_fill(fill)

            if not self._is_true_fill(row):
                rejected += 1

                forensic_trace.append({
                    "status": "REJECTED",
                    "reason": "Not true fill",
                    "row": row,
                })
                continue

            dedupe_key = (
                row.get("execution_key")
                or row.get("identity_key")
                or row.get("fill_key")
            )

            if not dedupe_key:
                rejected += 1

                forensic_trace.append({
                    "status": "REJECTED",
                    "reason": "Missing identity key",
                    "row": row,
                })
                continue

            if dedupe_key in seen_candidate_keys:
                skipped += 1

                forensic_trace.append({
                    "status": "SKIPPED",
                    "reason": "Duplicate candidate fill",
                    "dedupe_key": dedupe_key,
                    "row": row,
                })
                continue

            seen_candidate_keys.add(dedupe_key)

            existing = self._find_existing_fill(row)

            if existing:
                skipped += 1

                forensic_trace.append({
                    "status": "SKIPPED",
                    "reason": "Fill already exists in portfolio ledger",
                    "dedupe_key": dedupe_key,
                    "row": row,
                })
                continue

            missing.append(row)

        # =====================================================
        # REPLAY MISSING FILLS ONLY
        # =====================================================

        for row in missing:

            # Hard re-check after registry rebuild and candidate scan.
            existing = self._find_existing_fill(row)

            if existing:
                skipped += 1

                forensic_trace.append({
                    "execution_key": row.get("execution_key"),
                    "identity_key": row.get("identity_key"),
                    "fill_key": row.get("fill_key"),
                    "status": "SKIPPED",
                    "reason": "Replay fill already exists after registry rebuild",
                })

                continue

            replay = dict(row)
            replay["runtime_rebuild"] = True
            replay["audit_rebuild"] = True
            replay["replay_mode"] = True

            result = self.apply_fill(replay)

            if result.get("status") in ("COMPLETE", "PARTIAL"):
                applied += 1
            elif result.get("status") == "SKIPPED":
                skipped += 1
            else:
                rejected += 1

            forensic_trace.append({
                "execution_key": row.get("execution_key"),
                "identity_key": row.get("identity_key"),
                "fill_key": row.get("fill_key"),
                "status": result.get("status"),
                "reason": result.get("reason"),
                "result": result,
            })

        report = {
            "timestamp": self._now(),
            "status": "OK" if rejected == 0 else "PARTIAL_RECONCILE",
            "missing_detected": len(missing),
            "applied": applied,
            "skipped": skipped,
            "rejected": rejected,
            "forensic_trace": forensic_trace,
            "truth_source": self.TRUTH_SOURCE,
        }

        self.last_missing_fill_report = report
        return report

    def reconcile_runtime_vs_portfolio(
        self,
        runtime_fills,
        audit_fills=None,
    ):

        runtime_fills = runtime_fills if isinstance(runtime_fills, list) else []
        audit_fills = audit_fills if isinstance(audit_fills, list) else []

        report = self.reconcile_missing_fills(
            runtime_fills=runtime_fills,
            audit_fills=audit_fills,
        )

        runtime_truth = len([
            x for x in runtime_fills
            if self._is_true_fill(self._normalize_fill(x))
        ])

        audit_truth = len([
            x for x in audit_fills
            if self._is_true_fill(self._normalize_fill(x))
        ])

        ledger_truth = len([
            x for x in self.ledger
            if self._is_true_fill(self._normalize_fill(x))
        ])

        drift = max(runtime_truth, audit_truth) - ledger_truth

        self.last_drift_report = {
            "timestamp": self._now(),
            "runtime_truth": runtime_truth,
            "audit_truth": audit_truth,
            "ledger_truth": ledger_truth,
            "drift": drift,
            "status": "OK" if drift == 0 else "DRIFT_DETECTED",
            "reconcile_report": report,
            "truth_source": self.TRUTH_SOURCE,
        }

        return self.last_drift_report

    # =====================================================
    # DEDUPE / IDENTITY
    # =====================================================

    def _find_existing_fill(self, row):

        if row is None:
            return None

        if not isinstance(row, dict):
            try:
                row = {
                    "symbol": getattr(row, "symbol", None),
                    "action": getattr(row, "action", None),
                    "qty": getattr(row, "qty", None),
                    "price": getattr(row, "price", None),
                    "timestamp": getattr(row, "timestamp", None),
                    "fill_id": getattr(row, "fill_id", None),
                    "execution_id": getattr(row, "execution_id", None),
                    "exec_id": getattr(row, "exec_id", None),
                    "broker_order_id": getattr(row, "broker_order_id", None),
                    "order_id": getattr(row, "order_id", None),
                }
            except Exception:
                return None

        row = self._normalize_fill(row)

        execution_key = row.get("execution_key")
        identity_key = row.get("identity_key")
        fill_key = row.get("fill_key")
        identity_source = row.get("identity_source")

        # Hard broker execution id is the only absolute duplicate truth.
        if execution_key:
            existing = self.execution_registry.get(execution_key)
            if existing:
                return existing

            for existing in self.ledger:
                existing_row = self._normalize_fill(existing)
                if existing_row.get("execution_key") == execution_key:
                    return existing

            return None

        # Broker order fills may share an order id but still be separate fills.
        # Only dedupe if the full identity key matches.
        if identity_source == "broker_order_fill" and identity_key:
            existing = self.identity_registry.get(identity_key)
            if existing:
                return existing

            for existing in self.ledger:
                existing_row = self._normalize_fill(existing)
                if existing_row.get("identity_key") == identity_key:
                    return existing

            return None

        # Synthetic identity is weak. Do NOT use registry-only dedupe.
        # Only treat it as duplicate if an identical ledger row already exists.
        if identity_source == "synthetic" and identity_key:
            for existing in self.ledger:
                existing_row = self._normalize_fill(existing)

                if (
                    existing_row.get("identity_key") == identity_key
                    and existing_row.get("symbol") == row.get("symbol")
                    and existing_row.get("action") == row.get("action")
                    and self._float(existing_row.get("qty")) == self._float(row.get("qty"))
                    and self._float(existing_row.get("price")) == self._float(row.get("price"))
                    and str(existing_row.get("timestamp")) == str(row.get("timestamp"))
                ):
                    return existing

            return None

        # Final fallback: only exact fill_key match against real ledger.
        if fill_key:
            for existing in self.ledger:
                existing_row = self._normalize_fill(existing)
                if existing_row.get("fill_key") == fill_key:
                    return existing

        return None

    def _detect_identity_collision(self, row):
        return None

    def _register_fill_identity(self, row, meta):

        execution_key = row.get("execution_key")
        identity_key = row.get("identity_key")
        fill_key = row.get("fill_key")
        order_key = row.get("order_key")

        if execution_key:
            self.execution_registry[execution_key] = meta

        if identity_key:
            self.identity_registry[identity_key] = meta

        if fill_key:
            self.applied_fill_registry[fill_key] = meta

        if order_key:
            self.order_registry.setdefault(order_key, [])

            if fill_key and fill_key not in self.order_registry[order_key]:
                self.order_registry[order_key].append(fill_key)

        broker_order_id = row.get("broker_order_id")

        if broker_order_id:
            self.broker_order_registry.setdefault(broker_order_id, [])

            if fill_key and fill_key not in self.broker_order_registry[broker_order_id]:
                self.broker_order_registry[broker_order_id].append(fill_key)

        if identity_key:
            self.processed_fill_ids[identity_key] = {
                "timestamp": time.time(),
                "meta": meta,
            }

    # =====================================================
    # FORENSIC / RECONCILIATION HELPERS
    # =====================================================

    def _identity_map(self, rows):
        mapped = {}

        for row in rows:
            if not isinstance(row, dict):
                continue

            key = row.get("identity_key")
            if key:
                mapped[key] = row

        return mapped

    def _compare_fill_rows(self, key, left, right, left_name, right_name):
        mismatches = {}

        if not isinstance(left, dict) or not isinstance(right, dict):
            return {
                "identity_key": key,
                "mismatches": {
                    "type_error": {
                        left_name: type(left).__name__,
                        right_name: type(right).__name__,
                    }
                },
            }

        for field in ("symbol", "action", "qty", "price"):
            left_value = left.get(field)
            right_value = right.get(field)

            if left_value != right_value:
                mismatches[field] = {
                    left_name: left_value,
                    right_name: right_value,
                }

        if mismatches:
            return {
                "identity_key": key,
                "mismatches": mismatches,
            }

        return None

    def _forensic_row(self, key, runtime_row, audit_row, ledger_row):
        return {
            "identity_key": key,
            "runtime": runtime_row if isinstance(runtime_row, dict) else {},
            "audit": audit_row if isinstance(audit_row, dict) else {},
            "portfolio": ledger_row if isinstance(ledger_row, dict) else {},
        }

    # =====================================================
    # NORMALIZATION
    # =====================================================

    def _normalize_fill(self, fill):
        row = dict(fill or {})

        symbol = self._symbol(row.get("symbol"))
        action = self._action(row.get("action") or row.get("side"))

        qty = self._float(
            row.get("filled_qty")
            or row.get("fill_qty")
            or row.get("execution_qty")
            or row.get("qty")
            or row.get("quantity")
            or 0
        )

        price = self._float(
            row.get("fill_price")
            or row.get("execution_price")
            or row.get("price")
            or row.get("avg_fill_price")
            or 0
        )

        timestamp = str(
            row.get("timestamp")
            or self._now()
        ).strip()

        cumulative_qty = self._float(
            row.get("cumulative_filled_qty")
            or row.get("cum_qty")
            or row.get("filled")
            or qty
        )

        remaining_qty = self._float(
            row.get("remaining_qty")
            or row.get("remaining")
            or 0
        )

        execution_id = str(
            row.get("execution_id")
            or row.get("exec_id")
            or ""
        ).strip()

        broker_order_id = str(
            row.get("broker_order_id")
            or row.get("broker_id")
            or ""
        ).strip()

        order_id = str(
            row.get("order_id")
            or ""
        ).strip()

        perm_id = str(
            row.get("perm_id")
            or row.get("permId")
            or ""
        ).strip()

        source = str(
            row.get("source")
            or ""
        ).strip()

        partial_sequence = int(
            self._float(
                row.get("partial_sequence")
                or row.get("fill_sequence")
                or row.get("sequence")
                or 1
            )
        )

        status = str(
            row.get("status")
            or row.get("execution_status")
            or "FILLED"
        ).upper().strip()

        partial_fill = bool(
            status in self.PARTIAL_STATUSES
            or (
                cumulative_qty > 0
                and remaining_qty > 0
            )
        )

        execution_key = (
            f"EXEC::{execution_id}"
            if execution_id
            else ""
        )

        if execution_key:
            identity_key = execution_key
            identity_source = "execution_id"

        elif broker_order_id:
            identity_key = (
                f"BROKER::{broker_order_id}|"
                f"{symbol}|{action}|{qty}|{price}|{partial_sequence}"
            )
            identity_source = "broker_order_fill"

        elif order_id:
            identity_key = (
                f"ORDER::{order_id}|"
                f"{symbol}|{action}|{qty}|{price}|{partial_sequence}"
            )
            identity_source = "order_id_fill"

        else:
            identity_key = (
                f"SYNTH::{timestamp}|{source}|"
                f"{symbol}|{action}|{qty}|{price}|{partial_sequence}"
            )
            identity_source = "synthetic"

        fill_key = identity_key
        order_key = order_id or broker_order_id or perm_id or ""

        row.update({
            "symbol": symbol,
            "action": action,
            "qty": qty,
            "price": price,
            "execution_id": execution_id,
            "broker_order_id": broker_order_id,
            "order_id": order_id,
            "perm_id": perm_id,
            "execution_key": execution_key,
            "identity_key": identity_key,
            "fill_key": fill_key,
            "order_key": order_key,
            "identity_source": identity_source,
            "partial_sequence": partial_sequence,
            "partial_fill": partial_fill,
            "status": status,
            "timestamp": timestamp,
            "cumulative_filled_qty": cumulative_qty,
            "remaining_qty": remaining_qty,
            "truth_source": row.get("truth_source") or self.TRUTH_SOURCE,
        })

        return row

    def _is_true_fill(self, row):
        if not isinstance(row, dict):
            return False

        if row.get("action") not in self.VALID_ACTIONS:
            return False

        if row.get("status") in self.NON_FILL_STATUSES:
            return False

        if self._float(row.get("qty")) <= 0:
            return False

        if self._float(row.get("price")) <= 0:
            return False

        return True

    def _is_replay_mode(self, row):
        return bool(
            row.get("runtime_rebuild")
            or row.get("audit_rebuild")
            or row.get("replay_mode")
            or row.get("broker_repair")
        )

    # =====================================================
    # NORMALIZATION HELPERS
    # =====================================================

    def _reject(self, status, row, reason):
        event = {
            **row,
            "status": status,
            "reason": reason,
            "timestamp": self._now(),
            "truth_source": self.TRUTH_SOURCE,
        }

        self.rejection_trace.append(event)
        self.last_event = event
        self.last_error = reason
        return event

    def _symbol(self, value):
        return str(value or "").upper().strip()

    def _action(self, value):
        v = str(value or "").upper().strip()

        aliases = {
            "LONG": "BUY",
            "SHORT": "SELL",
            "BOT": "BUY",
            "SLD": "SELL",
        }

        return aliases.get(v, v)

    def _float(self, value):
        try:
            x = float(value)

            if math.isnan(x) or math.isinf(x):
                return 0.0

            return x

        except Exception:
            return 0.0

    def _clean_zero(self, x):
        x = self._float(x)
        return 0.0 if abs(x) < self.EPSILON else x

    def _side_from_qty(self, qty):
        if qty > 0:
            return "LONG"

        if qty < 0:
            return "SHORT"

        return "FLAT"

    def _purge_processed_fill_ids(self):
        cutoff = time.time() - self.PROCESSED_FILL_TTL_SECONDS

        stale = [
            key
            for key, meta in self.processed_fill_ids.items()
            if meta.get("timestamp", 0) < cutoff
        ]

        for key in stale:
            self.processed_fill_ids.pop(key, None)

    def _now(self):
        return datetime.now(timezone.utc).isoformat()

    def export_positions(self):

        rows = []

        for symbol, pos in self.positions.items():

            qty = float(pos.quantity)

            last_price = self.last_prices.get(
                symbol,
                pos.avg_price,
            )

            rows.append({
                "symbol": symbol,
                "shares": qty,
                "avg_price": pos.avg_price,
                "cost_basis": qty * pos.avg_price,
                "market_value": qty * last_price,
                "realized_pnl": pos.realized_pnl,
            })

        return rows

    def clear(self):
        self.__init__()

    reset = clear
