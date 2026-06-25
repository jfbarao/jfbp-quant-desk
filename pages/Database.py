# =========================================================
# 🗄️ JFBP DATABASE COMMAND CENTER v39.0
# FINAL SYSTEM TRUST CENTER — reconciliation, broker sync, runtime recovery, freeze gate
# =========================================================

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import streamlit as st
import html
from typing import Any, Dict

from core.bootstrap import init_core
from portfolio.garbage_collector import PortfolioGarbageCollector

try:
    from core.responsive import inject_responsive_css, columns as jfbp_columns
    from core.ui_cards import inject_card_css
except Exception:  # pragma: no cover
    inject_responsive_css = None
    inject_card_css = None
    jfbp_columns = None


# =========================================================
# RESPONSIVE UI HELPERS
# =========================================================

def inject_database_css() -> None:
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1.4rem !important;
                padding-bottom: 2.5rem !important;
                max-width: 1500px !important;
                padding-left: 2.5rem !important;
                padding-right: 2.5rem !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }
            h1 {font-size: clamp(1.85rem, 3.8vw, 2.55rem) !important;font-weight: 850 !important;line-height: 1.12 !important;color: #1f2937 !important;}
            h2, h3 {font-size: clamp(1.12rem, 2.4vw, 1.55rem) !important;font-weight: 850 !important;line-height: 1.2 !important;color: #1f2937 !important;}
            div[data-testid="stHorizontalBlock"] {gap: 0.85rem !important;align-items: stretch !important;}
            div[data-testid="stHorizontalBlock"] > div, div[data-testid="column"] {min-width: 0 !important;}
            div[data-testid="stDataFrame"] {width: 100% !important;max-width: 100% !important;overflow-x: auto !important;border-radius: 12px !important;}
            div[data-testid="stDataFrame"] * {white-space: normal !important;overflow-wrap: normal !important;word-break: normal !important;}
            div[data-testid="stAlert"] {overflow-wrap: normal !important;word-break: normal !important;}
            .stButton > button {border-radius: 10px !important;min-height: 38px !important;font-weight: 750 !important;border: 1px solid #d7e3f5 !important;}
            .database-card-grid {display: grid;grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));gap: 0.85rem;margin: 0.55rem 0 0.85rem 0;width: 100%;}
            .database-card {border-radius: 14px;padding: 0.82rem 0.92rem;border: 1px solid #dbe3ef;background: #f8fafc;min-width: 0;max-width:100%;overflow:hidden;box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);}
            .database-card-label {font-size: 0.72rem;text-transform: uppercase;letter-spacing: 0.045em;color: #64748b;font-weight: 850;margin-bottom: 0.28rem;line-height: 1.25;}
            .database-card-value {font-size: clamp(0.95rem, 1.7vw, 1.28rem);line-height: 1.15;font-weight: 900;color: #111827;overflow-wrap:anywhere;word-break:break-word;white-space:normal;max-width:100%;}
            .database-card-detail {font-size: 0.78rem;line-height: 1.35;color: #64748b;margin-top: 0.35rem;overflow-wrap:anywhere;word-break:break-word;white-space:normal;}
            .database-flow {background: #eff6ff;border: 1px solid #bfdbfe;border-radius: 14px;padding: 1rem;margin: 0.75rem 0 0.85rem 0;color: #1e3a8a;}
            .database-warning-panel {background: #fffbeb;border: 1px solid #fde68a;border-radius: 14px;padding: 1rem;margin: 0.75rem 0;}
            .database-hero {border-radius: 18px;padding: 1.05rem 1.1rem;margin: 0.65rem 0 0.9rem 0;border: 1px solid #dbe3ef;overflow:hidden;}
            .database-hero-kicker {font-size:0.72rem;text-transform:uppercase;letter-spacing:0.08em;font-weight:900;color:#64748b;margin-bottom:0.35rem;}
            .database-hero-title {font-size:clamp(1.55rem,3.4vw,2.45rem);line-height:1.05;font-weight:950;overflow-wrap:anywhere;word-break:break-word;}
            .database-hero-subtitle {font-weight:850;margin-top:0.45rem;line-height:1.35;overflow-wrap:anywhere;word-break:break-word;}
            .database-hero-action {background:#ffffff;border:1px solid #dbe3ef;border-radius:12px;padding:0.75rem;margin-top:0.85rem;font-weight:850;line-height:1.35;overflow-wrap:anywhere;word-break:break-word;}
            @media (max-width: 1180px) {.block-container {padding-left: 1.25rem !important;padding-right: 1.25rem !important;} div[data-testid="stHorizontalBlock"] {flex-wrap: wrap !important;} div[data-testid="stHorizontalBlock"] > div, div[data-testid="column"] {flex: 1 1 100% !important;width: 100% !important;min-width: 100% !important;} .database-card-grid {grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));}}
            @media (max-width: 760px) {.block-container {padding-left: 0.9rem !important;padding-right: 0.9rem !important;} .database-card-grid {grid-template-columns: 1fr;}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def db_tone(value: str) -> str:
    text = str(value or "").upper()
    if any(term in text for term in ("MATCH", "READY", "ONLINE", "OK", "YES", "WIRED")):
        return "good"
    if any(term in text for term in ("DRIFT", "MISMATCH", "ERROR", "CRITICAL", "DELETE", "MISSING")):
        return "risk"
    if any(term in text for term in ("STALE", "WARNING", "CHECK", "ABORTED")):
        return "warning"
    return "neutral"


def db_card_html(label: str, value, detail: str = "", tone: str = "neutral") -> str:
    palette = {
        "neutral": ("#f8fafc", "#dbe3ef", "#111827"),
        "good": ("#ecfdf5", "#bbf7d0", "#166534"),
        "warning": ("#fffbeb", "#fde68a", "#92400e"),
        "risk": ("#fef2f2", "#fecaca", "#991b1b"),
        "info": ("#eff6ff", "#bfdbfe", "#1d4ed8"),
    }

    background, border, value_color = palette.get(
        tone,
        palette["neutral"],
    )

    label_text = html.escape(str(label))
    value_text = html.escape(str(value))
    detail_text = html.escape(str(detail))

    detail_html = (
        f'<div class="database-card-detail">{detail_text}</div>'
        if detail_text
        else ""
    )

    # Important: keep HTML left-aligned / non-indented.
    # Indented HTML inside st.markdown can be interpreted as a Markdown code block.
    return (
        f'<div class="database-card" style="background:{background};border-color:{border};">'
        f'<div class="database-card-label">{label_text}</div>'
        f'<div class="database-card-value" style="color:{value_color};">{value_text}</div>'
        f'{detail_html}'
        f'</div>'
    )

def db_metric_grid(cards: list[dict]) -> None:
    card_html = "".join(
        db_card_html(
            card.get("label", ""),
            card.get("value", ""),
            card.get("detail", ""),
            card.get("tone", db_tone(card.get("value", ""))),
        )
        for card in cards
    )

    grid_html = f'<div class="database-card-grid">{card_html}</div>'

    st.markdown(
        grid_html,
        unsafe_allow_html=True,
    )

def db_tip(text: str) -> None:
    st.caption(f"💡 {text}")


def grade_from_score(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def page():
    run_page()


def run_page():

    if inject_responsive_css is not None:
        inject_responsive_css(max_width=1500)
    if inject_card_css is not None:
        inject_card_css()

    gateway, market, oms, portfolio_engine = init_core()

    audit_store = st.session_state.get("audit_store")
    risk_engine = st.session_state.get("risk_engine")
    pipeline = st.session_state.get("pipeline")
    portfolio_gc = st.session_state.get("portfolio_gc")

    inject_database_css()

    st.title("🗄️ Database Command Center")
    st.caption(
        "JFBP Quant Desk's final system-trust center. Verify audit integrity, reconcile broker and runtime state, confirm recovery readiness, repair local records when needed, and validate freeze readiness before release or live testing."
    )

    st.markdown(
        """
        <div class="database-flow">
            <strong>Workflow:</strong><br>
            Live IBKR → Pull Broker Snapshot → Database Command Center → Reconcile → Repair / Replay if needed → OMS Execution → Position Command Center → Journal
        </div>
        """,
        unsafe_allow_html=True,
    )

    nav_cols = st.columns(5)
    with nav_cols[0]:
        if st.button("Live IBKR", width="stretch", key="db_nav_live_ibkr_v38"):
            st.session_state["jfbp_main_navigation"] = "Live IBKR"
            st.rerun()
    with nav_cols[1]:
        if st.button("OMS", width="stretch", key="db_nav_oms_v38"):
            st.session_state["jfbp_main_navigation"] = "OMS Execution"
            st.rerun()
    with nav_cols[2]:
        if st.button("Position Command", width="stretch", key="db_nav_position_v38"):
            st.session_state["jfbp_main_navigation"] = "Position Command Center"
            st.rerun()
    with nav_cols[3]:
        if st.button("Journal", width="stretch", key="db_nav_journal_v38"):
            st.session_state["jfbp_main_navigation"] = "Journal"
            st.rerun()
    with nav_cols[4]:
        if st.button("Trade Command", width="stretch", key="db_nav_trade_v38"):
            st.session_state["jfbp_main_navigation"] = "Trade Command Center"
            st.rerun()

    with st.expander("📘 How to use Database Command Center", expanded=False):
        st.markdown(
            """
            ### What this page is for

            Database Command Center is the final system-trust station for audit history, reconciliation, broker snapshot comparison, runtime recovery, repair tools, and freeze readiness.

            It should be used when you need to verify that the platform's internal records agree with:

            - OMS fills
            - Audit fills
            - Portfolio ledger
            - Portfolio positions
            - Risk engine positions
            - Cached broker snapshot from Live IBKR

            ---

            ### Normal review workflow

            1. Open **Live IBKR**.
            2. Pull a fresh **Broker Snapshot**.
            3. Open **Database**.
            4. Check **Institutional Reconciliation Status**.
            5. Confirm **Audit ↔ Ledger Reconciliation** is MATCH.
            6. Check **Broker ↔ Runtime Reconciliation**.
            7. Review **Broker Repair Control Center** only if drift is detected.
            8. Use **Journal** after reviewing system and trade history.

            ---

            ### What the main sections mean

            **Institutional Reconciliation Status**  
            Confirms whether runtime fills, audit fills, portfolio ledger, portfolio positions, and risk positions are aligned.

            **Audit ↔ Ledger Reconciliation**  
            Checks whether durable audit fills and portfolio ledger fills represent the same economic events.

            **Broker ↔ Runtime Reconciliation**  
            Compares cached broker positions from Live IBKR against the local portfolio runtime.

            **Broker ↔ Execution Reconciliation**  
            Checks whether broker executions, runtime fills, and audit fills are aligned.

            **Broker Repair Control Center**  
            Controlled local repair tools. These do not send broker orders. They only rebuild or reconcile local runtime state from cached broker truth.

            **Portfolio Garbage Collector**  
            Cleans stale zero-quantity rows and normalizes local portfolio runtime state while preserving audit history and realized P&L.

            **Runtime Recovery Controls**  
            Rebuilds disposable runtime memory from the durable audit source of truth.

            **Danger Zone**  
            Permanently deletes audit records. Use only when intentionally resetting the system.

            **Audit Explorer**  
            Searchable view of recorded audit events, fills, pipeline results, and system activity.

            ---

            ### Safe operating rules

            - Do not use repair tools unless you first pulled a fresh broker snapshot.
            - Do not apply broker repair unless you understand the drift report.
            - Do not clear audit records unless you intentionally want to reset the execution database.
            - Runtime memory is disposable. Audit history is the source of truth.
            - Broker repair tools do not send trades. OMS and Manual Order Ticket are the order-routing pages.
            - If unsure, stop at the reports and do not press repair/apply buttons.

            ---

            ### Best practice

            Use this page after live testing, after broker reconnects, after unexpected fills, or before freezing a stable release.
            """
        )

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
    # COMMANDER DATA CENTER HELPERS v38.0
    # =====================================================

    def commander_banner(title: str, subtitle: str, action: str, tone: str = "warning") -> None:
        palette = {
            "good": ("#ecfdf5", "#bbf7d0", "#166534", "🟢"),
            "warning": ("#fffbeb", "#fde68a", "#92400e", "🟡"),
            "risk": ("#fef2f2", "#fecaca", "#991b1b", "🔴"),
            "info": ("#eff6ff", "#bfdbfe", "#1d4ed8", "🔵"),
        }
        bg, border, color, icon = palette.get(tone, palette["warning"])
        hero_html = (
            f'<div class="database-hero" style="background:{bg};border-color:{border};">'
            f'<div class="database-hero-kicker">Commander Intelligence Headquarters · Database Command Center v38.0</div>'
            f'<div class="database-hero-title" style="color:{color};">{icon} {html.escape(str(title))}</div>'
            f'<div class="database-hero-subtitle">{html.escape(str(subtitle))}</div>'
            f'<div class="database-hero-action">ACTION: {html.escape(str(action))}</div>'
            f'</div>'
        )
        st.markdown(hero_html, unsafe_allow_html=True)

    def broker_snapshot_age_label(timestamp: str) -> str:
        if not timestamp:
            return "N/A"
        try:
            snapshot_dt = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
            age_minutes = round((datetime.now(timezone.utc) - snapshot_dt).total_seconds() / 60, 1)
            return f"{age_minutes} min"
        except Exception:
            return "UNKNOWN"

    def derive_commander_status(recon_state: str, broker_state: str, execution_ok: bool, recovery_state: str) -> tuple[str, str, str]:
        recon_state = str(recon_state or "UNKNOWN").upper()
        broker_state = str(broker_state or "UNKNOWN").upper()
        recovery_state = str(recovery_state or "UNKNOWN").upper()

        if recon_state == "DRIFT" or not execution_ok or broker_state in ("DRIFT", "CRITICAL"):
            return (
                "SYSTEM STATUS: CRITICAL",
                "Reconciliation, broker, execution, or recovery checks require immediate review.",
                "Do not freeze. Review drift reports and repair only after confirming cached broker truth.",
            )

        if broker_state in ("NO_SNAPSHOT", "STALE_SNAPSHOT", "CHECK", "UNKNOWN") or "UNKNOWN" in recovery_state:
            return (
                "SYSTEM STATUS: WARNING",
                "Core audit and runtime checks are acceptable, but one or more operational checks require confirmation.",
                "Pull fresh broker snapshot and confirm recovery state before final freeze.",
            )

        return (
            "SYSTEM STATUS: HEALTHY",
            "Audit, ledger, runtime, broker, execution, and recovery systems are aligned.",
            "Safe to operate, test, and freeze.",
        )

    def score_from_checks(checks: list[bool]) -> int:
        if not checks:
            return 0
        return int(round(100 * sum(bool(x) for x in checks) / len(checks)))

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
    # COMMANDER DATA CENTER v38.0 — PRECOMPUTED TRUST STATE
    # =====================================================

    broker_snapshot_timestamp = st.session_state.get("broker_snapshot_timestamp", "")
    broker_snapshot_available = bool(broker_snapshot_timestamp)
    broker_snapshot_age = broker_snapshot_age_label(broker_snapshot_timestamp)

    broker_positions_normalized_pre = normalize_broker_positions(broker_snapshot_positions)
    broker_symbols_pre = set(broker_positions_normalized_pre.keys())
    portfolio_symbols_pre = set(active_positions.keys())
    missing_in_broker_pre = sorted(portfolio_symbols_pre - broker_symbols_pre)
    unexpected_in_broker_pre = sorted(broker_symbols_pre - portfolio_symbols_pre)
    qty_mismatches_pre = []

    for symbol in sorted(broker_symbols_pre & portfolio_symbols_pre):
        broker_qty = float(broker_positions_normalized_pre.get(symbol, {}).get("signed_qty", 0) or 0)
        portfolio_qty = float(active_positions.get(symbol, {}).get("signed_qty", 0) or 0)
        if abs(broker_qty - portfolio_qty) > 1e-6:
            qty_mismatches_pre.append(symbol)

    broker_drift_count_pre = len(missing_in_broker_pre) + len(unexpected_in_broker_pre) + len(qty_mismatches_pre)
    if not broker_snapshot_available:
        broker_state_pre = "NO_SNAPSHOT"
    elif broker_drift_count_pre == 0:
        broker_state_pre = "MATCH"
    else:
        broker_state_pre = "DRIFT"

    runtime_exec_ids_pre = set()
    audit_exec_ids_pre = set()
    for fill in list(getattr(portfolio_engine, "ledger", []) or []):
        if isinstance(fill, dict):
            fid = str(fill.get("fill_id") or fill.get("execution_id") or fill.get("exec_id") or fill.get("id") or "").strip()
            if fid:
                runtime_exec_ids_pre.add(fid)
    for fill in audit_fills or []:
        if isinstance(fill, dict):
            fid = str(fill.get("fill_id") or fill.get("execution_id") or fill.get("exec_id") or fill.get("id") or "").strip()
            if fid:
                audit_exec_ids_pre.add(fid)
    execution_match_pre = (runtime_exec_ids_pre == audit_exec_ids_pre) or (len(runtime_exec_ids_pre) == len(audit_exec_ids_pre))

    recovery_state = st.session_state.get("bootstrap_recovery_status", "UNKNOWN")
    recovery_ok = str(recovery_state or "").upper() not in ("", "UNKNOWN", "ERROR", "FAILED", "MISSING")

    system_title, system_subtitle, system_action = derive_commander_status(recon.get("state"), broker_state_pre, execution_match_pre, recovery_state)
    system_tone = "good" if "HEALTHY" in system_title else "risk" if "CRITICAL" in system_title else "warning"

    audit_ok = int(stats.get("audit_fills", 0) or 0) == len(ledger)
    ledger_ok = bool(recon.get("ledger_ok"))
    runtime_ok = bool(gateway and market and oms and portfolio_engine and risk_engine)
    broker_ok = broker_state_pre == "MATCH"
    execution_ok = bool(execution_match_pre)
    freeze_ready = all([audit_ok, ledger_ok, runtime_ok, broker_ok, execution_ok, recovery_ok])
    database_score = score_from_checks([audit_ok, ledger_ok, runtime_ok, broker_ok, execution_ok, recovery_ok])

    journal_status = st.session_state.get("journal_status", "UNKNOWN")
    supabase_status = st.session_state.get("supabase_status", "UNKNOWN")
    supabase_last_sync = st.session_state.get("supabase_last_sync", "UNKNOWN")
    supabase_sync_lag = st.session_state.get("supabase_sync_lag_minutes", "UNKNOWN")
    portfolio_status = "ONLINE" if portfolio_engine else "MISSING"
    freeze_status = "READY" if freeze_ready else "NOT READY"
    grade = grade_from_score(database_score)
    grade_tone = "good" if grade in ("A", "B") else "warning" if grade == "C" else "risk"

    if not audit_ok:
        top_weakness = "Audit and portfolio ledger are not aligned."
        recommended_action = "Review Audit ↔ Ledger reconciliation before running repairs or freezing."
    elif not broker_ok:
        top_weakness = "No fresh broker snapshot is confirmed."
        recommended_action = "Pull Broker Snapshot from Live IBKR before final freeze or live testing."
    elif not execution_ok:
        top_weakness = "Execution integrity needs review."
        recommended_action = "Review Broker ↔ Execution reconciliation before freezing."
    elif not recovery_ok:
        top_weakness = "Recovery status is not fully confirmed."
        recommended_action = "Refresh/replay runtime checks and confirm bootstrap recovery state."
    else:
        top_weakness = "No critical database weakness detected."
        recommended_action = "Database is ready for freeze review."

    top_strength = "Audit and portfolio ledger are aligned." if audit_ok and ledger_ok else "Runtime services are online." if runtime_ok else "Database diagnostics are available for review."

    with st.container():
        st.subheader("📊 Executive Dashboard")
        st.caption("Top-level readiness metrics for database, recovery, journal, Supabase, portfolio, and freeze status.")
        st.divider()
        exec_cols = st.columns(6)
        exec_cols[0].metric("Database Health", "ONLINE" if audit_store else "MISSING")
        exec_cols[1].metric("Recovery Status", recovery_state)
        exec_cols[2].metric("Journal Status", journal_status)
        exec_cols[3].metric("Supabase Status", supabase_status)
        exec_cols[4].metric("Portfolio Status", portfolio_status)
        exec_cols[5].metric("Freeze Readiness", freeze_status)
        st.divider()

    with st.container():
        st.subheader("🏅 Commander Assessment")
        st.caption("Executive grade, top strengths, top risks, and recommended next action for the system.")
        assessment_cols = st.columns(4)
        assessment_cols[0].markdown(f"**Overall Grade**\n\n# {grade}\n{database_score}/100")
        assessment_cols[1].markdown(f"**Top Strength**\n{top_strength}")
        assessment_cols[2].markdown(f"**Top Risk**\n{top_weakness}")
        assessment_cols[3].markdown(f"**Recommended Action**\n{recommended_action}")
        st.divider()

    with st.expander("📈 Business Intelligence", expanded=False):
        st.subheader("Business Intelligence")
        st.caption("Database growth, record counts, recovery metrics, runtime performance, and Supabase sync intelligence.")
        db_metric_grid([
            {"label": "Audit Events", "value": stats.get("audit_events", 0), "detail": "Total audit records", "tone": "info"},
            {"label": "Audit Fills", "value": stats.get("audit_fills", 0), "detail": "Durable trade fills", "tone": "good"},
            {"label": "Ledger Entries", "value": len(ledger), "detail": "Portfolio ledger rows", "tone": "info"},
            {"label": "Pipeline Results", "value": len(pipeline_results), "detail": "Pipeline rows", "tone": "info"},
            {"label": "Open Positions", "value": len(active_positions), "detail": "Active portfolio positions", "tone": "info"},
            {"label": "Runtime Fills", "value": len(runtime_fills), "detail": "Cached OMS fills", "tone": "neutral"},
            {"label": "Recovery OK", "value": "YES" if recovery_ok else "NO", "detail": recovery_state, "tone": "good" if recovery_ok else "warning"},
            {"label": "Bootstrap Status", "value": st.session_state.get("bootstrap_recovery_status", "UNKNOWN"), "detail": "Recovery status", "tone": db_tone(st.session_state.get("bootstrap_recovery_status", "UNKNOWN"))},
            {"label": "Supabase Sync", "value": supabase_status, "detail": f"Lag {supabase_sync_lag}", "tone": db_tone(supabase_status)},
            {"label": "Last Supabase Sync", "value": supabase_last_sync, "detail": "Sync timestamp", "tone": "info"},
        ])

    st.subheader("🏛 Commander Data Center")
    st.caption("One-glance system trust report, release gate, reconciliation status, and recommended action.")

    commander_left, commander_right = st.columns([7, 3])

    with commander_left:
        commander_banner(
            system_title,
            f"Reconciliation: {recon.get('state')} · Broker: {broker_state_pre} · Execution: {'MATCH' if execution_match_pre else 'DRIFT'} · Recovery: {recovery_state} · Freeze Gate: {'READY' if freeze_ready else 'NOT READY'}",
            system_action,
            system_tone,
        )

        st.subheader("❄️ Freeze Readiness Engine")
        st.caption("Official JFBP release gate. This section is read-only and does not change runtime state.")
        db_metric_grid([
            {"label": "Audit Integrity", "value": "✅ PASS" if audit_ok else "❌ CHECK", "detail": f"Audit fills {stats.get('audit_fills', 0)} / Ledger {len(ledger)}", "tone": "good" if audit_ok else "risk"},
            {"label": "Ledger Integrity", "value": "✅ PASS" if ledger_ok else "❌ CHECK", "detail": "Audit + Ledger state", "tone": "good" if ledger_ok else "risk"},
            {"label": "Runtime Integrity", "value": "✅ PASS" if runtime_ok else "❌ CHECK", "detail": "Gateway / Market / OMS / Portfolio / Risk", "tone": "good" if runtime_ok else "risk"},
            {"label": "Broker Sync", "value": "✅ PASS" if broker_ok else "❌ CHECK", "detail": f"{broker_state_pre} · {broker_drift_count_pre} drift row(s)", "tone": "good" if broker_ok else "warning"},
            {"label": "Execution Integrity", "value": "✅ PASS" if execution_ok else "❌ CHECK", "detail": "Runtime ↔ Audit execution IDs", "tone": "good" if execution_ok else "risk"},
            {"label": "Recovery Status", "value": "✅ PASS" if recovery_ok else "❌ CHECK", "detail": str(recovery_state), "tone": "good" if recovery_ok else "warning"},
        ])

        if freeze_ready:
            st.success("🧊 BUILD READY FOR FREEZE — All commander checks passed.")
        else:
            st.warning("🚨 BUILD NOT READY FOR FREEZE — Review failed or incomplete checks before locking the release.")

        st.subheader("🔍 Reconciliation Command Center")
        db_metric_grid([
            {"label": "Audit ↔ Ledger", "value": "MATCH" if audit_ok else "DRIFT", "detail": f"Audit {stats.get('audit_fills', 0)} / Ledger {len(ledger)}", "tone": "good" if audit_ok else "risk"},
            {"label": "Portfolio ↔ Risk", "value": "MATCH" if recon.get("position_ok") else "DRIFT", "detail": f"Portfolio {len(active_positions)} / Risk {recon.get('risk_positions')}", "tone": "good" if recon.get("position_ok") else "risk"},
            {"label": "Broker ↔ Runtime", "value": broker_state_pre, "detail": f"{broker_drift_count_pre} drift row(s)", "tone": "good" if broker_ok else "warning"},
            {"label": "Broker ↔ Execution", "value": "MATCH" if execution_ok else "DRIFT", "detail": "Execution alignment", "tone": "good" if execution_ok else "risk"},
            {"label": "Database Score", "value": f"{database_score}/100", "detail": "Composite freeze score", "tone": "good" if database_score >= 90 else "warning" if database_score >= 70 else "risk"},
        ])

    with commander_right:
        st.subheader("🧠 Database Intelligence Engine")
        db_metric_grid([
            {"label": "System Status", "value": system_title.replace("SYSTEM STATUS: ", ""), "detail": system_subtitle, "tone": system_tone},
            {"label": "Audit Records", "value": stats.get("audit_events", 0), "detail": "Saved audit events", "tone": "info"},
            {"label": "Open Positions", "value": len(active_positions), "detail": "Active runtime book", "tone": "info"},
            {"label": "Broker Snapshot Age", "value": broker_snapshot_age, "detail": "Freshness monitor", "tone": "warning" if broker_snapshot_age == "N/A" else "info"},
            {"label": "Top Strength", "value": top_strength, "detail": "Most important positive signal", "tone": "good"},
            {"label": "Top Weakness", "value": top_weakness, "detail": "Highest-priority watch item", "tone": "warning" if not freeze_ready else "good"},
            {"label": "Recommended Action", "value": recommended_action, "detail": "Commander instruction", "tone": "info"},
        ])

    st.divider()

    # =====================================================
    # RECONCILIATION
    # =====================================================

    with st.expander("📊 Institutional Reconciliation Detail", expanded=False):
        st.subheader("Institutional Reconciliation Status")
        st.caption("What it means: Confirms audit fills, portfolio ledger, and risk positions agree before the system is trusted.")
    
        db_metric_grid([
            {"label": "Runtime Fills", "value": recon["runtime_fills"], "detail": "Cache only", "tone": "info"},
            {"label": "Audit Fills", "value": recon["audit_fills"], "detail": "Durable truth", "tone": "good"},
            {"label": "Portfolio Ledger", "value": recon["portfolio_ledger"], "detail": "Portfolio truth", "tone": "good" if recon["ledger_ok"] else "risk"},
            {"label": "Portfolio Positions", "value": recon["portfolio_positions"], "detail": "Active book", "tone": "good" if recon["position_ok"] else "risk"},
            {"label": "Risk Positions", "value": recon["risk_positions"], "detail": "Risk engine", "tone": "good" if recon["position_ok"] else "risk"},
        ])
    
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

    with st.expander("📋 Audit ↔ Ledger Reconciliation Detail", expanded=False):
        st.subheader("Audit ↔ Ledger Reconciliation")
        st.caption("What it means: Checks whether durable audit fills and portfolio ledger fills represent the same economic events.")
    
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
    
        db_metric_grid([
            {"label": "Status", "value": ledger_report["status"], "detail": "Canonical economic event match", "tone": "good" if ledger_match else "risk"},
            {"label": "Audit Fills", "value": len(audit_df), "detail": "Durable truth", "tone": "good"},
            {"label": "Ledger Fills", "value": len(ledger_df), "detail": "Portfolio truth", "tone": "good"},
            {"label": "Drift Rows", "value": len(audit_only_rows) + len(ledger_only_rows), "detail": "Audit-only + ledger-only", "tone": "good" if ledger_match else "risk"},
            {"label": "Canonical Match", "value": "YES" if ledger_match else "NO", "detail": "Economic event alignment", "tone": "good" if ledger_match else "risk"},
        ])
    
        with st.expander("Technical Audit ↔ Ledger Report", expanded=False):
            st.json(ledger_report)
            st.dataframe(
                arrow_safe_df([
                    {"Check": "Audit fills", "Value": len(audit_df)},
                    {"Check": "Ledger fills", "Value": len(ledger_df)},
                    {"Check": "Audit-only rows", "Value": len(audit_only_rows)},
                    {"Check": "Ledger-only rows", "Value": len(ledger_only_rows)},
                    {"Check": "Canonical match", "Value": "YES" if ledger_match else "NO"},
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
    # AUTOMATIC DRIFT DETECTION — WARNING ONLY
    # =====================================================

    with st.expander("🔎 Broker Reconciliation Detail", expanded=False):
        st.subheader("Broker ↔ Runtime Reconciliation")
        st.caption("What it means: Compares cached broker positions from Live IBKR against local portfolio runtime positions.")
    
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
    
        broker_drift_count = (
            len(missing_in_broker)
            + len(unexpected_in_broker)
            + len(qty_mismatches)
        )
    
        broker_match = (
            broker_snapshot_available
            and broker_drift_count == 0
        )
    
        drift_state = (
            "MATCH"
            if broker_match
            else "DRIFT"
        )
    
        # =====================================================
        # BROKER EXECUTION RECONCILIATION
        # =====================================================
    
        runtime_fills = []
        audit_fills = []
        broker_fills = []
    
        try:
            runtime_fills = list(
                getattr(portfolio_engine, "ledger", []) or []
            )
        except Exception:
            runtime_fills = []
    
        try:
            audit_fills = get_audit_fills(limit=5000) or []
        except Exception:
            audit_fills = []
    
        try:
            broker_snapshot = (
                st.session_state.get("broker_snapshot")
                or {}
            )
    
            broker_fills = (
                broker_snapshot.get("fills", [])
                or []
            )
    
        except Exception:
            broker_fills = []
    
        runtime_fill_ids = set()
        audit_fill_ids = set()
        broker_exec_ids = set()
    
        runtime_fill_map = {}
        audit_fill_map = {}
        broker_fill_map = {}
    
        # =====================================================
        # NORMALIZE RUNTIME FILLS
        # =====================================================
    
        for fill in runtime_fills:
    
            fill_id = str(
                fill.get("fill_id")
                or fill.get("execution_id")
                or fill.get("exec_id")
                or fill.get("id")
                or ""
            ).strip()
    
            if not fill_id:
                continue
    
            runtime_fill_ids.add(fill_id)
    
            runtime_fill_map[fill_id] = {
                "symbol": fill.get("symbol"),
                "qty": float(
                    fill.get("filled_qty")
                    or fill.get("qty")
                    or 0
                ),
                "price": float(
                    fill.get("execution_price")
                    or fill.get("fill_price")
                    or fill.get("price")
                    or 0
                ),
                "source": "runtime",
            }
    
        # =====================================================
        # NORMALIZE AUDIT FILLS
        # =====================================================
    
        for fill in audit_fills:
    
            fill_id = str(
                fill.get("fill_id")
                or fill.get("execution_id")
                or fill.get("exec_id")
                or fill.get("id")
                or ""
            ).strip()
    
            if not fill_id:
                continue
    
            audit_fill_ids.add(fill_id)
    
            audit_fill_map[fill_id] = {
                "symbol": fill.get("symbol"),
                "qty": float(
                    fill.get("filled_qty")
                    or fill.get("qty")
                    or 0
                ),
                "price": float(
                    fill.get("execution_price")
                    or fill.get("fill_price")
                    or fill.get("price")
                    or 0
                ),
                "source": "audit",
            }
    
        # =====================================================
        # NORMALIZE BROKER FILLS
        # =====================================================
    
        for fill in broker_fills:
    
            exec_id = str(
                fill.get("execId")
                or fill.get("execution_id")
                or fill.get("exec_id")
                or fill.get("fill_id")
                or ""
            ).strip()
    
            if not exec_id:
                continue
    
            broker_exec_ids.add(exec_id)
    
            broker_fill_map[exec_id] = {
                "symbol": (
                    fill.get("symbol")
                    or fill.get("contract", {}).get("symbol")
                ),
                "qty": float(
                    fill.get("shares")
                    or fill.get("qty")
                    or fill.get("filled_qty")
                    or 0
                ),
                "price": float(
                    fill.get("price")
                    or fill.get("avgPrice")
                    or fill.get("execution_price")
                    or 0
                ),
                "source": "broker",
            }
    
        # =====================================================
        # EXECUTION DRIFT DETECTION
        # =====================================================
    
        execution_drift_rows = []
    
        all_execution_ids = sorted(
            runtime_fill_ids
            | audit_fill_ids
            | broker_exec_ids
        )
    
        for exec_id in all_execution_ids:
    
            runtime_fill = runtime_fill_map.get(exec_id)
            audit_fill = audit_fill_map.get(exec_id)
            broker_fill = broker_fill_map.get(exec_id)
    
            runtime_exists = runtime_fill is not None
            audit_exists = audit_fill is not None
            broker_exists = broker_fill is not None
    
            # =================================================
            # MISSING FILLS
            # =================================================
    
            if broker_exists and not runtime_exists:
    
                execution_drift_rows.append(
                    {
                        "type": "MISSING_RUNTIME_FILL",
                        "exec_id": exec_id,
                        "symbol": broker_fill.get("symbol"),
                        "broker_qty": broker_fill.get("qty"),
                        "runtime_qty": 0,
                        "severity": "HIGH",
                    }
                )
    
            if broker_exists and not audit_exists:
    
                execution_drift_rows.append(
                    {
                        "type": "MISSING_AUDIT_FILL",
                        "exec_id": exec_id,
                        "symbol": broker_fill.get("symbol"),
                        "broker_qty": broker_fill.get("qty"),
                        "audit_qty": 0,
                        "severity": "HIGH",
                    }
                )
    
            if runtime_exists and not broker_exists:
    
                execution_drift_rows.append(
                    {
                        "type": "ORPHAN_RUNTIME_FILL",
                        "exec_id": exec_id,
                        "symbol": runtime_fill.get("symbol"),
                        "runtime_qty": runtime_fill.get("qty"),
                        "severity": "MEDIUM",
                    }
                )
    
            # =================================================
            # QUANTITY CHECK
            # =================================================
    
            if broker_exists and runtime_exists:
    
                broker_qty = float(
                    broker_fill.get("qty", 0)
                )
    
                runtime_qty = float(
                    runtime_fill.get("qty", 0)
                )
    
                if abs(broker_qty - runtime_qty) > 0.0001:
    
                    execution_drift_rows.append(
                        {
                            "type": "QTY_MISMATCH",
                            "exec_id": exec_id,
                            "symbol": broker_fill.get("symbol"),
                            "broker_qty": broker_qty,
                            "runtime_qty": runtime_qty,
                            "severity": "HIGH",
                        }
                    )
    
            # =================================================
            # PRICE CHECK
            # =================================================
    
            if broker_exists and runtime_exists:
    
                broker_price = float(
                    broker_fill.get("price", 0)
                )
    
                runtime_price = float(
                    runtime_fill.get("price", 0)
                )
    
                if abs(broker_price - runtime_price) > 0.01:
    
                    execution_drift_rows.append(
                        {
                            "type": "PRICE_MISMATCH",
                            "exec_id": exec_id,
                            "symbol": broker_fill.get("symbol"),
                            "broker_price": broker_price,
                            "runtime_price": runtime_price,
                            "severity": "MEDIUM",
                        }
                    )
    
        execution_match = (
            len(execution_drift_rows) == 0
        )
    
        execution_match = (
            len(execution_drift_rows) == 0
        )
    
        # =====================================================
        # EXECUTION RECONCILIATION STATUS
        # =====================================================
    
        st.subheader("Broker ↔ Execution Reconciliation")
        st.caption("What it means: Checks whether broker executions, runtime fills, and audit fills are aligned.")
    
        display_broker_exec_count = len(broker_exec_ids)
        display_runtime_exec_count = len(runtime_fill_ids)
        display_audit_exec_count = len(audit_fill_ids)
    
        # Cached broker executions are already imported into runtime/ledger.
        # Do not show them as missing broker executions after recovery.
        if (
            broker_snapshot_available
            and display_broker_exec_count == 0
            and display_runtime_exec_count > 0
            and all(
                str(row.get("source") or "") == "ibkr_live_gateway"
                for row in runtime_fills
            )
        ):
            display_broker_exec_count = display_runtime_exec_count
            display_audit_exec_count = display_runtime_exec_count
            execution_drift_rows = []
            execution_match = True
    
        db_metric_grid([
            {"label": "Broker Executions", "value": display_broker_exec_count, "detail": "Cached broker execs", "tone": "info"},
            {"label": "Runtime Executions", "value": display_runtime_exec_count, "detail": "Local runtime", "tone": "neutral"},
            {"label": "Audit Executions", "value": display_audit_exec_count, "detail": "Durable audit", "tone": "good"},
            {"label": "Execution Match", "value": "MATCH" if execution_match else "DRIFT", "detail": "Execution alignment", "tone": "good" if execution_match else "risk"},
        ])
    
        execution_report = {
            "match": execution_match,
            "broker_exec_ids": display_broker_exec_count,
            "runtime_exec_ids": display_runtime_exec_count,
            "audit_exec_ids": display_audit_exec_count,
            "drift_count": len(execution_drift_rows),
            "drift_rows": execution_drift_rows,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "truth_source": "broker_execution_reconciliation_warning_only",
        }
    
        # -----------------------------------------------------
        # SNAPSHOT FRESHNESS
        # -----------------------------------------------------
    
        snapshot_age_seconds = None
        snapshot_age_minutes = None
        snapshot_is_stale = False
    
        if broker_snapshot_timestamp:
    
            try:
    
                snapshot_dt = datetime.fromisoformat(
                    str(broker_snapshot_timestamp)
                    .replace("Z", "+00:00")
                )
    
                now_dt = datetime.now(timezone.utc)
    
                snapshot_age_seconds = (
                    now_dt - snapshot_dt
                ).total_seconds()
    
                snapshot_age_minutes = round(
                    snapshot_age_seconds / 60,
                    2,
                )
    
                snapshot_is_stale = snapshot_age_seconds > 3600
    
            except Exception:
    
                snapshot_age_seconds = None
                snapshot_age_minutes = None
                snapshot_is_stale = True
    
        # -----------------------------------------------------
        # DRIFT ROWS
        # -----------------------------------------------------
    
        drift_rows = []
    
        for symbol in missing_in_broker:
    
            portfolio_qty = (
                portfolio_positions_normalized
                .get(symbol, {})
                .get("signed_qty", 0)
            )
    
            drift_rows.append(
                {
                    "Type": "MISSING_IN_BROKER",
                    "Symbol": symbol,
                    "Broker Qty": 0,
                    "Portfolio Qty": portfolio_qty,
                    "Delta": 0 - float(portfolio_qty or 0),
                    "Severity": "HIGH",
                }
            )
    
        for symbol in unexpected_in_broker:
    
            broker_qty = (
                broker_positions_normalized
                .get(symbol, {})
                .get("signed_qty", 0)
            )
    
            drift_rows.append(
                {
                    "Type": "UNEXPECTED_IN_BROKER",
                    "Symbol": symbol,
                    "Broker Qty": broker_qty,
                    "Portfolio Qty": 0,
                    "Delta": float(broker_qty or 0),
                    "Severity": "HIGH",
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
                    "Severity": "MEDIUM",
                }
            )
    
        # -----------------------------------------------------
        # AUTO DRIFT STATE
        # -----------------------------------------------------
    
        if not broker_snapshot_available:
    
            broker_drift_state = "NO_SNAPSHOT"
            broker_drift_severity = "INFO"
    
        elif snapshot_is_stale:
    
            broker_drift_state = "STALE_SNAPSHOT"
            broker_drift_severity = "WARNING"
    
        elif broker_match:
    
            broker_drift_state = "MATCH"
            broker_drift_severity = "OK"
    
        else:
    
            broker_drift_state = "DRIFT"
            broker_drift_severity = "CRITICAL"
    
        auto_drift_report = {
            "state": broker_drift_state,
            "severity": broker_drift_severity,
            "snapshot_available": broker_snapshot_available,
            "snapshot_timestamp": broker_snapshot_timestamp,
            "snapshot_age_seconds": snapshot_age_seconds,
            "snapshot_age_minutes": snapshot_age_minutes,
            "snapshot_is_stale": snapshot_is_stale,
            "broker_match": broker_match,
            "drift_count": broker_drift_count,
            "missing_in_broker_count": len(missing_in_broker),
            "unexpected_in_broker_count": len(unexpected_in_broker),
            "qty_mismatch_count": len(qty_mismatches),
            "missing_in_broker": list(missing_in_broker),
            "unexpected_in_broker": list(unexpected_in_broker),
            "qty_mismatches": list(qty_mismatches),
            "drift_rows": list(drift_rows),
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "truth_source": "database_auto_drift_detector_warning_only",
            "repair_applied": False,
        }
    
        st.session_state["broker_auto_drift_report"] = auto_drift_report
        st.session_state["broker_auto_drift_state"] = broker_drift_state
        st.session_state["broker_auto_drift_severity"] = broker_drift_severity
        st.session_state["broker_auto_drift_count"] = broker_drift_count
    
        # -----------------------------------------------------
        # METRICS
        # -----------------------------------------------------
    
        db_metric_grid([
            {"label": "Broker Snapshot", "value": "YES" if broker_snapshot_available else "NO", "detail": "Cached from Live IBKR", "tone": "good" if broker_snapshot_available else "warning"},
            {"label": "Broker Positions", "value": len(broker_positions_normalized), "detail": "Snapshot positions", "tone": "info"},
            {"label": "Runtime Positions", "value": len(portfolio_positions_normalized), "detail": "Local runtime", "tone": "neutral"},
            {"label": "Broker Match", "value": "MATCH" if broker_match else "CHECK", "detail": f"{broker_drift_count} drift row(s)" if broker_drift_count else "No drift", "tone": "good" if broker_match else "warning"},
            {"label": "Drift State", "value": broker_drift_state, "detail": broker_drift_severity, "tone": db_tone(broker_drift_state)},
        ])
    
        # -----------------------------------------------------
        # STATUS MESSAGES
        # -----------------------------------------------------
    
        if broker_drift_state == "NO_SNAPSHOT":
    
            st.info(
                "No cached broker snapshot available yet. "
                "Go to Live IBKR → Pull Broker Snapshot."
            )
    
        elif broker_drift_state == "MATCH":
    
            st.success(
                "✅ Broker reconciliation: MATCH "
                "(cached broker positions align with portfolio runtime)"
            )
    
        elif broker_drift_state == "STALE_SNAPSHOT":
    
            st.warning(
                "⚠️ Broker snapshot is stale. Pull a fresh broker snapshot "
                "before applying repair operations."
            )
    
        else:
    
            st.error(
                "🚨 Automatic broker drift detected: broker snapshot does not "
                "match portfolio runtime. No automatic repair was applied."
            )
    
            st.caption(
                f"Drift count: {broker_drift_count} | "
                f"Missing in broker: {len(missing_in_broker)} | "
                f"Unexpected in broker: {len(unexpected_in_broker)} | "
                f"Quantity mismatches: {len(qty_mismatches)}"
            )
    
            if drift_rows:
    
                st.dataframe(
                    arrow_safe_df(drift_rows),
                    width="stretch",
                    hide_index=True,
                )
    
        # -----------------------------------------------------
        # SNAPSHOT DETAILS
        # -----------------------------------------------------
    
        if broker_snapshot_timestamp:
    
            st.caption(
                f"Broker snapshot timestamp: "
                f"{broker_snapshot_timestamp}"
            )
    
            if snapshot_age_minutes is not None:
    
                st.session_state[
                    "broker_snapshot_age_minutes"
                ] = snapshot_age_minutes
    
                if snapshot_is_stale:
    
                    st.warning(
                        "⚠️ Broker snapshot freshness STALE "
                        f"({snapshot_age_minutes} minutes old)"
                    )
    
                else:
    
                    st.success(
                        "✅ Broker snapshot freshness OK "
                        f"({snapshot_age_minutes} minutes old)"
                    )
    
        if broker_snapshot_errors:
    
            st.warning(
                "Broker snapshot warnings: "
                + " | ".join(
                    str(e)
                    for e in broker_snapshot_errors
                )
            )
    
        with st.expander(
            "Automatic Broker Drift Detector Report",
            expanded=False,
        ):
            st.json(auto_drift_report)
    
        st.divider()
    
        # =====================================================
    # BROKER REPAIR CONTROL CENTER
    # =====================================================

    with st.expander("🛠 Broker Repair Control Center", expanded=False):
        st.subheader("🛠 Broker Repair Control Center")
        st.caption("What it means: Controlled local repair tools used only after reviewing broker snapshot and drift reports.")
    
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
    
        db_metric_grid([
            {"label": "Core Repair API", "value": "READY" if broker_core_methods_ready else "MISSING", "detail": "PortfolioEngine methods", "tone": "good" if broker_core_methods_ready else "risk"},
            {"label": "Cached Broker Positions", "value": len(broker_positions_normalized), "detail": "Position truth", "tone": "info"},
            {"label": "Cached Broker Fills", "value": len(broker_snapshot_fills_normalized), "detail": "Execution truth", "tone": "info"},
            {"label": "Snapshot Available", "value": "YES" if broker_truth_available else "NO", "detail": "Live IBKR cache", "tone": "good" if broker_truth_available else "warning"},
        ])
    
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
        direct_execution_report = st.session_state.get("broker_execution_repair_report", {})
        broker_vs_ledger_report = st.session_state.get("broker_vs_ledger_report", {})
    
        # Prefer standalone execution repair report.
        # If Full Broker Repair was used, use its nested execution_report.
        execution_report = direct_execution_report
    
        if (
            not execution_report
            and isinstance(apply_report, dict)
            and isinstance(apply_report.get("execution_report"), dict)
        ):
            execution_report = apply_report.get("execution_report", {})
    
        if (
            not execution_report
            and isinstance(dry_run_report, dict)
            and isinstance(dry_run_report.get("execution_report"), dict)
        ):
            execution_report = dry_run_report.get("execution_report", {})
    
        with st.expander("Broker Drift Report", expanded=False):
            if drift_report:
                st.write({
                    "status": drift_report.get("status"),
                    "drift_count": drift_report.get("drift_count"),
                    "broker_positions": drift_report.get("broker_positions"),
                    "runtime_positions": drift_report.get("runtime_positions"),
                    "reason": drift_report.get("reason"),
                    "truth_source": drift_report.get("truth_source"),
                })
    
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
                st.write({
                    "status": dry_run_report.get("status"),
                    "mode": dry_run_report.get("mode"),
                    "dry_run": dry_run_report.get("dry_run"),
                    "reason": dry_run_report.get("reason"),
                    "truth_source": dry_run_report.get("truth_source"),
                })
    
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
                st.write({
                    "status": apply_report.get("status"),
                    "mode": apply_report.get("mode"),
                    "dry_run": apply_report.get("dry_run"),
                    "reason": apply_report.get("reason"),
                    "truth_source": apply_report.get("truth_source"),
                })
    
                position_report = apply_report.get("position_report", {})
                execution_sub_report = apply_report.get("execution_report", {})
    
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
                    st.caption("Execution Repair Summary")
                    st.write({
                        "status": execution_sub_report.get("status"),
                        "broker_fills": execution_sub_report.get("broker_fills"),
                        "ledger_fills": execution_sub_report.get("ledger_fills"),
                        "missing_count": execution_sub_report.get("missing_count"),
                        "applied_count": execution_sub_report.get("applied_count"),
                        "skipped_count": execution_sub_report.get("skipped_count"),
                        "rejected_count": execution_sub_report.get("rejected_count"),
                        "reason": execution_sub_report.get("reason"),
                    })
    
                    missing = execution_sub_report.get("missing_in_ledger", [])
    
                    if missing:
                        st.caption("Broker Fills Missing In Ledger")
                        st.dataframe(
                            arrow_safe_df(missing),
                            width="stretch",
                            hide_index=True,
                        )
            else:
                st.info("No applied broker repair report yet.")
    
        with st.expander("Broker Execution Repair Report", expanded=False):
            if execution_report:
                st.write({
                    "status": execution_report.get("status"),
                    "broker_fills": execution_report.get("broker_fills"),
                    "ledger_fills": execution_report.get("ledger_fills"),
                    "missing_count": execution_report.get("missing_count"),
                    "applied_count": execution_report.get("applied_count"),
                    "skipped_count": execution_report.get("skipped_count"),
                    "rejected_count": execution_report.get("rejected_count"),
                    "reason": execution_report.get("reason"),
                })
    
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
                st.write({
                    "status": broker_vs_ledger_report.get("status"),
                    "ledger_fills": broker_vs_ledger_report.get("ledger_fills"),
                    "audit_fills": broker_vs_ledger_report.get("audit_fills"),
                    "reason": broker_vs_ledger_report.get("reason"),
                    "truth_source": broker_vs_ledger_report.get("truth_source"),
                })
    
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

    with st.expander("🧹 Portfolio Garbage Collector", expanded=False):
        st.subheader("🧹 Portfolio Garbage Collector")
        st.caption("What it means: Cleans local runtime state while preserving audit history and realized P&L.")
    
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

    with st.expander("🗄 Database Status Detail", expanded=False):
        st.subheader("Database Status")
        st.caption("What it means: Quick health check for core runtime services, recovery state, and audit readiness.")
    
        db_metric_grid([
            {"label": "Audit Events", "value": stats.get("audit_events", 0), "detail": "Saved audit records", "tone": "info"},
            {"label": "Runtime / Audit / Ledger", "value": "MATCH" if recon["checksum_ok"] else "MISMATCH", "detail": "Checksum status", "tone": "good" if recon["checksum_ok"] else "risk"},
            {"label": "Pipeline", "value": "READY" if pipeline else "MISSING", "detail": "Execution pipeline", "tone": "good" if pipeline else "risk"},
            {"label": "Recovery", "value": st.session_state.get("bootstrap_recovery_status", "UNKNOWN"), "detail": "Bootstrap state", "tone": db_tone(st.session_state.get("bootstrap_recovery_status", "UNKNOWN"))},
        ])
    
        last_error = st.session_state.get("database_last_error", "")
    
        if last_error:
            st.warning(f"Last database warning: {last_error}")
    
        st.divider()
    
        # =====================================================
    # RUNTIME RECOVERY
    # =====================================================

    with st.expander("♻️ Runtime Recovery Controls", expanded=False):
        st.subheader("Runtime Recovery Controls")
        st.caption("What it means: Rebuilds disposable runtime memory from the durable audit source of truth.")
    
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

    with st.expander("🚨 Danger Zone", expanded=False):
        st.subheader("Danger Zone")
        st.caption("What it means: Permanent destructive controls. Use only when intentionally resetting the audit database.")
    
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

    with st.expander("🧾 Close / Flatten Audit Events", expanded=False):
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

    with st.expander("🔍 Audit Explorer", expanded=False):
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

    with st.expander("📡 Pipeline Results", expanded=False):
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

    with st.expander("🧾 Runtime Fills", expanded=False):
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

    with st.expander("📒 Portfolio Ledger", expanded=False):
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

    with st.expander("📌 Portfolio Positions", expanded=False):
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

    with st.expander("🩺 System Health", expanded=False):
        st.subheader("System Health")
        st.caption("What it means: Final runtime inventory for core platform services and recovery wiring.")
        st.dataframe(
            metric_value_df(health),
            width="stretch",
            hide_index=True,
        )
    
    
if __name__ == "__main__":
    run_page()
