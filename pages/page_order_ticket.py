# =========================================================
# 🎫 MANUAL ORDER TICKET — v2.0
# INSTITUTIONAL MANUAL ORDER COMMAND CENTER
# LIVE-SAFE OMS ORDER ENTRY + COMMANDER TREATMENT
# PRE-TRADE RISK CHECKLIST + ORDER PREVIEW
# FILL PROPAGATION DIAGNOSTICS + BROKER CANCEL CONTROLS
# =========================================================

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, List
import html

import pandas as pd
import streamlit as st

from core.bootstrap import init_core
from core.responsive import inject_responsive_css
from core.ui_cards import inject_card_css


def now():
    return datetime.now(timezone.utc).isoformat()


def flatten_for_table(data: Dict[str, Any]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []

    if not isinstance(data, dict):
        return pd.DataFrame([{"Field": "value", "Value": str(data)}])

    for key, value in data.items():
        if isinstance(value, (dict, list, tuple)):
            value = str(value)

        rows.append({
            "Field": str(key),
            "Value": value,
        })

    return pd.DataFrame(rows)


def _safe_len(obj) -> int:
    try:
        return len(obj)
    except Exception:
        return 0


def _extract_oms_fills(oms):
    if oms is None:
        return []

    for name in (
        "fills_snapshot",
        "raw_fills_snapshot",
        "fills",
        "fill_registry",
        "execution_fills",
        "fill_history",
        "completed_fills",
        "recent_fills",
        "fills_by_id",
        "broker_fills",
    ):
        if hasattr(oms, name):
            try:
                value = getattr(oms, name)

                if callable(value):
                    value = value()

                if isinstance(value, dict):
                    return list(value.values())

                if isinstance(value, list):
                    return value

            except Exception:
                pass

    try:
        snapshot = oms.snapshot()
        if isinstance(snapshot, dict):
            runtime_fill_count = snapshot.get("raw_fills")
            if isinstance(runtime_fill_count, int):
                return [None] * runtime_fill_count
    except Exception:
        pass

    return []


def _extract_execution_registry(oms):
    if oms is None:
        return []

    for name in (
        "execution_registry",
        "fill_identity_registry",
        "broker_execution_registry",
        "execution_map",
        "executions",
        "broker_fills",
    ):
        if hasattr(oms, name):
            try:
                value = getattr(oms, name)

                if callable(value):
                    value = value()

                if isinstance(value, dict):
                    return list(value.values())

                if isinstance(value, list):
                    return value

            except Exception:
                pass

    try:
        snapshot = oms.snapshot()
        if isinstance(snapshot, dict):
            count = snapshot.get("execution_registry")
            if isinstance(count, int):
                return [None] * count
    except Exception:
        pass

    return []


def _extract_last_fill(oms):
    if oms is None:
        return None

    for name in (
        "last_fill",
        "last_execution",
        "last_fill_payload",
        "latest_fill",
        "last_broker_fill",
    ):
        if hasattr(oms, name):
            try:
                value = getattr(oms, name)

                if callable(value):
                    value = value()

                if value:
                    return value

            except Exception:
                pass

    try:
        snapshot = oms.snapshot()
        if isinstance(snapshot, dict):
            if snapshot.get("last_fill"):
                return snapshot.get("last_fill")
    except Exception:
        pass

    return None


def _extract_audit_store(oms, gateway):
    candidates = [
        getattr(oms, "audit_store", None),
        getattr(oms, "audit_logger", None),
        getattr(gateway, "audit_store", None),
        st.session_state.get("audit_store"),
    ]

    for candidate in candidates:
        if candidate is not None:
            return candidate

    return None


def _extract_audit_fills(audit_store):
    if audit_store is None:
        return []

    for name in (
        "fills",
        "recent_fills",
        "records",
        "entries",
        "events",
        "get_fills",
        "get_records",
    ):
        if hasattr(audit_store, name):
            try:
                value = getattr(audit_store, name)

                if callable(value):
                    try:
                        value = value(limit=10000)
                    except TypeError:
                        value = value()

                if isinstance(value, dict):
                    return list(value.values())

                if isinstance(value, list):
                    return value

            except Exception:
                pass

    return []


def _extract_portfolio_ledger(portfolio_engine):
    if portfolio_engine is None:
        return []

    for name in (
        "ledger_snapshot",
        "ledger",
        "fills",
        "positions_ledger",
        "transactions",
        "trade_log",
    ):
        if hasattr(portfolio_engine, name):
            try:
                value = getattr(portfolio_engine, name)

                if callable(value):
                    value = value()

                if isinstance(value, dict):
                    return list(value.values())

                if isinstance(value, list):
                    return value

            except Exception:
                pass

    return []


def _extract_broker_positions(gateway):
    positions = []

    if gateway is None:
        return positions

    try:
        if hasattr(gateway, "positions_snapshot"):
            positions = gateway.positions_snapshot()

        elif hasattr(gateway, "get_positions"):
            raw_positions = gateway.get_positions()

            if isinstance(raw_positions, dict):
                positions = [
                    {"symbol": symbol, "position": qty}
                    for symbol, qty in raw_positions.items()
                ]
            elif isinstance(raw_positions, list):
                positions = raw_positions

    except Exception:
        positions = []

    if isinstance(positions, dict):
        positions = list(positions.values())

    return positions if isinstance(positions, list) else []


def _extract_broker_open_orders(gateway):
    open_orders = []

    if gateway is None:
        return open_orders

    try:
        if hasattr(gateway, "open_orders"):
            open_orders = gateway.open_orders()
        elif hasattr(gateway, "get_open_orders"):
            open_orders = gateway.get_open_orders()
    except Exception:
        open_orders = []

    if isinstance(open_orders, dict):
        open_orders = list(open_orders.values())

    return open_orders if isinstance(open_orders, list) else []


def _cancel_broker_order(gateway, broker_order_id: str) -> bool:
    if gateway is None:
        return False

    broker_order_id = str(broker_order_id or "").strip()

    if not broker_order_id:
        return False

    if hasattr(gateway, "cancel_order"):
        try:
            return bool(gateway.cancel_order(broker_order_id))
        except Exception as exc:
            st.session_state["manual_ticket_cancel_error"] = str(exc)
            return False

    return False




def inject_order_ticket_css() -> None:
    inject_responsive_css(max_width=1500)
    inject_card_css()
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1.4rem !important;
                padding-bottom: 2.5rem !important;
                max-width: 1500px !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }

            h1 {
                font-size: var(--jfbp-type-h1, clamp(1.75rem, 3.6vw, 2.45rem)) !important;
                font-weight: 850 !important;
                color: #1f2937 !important;
                line-height: 1.12 !important;
            }

            h2, h3 {
                font-size: var(--jfbp-type-h2, clamp(1.08rem, 2.2vw, 1.45rem)) !important;
                font-weight: 850 !important;
                color: #1f2937 !important;
                line-height: 1.18 !important;
            }

            div[data-testid="stHorizontalBlock"] {
                gap: 0.85rem !important;
                align-items: stretch !important;
            }

            div[data-testid="stHorizontalBlock"] > div,
            div[data-testid="column"] {
                min-width: 0 !important;
            }

            div[data-testid="stDataFrame"] {
                width: 100% !important;
                max-width: 100% !important;
                overflow-x: auto !important;
                border-radius: 12px !important;
            }

            div[data-testid="stAlert"] {
                overflow-wrap: anywhere !important;
                word-break: normal !important;
            }

            .stButton > button,
            div[data-testid="stFormSubmitButton"] button {
                border-radius: 10px !important;
                font-weight: 800 !important;
                min-height: 40px !important;
                border: 1px solid #d7e3f5 !important;
            }

            .ticket-card {
                border-radius: 14px;
                padding: 0.85rem 0.95rem;
                margin-bottom: 0.70rem;
                border: 1px solid #dbe3ef;
                background: #f8fafc;
                min-width: 0;
                overflow-wrap: normal;
            }

            .ticket-card.good {
                background: #ecfdf5;
                border-color: #bbf7d0;
            }

            .ticket-card.warning {
                background: #fffbeb;
                border-color: #fde68a;
            }

            .ticket-card.risk {
                background: #fef2f2;
                border-color: #fecaca;
            }

            .ticket-card.info {
                background: #eff6ff;
                border-color: #bfdbfe;
            }

            .ticket-card-label {
                font-size: var(--jfbp-type-card-label, 0.72rem);
                text-transform: uppercase;
                letter-spacing: 0.04em;
                color: #64748b;
                font-weight: 850;
                margin-bottom: 0.28rem;
                white-space: normal;
            }

            .ticket-card-value {
                font-size: var(--jfbp-type-card-value, clamp(1.05rem, 2.2vw, 1.35rem));
                line-height: 1.18;
                font-weight: 880;
                color: #111827;
                white-space: normal;
                overflow-wrap: normal;
                word-break: keep-all;
            }

            .ticket-card.good .ticket-card-value {
                color: #166534;
            }

            .ticket-card.warning .ticket-card-value {
                color: #92400e;
            }

            .ticket-card.risk .ticket-card-value {
                color: #991b1b;
            }

            .ticket-card.info .ticket-card-value {
                color: #1d4ed8;
            }

            .ticket-card-detail {
                font-size: var(--jfbp-type-caption, 0.82rem);
                color: #64748b;
                margin-top: 0.34rem;
                line-height: 1.35;
                overflow-wrap: normal;
            }

            .ticket-flow {
                background: #eff6ff;
                border: 1px solid #bfdbfe;
                border-radius: 12px;
                padding: 0.72rem 0.82rem;
                margin: 0.50rem 0 0.78rem 0;
                color: #1e3a8a;
                font-weight: 750;
                line-height: 1.4;
            }

            .ticket-panel {
                border: 1px solid #e5e7eb;
                border-radius: 14px;
                background: #ffffff;
                padding: 0.88rem 0.94rem;
                margin-bottom: 0.82rem;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            }

            .ticket-hero {
                border: 1px solid;
                border-radius: 18px;
                padding: 0.88rem 0.92rem;
                margin: 0.60rem 0 0.82rem 0;
                box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05);
                overflow-wrap: anywhere;
            }

            .ticket-hero-kicker {
                font-size: var(--jfbp-type-card-label, 0.72rem);
                font-weight: 850;
                letter-spacing: 0.055em;
                text-transform: uppercase;
                color: #64748b;
                margin-bottom: 0.24rem;
            }

            .ticket-hero-title {
                font-size: clamp(1.22rem, 2.35vw, 1.62rem);
                font-weight: 880;
                line-height: 1.14;
                margin-bottom: 0.30rem;
            }

            .ticket-hero-text {
                font-size: var(--jfbp-type-body, 0.94rem);
                font-weight: 700;
                color: #334155;
                line-height: 1.38;
                margin-bottom: 0.36rem;
            }

            .ticket-hero-action {
                border-radius: 12px;
                padding: 0.60rem 0.78rem;
                background: rgba(255,255,255,0.75);
                border: 1px solid rgba(148, 163, 184, 0.35);
                color: #111827;
                font-size: var(--jfbp-type-body, 0.94rem);
                font-weight: 820;
            }

            .ticket-check-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 0.75rem;
                padding: 0.62rem 0.72rem;
                margin-bottom: 0.42rem;
                background: #f8fafc;
                border: 1px solid #dbe3ef;
                border-radius: 12px;
                font-size: 0.9rem;
                font-weight: 750;
                color: #111827;
            }

            .ticket-check-detail {
                color: #64748b;
                font-size: 0.78rem;
                font-weight: 700;
                text-align: right;
            }

            @media (max-width: 1180px) {
                .block-container {
                    padding-left: 1.25rem !important;
                    padding-right: 1.25rem !important;
                }

                div[data-testid="stHorizontalBlock"] {
                    flex-wrap: wrap !important;
                }

                div[data-testid="stHorizontalBlock"] > div,
                div[data-testid="column"] {
                    flex: 1 1 48% !important;
                    width: 48% !important;
                    min-width: 48% !important;
                }
            }

            @media (max-width: 760px) {
                .block-container {
                    padding-left: 0.9rem !important;
                    padding-right: 0.9rem !important;
                }

                div[data-testid="stHorizontalBlock"] > div,
                div[data-testid="column"] {
                    flex: 1 1 100% !important;
                    width: 100% !important;
                    min-width: 100% !important;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def responsive_columns(spec, gap: str = "small"):
    return st.columns(spec, gap=gap)


def ticket_tip(text: str) -> None:
    st.caption(f"💡 {text}")


def ticket_metric_card(
    label: str,
    value,
    detail: str = "",
    tone: str = "neutral",
) -> None:
    label_text = str(label)
    value_text = str(value)
    detail_text = str(detail or "")

    detail_html = (
        f'<div class="ticket-card-detail">{detail_text}</div>'
        if detail_text
        else ""
    )

    st.markdown(
        f"""
        <div class="ticket-card {tone}">
            <div class="ticket-card-label">{label_text}</div>
            <div class="ticket-card-value">{value_text}</div>
            {detail_html}
        </div>
        """,
        unsafe_allow_html=True,
    )



def ticket_tone_palette(tone: str):
    palette = {
        "neutral": ("#f8fafc", "#dbe3ef", "#111827"),
        "info": ("#eff6ff", "#bfdbfe", "#1d4ed8"),
        "good": ("#ecfdf5", "#bbf7d0", "#166534"),
        "warning": ("#fffbeb", "#fde68a", "#92400e"),
        "risk": ("#fef2f2", "#fecaca", "#991b1b"),
    }
    return palette.get(str(tone), palette["neutral"])


def render_ticket_hero(title: str, subtitle: str, action: str, tone: str = "info") -> None:
    background, border, value_color = ticket_tone_palette(tone)
    st.markdown(
        f"""
        <div class="ticket-hero" style="background:{background};border-color:{border};">
            <div class="ticket-hero-kicker">Institutional Manual Order Command</div>
            <div class="ticket-hero-title" style="color:{value_color};">{html.escape(str(title))}</div>
            <div class="ticket-hero-text">{html.escape(str(subtitle))}</div>
            <div class="ticket-hero-action">{html.escape(str(action))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_ticket_check(label: str, passed: bool, detail: str = "") -> None:
    icon = "✅" if passed else "❌"
    color = "#166534" if passed else "#991b1b"
    st.markdown(
        f"""
        <div class="ticket-check-row">
            <span style="color:{color};">{icon} {html.escape(str(label))}</span>
            <span class="ticket-check-detail">{html.escape(str(detail))}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def readiness_tone(mode: str, live_armed: bool, kill_switch: bool) -> tuple[str, str, str]:
    if kill_switch:
        return (
            "EXECUTION LOCKED",
            "Kill switch is active. New manual orders should remain blocked.",
            "risk",
        )

    if mode == "LIVE" and live_armed:
        return (
            "LIVE ARMED",
            "LIVE mode is active and trading is armed. Orders may route to broker.",
            "risk",
        )

    if mode == "LIVE" and not live_armed:
        return (
            "LIVE NOT ARMED",
            "LIVE infrastructure is active, but trading is not armed.",
            "warning",
        )

    return (
        "SIM READY",
        "SIM mode is active. Manual orders are routed through the simulator path.",
        "good",
    )


def display_table_or_info(df, empty_message: str) -> None:
    if df is not None and not df.empty:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(empty_message)


def page():

    gateway, market, oms, portfolio_engine = init_core()

    inject_order_ticket_css()

    st.title("🎫 Manual Order Ticket")
    st.caption(
        "Manual Order Ticket v2.0 Institutional Edition — commander order entry, pre-trade risk checklist, OMS-routed submission, fill propagation, and broker cancel controls."
    )

    st.markdown(
        """
        <div class="ticket-flow">
            🚀 Workflow: Market Pulse → Scanner → Research Stock → Trade Command Center → OMS Execution → Live IBKR → Manual Order Ticket → Broker → Position Command Center → Journal
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("📘 How to use this page", expanded=False):
        st.markdown(
            """
            **1. Confirm the trade idea**  
            Start from Scanner and Research Stock. Do not use the manual ticket as a replacement for analysis.

            **2. Verify OMS and broker readiness**  
            Check OMS Execution first, then confirm Live IBKR is connected if working in LIVE mode.

            **3. Build the order ticket**  
            Enter symbol, side, quantity, order type, and limit price when required.

            **4. Review the order preview**  
            Confirm symbol, side, size, mode, and approximate notional value.

            **5. Submit only after confirmation**  
            Manual orders require explicit confirmation before routing through OMS.

            **6. Monitor propagation**  
            After submission, verify OMS fills, audit fills, portfolio ledger, and broker state.
            """
        )

    mode = str(st.session_state.get("mode", "SIM")).upper().strip()
    live_armed = bool(st.session_state.get("live_trading_armed", False))
    kill_switch = bool(st.session_state.get("risk_kill_switch", False))

    if mode not in ("SIM", "LIVE"):
        mode = "SIM"

    readiness_label, readiness_detail, readiness_card_tone = readiness_tone(
        mode,
        live_armed,
        kill_switch,
    )

    oms_ready = oms is not None
    gateway_connected = False
    if gateway is not None:
        for attr in ("broker_connected", "ui_connected", "connected"):
            if hasattr(gateway, attr):
                try:
                    gateway_connected = bool(getattr(gateway, attr))
                    break
                except Exception:
                    gateway_connected = False

    if kill_switch:
        command_title = "🛑 ORDER TICKET STATUS: LOCKED"
        command_tone = "risk"
        command_action = "Manual orders are blocked by the Kill Switch."
    elif mode == "LIVE" and live_armed:
        command_title = "🚨 ORDER TICKET STATUS: LIVE ARMED"
        command_tone = "risk"
        command_action = "Manual orders may route to the broker through OMS. Verify every field before submitting."
    elif mode == "LIVE":
        command_title = "🟡 ORDER TICKET STATUS: LIVE NOT ARMED"
        command_tone = "warning"
        command_action = "LIVE infrastructure is selected, but order routing should remain blocked until OMS is armed."
    else:
        command_title = "🟢 ORDER TICKET STATUS: SIM READY"
        command_tone = "good"
        command_action = "SIM route is ready for manual ticket testing."

    command_summary = (
        f"Mode: {mode} · OMS: {'ONLINE' if oms_ready else 'MISSING'} · "
        f"Gateway: {'CONNECTED' if gateway_connected else 'DISCONNECTED'} · "
        f"LIVE Armed: {'YES' if live_armed else 'NO'} · Kill Switch: {'ON' if kill_switch else 'OFF'}"
    )

    render_ticket_hero(command_title, command_summary, command_action, command_tone)

    # =====================================================
    # EXECUTION GUARD
    # =====================================================

    st.divider()
    st.subheader("🛡️ Execution Guard")
    st.caption(
        "What it means: Confirms whether the manual order ticket is operating in SIM or LIVE mode, "
        "whether live trading is armed, and whether the kill switch blocks execution."
    )

    guard_cols = responsive_columns(4)

    with guard_cols[0]:
        ticket_metric_card(
            "Mode",
            mode,
            "Execution environment.",
            tone="risk" if mode == "LIVE" else "info",
        )

    with guard_cols[1]:
        ticket_metric_card(
            "LIVE Armed",
            "YES" if live_armed else "NO",
            "Broker routing permission.",
            tone="risk" if live_armed else "neutral",
        )

    with guard_cols[2]:
        ticket_metric_card(
            "Kill Switch",
            "ON" if kill_switch else "OFF",
            "Hard execution block.",
            tone="risk" if kill_switch else "good",
        )

    with guard_cols[3]:
        ticket_metric_card(
            "Readiness",
            readiness_label,
            readiness_detail,
            tone=readiness_card_tone,
        )

    if kill_switch:
        st.error("Kill switch is active. Manual orders are blocked.")
    elif mode == "LIVE" and not live_armed:
        st.warning(
            "LIVE infrastructure is active, but LIVE trading is not armed. "
            "Orders should remain blocked until OMS Execution arms live trading."
        )
    elif mode == "LIVE" and live_armed:
        st.error(
            "LIVE TRADING ARMED. Confirm broker connection, account snapshot, symbol, side, "
            "quantity, and order type before submitting."
        )
    else:
        st.success("SIM mode active. This is the recommended environment for testing manual tickets.")

    st.subheader("✅ Pre-Trade Risk Checklist")
    st.caption("Commander check before any manual order is built or routed.")

    check_left, check_right = responsive_columns([0.58, 0.42], gap="large")
    with check_left:
        render_ticket_check("OMS Loaded", oms_ready, "Required for routing")
        render_ticket_check("Kill Switch OFF", not kill_switch, "Hard block must be OFF")
        render_ticket_check("Mode Confirmed", mode in ("SIM", "LIVE"), mode)
        render_ticket_check("LIVE Armed Only When Intended", (mode != "LIVE") or live_armed, "Required only for LIVE routing")
        render_ticket_check("Gateway Connected for LIVE", (mode != "LIVE") or gateway_connected, "Required before live broker routing")

    with check_right:
        if kill_switch:
            render_ticket_hero(
                "🚫 PRE-TRADE STATUS: BLOCKED",
                "Kill Switch is ON.",
                "DO NOT SUBMIT MANUAL ORDERS",
                "risk",
            )
        elif mode == "LIVE" and not live_armed:
            render_ticket_hero(
                "⚠️ PRE-TRADE STATUS: LIVE NOT ARMED",
                "LIVE mode is selected but routing permission is OFF.",
                "ARM LIVE ONLY FROM OMS WHEN INTENTIONAL",
                "warning",
            )
        elif mode == "LIVE" and live_armed:
            render_ticket_hero(
                "🚨 PRE-TRADE STATUS: LIVE ROUTING POSSIBLE",
                "OMS may route broker orders if this ticket is submitted.",
                "VERIFY SYMBOL, SIDE, SIZE, ORDER TYPE, AND BROKER",
                "risk",
            )
        else:
            render_ticket_hero(
                "🟢 PRE-TRADE STATUS: SIM SAFE",
                "Manual ticket is operating in simulator mode.",
                "READY FOR SIM ORDER TESTING",
                "good",
            )

    # =====================================================
    # ORDER ENTRY
    # =====================================================

    st.divider()
    st.subheader("🧾 Order Entry")
    st.caption(
        "What it means: Builds a single manual OMS order. Use this only after the trade idea, "
        "risk controls, and execution mode have been verified."
    )

    with st.form("manual_order_ticket_form"):

        entry_left, entry_right = responsive_columns(2, gap="large")

        with entry_left:
            symbol = st.text_input(
                "Symbol",
                value="AAPL",
                help="Ticker symbol to route through OMS.",
            ).upper().strip()

            side = st.selectbox(
                "Side",
                ["BUY", "SELL"],
                help="BUY opens/adds long exposure. SELL reduces/closes long exposure or may open short depending on OMS rules.",
            )

            qty = st.number_input(
                "Quantity",
                min_value=1,
                max_value=100000,
                value=1,
                step=1,
                help="Share quantity. Confirm position size before submitting.",
            )

        with entry_right:
            order_type = st.selectbox(
                "Order Type",
                ["MKT", "LMT"],
                index=0,
                help="MKT routes without a limit price. LMT requires a limit price.",
            )

            limit_price = None

            if order_type == "LMT":
                limit_price = st.number_input(
                    "Limit Price",
                    min_value=0.01,
                    value=100.00,
                    step=0.01,
                    format="%.2f",
                    help="Maximum buy price or minimum sell price for limit orders.",
                )
            else:
                st.info("Market order selected. No limit price will be sent.")

            estimated_value = 0.0

            if order_type == "LMT" and limit_price is not None:
                estimated_value = float(qty) * float(limit_price)

            preview_price = (
                f"${float(limit_price):,.2f}"
                if order_type == "LMT" and limit_price is not None
                else "Market"
            )

            st.markdown("### Order Preview")
            ticket_metric_card(
                "Preview",
                f"{side} {int(qty):,} {symbol}",
                f"{order_type} · {preview_price} · {mode} mode",
                tone="risk" if mode == "LIVE" else "info",
            )

            if estimated_value > 0:
                ticket_metric_card(
                    "Estimated Notional",
                    f"${estimated_value:,.2f}",
                    "Approximate order value before commissions, FX, and slippage.",
                    tone="neutral",
                )

        confirm = st.checkbox(
            "I confirm this order should be routed through OMS",
            value=False,
        )

        submit = st.form_submit_button(
            "Submit Manual Order",
            use_container_width=True,
        )

    st.subheader("🎯 Commander Order Preview")
    st.caption("Final visual preview before OMS submission. The order is not routed unless the form was submitted with confirmation.")

    preview_cols = responsive_columns(5)
    with preview_cols[0]:
        ticket_metric_card("Symbol", symbol or "—", "Manual order symbol", tone="info")
    with preview_cols[1]:
        ticket_metric_card("Side", side, "BUY or SELL", tone="good" if side == "BUY" else "warning")
    with preview_cols[2]:
        ticket_metric_card("Quantity", f"{int(qty):,}", "Share quantity", tone="info")
    with preview_cols[3]:
        ticket_metric_card("Order Type", order_type, "MKT or LMT", tone="warning" if order_type == "MKT" else "info")
    with preview_cols[4]:
        ticket_metric_card("Route Mode", mode, "SIM or LIVE", tone="risk" if mode == "LIVE" else "good")

    if order_type == "LMT" and limit_price is not None:
        st.info(f"Limit order preview: {side} {int(qty):,} {symbol} @ ${float(limit_price):,.2f}")
    else:
        st.warning(f"Market order preview: {side} {int(qty):,} {symbol}. Market orders can fill away from the last displayed price.")

    if submit:

        if kill_switch:
            st.error("Order blocked: kill switch is active.")
            return

        if mode == "LIVE" and not live_armed:
            st.error("Order blocked: LIVE mode is active but LIVE trading is not armed.")
            return

        if not confirm:
            st.error("Order blocked: confirmation checkbox is required.")
            return

        if not symbol:
            st.error("Order blocked: symbol is required.")
            return

        signal: Dict[str, Any] = {
            "source": "manual_order_ticket_v2_0",
            "symbol": symbol,
            "action": side,
            "side": side,
            "qty": int(qty),
            "quantity": int(qty),
            "order_type": order_type,
            "mode": mode,
            "timestamp": now(),
        }

        if order_type == "LMT":
            signal["limit_price"] = float(limit_price)

        try:
            result = oms.execute_signal(signal)

            if result is None:
                st.error("Order blocked or rejected by OMS.")
                st.write("Last OMS error:", getattr(oms, "last_error", ""))
                st.write("Last rejection:", getattr(oms, "last_rejection", None))
                return

            status = str(result.get("status", "")).upper()

            if status in {"WORKING", "SUBMITTED", "ROUTED", "ACKNOWLEDGED"}:
                st.success("Order submitted to OMS / broker path.")
            elif status in {"FILLED", "PARTIAL_FILLED"}:
                st.success("Order filled.")
            else:
                st.warning(f"Order returned status: {status}")

            with st.expander("Last Manual Order Result", expanded=True):
                st.dataframe(
                    flatten_for_table(result),
                    use_container_width=True,
                    hide_index=True,
                )

        except Exception as exc:
            st.error(f"Manual order failed: {exc}")

    # =====================================================
    # FILL PROPAGATION CHECK
    # =====================================================

    st.divider()
    st.subheader("🔁 Fill Propagation Check")
    st.caption(
        "What it means: Validates whether fills are moving from broker/OMS into the execution registry, "
        "portfolio ledger, and audit trail."
    )

    try:
        broker_positions = _extract_broker_positions(gateway)
        oms_fills = _extract_oms_fills(oms)
        execution_registry = _extract_execution_registry(oms)
        last_fill = _extract_last_fill(oms)

        audit_store = _extract_audit_store(oms, gateway)
        audit_fills = _extract_audit_fills(audit_store)

        portfolio_ledger = _extract_portfolio_ledger(portfolio_engine)

        fill_cols = responsive_columns(5)

        with fill_cols[0]:
            ticket_metric_card(
                "Broker Positions",
                "SIM N/A" if mode == "SIM" else _safe_len(broker_positions),
                "Broker-side position count.",
                tone="neutral" if mode == "SIM" else "info",
            )

        with fill_cols[1]:
            ticket_metric_card(
                "OMS Fills",
                _safe_len(oms_fills),
                "Runtime OMS fills.",
                tone="info",
            )

        with fill_cols[2]:
            ticket_metric_card(
                "OMS Registry",
                _safe_len(execution_registry),
                "Execution identity records.",
                tone="info",
            )

        with fill_cols[3]:
            ticket_metric_card(
                "Portfolio Ledger",
                _safe_len(portfolio_ledger),
                "Portfolio-side records.",
                tone="info",
            )

        with fill_cols[4]:
            ticket_metric_card(
                "Audit Fills",
                _safe_len(audit_fills),
                "Persistent audit truth.",
                tone="info",
            )

        last_error = getattr(oms, "last_error", None)

        if last_error:
            st.warning(f"Last OMS Error: {last_error}")
        else:
            st.caption("Last OMS Error: None")

        if mode == "SIM":
            st.caption(
                "SIM mode uses OMS synthetic fills. Broker positions are not expected "
                "to update until LIVE/paper broker callbacks are tested."
            )

        if last_fill:
            with st.expander("Last Fill Payload", expanded=False):
                st.dataframe(
                    flatten_for_table(last_fill),
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.info("No fill detected yet.")

    except Exception as exc:
        st.error(f"Fill propagation diagnostics failed: {exc}")

    # =====================================================
    # DIAGNOSTICS
    # =====================================================

    st.divider()
    st.subheader("🧪 Diagnostics & Broker State")
    st.caption(
        "What it means: Collapsed operational views for OMS state, gateway connection, broker positions, "
        "open orders, and account summary. These are normally used for testing and troubleshooting."
    )

    with st.expander("OMS Snapshot", expanded=False):
        try:
            oms_snapshot = oms.snapshot()
            st.dataframe(
                flatten_for_table(oms_snapshot),
                use_container_width=True,
                hide_index=True,
            )
        except Exception as exc:
            st.error(f"OMS snapshot failed: {exc}")

    with st.expander("Gateway Status", expanded=False):
        try:
            if gateway and hasattr(gateway, "connection_status"):
                gateway_status = gateway.connection_status()
                st.dataframe(
                    flatten_for_table(gateway_status),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Gateway status unavailable.")
        except Exception as exc:
            st.error(f"Gateway status failed: {exc}")

    with st.expander("Broker Positions", expanded=False):
        try:
            positions = _extract_broker_positions(gateway)

            if positions:
                st.dataframe(
                    pd.DataFrame(positions),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                if mode == "SIM":
                    st.info(
                        "No broker positions expected in SIM mode. "
                        "SIM fills are internal OMS fills."
                    )
                else:
                    st.info("No broker positions returned.")

        except Exception as exc:
            st.error(f"Broker positions failed: {exc}")

    with st.expander("Broker Open Orders & Cancel Controls", expanded=False):
        try:
            open_orders = _extract_broker_open_orders(gateway)

            if open_orders:
                open_orders_df = pd.DataFrame(open_orders)

                st.dataframe(
                    open_orders_df,
                    use_container_width=True,
                    hide_index=True,
                )

                st.markdown("### Broker Order Controls")
                st.warning(
                    "Cancel controls send cancel requests to the broker gateway. "
                    "Use only for test/stale/open orders."
                )

                broker_order_ids = []

                if "broker_order_id" in open_orders_df.columns:
                    broker_order_ids = [
                        str(x).strip()
                        for x in open_orders_df["broker_order_id"].tolist()
                        if str(x).strip()
                    ]

                broker_order_ids = list(dict.fromkeys(broker_order_ids))

                if broker_order_ids:

                    selected_broker_order_id = st.selectbox(
                        "Select broker order to cancel",
                        broker_order_ids,
                        key="manual_ticket_cancel_order_select",
                    )

                    cancel_left, cancel_right = responsive_columns(2)

                    confirm_cancel_selected = cancel_left.checkbox(
                        "Confirm cancel selected broker order",
                        key="manual_ticket_confirm_cancel_selected",
                    )

                    cancel_selected_clicked = cancel_left.button(
                        "Cancel Selected Broker Order",
                        use_container_width=True,
                        disabled=not confirm_cancel_selected,
                    )

                    confirm_cancel_all = cancel_right.checkbox(
                        "Confirm cancel ALL broker open orders",
                        key="manual_ticket_confirm_cancel_all",
                    )

                    cancel_all_clicked = cancel_right.button(
                        "Cancel All Broker Orders",
                        use_container_width=True,
                        disabled=not confirm_cancel_all,
                    )

                    if cancel_selected_clicked:
                        ok = _cancel_broker_order(
                            gateway,
                            selected_broker_order_id,
                        )

                        if ok:
                            st.success(
                                f"Cancel request sent for broker order "
                                f"{selected_broker_order_id}."
                            )
                            st.rerun()
                        else:
                            st.error(
                                "Cancel selected failed. "
                                f"{st.session_state.get('manual_ticket_cancel_error', '')}"
                            )

                    if cancel_all_clicked:
                        cancelled = 0
                        failed = 0

                        for broker_order_id in broker_order_ids:
                            ok = _cancel_broker_order(
                                gateway,
                                broker_order_id,
                            )

                            if ok:
                                cancelled += 1
                            else:
                                failed += 1

                        if failed == 0:
                            st.success(
                                f"Cancel requests sent for all {cancelled} broker orders."
                            )
                        else:
                            st.warning(
                                f"Cancel attempted. Sent={cancelled}, Failed={failed}."
                            )

                        st.rerun()

                else:
                    st.info("Open orders returned, but no broker_order_id column was found.")

            else:
                st.info("No broker open orders returned.")

        except Exception as exc:
            st.error(f"Broker open orders failed: {exc}")

    with st.expander("Broker Account Summary", expanded=False):
        try:
            account_summary = []

            if gateway and hasattr(gateway, "account_summary"):
                account_summary = gateway.account_summary()
            elif gateway and hasattr(gateway, "get_account_summary"):
                account_summary = gateway.get_account_summary()

            if account_summary:
                st.dataframe(
                    pd.DataFrame(account_summary),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No broker account summary returned.")

        except Exception as exc:
            st.error(f"Broker account summary failed: {exc}")


def run_page():
    page()
