# =========================================================
# 🗄️ JFBP DATABASE PAGE v34.0
# BROKER REPAIR CONTROL CENTER + ARROW-SAFE DATAFRAMES
# =========================================================

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.bootstrap import init_core
from portfolio.garbage_collector import PortfolioGarbageCollector


def page():
    run_page()


def run_page():

    gateway, market, oms, portfolio_engine = init_core()

    audit_store = st.session_state.get("audit_store")
    risk_engine = st.session_state.get("risk_engine")
    pipeline = st.session_state.get("pipeline")
    portfolio_gc = st.session_state.get("portfolio_gc")

    st.title("🗄️ Database")
    st.subheader("Institutional Reconciliation + Audit Control Center")

    if audit_store is None:
        st.error("Audit store unavailable.")
        return

    st.session_state.setdefault("portfolio_gc_report", {})
    st.session_state.setdefault("portfolio_gc_last_run_status", "NEVER_RUN")
    st.session_state.setdefault("broker_repair_drift_report", {})
    st.session_state.setdefault("broker_repair_dry_run_report", {})
    st.session_state.setdefault("broker_repair_apply_report", {})
    st.session_state.setdefault("broker_execution_repair_report", {})
    st.session_state.setdefault("broker_vs_ledger_report", {})

    # =====================================================
    # HELPERS
    # =====================================================

    def arrow_safe_df(data) -> pd.DataFrame:
        df = pd.DataFrame(data)

        if df.empty:
            return df

        for col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].astype(str)

        return df

    def metric_value_df(data: dict, metric_col="Metric", value_col="Value") -> pd.DataFrame:
        df = pd.DataFrame(
            list((data or {}).items()),
            columns=[metric_col, value_col],
        )

        df[metric_col] = df[metric_col].astype(str)
        df[value_col] = df[value_col].astype(str)

        return df

    def refresh_refs():
        nonlocal gateway, market, oms, portfolio_engine, audit_store, risk_engine, pipeline, portfolio_gc

        gateway = st.session_state.get("gateway", gateway)
        market = st.session_state.get("market", market)
        oms = st.session_state.get("oms", oms)
        portfolio_engine = st.session_state.get("portfolio_engine", portfolio_engine)
        audit_store = st.session_state.get("audit_store", audit_store)
        risk_engine = st.session_state.get("risk_engine", risk_engine)
        pipeline = st.session_state.get("pipeline", pipeline)
        portfolio_gc = st.session_state.get("portfolio_gc", portfolio_gc)

    def safe_call(obj, method_name: str, default=None, *args, **kwargs):
        if obj is None or not hasattr(obj, method_name):
            return default

        try:
            return getattr(obj, method_name)(*args, **kwargs)

        except Exception as exc:
            st.session_state["database_last_error"] = (
                f"{obj.__class__.__name__}.{method_name} failed: {exc}"
            )
            return default

    def safe_snapshot(obj):
        snap = safe_call(obj, "snapshot", default={})
        return snap if isinstance(snap, dict) else {}

    def sync_risk():
        refresh_refs()

        try:
            if (
                portfolio_engine
                and risk_engine
                and hasattr(portfolio_engine, "risk_positions")
                and hasattr(risk_engine, "sync_positions")
            ):
                try:
                    risk_engine.sync_positions(
                        portfolio_engine.risk_positions(),
                        historical=True,
                    )
                except TypeError:
                    risk_engine.sync_positions(
                        portfolio_engine.risk_positions()
                    )

                return True

        except Exception as exc:
            st.session_state["database_last_error"] = f"Risk sync failed: {exc}"

        return False

    def get_audit_events(limit=2000):
        refresh_refs()

        if hasattr(audit_store, "events"):
            return safe_call(audit_store, "events", default=[], limit=limit)

        if hasattr(audit_store, "recent_events"):
            return safe_call(audit_store, "recent_events", default=[], limit=limit)

        return []

    def get_audit_fills(limit=2000):
        refresh_refs()

        if hasattr(audit_store, "fills"):
            return safe_call(audit_store, "fills", default=[], limit=limit)

        if hasattr(audit_store, "recent_fills"):
            return safe_call(audit_store, "recent_fills", default=[], limit=limit)

        return []

    def get_stats():
        refresh_refs()

        stats = safe_call(audit_store, "stats", default=None)

        if isinstance(stats, dict):
            return stats

        events = get_audit_events(limit=5000)

        fills = [
            e for e in events
            if isinstance(e, dict)
            and str(e.get("event_type", "")).upper() == "FILL"
        ]

        return {
            "audit_events": len(events),
            "audit_fills": len(fills),
        }

    def get_runtime_fills():
        refresh_refs()

        if oms and hasattr(oms, "fills_snapshot"):
            rows = safe_call(oms, "fills_snapshot", default=[])
            return rows if isinstance(rows, list) else []

        if oms and hasattr(oms, "fills"):
            try:
                return list(oms.fills)
            except Exception:
                return []

        return []

    def get_positions():
        refresh_refs()

        rows = safe_call(portfolio_engine, "snapshot", default={})
        return rows if isinstance(rows, dict) else {}

    def get_active_positions():
        positions = get_positions()
        active = {}

        for symbol, row in positions.items():
            if not isinstance(row, dict):
                continue

            try:
                signed_qty = float(row.get("signed_qty", row.get("qty", 0)) or 0)
            except Exception:
                signed_qty = 0.0

            if abs(signed_qty) > 1e-9:
                active[str(symbol).upper().strip()] = {
                    **row,
                    "symbol": str(symbol).upper().strip(),
                    "side": "LONG" if signed_qty > 0 else "SHORT",
                    "qty": abs(signed_qty),
                    "signed_qty": signed_qty,
                }

        return active

    def get_ledger():
        refresh_refs()

        if portfolio_engine and hasattr(portfolio_engine, "ledger_snapshot"):
            rows = safe_call(portfolio_engine, "ledger_snapshot", default=[])
            return rows if isinstance(rows, list) else []

        return []

    def get_pipeline_results():
        refresh_refs()

        if pipeline and hasattr(pipeline, "results_snapshot"):
            rows = safe_call(pipeline, "results_snapshot", default=[])
            return rows if isinstance(rows, list) else []

        if pipeline and hasattr(pipeline, "results"):
            try:
                return list(pipeline.results)
            except Exception:
                return []

        return []

    def clear_runtime_only():
        refresh_refs()

        if oms and hasattr(oms, "clear"):
            oms.clear()

        if portfolio_engine and hasattr(portfolio_engine, "clear"):
            portfolio_engine.clear()

        if risk_engine and hasattr(risk_engine, "reset"):
            risk_engine.reset()

        st.session_state["last_close_verification"] = []
        st.session_state["last_runtime_replay_result"] = {}

        sync_risk()

    def replay_runtime():
        refresh_refs()
        clear_runtime_only()
        refresh_refs()

        audit_rows = get_audit_fills(limit=5000)

        result = {
            "status": "SKIPPED",
            "reason": "No compatible portfolio replay method found",
            "audit_fills": len(audit_rows),
            "portfolio_rebuilt": False,
            "oms_rebuilt": False,
        }

        # =====================================================
        # PORTFOLIO DURABLE REBUILD
        # =====================================================

        if portfolio_engine is not None:

            try:
                if hasattr(portfolio_engine, "rebuild_from_audit"):
                    result = portfolio_engine.rebuild_from_audit(audit_rows)

                elif hasattr(portfolio_engine, "replay_fills"):
                    result = portfolio_engine.replay_fills(
                        fills=audit_rows,
                        reset_first=True,
                    )

                else:
                    result = {
                        **result,
                        "status": "ERROR",
                        "reason": "Portfolio engine has no audit replay method",
                    }

                result["portfolio_rebuilt"] = True

            except Exception as exc:
                result = {
                    **result,
                    "status": "ERROR",
                    "reason": f"Portfolio rebuild failed: {exc}",
                    "portfolio_rebuilt": False,
                }

                st.session_state["database_last_error"] = result["reason"]

        # =====================================================
        # OMS RUNTIME CACHE REBUILD
        # =====================================================

        if oms is not None and audit_rows:

            try:
                replay_rows = [
                    dict(row)
                    for row in audit_rows
                    if isinstance(row, dict)
                ]

                if hasattr(oms, "fills") and isinstance(oms.fills, list):
                    oms.fills.clear()
                    oms.fills.extend(replay_rows)
                    result["oms_rebuilt"] = True

                elif hasattr(oms, "runtime_fills") and isinstance(oms.runtime_fills, list):
                    oms.runtime_fills.clear()
                    oms.runtime_fills.extend(replay_rows)
                    result["oms_rebuilt"] = True

                elif hasattr(oms, "last_fills") and isinstance(oms.last_fills, list):
                    oms.last_fills.clear()
                    oms.last_fills.extend(replay_rows)
                    result["oms_rebuilt"] = True

            except Exception as exc:
                st.session_state["database_last_error"] = (
                    f"OMS runtime fill replay failed: {exc}"
                )

        run_portfolio_gc(silent=True)
        sync_risk()

        st.session_state["portfolio_engine"] = portfolio_engine

        if risk_engine is not None:
            st.session_state["risk_engine"] = risk_engine

        st.session_state["last_runtime_replay_result"] = result

        return result

    def clear_audit_all():
        refresh_refs()

        if hasattr(audit_store, "clear_audit"):
            result = audit_store.clear_audit(
                oms=oms,
                portfolio=portfolio_engine,
                risk=risk_engine,
                session_state=st.session_state,
            )

        elif hasattr(audit_store, "clear"):
            result = audit_store.clear()

        else:
            result = False

        clear_runtime_only()
        return result

    def run_portfolio_gc(silent: bool = False):
        refresh_refs()

        gc = portfolio_gc

        if gc is None:
            gc = PortfolioGarbageCollector(portfolio_engine=portfolio_engine)
            st.session_state["portfolio_gc"] = gc

        if hasattr(gc, "attach"):
            gc.attach(portfolio_engine)

        report = gc.run(portfolio_engine=portfolio_engine)

        st.session_state["portfolio_gc_report"] = report
        st.session_state["portfolio_gc_last_run_status"] = report.get("status", "UNKNOWN")

        if report.get("status") == "OK":
            sync_risk()

        if not silent:
            if report.get("status") == "OK":
                st.success(
                    f"Portfolio garbage collection complete. "
                    f"Actions: {report.get('actions_count', 0)}"
                )
            else:
                st.error(f"Portfolio garbage collection failed: {report.get('reason')}")

        return report

    def clean_events(rows):
        cleaned = []

        for row in rows:
            if not isinstance(row, dict):
                continue

            payload = row.get("payload")

            cleaned.append({
                "timestamp": row.get("timestamp"),
                "event_type": row.get("event_type"),
                "symbol": row.get("symbol"),
                "action": row.get("action"),
                "side": row.get("side"),
                "qty": row.get("qty"),
                "price": row.get("price"),
                "status": row.get("status"),
                "source": row.get("source"),
                "mode": row.get("mode"),
                "order_id": row.get("order_id"),
                "fill_id": row.get("fill_id"),
                "batch_id": row.get("batch_id"),
                "payload": str(payload)[:300] if payload else "",
            })

        return cleaned

    def build_pipeline_rows(rows):
        cleaned = []

        for row in rows:
            if not isinstance(row, dict):
                continue

            cleaned.append({
                "timestamp": row.get("timestamp"),
                "symbol": row.get("symbol"),
                "action": row.get("action"),
                "qty": row.get("qty"),
                "price": row.get("price"),
                "fill_price": row.get("fill_price"),
                "status": row.get("execution_status") or row.get("status"),
                "reason": row.get("reason"),
                "position_action": row.get("position_action"),
                "position_before": row.get("position_before"),
                "position_after_expected": row.get("position_after_expected"),
                "lifecycle_stage": row.get("lifecycle_stage"),
                "realized_delta": row.get("realized_delta"),
                "realized_pnl": row.get("realized_pnl"),
                "order_id": row.get("order_id"),
                "fill_id": row.get("fill_id"),
                "source": row.get("source"),
                "mode": row.get("mode"),
            })

        return cleaned

    def filter_close_flatten_events(events):
        filtered = []

        for row in events:
            if not isinstance(row, dict):
                continue

            event_type = str(row.get("event_type", "") or "").upper()
            source = str(row.get("source", "") or "")

            if (
                "CLOSE" in event_type
                or "FLATTEN" in event_type
                or source.startswith("oms_close")
                or source.startswith("oms_flatten")
                or source.startswith("oms_emergency")
            ):
                filtered.append(row)

        return filtered

    def normalize_broker_positions(rows):
        normalized = {}

        if isinstance(rows, dict):
            expanded = []

            for key, value in rows.items():
                if isinstance(value, dict):
                    row = dict(value)
                    row.setdefault("symbol", key)
                    expanded.append(row)
                else:
                    expanded.append({
                        "symbol": key,
                        "position": value,
                    })

            rows = expanded

        if not isinstance(rows, list):
            try:
                rows = list(rows)
            except Exception:
                rows = []

        for row in rows:
            if not isinstance(row, dict):
                continue

            symbol = str(
                row.get("symbol")
                or row.get("localSymbol")
                or row.get("contract_symbol")
                or row.get("ticker")
                or ""
            ).upper().strip()

            if not symbol:
                continue

            try:
                qty = float(
                    row.get("signed_qty")
                    if row.get("signed_qty") is not None
                    else row.get("position")
                    if row.get("position") is not None
                    else row.get("quantity")
                    if row.get("quantity") is not None
                    else row.get("qty")
                    if row.get("qty") is not None
                    else 0
                )
            except Exception:
                qty = 0.0

            if abs(qty) <= 1e-9:
                continue

            avg_price = (
                row.get("avg_price")
                if row.get("avg_price") is not None
                else row.get("avg_cost")
                if row.get("avg_cost") is not None
                else row.get("average_cost")
                if row.get("average_cost") is not None
                else row.get("price")
            )

            normalized[symbol] = {
                "symbol": symbol,
                "qty": abs(qty),
                "signed_qty": qty,
                "side": "LONG" if qty > 0 else "SHORT",
                "avg_price": avg_price,
                "source": "broker_snapshot",
            }

        return normalized

    def normalize_broker_fills(rows):
        normalized = []

        if rows is None:
            return []

        if isinstance(rows, dict):
            rows = list(rows.values())

        if not isinstance(rows, list):
            try:
                rows = list(rows)
            except Exception:
                rows = []

        for row in rows:
            if not isinstance(row, dict):
                continue

            symbol = str(row.get("symbol") or "").upper().strip()
            action = str(row.get("action") or row.get("side") or "").upper().strip()

            if action == "BOT":
                action = "BUY"
            elif action == "SLD":
                action = "SELL"

            try:
                qty = float(
                    row.get("filled_qty")
                    or row.get("fill_qty")
                    or row.get("execution_qty")
                    or row.get("qty")
                    or row.get("quantity")
                    or 0
                )
            except Exception:
                qty = 0.0

            try:
                price = float(
                    row.get("fill_price")
                    or row.get("execution_price")
                    or row.get("price")
                    or row.get("avg_fill_price")
                    or 0
                )
            except Exception:
                price = 0.0

            if not symbol or action not in ("BUY", "SELL") or qty <= 0 or price <= 0:
                continue

            normalized.append({
                **row,
                "symbol": symbol,
                "action": action,
                "side": action,
                "qty": qty,
                "price": price,
                "status": str(row.get("status") or row.get("execution_status") or "FILLED").upper(),
                "source": row.get("source") or "broker_snapshot_fill",
            })

        return normalized

    def get_broker_snapshot_positions():
        return st.session_state.get("broker_snapshot_positions", [])

    def get_broker_snapshot_fills():
        return (
            st.session_state.get("broker_snapshot_fills")
            or st.session_state.get("broker_snapshot_executions")
            or st.session_state.get("broker_snapshot_trades")
            or []
        )

    def reconciliation_status():
        stats = get_stats()
        runtime_fills = get_runtime_fills()
        ledger = get_ledger()
        active = get_active_positions()
        risk_snapshot = safe_snapshot(risk_engine)

        runtime_fill_count = len(runtime_fills)
        audit_fill_count = int(stats.get("audit_fills", 0) or 0)
        ledger_count = len(ledger)

        try:
            risk_positions = int(risk_snapshot.get("open_positions", 0) or 0)
        except Exception:
            risk_positions = 0

        portfolio_positions = len(active)

        ledger_ok = (
            audit_fill_count == ledger_count
        )

        position_ok = (
            portfolio_positions == risk_positions
        )

        drift = []

        if not ledger_ok:
            drift.append("AUDIT_LEDGER_MISMATCH")

        if not position_ok:
            drift.append("RISK_PORTFOLIO_POSITION_MISMATCH")

        return {
            "runtime_fills": runtime_fill_count,
            "audit_fills": audit_fill_count,
            "portfolio_ledger": ledger_count,
            "portfolio_positions": portfolio_positions,
            "risk_positions": risk_positions,
            "runtime_cache_only": True,
            "ledger_ok": ledger_ok,
            "checksum_ok": ledger_ok,
            "position_ok": position_ok,
            "state": "MATCH" if ledger_ok and position_ok else "DRIFT",
            "drift": drift,
        }

    # =====================================================
    # SNAPSHOTS
    # =====================================================

    sync_risk()

    stats = get_stats()
    audit_events = get_audit_events(limit=2000)
    audit_fills = get_audit_fills(limit=2000)
    runtime_fills = get_runtime_fills()
    positions = get_positions()
    active_positions = get_active_positions()
    ledger = get_ledger()
    pipeline_results = get_pipeline_results()
    recon = reconciliation_status()

    broker_snapshot_positions = get_broker_snapshot_positions()
    broker_snapshot_fills = get_broker_snapshot_fills()

    # =====================================================
    # RECONCILIATION
    # =====================================================

    st.subheader("Institutional Reconciliation Status")

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Runtime Fills", recon["runtime_fills"])
    c2.metric("Audit Fills", recon["audit_fills"])
    c3.metric("Portfolio Ledger", recon["portfolio_ledger"])
    c4.metric("Portfolio Positions", recon["portfolio_positions"])
    c5.metric("Risk Positions", recon["risk_positions"])

    if recon["state"] == "MATCH":
        st.success(
            "✅ Institutional reconciliation: MATCH "
            "(audit/portfolio/risk aligned; runtime fills are cache only)"
        )
    else:
        st.error(
            f"🚨 Institutional reconciliation drift: "
            f"{', '.join(recon['drift'])}"
        )

    st.caption(
        "Durable reconciliation requires Audit fills = Portfolio ledger, "
        "and Portfolio positions = Risk open positions. "
        "Runtime fills are informational cache only."
    )

    st.divider()

    # =====================================================
    # CANONICAL FILL NORMALIZATION
    # =====================================================

    def canonical_fill_key(row):

        symbol = str(row.get("symbol", "")).upper().strip()

        action = str(
            row.get("action")
            or row.get("side")
            or ""
        ).upper().strip()

        qty = round(
            float(row.get("qty", 0) or 0),
            6,
        )

        price = round(
            float(
                row.get("price")
                or row.get("fill_price")
                or row.get("execution_price")
                or 0
            ),
            2,
        )

        return (
            symbol,
            action,
            qty,
            price,
        )

    # =====================================================
    # AUDIT ↔ LEDGER RECONCILIATION
    # =====================================================

    st.subheader("Audit ↔ Ledger Reconciliation")

    audit_df = arrow_safe_df(audit_fills)
    ledger_df = arrow_safe_df(ledger)

    audit_map = {}
    ledger_map = {}

    for _, row in audit_df.iterrows():

        key = canonical_fill_key(row)

        if key not in audit_map:
            audit_map[key] = []

        audit_map[key].append(dict(row))

    for _, row in ledger_df.iterrows():

        key = canonical_fill_key(row)

        if key not in ledger_map:
            ledger_map[key] = []

        ledger_map[key].append(dict(row))

    audit_only_rows = []
    ledger_only_rows = []

    audit_keys = set(audit_map.keys())
    ledger_keys = set(ledger_map.keys())

    missing_in_ledger = sorted(
        audit_keys - ledger_keys
    )

    missing_in_audit = sorted(
        ledger_keys - audit_keys
    )

    for key in missing_in_ledger:

        rows = audit_map.get(key, [])

        for row in rows:

            audit_only_rows.append(
                {
                    "symbol": row.get("symbol"),
                    "action": row.get("action"),
                    "qty": row.get("qty"),
                    "price": (
                        row.get("price")
                        or row.get("fill_price")
                        or row.get("execution_price")
                    ),
                    "type": "AUDIT_FILL_MISSING_IN_LEDGER",
                    "canonical_key": str(key),
                }
            )

    for key in missing_in_audit:

        rows = ledger_map.get(key, [])

        for row in rows:

            ledger_only_rows.append(
                {
                    "symbol": row.get("symbol"),
                    "action": row.get("action"),
                    "qty": row.get("qty"),
                    "price": (
                        row.get("price")
                        or row.get("fill_price")
                        or row.get("execution_price")
                    ),
                    "type": "LEDGER_FILL_MISSING_IN_AUDIT",
                    "canonical_key": str(key),
                }
            )

    ledger_match = (
        not audit_only_rows
        and not ledger_only_rows
    )

    ledger_report = {
        "status": "MATCH" if ledger_match else "DRIFT",
        "ledger_fills": len(ledger_df),
        "audit_fills": len(audit_df),
        "audit_only_count": len(audit_only_rows),
        "ledger_only_count": len(ledger_only_rows),
        "truth_source": "canonical_economic_event_match",
    }

    st.json(ledger_report)

    st.dataframe(
        arrow_safe_df([
            {
                "Check": "Audit fills",
                "Value": len(audit_df),
            },
            {
                "Check": "Ledger fills",
                "Value": len(ledger_df),
            },
            {
                "Check": "Audit-only rows",
                "Value": len(audit_only_rows),
            },
            {
                "Check": "Ledger-only rows",
                "Value": len(ledger_only_rows),
            },
            {
                "Check": "Canonical match",
                "Value": "YES" if ledger_match else "NO",
            },
        ]),
        width="stretch",
        hide_index=True,
    )

    if ledger_match:

        st.success(
            "✅ Audit ↔ Ledger reconciliation MATCH "
            "(canonical economic events aligned)"
        )

    else:

        st.warning(
            "⚠️ Audit ↔ Ledger reconciliation drift detected."
        )

        if audit_only_rows:

            st.caption("Audit Fills Missing In Ledger")

            st.dataframe(
                arrow_safe_df(audit_only_rows),
                width="stretch",
                hide_index=True,
            )

        if ledger_only_rows:

            st.caption("Ledger Fills Missing In Audit")

            st.dataframe(
                arrow_safe_df(ledger_only_rows),
                width="stretch",
                hide_index=True,
            )

    st.divider()

    # =====================================================
    # BROKER ↔ RUNTIME RECONCILIATION
    # =====================================================

    st.subheader("Broker ↔ Runtime Reconciliation")

    broker_snapshot_timestamp = st.session_state.get(
        "broker_snapshot_timestamp",
        "",
    )

    broker_snapshot_errors = st.session_state.get(
        "broker_snapshot_errors",
        [],
    )

    broker_positions_normalized = normalize_broker_positions(
        broker_snapshot_positions
    )

    portfolio_positions_normalized = active_positions

    broker_symbols = set(broker_positions_normalized.keys())
    portfolio_symbols = set(portfolio_positions_normalized.keys())

    missing_in_broker = sorted(
        portfolio_symbols - broker_symbols
    )

    unexpected_in_broker = sorted(
        broker_symbols - portfolio_symbols
    )

    qty_mismatches = []

    for symbol in sorted(broker_symbols & portfolio_symbols):

        broker_qty = float(
            broker_positions_normalized
            .get(symbol, {})
            .get("signed_qty", 0)
            or 0
        )

        portfolio_qty = float(
            portfolio_positions_normalized
            .get(symbol, {})
            .get("signed_qty", 0)
            or 0
        )

        if abs(broker_qty - portfolio_qty) > 1e-6:

            qty_mismatches.append(
                {
                    "symbol": symbol,
                    "broker_qty": broker_qty,
                    "portfolio_qty": portfolio_qty,
                    "delta": broker_qty - portfolio_qty,
                }
            )

    broker_snapshot_available = bool(
        broker_snapshot_timestamp
    )

    broker_match = (
        broker_snapshot_available
        and not missing_in_broker
        and not unexpected_in_broker
        and not qty_mismatches
    )

    broker_drift_count = (
        len(missing_in_broker)
        + len(unexpected_in_broker)
        + len(qty_mismatches)
    )

    st.session_state["broker_auto_drift_report"] = {
        "snapshot_available": broker_snapshot_available,
        "broker_match": broker_match,
        "drift_count": broker_drift_count,
        "missing_in_broker": list(missing_in_broker),
        "unexpected_in_broker": list(unexpected_in_broker),
        "qty_mismatches": list(qty_mismatches),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "truth_source": "database_auto_warning_only",
    }

    b1, b2, b3, b4 = st.columns(4)

    b1.metric(
        "Broker Snapshot",
        "YES" if broker_snapshot_available else "NO",
    )

    b2.metric(
        "Broker Positions",
        len(broker_positions_normalized),
    )

    b3.metric(
        "Runtime Positions",
        len(portfolio_positions_normalized),
    )

    b4.metric(
        "Broker Match",
        "MATCH" if broker_match else "CHECK",
        delta=(
            None
            if broker_match or not broker_snapshot_available
            else f"{broker_drift_count} drift"
        ),
    )

    if not broker_snapshot_available:

        st.info(
            "No cached broker snapshot available yet. "
            "Go to Live IBKR → Pull Broker Snapshot."
        )

    elif broker_match:

        st.success(
            "✅ Broker reconciliation: MATCH "
            "(cached broker positions align with portfolio runtime)"
        )

    else:

        st.error(
            "🚨 Automatic broker drift warning: broker snapshot does not match "
            "portfolio runtime. No automatic repair was applied."
        )

        st.caption(
            f"Drift count: {broker_drift_count} | "
            f"Missing in broker: {len(missing_in_broker)} | "
            f"Unexpected in broker: {len(unexpected_in_broker)} | "
            f"Quantity mismatches: {len(qty_mismatches)}"
        )

        drift_rows = []

        for symbol in missing_in_broker:

            drift_rows.append(
                {
                    "Type": "MISSING_IN_BROKER",
                    "Symbol": symbol,
                    "Broker Qty": 0,
                    "Portfolio Qty": portfolio_positions_normalized
                    .get(symbol, {})
                    .get("signed_qty", 0),
                }
            )

        for symbol in unexpected_in_broker:

            drift_rows.append(
                {
                    "Type": "UNEXPECTED_IN_BROKER",
                    "Symbol": symbol,
                    "Broker Qty": broker_positions_normalized
                    .get(symbol, {})
                    .get("signed_qty", 0),
                    "Portfolio Qty": 0,
                }
            )

        for row in qty_mismatches:

            drift_rows.append(
                {
                    "Type": "QTY_MISMATCH",
                    "Symbol": row["symbol"],
                    "Broker Qty": row["broker_qty"],
                    "Portfolio Qty": row["portfolio_qty"],
                    "Delta": row["delta"],
                }
            )

        if drift_rows:

            st.dataframe(
                arrow_safe_df(drift_rows),
                width="stretch",
                hide_index=True,
            )

    if broker_snapshot_timestamp:

        st.caption(
            f"Broker snapshot timestamp: "
            f"{broker_snapshot_timestamp}"
        )

    if broker_snapshot_errors:

        st.warning(
            "Broker snapshot warnings: "
            + " | ".join(
                str(e)
                for e in broker_snapshot_errors
            )
        )

    st.divider()

    # =====================================================
    # BROKER REPAIR CONTROL CENTER
    # =====================================================

    st.subheader("🛠 Broker Repair Control Center")

    st.warning(
        "Institutional repair tools. These controls never send broker orders. "
        "They only reconcile or rebuild local runtime state from cached broker truth."
    )

    broker_positions_normalized = (
        broker_positions_normalized
        if isinstance(broker_positions_normalized, dict)
        else {}
    )

    broker_snapshot_fills_normalized = normalize_broker_fills(
        broker_snapshot_fills
    )

    broker_core_methods_ready = (
        portfolio_engine is not None
        and hasattr(portfolio_engine, "detect_broker_drift")
        and hasattr(portfolio_engine, "rebuild_from_broker_snapshot")
        and hasattr(portfolio_engine, "flatten_runtime_orphans")
        and hasattr(portfolio_engine, "repair_from_broker_truth")
    )

    broker_vs_ledger_ready = (
        portfolio_engine is not None
        and hasattr(portfolio_engine, "broker_vs_ledger_reconcile")
    )

    broker_execution_repair_ready = (
        portfolio_engine is not None
        and hasattr(portfolio_engine, "broker_execution_repair")
    )

    broker_truth_available = (
        broker_snapshot_available
        and len(broker_positions_normalized) > 0
    )

    broker_fills_available = (
        broker_snapshot_available
        and len(broker_snapshot_fills_normalized) > 0
    )

    br1, br2, br3, br4 = st.columns(4)

    br1.metric(
        "Core Repair API",
        "READY" if broker_core_methods_ready else "MISSING",
    )

    br2.metric(
        "Cached Broker Positions",
        len(broker_positions_normalized),
    )

    br3.metric(
        "Cached Broker Fills",
        len(broker_snapshot_fills_normalized),
    )

    br4.metric(
        "Snapshot Available",
        "YES" if broker_truth_available else "NO",
    )

    if not broker_core_methods_ready:
        st.error(
            "Core broker repair methods are missing from PortfolioEngine. "
            "Confirm portfolio/engine.py includes detect_broker_drift, "
            "rebuild_from_broker_snapshot, flatten_runtime_orphans, "
            "and repair_from_broker_truth."
        )

    if not broker_truth_available:
        st.info(
            "Broker repair requires a valid cached broker position snapshot. "
            "Go to Live IBKR → Pull Broker Snapshot first."
        )

    repair_mode = st.selectbox(
        "Broker Repair Mode",
        [
            "HYBRID_CONSENSUS",
            "BROKER_POSITIONS_ONLY",
            "BROKER_EXECUTIONS_ONLY",
        ],
        index=0,
    )

    preserve_realized = st.checkbox(
        "Preserve realized P&L during position rebuild",
        value=True,
    )

    preserve_ledger = st.checkbox(
        "Preserve portfolio ledger during position rebuild",
        value=True,
    )

    st.caption(
        "Recommended path: Detect Drift → Dry Run Repair → Review Report → Apply only if expected."
    )

    repair_col1, repair_col2, repair_col3 = st.columns(3)

    with repair_col1:
        detect_broker_drift_btn = st.button(
            "Detect Broker Drift",
            width="stretch",
            disabled=not broker_core_methods_ready or not broker_truth_available,
        )

    with repair_col2:
        dry_run_broker_repair_btn = st.button(
            "Dry Run Broker Repair",
            width="stretch",
            disabled=not broker_core_methods_ready or not broker_truth_available,
        )

    with repair_col3:
        dry_run_orphan_flatten_btn = st.button(
            "Dry Run Runtime Orphan Flatten",
            width="stretch",
            disabled=not broker_core_methods_ready or not broker_truth_available,
        )

    apply_col1, apply_col2, apply_col3 = st.columns(3)

    with apply_col1:
        confirm_broker_rebuild = st.checkbox(
            "Confirm broker rebuild apply",
            value=False,
        )

        apply_broker_rebuild_btn = st.button(
            "Apply Broker Runtime Rebuild",
            width="stretch",
            disabled=(
                not broker_core_methods_ready
                or not broker_truth_available
                or not confirm_broker_rebuild
            ),
        )

    with apply_col2:
        confirm_orphan_flatten = st.checkbox(
            "Confirm orphan flatten apply",
            value=False,
        )

        apply_orphan_flatten_btn = st.button(
            "Apply Runtime Orphan Flatten",
            width="stretch",
            disabled=(
                not broker_core_methods_ready
                or not broker_truth_available
                or not confirm_orphan_flatten
            ),
        )

    with apply_col3:
        confirm_full_repair = st.checkbox(
            "Confirm full broker repair apply",
            value=False,
        )

        apply_full_repair_btn = st.button(
            "Apply Full Broker Repair",
            width="stretch",
            disabled=(
                not broker_core_methods_ready
                or not broker_truth_available
                or not confirm_full_repair
            ),
        )

    forensic_col1, forensic_col2 = st.columns(2)

    with forensic_col1:
        broker_vs_ledger_btn = st.button(
            "Broker vs Ledger Reconcile",
            width="stretch",
            disabled=not broker_vs_ledger_ready or not broker_truth_available,
        )

    with forensic_col2:
        broker_exec_dry_run_btn = st.button(
            "Dry Run Broker Execution Repair",
            width="stretch",
            disabled=not broker_execution_repair_ready or not broker_fills_available,
        )

    def broker_apply_succeeded(report: Dict[str, Any]) -> bool:
        return isinstance(report, dict) and report.get("status") in (
            "APPLIED",
            "PARTIAL_REPAIR",
        )

    def broker_apply_aborted(report: Dict[str, Any]) -> bool:
        return isinstance(report, dict) and report.get("status") in (
            "ABORTED",
            "ERROR",
        )

    def broker_blocked_report(reason: str) -> Dict[str, Any]:
        return {
            "status": "ABORTED",
            "reason": reason,
            "broker_positions": len(broker_positions_normalized),
            "broker_fills": len(broker_snapshot_fills_normalized),
            "truth_source": "ui_guard",
        }

    if detect_broker_drift_btn:
        report = portfolio_engine.detect_broker_drift(
            broker_positions=broker_snapshot_positions,
        )

        st.session_state["broker_repair_drift_report"] = report

        if report.get("status") == "MATCH":
            st.success("Broker drift check complete: MATCH.")
        elif report.get("status") == "ABORTED":
            st.warning(report.get("reason", "Broker drift check aborted."))
        else:
            st.warning(
                f"Broker drift check complete: "
                f"{report.get('drift_count', 0)} drift row(s)."
            )

    if dry_run_broker_repair_btn:
        report = portfolio_engine.repair_from_broker_truth(
            broker_positions=broker_snapshot_positions,
            broker_fills=broker_snapshot_fills if broker_snapshot_fills else None,
            audit_fills=audit_fills,
            dry_run=True,
            mode=repair_mode,
        )

        st.session_state["broker_repair_dry_run_report"] = report

        if broker_apply_aborted(report):
            st.warning(report.get("reason", "Dry-run broker repair aborted."))
        else:
            st.success("Dry-run broker repair completed.")

    if dry_run_orphan_flatten_btn:
        report = portfolio_engine.flatten_runtime_orphans(
            broker_positions=broker_snapshot_positions,
            dry_run=True,
            preserve_realized_pnl=preserve_realized,
        )

        st.session_state["broker_repair_dry_run_report"] = report

        if broker_apply_aborted(report):
            st.warning(report.get("reason", "Dry-run runtime orphan flatten aborted."))
        else:
            st.success("Dry-run runtime orphan flatten completed.")

    if apply_broker_rebuild_btn:
        report = portfolio_engine.rebuild_from_broker_snapshot(
            broker_positions=broker_snapshot_positions,
            dry_run=False,
            preserve_realized_pnl=preserve_realized,
            preserve_ledger=preserve_ledger,
        )

        st.session_state["broker_repair_apply_report"] = report

        if broker_apply_succeeded(report):
            run_portfolio_gc(silent=True)
            sync_risk()

            st.success("Broker runtime rebuild applied.")
            st.rerun()
        else:
            st.warning(
                report.get(
                    "reason",
                    "Broker runtime rebuild was not applied. Runtime preserved.",
                )
            )

    if apply_orphan_flatten_btn:
        report = portfolio_engine.flatten_runtime_orphans(
            broker_positions=broker_snapshot_positions,
            dry_run=False,
            preserve_realized_pnl=preserve_realized,
        )

        st.session_state["broker_repair_apply_report"] = report

        if broker_apply_succeeded(report):
            run_portfolio_gc(silent=True)
            sync_risk()

            st.success("Runtime orphan flatten applied.")
            st.rerun()
        else:
            st.warning(
                report.get(
                    "reason",
                    "Runtime orphan flatten was not applied. Runtime preserved.",
                )
            )

    if apply_full_repair_btn:
        report = portfolio_engine.repair_from_broker_truth(
            broker_positions=broker_snapshot_positions,
            broker_fills=broker_snapshot_fills if broker_snapshot_fills else None,
            audit_fills=audit_fills,
            dry_run=False,
            mode=repair_mode,
        )

        st.session_state["broker_repair_apply_report"] = report

        if broker_apply_succeeded(report):
            run_portfolio_gc(silent=True)
            sync_risk()

            st.success("Full broker repair applied.")
            st.rerun()
        else:
            st.warning(
                report.get(
                    "reason",
                    "Full broker repair was not applied. Runtime preserved.",
                )
            )

    if broker_vs_ledger_btn:
        report = portfolio_engine.broker_vs_ledger_reconcile(
            broker_positions=broker_snapshot_positions,
            audit_fills=audit_fills,
        )

        st.session_state["broker_vs_ledger_report"] = report

        if report.get("status") == "MATCH":
            st.success("Broker vs ledger reconcile complete: MATCH.")
        elif report.get("status") == "ABORTED":
            st.warning(report.get("reason", "Broker vs ledger reconcile aborted."))
        else:
            st.warning("Broker vs ledger reconcile complete: DRIFT detected.")

    if broker_exec_dry_run_btn:
        report = portfolio_engine.broker_execution_repair(
            broker_fills=broker_snapshot_fills,
            audit_fills=audit_fills,
            dry_run=True,
        )

        st.session_state["broker_execution_repair_report"] = report

        if report.get("status") == "ABORTED":
            st.warning(report.get("reason", "Broker execution repair aborted."))
        else:
            st.success("Broker execution repair dry-run completed.")

    drift_report = st.session_state.get("broker_repair_drift_report", {})
    dry_run_report = st.session_state.get("broker_repair_dry_run_report", {})
    apply_report = st.session_state.get("broker_repair_apply_report", {})
    execution_report = st.session_state.get("broker_execution_repair_report", {})
    broker_vs_ledger_report = st.session_state.get("broker_vs_ledger_report", {})

    with st.expander("Broker Drift Report", expanded=False):
        if drift_report:
            st.write(
                {
                    "status": drift_report.get("status"),
                    "drift_count": drift_report.get("drift_count"),
                    "broker_positions": drift_report.get("broker_positions"),
                    "runtime_positions": drift_report.get("runtime_positions"),
                    "reason": drift_report.get("reason"),
                    "truth_source": drift_report.get("truth_source"),
                }
            )

            drift_rows = drift_report.get("drift_rows", [])

            if drift_rows:
                st.dataframe(
                    arrow_safe_df(drift_rows),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info("No broker drift rows.")
        else:
            st.info("No broker drift report yet.")

    with st.expander("Dry Run Broker Repair Report", expanded=False):
        if dry_run_report:
            st.write(
                {
                    "status": dry_run_report.get("status"),
                    "mode": dry_run_report.get("mode"),
                    "dry_run": dry_run_report.get("dry_run"),
                    "reason": dry_run_report.get("reason"),
                    "truth_source": dry_run_report.get("truth_source"),
                }
            )

            position_report = dry_run_report.get("position_report", {})
            execution_sub_report = dry_run_report.get("execution_report", {})

            if isinstance(position_report, dict):
                actions = position_report.get("actions", [])

                if actions:
                    st.caption("Position Repair Actions")
                    st.dataframe(
                        arrow_safe_df(actions),
                        width="stretch",
                        hide_index=True,
                    )
                else:
                    st.info(f"Position report: {position_report}")

            if isinstance(execution_sub_report, dict):
                missing = execution_sub_report.get("missing_in_ledger", [])

                if missing:
                    st.caption("Broker Fills Missing In Ledger")
                    st.dataframe(
                        arrow_safe_df(missing),
                        width="stretch",
                        hide_index=True,
                    )
        else:
            st.info("No dry-run repair report yet.")

    with st.expander("Applied Broker Repair Report", expanded=False):
        if apply_report:
            st.write(
                {
                    "status": apply_report.get("status"),
                    "mode": apply_report.get("mode"),
                    "dry_run": apply_report.get("dry_run"),
                    "reason": apply_report.get("reason"),
                    "truth_source": apply_report.get("truth_source"),
                }
            )

            position_report = apply_report.get("position_report", apply_report)

            if isinstance(position_report, dict):
                actions = position_report.get("actions", [])

                if actions:
                    st.dataframe(
                        arrow_safe_df(actions),
                        width="stretch",
                        hide_index=True,
                    )
                else:
                    st.write(position_report)
        else:
            st.info("No applied broker repair report yet.")

    with st.expander("Broker Execution Repair Report", expanded=False):
        if execution_report:
            st.write(
                {
                    "status": execution_report.get("status"),
                    "broker_fills": execution_report.get("broker_fills"),
                    "ledger_fills": execution_report.get("ledger_fills"),
                    "missing_count": execution_report.get("missing_count"),
                    "applied_count": execution_report.get("applied_count"),
                    "skipped_count": execution_report.get("skipped_count"),
                    "rejected_count": execution_report.get("rejected_count"),
                    "reason": execution_report.get("reason"),
                }
            )

            missing = execution_report.get("missing_in_ledger", [])

            if missing:
                st.dataframe(
                    arrow_safe_df(missing),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info("No missing broker executions detected.")
        else:
            st.info("No broker execution repair report yet.")

    with st.expander("Broker vs Ledger Report", expanded=False):
        if broker_vs_ledger_report:
            st.write(
                {
                    "status": broker_vs_ledger_report.get("status"),
                    "ledger_fills": broker_vs_ledger_report.get("ledger_fills"),
                    "audit_fills": broker_vs_ledger_report.get("audit_fills"),
                    "reason": broker_vs_ledger_report.get("reason"),
                    "truth_source": broker_vs_ledger_report.get("truth_source"),
                }
            )

            missing_ledger = broker_vs_ledger_report.get("missing_in_ledger", [])
            missing_audit = broker_vs_ledger_report.get("missing_in_audit", [])

            if missing_ledger:
                st.caption("Audit Fills Missing In Ledger")
                st.dataframe(
                    arrow_safe_df(missing_ledger),
                    width="stretch",
                    hide_index=True,
                )

            if missing_audit:
                st.caption("Ledger Fills Missing In Audit")
                st.dataframe(
                    arrow_safe_df(missing_audit),
                    width="stretch",
                    hide_index=True,
                )

            if not missing_ledger and not missing_audit:
                st.info("No audit/ledger fill mismatch rows.")
        else:
            st.info("No broker vs ledger report yet.")

    st.divider()

    # =====================================================
    # PORTFOLIO GARBAGE COLLECTOR
    # =====================================================

    st.subheader("🧹 Portfolio Garbage Collector")

    st.warning(
        "Manual cleanup only. This normalizes portfolio runtime state, purges zero-qty stale rows, "
        "repairs position quantities from lots, and preserves realized P&L."
    )

    gc1, gc2, gc3 = st.columns([1, 1, 2])

    with gc1:
        confirm_gc = st.checkbox("Confirm portfolio cleanup")

    with gc2:
        run_gc = st.button(
            "Run Portfolio Garbage Collector",
            width="stretch",
            disabled=not confirm_gc,
        )

    with gc3:
        st.caption(
            "Safe path: run only when Runtime/Audit/Ledger is MATCH. "
            "No trades are executed. Audit history is preserved."
        )

    if run_gc:
        run_portfolio_gc()
        st.rerun()

    gc_report = st.session_state.get("portfolio_gc_report", {})

    if gc_report:
        st.markdown(
            f"**Last GC status:** `{gc_report.get('status')}` — "
            f"{gc_report.get('reason')} | "
            f"Actions: `{gc_report.get('actions_count', 0)}`"
        )

        before = gc_report.get("before", {})
        after = gc_report.get("after", {})
        actions = gc_report.get("actions", [])

        b1, b2 = st.columns(2)

        with b1:
            st.caption("Before")
            st.dataframe(
                metric_value_df(before),
                width="stretch",
            )

        with b2:
            st.caption("After")
            st.dataframe(
                metric_value_df(after),
                width="stretch",
            )

        if actions:
            st.caption("GC Action Log")
            st.dataframe(
                arrow_safe_df(actions),
                width="stretch",
            )
        else:
            st.info("No cleanup actions were needed.")

    st.divider()

    # =====================================================
    # DATABASE STATUS
    # =====================================================

    st.subheader("Database Status")

    d1, d2, d3, d4 = st.columns(4)

    d1.metric("Audit Events", stats.get("audit_events", 0))
    d2.metric(
        "Runtime/Audit/Ledger",
        "MATCH" if recon["checksum_ok"] else "MISMATCH",
    )
    d3.metric("Pipeline", "READY" if pipeline else "MISSING")
    d4.metric("Recovery", st.session_state.get("bootstrap_recovery_status", "UNKNOWN"))

    last_error = st.session_state.get("database_last_error", "")

    if last_error:
        st.warning(f"Last database warning: {last_error}")

    st.divider()

    # =====================================================
    # RUNTIME RECOVERY
    # =====================================================

    st.subheader("Runtime Recovery Controls")

    st.warning("Runtime memory is disposable. Audit DB is the source of truth.")

    r1, r2, r3 = st.columns(3)

    with r1:
        confirm_replay = st.checkbox("Confirm replay from audit", value=False)

        replay_btn = st.button(
            "Replay Runtime From Audit",
            width="stretch",
            disabled=not confirm_replay,
        )

    with r2:
        confirm_clear_runtime = st.checkbox("Confirm runtime clear", value=False)

        clear_runtime_btn = st.button(
            "Clear Runtime Only",
            width="stretch",
            disabled=not confirm_clear_runtime,
        )

    with r3:
        refresh_btn = st.button(
            "Refresh Database View",
            width="stretch",
        )

    if replay_btn:

        result = replay_runtime()

        st.success(
            f"Runtime replay complete: {result}"
        )

        st.rerun()

    if clear_runtime_btn:
        clear_runtime_only()
        st.success("Runtime cleared. Audit DB preserved.")
        st.rerun()

    if refresh_btn:
        st.rerun()

    st.divider()

    # =====================================================
    # DANGER ZONE
    # =====================================================

    st.subheader("Danger Zone")

    st.error(
        "Clear Audit DB permanently deletes the execution ledger. "
        "This cannot be rebuilt from runtime memory."
    )

    dz1, dz2, dz3, dz4 = st.columns([1, 1, 1, 2])

    with dz1:
        confirm_clear_audit_1 = st.checkbox("Confirm audit deletion", value=False)

    with dz2:
        confirm_clear_audit_2 = st.checkbox(
            "I understand audit is source of truth",
            value=False,
        )

    with dz3:
        typed_delete = st.text_input(
            "Type DELETE",
            value="",
            placeholder="DELETE",
        )

    with dz4:
        clear_audit_btn = st.button(
            "Clear Audit DB",
            width="stretch",
            disabled=not (
                confirm_clear_audit_1
                and confirm_clear_audit_2
                and typed_delete.strip().upper() == "DELETE"
            ),
        )

    if clear_audit_btn:
        ok = clear_audit_all()

        if ok:
            st.success("Audit DB and runtime state cleared.")
            st.rerun()

        st.error("Audit clear failed.")

    st.divider()

    # =====================================================
    # CLOSE / FLATTEN AUDIT
    # =====================================================

    st.subheader("Close / Flatten Audit Events")

    close_events = filter_close_flatten_events(audit_events)
    close_df = arrow_safe_df(clean_events(close_events))

    if not close_df.empty:
        st.dataframe(close_df, width="stretch")

        close_csv = close_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "Download Close / Flatten Audit CSV",
            data=close_csv,
            file_name="jfbp_close_flatten_audit.csv",
            mime="text/csv",
            width="stretch",
        )
    else:
        st.info("No close/flatten audit events found.")

    st.divider()

    # =====================================================
    # AUDIT EXPLORER
    # =====================================================

    st.subheader("Audit Explorer")

    events_df = arrow_safe_df(clean_events(audit_events))

    if not events_df.empty:
        f1, f2, f3, f4 = st.columns(4)

        with f1:
            event_types = sorted(events_df["event_type"].dropna().unique())
            selected_types = st.multiselect(
                "Event Type",
                event_types,
                default=event_types,
            )

        with f2:
            symbols = sorted(events_df["symbol"].dropna().unique())
            selected_symbols = st.multiselect("Symbol", symbols)

        with f3:
            statuses = sorted(events_df["status"].dropna().unique())
            selected_statuses = st.multiselect("Status", statuses)

        with f4:
            sources = sorted(events_df["source"].dropna().unique())
            selected_sources = st.multiselect("Source", sources)

        filtered_df = events_df.copy()

        if selected_types:
            filtered_df = filtered_df[filtered_df["event_type"].isin(selected_types)]

        if selected_symbols:
            filtered_df = filtered_df[filtered_df["symbol"].isin(selected_symbols)]

        if selected_statuses:
            filtered_df = filtered_df[filtered_df["status"].isin(selected_statuses)]

        if selected_sources:
            filtered_df = filtered_df[filtered_df["source"].isin(selected_sources)]

        st.dataframe(filtered_df, width="stretch")

        csv = filtered_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "Download Filtered Audit CSV",
            data=csv,
            file_name="jfbp_audit_filtered.csv",
            mime="text/csv",
            width="stretch",
        )

    else:
        st.info("No audit events found.")

    st.divider()

    # =====================================================
    # PIPELINE RESULTS
    # =====================================================

    st.subheader("Pipeline Results")

    pipeline_df = arrow_safe_df(build_pipeline_rows(pipeline_results))

    if not pipeline_df.empty:
        st.dataframe(pipeline_df, width="stretch")
    else:
        st.info("No pipeline results.")

    st.divider()

    # =====================================================
    # RUNTIME FILLS
    # =====================================================

    st.subheader("Runtime Fills")

    if runtime_fills:
        st.dataframe(
            arrow_safe_df(runtime_fills),
            width="stretch",
        )
    else:
        st.info("No runtime fills.")

    st.divider()

    # =====================================================
    # PORTFOLIO LEDGER
    # =====================================================

    st.subheader("Portfolio Ledger")

    if ledger:
        st.dataframe(
            arrow_safe_df(ledger),
            width="stretch",
        )
    else:
        st.info("No portfolio ledger entries.")

    st.divider()

    # =====================================================
    # POSITIONS
    # =====================================================

    st.subheader("Portfolio Positions")

    if positions:
        st.dataframe(
            arrow_safe_df(pd.DataFrame(positions).T),
            width="stretch",
        )
    else:
        st.info("No positions.")

    st.divider()

    health = {
        "Gateway": "ONLINE" if gateway else "MISSING",
        "Market": "ONLINE" if market else "MISSING",
        "OMS": "ONLINE" if oms else "MISSING",
        "Portfolio Engine": "ONLINE" if portfolio_engine else "MISSING",
        "Portfolio Garbage Collector": "WIRED" if portfolio_gc else "MISSING",
        "Risk Engine": "ONLINE" if risk_engine else "MISSING",
        "Pipeline": "READY" if pipeline else "MISSING",
        "Audit Store": "ONLINE" if audit_store else "MISSING",

        "Broker Repair API": (
            "READY"
            if (
                portfolio_engine is not None
                and hasattr(portfolio_engine, "detect_broker_drift")
                and hasattr(portfolio_engine, "rebuild_from_broker_snapshot")
                and hasattr(portfolio_engine, "flatten_runtime_orphans")
                and hasattr(portfolio_engine, "repair_from_broker_truth")
            )
            else "MISSING"
        ),

        "Broker Snapshot Cached": (
            "YES" if broker_snapshot_available else "NO"
        ),

        "Broker Position Count": len(
            broker_positions_normalized
            if isinstance(broker_positions_normalized, dict)
            else {}
        ),

        "Broker Fill Count": len(
            normalize_broker_fills(broker_snapshot_fills)
        ),

        "Bootstrap Initialized": st.session_state.get(
            "bootstrap_initialized"
        ),

        "Bootstrap Recovered": st.session_state.get(
            "bootstrap_recovered"
        ),

        "Bootstrap Recovery OK": st.session_state.get(
            "bootstrap_recovered_ok"
        ),

        "Bootstrap Status": st.session_state.get(
            "bootstrap_recovery_status"
        ),

        "Shared Runtime Unified": st.session_state.get(
            "shared_runtime_unified"
        ),

        "Portfolio GC Wired": st.session_state.get(
            "portfolio_gc_wired"
        ),

        "Portfolio GC Last Status": st.session_state.get(
            "portfolio_gc_last_run_status"
        ),

        "Reconciliation State": recon["state"],

        "Reconciliation Drift": (
            ", ".join(recon["drift"])
            if recon["drift"]
            else "NONE"
        ),
    }

