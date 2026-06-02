# =========================================================
# 🧾 JFBP AUDIT STORE v31.0
# SAFE IDEMPOTENT AUDIT REPLAY RESTORED
# LIVE-SAFE + PORTFOLIO-TRUTH REBUILD
# =========================================================

from __future__ import annotations

import json
import sqlite3

from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


class AuditStore:

    def __init__(self, db_path: str = "audit/jfbp_audit.db"):

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.last_error = ""

        self._init_db()

    # =====================================================
    # DB INIT
    # =====================================================

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):

        with self._connect() as conn:

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    event_type TEXT,
                    symbol TEXT,
                    action TEXT,
                    side TEXT,
                    qty INTEGER,
                    price REAL,
                    status TEXT,
                    source TEXT,
                    mode TEXT,
                    order_id TEXT,
                    fill_id TEXT,
                    batch_id TEXT,
                    payload TEXT
                )
                """
            )

            conn.commit()

    # =====================================================
    # RECORDING
    # =====================================================

    def record_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> bool:

        self.last_error = ""

        if not isinstance(payload, dict):
            payload = {"raw_payload": str(payload)}

        try:

            timestamp = (
                payload.get("timestamp")
                or datetime.now(timezone.utc).isoformat()
            )

            symbol = payload.get("symbol")

            action = (
                payload.get("action")
                or payload.get("signal_action")
            )

            side = payload.get("side")

            qty = (
                payload.get("qty")
                or payload.get("quantity")
            )

            price = (
                payload.get("fill_price")
                or payload.get("price")
                or payload.get("last_price")
            )

            status = payload.get("status")
            source = payload.get("source")
            mode = payload.get("mode")

            order_id = payload.get("order_id")

            fill_id = (
                payload.get("fill_id")
                or payload.get("id")
            )

            batch_id = payload.get("batch_id")

            with self._connect() as conn:

                conn.execute(
                    """
                    INSERT INTO audit_events (
                        timestamp,
                        event_type,
                        symbol,
                        action,
                        side,
                        qty,
                        price,
                        status,
                        source,
                        mode,
                        order_id,
                        fill_id,
                        batch_id,
                        payload
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        timestamp,
                        str(event_type or "").upper(),
                        symbol,
                        action,
                        side,
                        self._safe_int(qty),
                        self._safe_float(price),
                        status,
                        source,
                        mode,
                        order_id,
                        fill_id,
                        batch_id,
                        json.dumps(payload, default=str),
                    ),
                )

                conn.commit()

            return True

        except Exception as exc:

            self.last_error = str(exc)
            return False

    def record_fill(self, fill: Dict[str, Any]) -> bool:
        return self.record_event("FILL", fill)

    def record_order(self, order: Dict[str, Any]) -> bool:
        return self.record_event("ORDER", order)

    def record_pipeline_result(
        self,
        result: Dict[str, Any],
    ) -> bool:
        return self.record_event("PIPELINE_RESULT", result)

    # =====================================================
    # READ
    # =====================================================

    def events(
        self,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:

        try:

            with self._connect() as conn:

                conn.row_factory = sqlite3.Row

                rows = conn.execute(
                    """
                    SELECT *
                    FROM audit_events
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (int(limit),),
                ).fetchall()

            return [dict(row) for row in rows]

        except Exception as exc:

            self.last_error = str(exc)
            return []

    recent_events = events

    def fills(
        self,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:

        try:

            with self._connect() as conn:

                conn.row_factory = sqlite3.Row

                rows = conn.execute(
                    """
                    SELECT *
                    FROM audit_events
                    WHERE UPPER(event_type) = 'FILL'
                    ORDER BY id ASC
                    LIMIT ?
                    """,
                    (int(limit),),
                ).fetchall()

            return [
                self._row_to_fill(dict(row))
                for row in rows
            ]

        except Exception as exc:

            self.last_error = str(exc)
            return []

    recent_fills = fills

    def count(self) -> int:

        try:

            with self._connect() as conn:

                row = conn.execute(
                    "SELECT COUNT(*) FROM audit_events"
                ).fetchone()

            return int(row[0] or 0)

        except Exception:
            return 0

    def stats(self) -> Dict[str, Any]:

        try:

            with self._connect() as conn:

                audit_events = conn.execute(
                    "SELECT COUNT(*) FROM audit_events"
                ).fetchone()[0]

                audit_fills = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM audit_events
                    WHERE UPPER(event_type) = 'FILL'
                    """
                ).fetchone()[0]

            return {
                "audit_events": int(audit_events or 0),
                "audit_fills": int(audit_fills or 0),
            }

        except Exception as exc:

            self.last_error = str(exc)

            return {
                "audit_events": 0,
                "audit_fills": 0,
            }

    # =====================================================
    # SAFE IDEMPOTENT REPLAY
    # =====================================================

    def replay_fills(
        self,
        oms=None,
        portfolio=None,
        risk=None,
        limit: int = 5000,
        allow_live: bool = False,
    ) -> Dict[str, Any]:

        """
        Safe audit replay.

        Rules:
        - Does NOT write new audit rows.
        - Does NOT send broker orders.
        - Rebuilds local runtime from persistent audit fills.
        - PortfolioEngine identity layer prevents duplicate application.
        - LIVE replay is blocked unless allow_live=True.
        """

        self.last_error = ""

        fills = self.fills(limit=limit)

        mode = self._detect_mode(
            oms=oms,
            portfolio=portfolio,
            risk=risk,
        )

        if mode == "LIVE" and not allow_live:
            return {
                "status": "SKIPPED",
                "reason": "Audit replay blocked in LIVE mode",
                "mode": mode,
                "fills_found": len(fills),
                "fills_replayed": 0,
                "portfolio_applied": 0,
                "oms_replayed": 0,
                "risk_synced": False,
                "errors": 0,
                "last_error": "",
            }

        fills_replayed = 0
        portfolio_applied = 0
        oms_replayed = 0
        skipped = 0
        rejected = 0
        errors = 0

        replay_trace = []

        for raw_fill in fills:

            fill = self._normalize_replay_fill(raw_fill)

            if not self._is_replayable_fill(fill):
                rejected += 1

                replay_trace.append({
                    "status": "REJECTED",
                    "reason": "Not replayable fill",
                    "fill": fill,
                })
                continue

            result = None
            portfolio_status = "SKIPPED"

            # =====================================================
            # PORTFOLIO REBUILD
            # =====================================================

            if portfolio is not None:
                try:
                    if hasattr(portfolio, "apply_fill"):
                        result = portfolio.apply_fill(fill)

                    elif hasattr(portfolio, "process_fill"):
                        result = portfolio.process_fill(fill)

                    elif hasattr(portfolio, "record_fill"):
                        result = portfolio.record_fill(fill)

                    elif hasattr(portfolio, "update_from_fill"):
                        result = portfolio.update_from_fill(fill)

                    if isinstance(result, dict):

                        status = str(
                            result.get("status")
                            or result.get("execution_status")
                            or ""
                        ).upper().strip()

                        accepted_statuses = {
                            "COMPLETE",
                            "COMPLETED",
                            "PARTIAL",
                            "FILLED",
                            "APPLIED",
                            "SUCCESS",
                        }

                        skipped_statuses = {
                            "SKIPPED",
                            "DUPLICATE",
                            "ALREADY_APPLIED",
                        }

                        if status in accepted_statuses:

                            portfolio_applied += 1
                            portfolio_status = status

                        elif status in skipped_statuses:

                            skipped += 1
                            portfolio_status = status

                        else:

                            rejected += 1
                            portfolio_status = status or "REJECTED"

                    elif result is True:

                        portfolio_applied += 1
                        portfolio_status = "APPLIED"

                    elif result is not None:

                        portfolio_applied += 1
                        portfolio_status = "APPLIED"

                    else:

                        rejected += 1
                        portfolio_status = "NO_PORTFOLIO_RESULT"

                except Exception as exc:
                    errors += 1
                    self.last_error = str(exc)
                    portfolio_status = "ERROR"

                    replay_trace.append({
                        "status": "ERROR",
                        "stage": "portfolio_apply",
                        "error": str(exc),
                        "fill": fill,
                    })
                    continue

            # =====================================================
            # OMS RUNTIME CACHE REBUILD
            # =====================================================

            oms_status = "SKIPPED"

            if oms is not None:
                try:
                    replayed_to_oms = self._append_oms_replay_fill(
                        oms=oms,
                        fill=fill,
                    )

                    if replayed_to_oms:
                        oms_replayed += 1
                        oms_status = "APPENDED"

                    else:
                        oms_status = "SKIPPED"

                except Exception as exc:
                    errors += 1
                    self.last_error = str(exc)
                    oms_status = "ERROR"

                    replay_trace.append({
                        "status": "ERROR",
                        "stage": "oms_append",
                        "error": str(exc),
                        "fill": fill,
                    })
                    continue

            fills_replayed += 1

            replay_trace.append({
                "status": "REPLAYED",
                "symbol": fill.get("symbol"),
                "action": fill.get("action"),
                "qty": fill.get("qty"),
                "price": fill.get("price"),
                "identity": (
                    fill.get("execution_id")
                    or fill.get("fill_id")
                    or fill.get("audit_event_id")
                ),
                "portfolio_status": portfolio_status,
                "oms_status": oms_status,
            })

        risk_synced = self._sync_risk_from_portfolio(
            risk=risk,
            portfolio=portfolio,
        )

        return {
            "status": "OK" if errors == 0 else "PARTIAL_REPLAY",
            "reason": "Audit replay completed",
            "mode": mode,
            "fills_found": len(fills),
            "fills_replayed": fills_replayed,
            "portfolio_applied": portfolio_applied,
            "oms_replayed": oms_replayed,
            "skipped": skipped,
            "rejected": rejected,
            "errors": errors,
            "risk_synced": risk_synced,
            "last_error": self.last_error,
            "replay_trace": replay_trace[-250:],
        }

    rebuild_runtime_state = replay_fills

    # =====================================================
    # CLEAR
    # =====================================================

    def clear(self) -> bool:

        try:

            with self._connect() as conn:

                conn.execute("DELETE FROM audit_events")
                conn.commit()

            return True

        except Exception as exc:

            self.last_error = str(exc)
            return False

    def clear_audit(
        self,
        oms=None,
        portfolio=None,
        risk=None,
        session_state=None,
    ) -> bool:

        ok = self.clear()

        if ok:

            if oms is not None and hasattr(oms, "clear"):
                oms.clear()

            if portfolio is not None and hasattr(portfolio, "clear"):
                portfolio.clear()

            if risk is not None and hasattr(risk, "reset"):
                risk.reset()

            if session_state is not None:

                session_state["bootstrap_recovered"] = False
                session_state["bootstrap_recovered_ok"] = False

                session_state[
                    "bootstrap_recovery_status"
                ] = "AUDIT_CLEARED"

        return ok

    # =====================================================
    # REPLAY HELPERS
    # =====================================================

    def _detect_mode(
        self,
        oms=None,
        portfolio=None,
        risk=None,
    ) -> str:

        for obj in (oms, portfolio, risk):
            try:
                mode = getattr(obj, "mode", None)

                if mode:
                    return str(mode).upper().strip()
            except Exception:
                pass

        return "SIM"

    def _normalize_replay_fill(
        self,
        fill: Dict[str, Any],
    ) -> Dict[str, Any]:

        row = dict(fill or {})

        action = (
            row.get("action")
            or row.get("side")
            or row.get("signal_action")
        )

        action = str(action or "").upper().strip()

        if action == "BOT":
            action = "BUY"

        elif action == "SLD":
            action = "SELL"

        qty = (
            row.get("filled_qty")
            or row.get("fill_qty")
            or row.get("execution_qty")
            or row.get("qty")
            or row.get("quantity")
            or 0
        )

        price = (
            row.get("fill_price")
            or row.get("execution_price")
            or row.get("price")
            or row.get("avg_fill_price")
            or row.get("last_price")
            or 0
        )

        audit_event_id = row.get("audit_event_id")

        execution_id = (
            row.get("execution_id")
            or row.get("exec_id")
            or ""
        )

        fill_id = (
            row.get("fill_id")
            or row.get("id")
            or (
                f"AUDIT-FILL-{audit_event_id}"
                if audit_event_id is not None
                else ""
            )
        )

        source = str(row.get("source") or "audit_replay").strip()

        row.update({
            "symbol": str(row.get("symbol") or "").upper().strip(),
            "action": action,
            "side": action,
            "qty": self._safe_float(qty),
            "filled_qty": self._safe_float(qty),
            "fill_qty": self._safe_float(qty),
            "price": self._safe_float(price),
            "fill_price": self._safe_float(price),
            "execution_price": self._safe_float(price),
            "avg_fill_price": self._safe_float(price),
            "status": str(
                row.get("status")
                or row.get("execution_status")
                or "FILLED"
            ).upper().strip(),
            "execution_status": str(
                row.get("execution_status")
                or row.get("status")
                or "FILLED"
            ).upper().strip(),
            "timestamp": (
                row.get("timestamp")
                or datetime.now(timezone.utc).isoformat()
            ),
            "fill_id": str(fill_id or "").strip(),
            "execution_id": str(execution_id or "").strip(),
            "exec_id": str(execution_id or "").strip(),
            "source": source,
            "mode": str(row.get("mode") or "SIM").upper().strip(),
            "audit_replay": True,
            "audit_rebuild": True,
            "runtime_rebuild": True,
            "replay_mode": True,
        })

        if not row.get("execution_id"):
            row["execution_id"] = str(row.get("fill_id") or "").strip()
            row["exec_id"] = row["execution_id"]

        if not row.get("source"):
            row["source"] = "audit_replay"

        return row

    def _is_replayable_fill(
        self,
        fill: Dict[str, Any],
    ) -> bool:

        if not isinstance(fill, dict):
            return False

        if not fill.get("symbol"):
            return False

        if fill.get("action") not in ("BUY", "SELL"):
            return False

        if self._safe_float(fill.get("qty")) <= 0:
            return False

        if self._safe_float(fill.get("price")) <= 0:
            return False

        status = str(
            fill.get("status")
            or fill.get("execution_status")
            or ""
        ).upper().strip()

        blocked = {
            "REJECTED",
            "BLOCKED",
            "ERROR",
            "TIMEOUT",
            "CANCELLED",
            "CANCELED",
            "SKIPPED",
            "NEW",
            "INIT",
            "WORKING",
            "",
        }

        if status in blocked:
            return False

        return True

    def _append_oms_replay_fill(
        self,
        oms,
        fill: Dict[str, Any],
    ) -> bool:

        if oms is None:
            return False

        existing = []

        for attr in ("fills", "runtime_fills"):
            try:
                rows = getattr(oms, attr, None)

                if isinstance(rows, list):
                    existing = rows
                    break
            except Exception:
                pass

        fill_key = (
            fill.get("execution_id")
            or fill.get("exec_id")
            or fill.get("fill_id")
            or fill.get("audit_event_id")
        )

        if existing is not None and isinstance(existing, list):
            for row in existing:
                if not isinstance(row, dict):
                    continue

                row_key = (
                    row.get("execution_id")
                    or row.get("exec_id")
                    or row.get("fill_id")
                    or row.get("audit_event_id")
                )

                if str(row_key) and str(row_key) == str(fill_key):
                    return False

            existing.append(dict(fill))
            return True

        try:
            setattr(oms, "fills", [dict(fill)])
            return True
        except Exception:
            return False

    def _sync_risk_from_portfolio(
        self,
        risk=None,
        portfolio=None,
    ) -> bool:

        if risk is None or portfolio is None:
            return False

        if not hasattr(risk, "sync_positions"):
            return False

        try:
            positions = {}

            if hasattr(portfolio, "risk_positions"):
                positions = portfolio.risk_positions()

            elif hasattr(portfolio, "snapshot"):
                snap = portfolio.snapshot()

                if isinstance(snap, dict):
                    positions = {
                        symbol: row.get("signed_qty", row.get("qty", 0))
                        for symbol, row in snap.items()
                        if isinstance(row, dict)
                    }

            try:
                risk.sync_positions(positions, historical=True)
            except TypeError:
                risk.sync_positions(positions)

            return True

        except Exception as exc:
            self.last_error = str(exc)
            return False

    # =====================================================
    # NORMALIZATION
    # =====================================================

    def _row_to_fill(
        self,
        row: Dict[str, Any],
    ) -> Dict[str, Any]:

        payload = {}

        try:

            payload_raw = row.get("payload")

            if payload_raw:
                payload = json.loads(payload_raw)

        except Exception:
            payload = {}

        fill = dict(payload)

        audit_event_id = row.get("id")

        fill.setdefault("audit_event_id", audit_event_id)

        fill.setdefault("timestamp", row.get("timestamp"))
        fill.setdefault("symbol", row.get("symbol"))
        fill.setdefault("action", row.get("action"))

        fill.setdefault(
            "side",
            row.get("side") or row.get("action"),
        )

        fill.setdefault("qty", row.get("qty"))

        fill.setdefault(
            "fill_price",
            row.get("price"),
        )

        fill.setdefault(
            "price",
            row.get("price"),
        )

        fill.setdefault(
            "status",
            row.get("status") or "FILLED",
        )

        fill.setdefault(
            "execution_status",
            row.get("status") or "FILLED",
        )

        fill.setdefault(
            "source",
            row.get("source") or "audit_replay",
        )

        fill.setdefault("mode", row.get("mode"))
        fill.setdefault("order_id", row.get("order_id"))

        fill.setdefault(
            "fill_id",
            row.get("fill_id")
            or fill.get("id")
            or f"AUDIT-FILL-{audit_event_id}",
        )

        return fill

    # =====================================================
    # SAFE CASTS
    # =====================================================

    def _safe_float(self, value: Any) -> float:

        try:
            return float(value)

        except Exception:
            return 0.0

    def _safe_int(self, value: Any) -> int:

        try:
            return int(value)

        except Exception:
            return 0