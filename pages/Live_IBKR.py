# =========================================================
# 📡 LIVE IBKR PAGE v25.1
# INSTITUTIONAL BROKER OPERATIONS CENTER
# LIVE CONNECTIVITY + OMS EXECUTION STATUS + ACCOUNT COMMAND BRIEF
# BROKER SNAPSHOT SYNC + RECOVERY CENTER + TELEGRAM OPS
# STREAMLIT-SAFE + MOBILE RESPONSIVE + HELP LAYER
# =========================================================

from __future__ import annotations

from datetime import datetime, timezone
import html

import streamlit as st

from core.bootstrap import init_core


# =========================================================
# RESPONSIVE UI HELPERS
# =========================================================

def inject_live_ibkr_responsive_css() -> None:
    """Visual-only responsive guardrails for Live IBKR."""

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
                font-size: clamp(1.9rem, 4vw, 2.55rem) !important;
                font-weight: 850 !important;
                line-height: 1.12 !important;
                color: #1f2937 !important;
            }

            h2, h3 {
                font-size: clamp(1.15rem, 2.4vw, 1.55rem) !important;
                font-weight: 850 !important;
                line-height: 1.2 !important;
                color: #1f2937 !important;
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

            div[data-testid="stDataFrame"] *,
            div[data-testid="stMarkdownContainer"] div,
            div[data-testid="stAlert"] {
                overflow-wrap: anywhere !important;
                word-break: normal !important;
            }

            div[data-testid="stMetric"] {
                background: #f7fbff;
                border: 1px solid #d9e8ff;
                border-radius: 14px;
                padding: 12px 13px;
                min-height: 86px;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            }

            div[data-testid="stMetricLabel"],
            div[data-testid="stMetricValue"] {
                white-space: normal !important;
                overflow-wrap: anywhere !important;
                overflow: visible !important;
                text-overflow: clip !important;
            }

            .stButton > button {
                width: 100%;
                border-radius: 10px;
                font-weight: 750;
                min-height: 40px;
                border: 1px solid #d7e3f5;
            }

            .ibkr-card {
                border-radius: 14px;
                padding: 0.82rem 0.92rem;
                min-height: 86px;
                margin-bottom: 0.55rem;
                overflow-wrap: anywhere;
            }

            .ibkr-pill {
                display: inline-flex;
                align-items: center;
                gap: 0.45rem;
                padding: 0.35rem 0.75rem;
                border-radius: 999px;
                background: #eef6ff;
                border: 1px solid #bfdbfe;
                color: #1d4ed8;
                font-weight: 850;
                margin: 0.25rem 0 0.7rem 0;
            }

            .ibkr-hero {
                border: 1px solid;
                border-radius: 20px;
                padding: 1.05rem 1.15rem;
                margin: 0.75rem 0 1rem 0;
                box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
                overflow-wrap: anywhere;
            }

            .ibkr-hero-kicker {
                font-size: 0.72rem;
                font-weight: 950;
                letter-spacing: 0.075em;
                text-transform: uppercase;
                color: #64748b;
                margin-bottom: 0.32rem;
            }

            .ibkr-hero-title {
                font-size: clamp(1.65rem, 3.8vw, 2.75rem);
                font-weight: 1000;
                line-height: 1.05;
                margin-bottom: 0.45rem;
            }

            .ibkr-hero-text {
                font-size: clamp(0.92rem, 1.6vw, 1.08rem);
                font-weight: 760;
                color: #334155;
                line-height: 1.45;
                margin-bottom: 0.55rem;
            }

            .ibkr-hero-action {
                border-radius: 14px;
                padding: 0.72rem 0.9rem;
                background: rgba(255,255,255,0.75);
                border: 1px solid rgba(148, 163, 184, 0.35);
                color: #111827;
                font-size: 0.92rem;
                font-weight: 900;
            }

            .ibkr-check-row {
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

            .ibkr-check-detail {
                color: #64748b;
                font-size: 0.78rem;
                font-weight: 700;
                text-align: right;
            }

            @media (max-width: 1100px) {
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
                }
            }

            @media (max-width: 760px) {
                .block-container {
                    padding-left: 0.9rem !important;
                    padding-right: 0.9rem !important;
                }

                div[data-testid="stHorizontalBlock"] {
                    flex-wrap: wrap !important;
                    gap: 0.65rem !important;
                }

                div[data-testid="stHorizontalBlock"] > div,
                div[data-testid="column"] {
                    flex: 1 1 100% !important;
                    width: 100% !important;
                    min-width: 100% !important;
                }

                div[data-testid="stDataFrame"] {
                    font-size: 0.82rem !important;
                }

                .ibkr-card {
                    min-height: 78px;
                    padding: 0.75rem 0.82rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def responsive_columns(spec, gap: str = "small"):
    return st.columns(spec, gap=gap)


def ibkr_tip(text: str) -> None:
    st.caption(f"💡 {text}")


def ibkr_metric_card(label: str, value, detail: str = "", tone: str = "neutral") -> None:
    palette = {
        "neutral": ("#f8fafc", "#dbe3ef", "#111827"),
        "info": ("#eff6ff", "#bfdbfe", "#1d4ed8"),
        "good": ("#ecfdf5", "#bbf7d0", "#166534"),
        "warning": ("#fffbeb", "#fde68a", "#92400e"),
        "risk": ("#fef2f2", "#fecaca", "#991b1b"),
    }

    background, border, value_color = palette.get(tone, palette["neutral"])
    label_text = html.escape(str(label))
    value_text = html.escape(str(value))
    detail_text = html.escape(str(detail))

    detail_html = (
        f'<div style="font-size:0.78rem;color:#64748b;margin-top:0.35rem;line-height:1.25;">{detail_text}</div>'
        if detail_text
        else ""
    )

    st.markdown(
        f"""
        <div class="ibkr-card" style="background:{background};border:1px solid {border};">
            <div style="font-size:0.70rem;text-transform:uppercase;letter-spacing:0.04em;color:#64748b;font-weight:800;margin-bottom:0.25rem;">
                {label_text}
            </div>
            <div style="font-size:1.18rem;line-height:1.15;font-weight:850;color:{value_color};">
                {value_text}
            </div>
            {detail_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def ibkr_status_tone(value: str) -> str:
    text = str(value or "").upper()
    if any(word in text for word in ("CONNECTED", "RUNNING", "READY", "ONLINE", "YES", "LIVE")):
        return "good"
    if any(word in text for word in ("DISCONNECTED", "STOPPED", "MISSING", "NO", "OFF")):
        return "risk"
    return "info"


def ibkr_tone_palette(tone: str):
    palette = {
        "neutral": ("#f8fafc", "#dbe3ef", "#111827"),
        "info": ("#eff6ff", "#bfdbfe", "#1d4ed8"),
        "good": ("#ecfdf5", "#bbf7d0", "#166534"),
        "warning": ("#fffbeb", "#fde68a", "#92400e"),
        "risk": ("#fef2f2", "#fecaca", "#991b1b"),
    }
    return palette.get(str(tone), palette["neutral"])


def render_ibkr_hero(title: str, subtitle: str, action: str, tone: str = "info") -> None:
    background, border, value_color = ibkr_tone_palette(tone)
    st.markdown(
        f"""
        <div class="ibkr-hero" style="background:{background};border-color:{border};">
            <div class="ibkr-hero-kicker">Institutional Broker Operations</div>
            <div class="ibkr-hero-title" style="color:{value_color};">{html.escape(str(title))}</div>
            <div class="ibkr-hero-text">{html.escape(str(subtitle))}</div>
            <div class="ibkr-hero-action">{html.escape(str(action))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_readiness_check(label: str, passed: bool, detail: str = "") -> None:
    icon = "✅" if passed else "❌"
    color = "#166534" if passed else "#991b1b"
    st.markdown(
        f"""
        <div class="ibkr-check-row">
            <span style="color:{color};">{icon} {html.escape(str(label))}</span>
            <span class="ibkr-check-detail">{html.escape(str(detail))}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def ibkr_telegram_ready() -> bool:
    return bool(
        st.session_state.get("ibkr_telegram_connected", False)
        and st.session_state.get("ibkr_telegram_alerts_enabled", False)
    )


def ibkr_telegram_notifier():
    for key in (
        "telegram_notifier",
        "telegram_alerts",
        "telegram_client",
        "notifier",
    ):
        obj = st.session_state.get(key)
        if obj is not None:
            return obj
    return None


def send_ibkr_telegram(title: str, message: str) -> bool:
    if not ibkr_telegram_ready():
        return False

    text = f"{title}\n\n{message}"
    notifier = ibkr_telegram_notifier()

    if notifier is None:
        st.session_state["ibkr_last_telegram_alert"] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "title": title,
            "message": message,
            "status": "SIMULATED_NO_NOTIFIER",
        }
        return True

    for method_name in ("send", "send_message", "notify", "alert"):
        if hasattr(notifier, method_name):
            try:
                getattr(notifier, method_name)(text)
                st.session_state["ibkr_last_telegram_alert"] = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "title": title,
                    "message": message,
                    "status": "SENT",
                }
                return True
            except Exception as exc:
                st.session_state["ibkr_last_telegram_alert"] = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "title": title,
                    "message": message,
                    "status": f"ERROR: {exc}",
                }
                return False

    st.session_state["ibkr_last_telegram_alert"] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "title": title,
        "message": message,
        "status": "NO_SUPPORTED_METHOD",
    }
    return False


def ibkr_telegram_panel() -> None:
    with st.expander("📲 Telegram Alerts", expanded=False):
        st.caption(
            "Telegram alerts provide immediate visibility for IBKR connection, "
            "snapshot, recovery, LIVE armed, and kill-switch events."
        )

        t1, t2, t3 = st.columns(3)
        with t1:
            st.toggle("Telegram Connected", key="ibkr_telegram_connected")
            st.toggle("Telegram Alerts Enabled", key="ibkr_telegram_alerts_enabled")
        with t2:
            st.toggle("Notify Connect", key="ibkr_notify_connect")
            st.toggle("Notify Disconnect", key="ibkr_notify_disconnect")
            st.toggle("Notify Snapshot", key="ibkr_notify_snapshot")
        with t3:
            st.toggle("Notify Recovery", key="ibkr_notify_recovery")
            st.toggle("Notify Kill Switch", key="ibkr_notify_kill_switch")
            st.toggle("Notify LIVE Armed", key="ibkr_notify_live_armed")

        st.metric("Telegram Status", "ACTIVE" if ibkr_telegram_ready() else "OFFLINE")

        if st.button("Send IBKR Telegram Test", width="stretch"):
            ok = send_ibkr_telegram(
                "📡 JFBP Live IBKR Test",
                "Telegram alerts are connected to Live IBKR.",
            )
            if ok:
                st.success("IBKR Telegram test alert recorded/sent.")
            else:
                st.warning("IBKR Telegram test alert was not sent.")

        last_alert = st.session_state.get("ibkr_last_telegram_alert", {})
        if last_alert:
            st.json(last_alert)


def page():

    inject_live_ibkr_responsive_css()

    gateway, market, oms, portfolio_engine = init_core()

    pipeline = st.session_state.get("pipeline")
    stream_engine = st.session_state.get("stream_engine")
    risk_engine = st.session_state.get("risk_engine")

    st.session_state.setdefault("mode", "SIM")
    st.session_state.setdefault("live_trading_armed", False)
    st.session_state.setdefault("risk_kill_switch", False)
    st.session_state.setdefault("live_ibkr_last_refresh", "")
    st.session_state.setdefault("live_ibkr_intent_reset_id", 0)

    # Telegram alert state
    st.session_state.setdefault("ibkr_telegram_connected", True)
    st.session_state.setdefault("ibkr_telegram_alerts_enabled", True)
    st.session_state.setdefault("ibkr_notify_connect", True)
    st.session_state.setdefault("ibkr_notify_disconnect", True)
    st.session_state.setdefault("ibkr_notify_snapshot", True)
    st.session_state.setdefault("ibkr_notify_recovery", True)
    st.session_state.setdefault("ibkr_notify_kill_switch", True)
    st.session_state.setdefault("ibkr_notify_live_armed", True)

    mode = st.session_state.get("mode", "SIM")
    live_armed = st.session_state.get(
        "live_trading_armed",
        False,
    )

    kill_switch = st.session_state.get(
        "risk_kill_switch",
        False,
    )

    # =====================================================
    # HELPERS
    # =====================================================

    def now():
        return datetime.now(timezone.utc).isoformat()

    def safe_bool(value):
        try:
            return bool(value)
        except Exception:
            return False

    def _safe_len(value):
        try:
            return len(value)
        except Exception:
            return 0

    def _as_list(value):

        if value is None:
            return []

        if isinstance(value, list):
            return value

        if isinstance(value, dict):
            return list(value.values())

        try:
            return list(value)

        except Exception:
            return []


    def call_if_exists(obj, method_name, *args, **kwargs):

        if obj is None:
            return False, "Object missing"

        if not hasattr(obj, method_name):
            return False, f"Object has no {method_name}() method"

        try:
            result = getattr(obj, method_name)(*args, **kwargs)
            return True, result

        except Exception as exc:
            return False, str(exc)

    def safe_float(value, default=0.0):

        try:
            if value is None:
                return default

            if isinstance(value, str):
                value = value.replace(",", "").strip()

                if value == "":
                    return default

            return float(value)

        except Exception:
            return default

    def _is_number(value):

        try:
            if value is None:
                return False

            if isinstance(value, str) and value.strip() == "":
                return False

            float(str(value).replace(",", "").strip())
            return True

        except Exception:
            return False

    def _money(value, currency=""):

        if value is None:
            return "—"

        if not _is_number(value):
            return str(value)

        amount = safe_float(value, 0.0)
        currency = str(currency or "").upper().strip()

        if currency and currency != "BASE":
            return f"{currency} {amount:,.2f}"

        return f"{amount:,.2f}"

    def account_summary_to_values(rows):

        values = {}
        rows = _as_list(rows)

        for row in rows:

            if not isinstance(row, dict):
                continue

            tag = str(row.get("tag", "") or "").strip()
            currency = str(row.get("currency", "") or "").upper().strip()
            raw_value = row.get("value")

            if not tag:
                continue

            value = safe_float(raw_value) if _is_number(raw_value) else raw_value

            values[tag] = value

            if currency:
                values[f"{tag}_{currency}"] = value

        return values

    def gateway_account_values():

        values = {}

        try:
            if gateway is not None and hasattr(gateway, "account_values"):
                raw_values = gateway.account_values()

                if isinstance(raw_values, dict):
                    values.update(raw_values)

        except Exception as exc:
            st.session_state["live_ibkr_account_values_error"] = str(exc)

        return values

    def merged_account_values(snapshot_rows):

        values = {}

        values.update(account_summary_to_values(snapshot_rows))

        gateway_values = gateway_account_values()

        if isinstance(gateway_values, dict):
            values.update(gateway_values)

        return values

    def find_account_value(values, tag, currencies=("BASE", "CAD", "USD", "")):

        if not isinstance(values, dict):
            return None, ""

        tag = str(tag or "").strip()

        for currency in currencies:
            currency = str(currency or "").upper().strip()

            key = f"{tag}_{currency}" if currency else tag

            if key in values:
                return values.get(key), currency

        if tag in values:
            return values.get(tag), ""

        return None, ""

    def account_metric(label, values, tag, currencies=("BASE", "CAD", "USD", ""), detail=""):

        value, currency = find_account_value(
            values,
            tag,
            currencies=currencies,
        )

        ibkr_metric_card(label, _money(value, currency), detail=detail, tone="info")

    def reset_operator_intent():
        st.session_state["live_ibkr_intent_reset_id"] = (
            int(
                st.session_state.get(
                    "live_ibkr_intent_reset_id",
                    0,
                ) or 0
            )
            + 1
        )

    def _cached_gateway_status(ttl_seconds: int = 5):

        import time

        current_ts = time.time()

        cached_at = float(
            st.session_state.get(
                "live_ibkr_status_cached_at",
                0.0,
            ) or 0.0
        )

        cached_status = st.session_state.get(
            "live_ibkr_cached_status"
        )

        if (
            isinstance(cached_status, dict)
            and current_ts - cached_at < ttl_seconds
        ):
            return cached_status

        if gateway is None:

            status = {
                "connected": False,
                "status": "MISSING",
                "detail": "Gateway missing",
            }

        else:

            connected = False

            for attr in (
                "broker_connected",
                "ui_connected",
                "connected",
            ):

                if hasattr(gateway, attr):

                    connected = safe_bool(
                        getattr(gateway, attr)
                    )

                    break

            status = {
                "connected": connected,
                "status": (
                    "CONNECTED"
                    if connected
                    else "DISCONNECTED"
                ),
                "detail": (
                    "attribute-only status; "
                    "no broker probe during render"
                ),
            }

        st.session_state[
            "live_ibkr_cached_status"
        ] = status

        st.session_state[
            "live_ibkr_status_cached_at"
        ] = current_ts

        return status

    def gateway_status():
        return _cached_gateway_status()

    def stream_running():

        if stream_engine is None:
            return False

        if hasattr(stream_engine, "running"):
            return safe_bool(stream_engine.running)

        if hasattr(stream_engine, "is_running"):

            try:
                return safe_bool(
                    stream_engine.is_running()
                )

            except Exception:
                return False

        return False

    def market_snapshot_count():

        if market is None:
            return 0

        for attr in (
            "prices",
            "last_prices",
            "data",
            "snapshot_cache",
            "cache",
            "last_snapshot",
        ):

            try:

                value = getattr(
                    market,
                    attr,
                    None,
                )

                if isinstance(value, dict):
                    return len(value)

            except Exception:
                pass

        try:

            universe = st.session_state.get(
                "universe",
                {},
            )

            if isinstance(universe, dict):
                return len(universe)

            if isinstance(universe, list):
                return len(universe)

        except Exception:
            pass

        return 0

    def snapshot_age_label(timestamp_value):
        if not timestamp_value:
            return "No snapshot"
        try:
            ts = datetime.fromisoformat(str(timestamp_value).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - ts.astimezone(timezone.utc)
            seconds = max(0, int(delta.total_seconds()))
            if seconds < 60:
                return f"{seconds}s ago"
            minutes = seconds // 60
            if minutes < 60:
                return f"{minutes}m ago"
            hours = minutes // 60
            return f"{hours}h ago"
        except Exception:
            return "Timestamp cached"

    def account_value(values, tag, currencies=("BASE", "CAD", "USD", "")):
        value, _currency = find_account_value(values, tag, currencies=currencies)
        return safe_float(value, 0.0) if _is_number(value) else 0.0

    status = gateway_status()
    connected = status.get("connected", False)
    streaming = stream_running()
    broker_snapshot_timestamp = st.session_state.get("broker_snapshot_timestamp", "")
    snapshot_cached = bool(broker_snapshot_timestamp)
    snapshot_age = snapshot_age_label(broker_snapshot_timestamp)
    telegram_online = ibkr_telegram_ready()
    oms_ready = oms is not None
    risk_ready = risk_engine is not None
    pipeline_ready = pipeline is not None
    readiness_passed = bool(connected and oms_ready and risk_ready and snapshot_cached and mode == "LIVE" and live_armed and not kill_switch)

    if kill_switch:
        broker_status_label = "🛑 BROKER STATUS: BLOCKED"
        broker_status_tone = "risk"
        broker_action = "Execution blocked by Kill Switch. Do not route orders until risk controls are cleared."
    elif mode == "LIVE" and connected and live_armed:
        broker_status_label = "🚨 BROKER STATUS: LIVE EXECUTION CAPABLE"
        broker_status_tone = "risk"
        broker_action = "Orders submitted from OMS may route to IBKR. Verify snapshot, account, and risk before sending orders."
    elif connected and snapshot_cached:
        broker_status_label = "🟢 BROKER STATUS: CONNECTED"
        broker_status_tone = "good"
        broker_action = "Broker is connected and snapshot is cached. Review OMS readiness before execution."
    elif connected:
        broker_status_label = "🟡 BROKER STATUS: CONNECTED — SNAPSHOT NEEDED"
        broker_status_tone = "warning"
        broker_action = "Pull Broker Snapshot before relying on account, position, or fill data."
    else:
        broker_status_label = "🔴 BROKER STATUS: DISCONNECTED"
        broker_status_tone = "risk"
        broker_action = "Start TWS or IBKR Gateway, confirm API settings, then connect the gateway."

    broker_status_summary = (
        f"Gateway: {'CONNECTED' if connected else 'DISCONNECTED'} · "
        f"Mode: {mode} · LIVE Armed: {'YES' if live_armed else 'NO'} · "
        f"Kill Switch: {'ON' if kill_switch else 'OFF'} · Snapshot: {snapshot_age} · "
        f"Telegram: {'ACTIVE' if telegram_online else 'OFFLINE'}"
    )
    
    # =====================================================
    # HEADER
    # =====================================================

    st.title("📡 Live IBKR")
    st.caption("Live IBKR v25.1 Institutional Edition — Broker Operations Center, OMS readiness, account command brief, recovery center, Telegram ops, and safety controls.")

    st.info(
        "🚀 LIVE Workflow: OMS Execution → Live IBKR → Pull Snapshot → "
        "Verify Account → Trade → Portfolio → Journal"
    )

    render_ibkr_hero(
        broker_status_label,
        broker_status_summary,
        broker_action,
        broker_status_tone,
    )


    with st.expander("🚀 Interactive Brokers Connection Guide", expanded=True):
        st.markdown(
            """
            **Live IBKR is the broker connection center for JFBP Quant Desk.** Use this page to connect/disconnect Interactive Brokers, verify gateway status, pull broker snapshots, review account balances, and recover broker executions.

            This page does **not** place trades directly. It prepares and verifies the broker connection used by OMS Execution.

            ---

            ### Step 1 — Start IBKR first

            Before connecting JFBP Quant Desk:

            1. Open **Trader Workstation (TWS)** or **IBKR Gateway**
            2. Log in to the correct account
            3. Wait until TWS/Gateway is fully loaded

            ---

            ### Step 2 — Check IBKR API settings

            In TWS or IBKR Gateway, go to:

            `File → Global Configuration → API → Settings`

            Make sure this is enabled:

            - **Enable ActiveX and Socket Clients**

            Recommended local connection settings:

            - **Host:** `127.0.0.1`
            - **Paper Trading Port:** `7497`
            - **Live Trading Port:** `7496`

            ---

            ### Step 3 — Prepare OMS Execution inside JFBP

            Before connecting the broker, open **OMS Execution** and complete the LIVE safety sequence:

            1. Set **Mode = LIVE**
            2. Tick **I understand OMS LIVE can route REAL broker orders**
            3. Type **ARM OMS LIVE** in the confirmation field
            4. Press **Enter**
            5. Verify **OMS LIVE INFRASTRUCTURE MODE ENABLED**
            6. Tick **LIVE Trading Armed** only when you intentionally want JFBP allowed to route real broker orders
            7. Return to **Live IBKR**

            ---

            ### Step 4 — Connect JFBP Quant Desk to IBKR

            Under **Connection Controls**:

            1. Check **Confirm IBKR connect**
            2. Click **Connect Gateway**
            3. Verify the top status card changes to **Gateway: CONNECTED**

            ---

            ### Step 5 — Pull Broker Snapshot

            After connecting:

            1. Check **Confirm broker snapshot pull**
            2. Click **Pull Broker Snapshot**
            3. Confirm the broker data appears correctly:
               - Positions
               - Account values
               - Buying power
               - Available funds
               - Open orders
               - Broker fills

            ---

            ### Step 6 — Verify account and safety status

            Before trading, verify:

            - **Gateway = CONNECTED**
            - **Broker Snapshot** has been pulled
            - Balances and positions match IBKR
            - **LIVE Trading Armed** is intentional
            - **Risk Kill Switch** is reviewed

            ---

            ### Safe disconnect

            When finished:

            1. Check **Confirm IBKR disconnect**
            2. Click **Disconnect Gateway**
            3. Verify **Gateway: DISCONNECTED**

            Disconnecting JFBP only closes the app's broker connection. It does **not** close TWS/IBKR Gateway, cancel positions, cancel broker orders, or place trades.

            ---

            ### Safety reminders

            - **SIM mode** is safe for testing and should not route real orders.
            - **LIVE mode** can interact with the broker once OMS is unlocked and trading is armed.
            - **Kill Switch ON** blocks execution at the risk-control level.
            - Before trading, always verify **Mode**, **Gateway**, **LIVE Armed**, and **Kill Switch**.
            """
        )

    with st.expander("ℹ️ Page Map", expanded=False):
        st.markdown(
            """
            - **Live Connectivity Safety Panel** shows connection status, stream status, cached symbols, and runtime mode.
            - **Broker Recovery** attempts to recover broker executions that may have occurred while the app was offline or disconnected.
            - **Live Safety Controls** arms live trading and controls the kill switch.
            - **Connection Controls** connects/disconnects the IBKR gateway.
            - **Broker Snapshot Sync** pulls read-only cached broker data into the app session.
            - **IBKR Account Balance** shows cached account values from IBKR.
            - **Component Status** confirms whether the gateway, OMS, pipeline, risk engine, and market hub are online.
            """
        )

    ibkr_telegram_panel()

    st.subheader("🛡 Live Connectivity Safety Panel")

    status = gateway_status()
    connected = status.get("connected", False)
    streaming = stream_running()

    st.markdown(
        f'<div class="ibkr-pill">📡 {mode} mode • Gateway {"connected" if connected else "disconnected"} • Stream {"running" if streaming else "stopped"}</div>',
        unsafe_allow_html=True,
    )

    # =====================================================
    # LIVE STATUS BANNER
    # =====================================================

    if kill_switch:

        st.error(
            "🛑 KILL SWITCH ACTIVE — execution is blocked."
        )

    elif mode == "LIVE":

        if live_armed and connected:

            st.success(
                "🟢 LIVE MODE ACTIVE — broker connected and live execution armed."
            )

        elif live_armed and not connected:

            st.warning(
                "🟡 LIVE MODE ARMED — broker disconnected."
            )

        else:

            st.warning(
                "🟠 LIVE MODE SELECTED — live trading is not armed."
            )

    else:

        st.info(
            f"🔵 {mode} MODE ACTIVE — live execution is not armed."
        )

    # =====================================================
    # STATUS STRIP
    # =====================================================

    c1, c2, c3, c4, c5 = responsive_columns(5)

    with c1:
        gateway_value = "CONNECTED" if connected else "DISCONNECTED"
        ibkr_metric_card("Gateway", gateway_value, "IBKR connection state", tone=ibkr_status_tone(gateway_value))

    with c2:
        stream_value = "RUNNING" if streaming else "STOPPED"
        ibkr_metric_card("Stream", stream_value, "Market data stream", tone=ibkr_status_tone(stream_value))

    with c3:
        ibkr_metric_card("Market Symbols", market_snapshot_count(), "Cached market hub symbols", tone="info")

    with c4:
        ibkr_metric_card("Mode", mode, "SIM or LIVE runtime mode", tone="warning" if mode == "LIVE" else "info")

    with c5:
        telegram_value = "ACTIVE" if ibkr_telegram_ready() else "OFFLINE"
        ibkr_metric_card("Telegram", telegram_value, "Operator alerts", tone=ibkr_status_tone(telegram_value))

    st.subheader("✅ Live OMS Readiness Check")
    ibkr_tip("Single go/no-go view for live execution capability. This page still does not place trades.")

    r_left, r_right = responsive_columns([0.58, 0.42], gap="large")
    with r_left:
        render_readiness_check("Gateway Connected", bool(connected), "Required")
        render_readiness_check("OMS Loaded", bool(oms_ready), "Execution module")
        render_readiness_check("Risk Engine Loaded", bool(risk_ready), "Risk controls")
        render_readiness_check("Broker Snapshot Cached", bool(snapshot_cached), snapshot_age)
        render_readiness_check("LIVE Mode Selected", mode == "LIVE", str(mode))
        render_readiness_check("LIVE Trading Armed", bool(live_armed), "Intentional only")
        render_readiness_check("Kill Switch OFF", not bool(kill_switch), "Must be OFF to execute")
    with r_right:
        if readiness_passed:
            render_ibkr_hero(
                "🟢 EXECUTION STATUS: READY",
                (
                    "Gateway connected • Snapshot cached • LIVE mode selected • "
                    "LIVE armed • Kill Switch OFF"
                ),
                "READY FOR LIVE EXECUTION",
                "good",
            )
        else:
            if kill_switch:
                reason = "Kill Switch is ON."
            elif mode != "LIVE":
                reason = "Runtime mode is not LIVE."
            elif not connected:
                reason = "Gateway is disconnected."
            elif not snapshot_cached:
                reason = "Broker snapshot not cached."
            elif not live_armed:
                reason = "LIVE Trading Armed is OFF."
            else:
                reason = "Execution components are missing."

            render_ibkr_hero(
                "🚫 EXECUTION STATUS: NOT READY",
                reason,
                "NOT READY FOR LIVE EXECUTION",
                "risk",
            )

        ibkr_metric_card(
            "Snapshot Age",
            snapshot_age,
            "Cached broker data age",
            tone="good" if snapshot_cached else "warning",
        )

    st.divider()

    # =====================================================
    # MANUAL BROKER RECOVERY
    # =====================================================

    st.subheader("🔧 Broker Recovery Center")
    ibkr_tip("Use this only when broker fills may have occurred while the app was offline or disconnected. It does not place trades.")

    last_recovery = st.session_state.get("live_ibkr_last_recovery_time", "")
    last_recovery_rows = st.session_state.get("live_ibkr_last_recovery_rows", 0)
    last_recovery_status = st.session_state.get("live_ibkr_last_recovery_status", "NEVER RUN")

    rec_m1, rec_m2, rec_m3 = responsive_columns(3)
    with rec_m1:
        ibkr_metric_card("Last Recovery", snapshot_age_label(last_recovery), "Broker execution recovery", tone="info" if last_recovery else "warning")
    with rec_m2:
        ibkr_metric_card("Recovered Rows", last_recovery_rows, "Last recovery result count", tone="info")
    with rec_m3:
        ibkr_metric_card("Recovery Status", last_recovery_status, "Latest recovery outcome", tone=ibkr_status_tone(last_recovery_status))

    recovery_col1, recovery_col2 = responsive_columns(2)

    with recovery_col1:

        recover_exec_btn = st.button(
            "Recover Broker Executions",
            width="stretch",
            disabled=False,
            help=(
                "Manually trigger IBKR execution recovery "
                "to replay broker fills into runtime."
            ),
        )

        if recover_exec_btn:

            st.info("Recover Broker Executions button clicked.")

            if gateway is None:

                st.error("Gateway object is missing.")

            elif not hasattr(gateway, "recover_broker_executions"):

                st.error(
                    "Gateway does not have recover_broker_executions()."
                )

            else:

                try:

                    st.write("Gateway class:", type(gateway).__name__)
                    st.write(
                        "Broker connected:",
                        gateway.verify_connection()
                        if hasattr(gateway, "verify_connection")
                        else "verify_connection unavailable",
                    )

                    with st.spinner(
                        "Requesting broker executions from IBKR..."
                    ):

                        result = gateway.recover_broker_executions()

                    gateway_error = str(
                        getattr(gateway, "last_error", "") or ""
                    )

                    st.write("Recovery result:", result)
                    st.write("Gateway last_error:", gateway_error)

                    if gateway_error:

                        st.error(gateway_error)

                    else:

                        count = (
                            len(result)
                            if result is not None
                            else 0
                        )

                        if st.session_state.get("ibkr_notify_recovery", True):
                            send_ibkr_telegram(
                                "🔧 JFBP IBKR Recovery",
                                f"Broker execution recovery completed. Returned rows: {count}",
                            )

                        st.session_state["live_ibkr_last_recovery_time"] = now()
                        st.session_state["live_ibkr_last_recovery_rows"] = count
                        st.session_state["live_ibkr_last_recovery_status"] = "OK"

                        st.success(
                            "Broker execution recovery call completed. "
                            f"Returned rows: {count}"
                        )

                    st.session_state[
                        "live_ibkr_last_refresh"
                    ] = now()

                    st.session_state[
                        "live_ibkr_cached_status"
                    ] = None

                    st.session_state[
                        "live_ibkr_status_cached_at"
                    ] = 0.0

                except Exception as exc:

                    st.session_state["live_ibkr_last_recovery_time"] = now()
                    st.session_state["live_ibkr_last_recovery_rows"] = 0
                    st.session_state["live_ibkr_last_recovery_status"] = "ERROR"

                    st.error(
                        f"Recover Broker Executions failed: {exc}"
                    )

    with recovery_col2:

        st.caption(
            "Diagnostic version: this will show whether the button, "
            "gateway, connection, and recovery method are actually firing."
        )

    st.divider()

    
    # =====================================================
    # LIVE SAFETY CONTROLS
    # =====================================================

    st.subheader("Live Safety Controls")
    ibkr_tip("Arm LIVE trading only when you intentionally want other execution pages to be allowed to route real orders. Kill Switch blocks execution.")

    s1, s2, s3 = responsive_columns(3)

    with s1:
        st.session_state["live_trading_armed"] = st.toggle(
            "LIVE Trading Armed",
            value=live_armed,
            disabled=mode != "LIVE",
        )

    with s2:
        st.session_state["risk_kill_switch"] = st.toggle(
            "Kill Switch",
            value=kill_switch,
        )

    with s3:
        refresh = st.button(
            "Refresh Status",
            width="stretch",
        )

    if refresh:
        reset_operator_intent()

        st.session_state["live_ibkr_cached_status"] = None
        st.session_state["live_ibkr_status_cached_at"] = 0.0
        st.session_state["live_ibkr_last_refresh"] = now()

        st.rerun()

    current_kill = bool(st.session_state.get("risk_kill_switch", False))
    previous_kill = bool(st.session_state.get("ibkr_last_notified_kill_switch", False))
    if current_kill and not previous_kill and st.session_state.get("ibkr_notify_kill_switch", True):
        send_ibkr_telegram(
            "🛑 JFBP IBKR Kill Switch",
            "Risk kill switch is ON. Execution should remain blocked.",
        )
    st.session_state["ibkr_last_notified_kill_switch"] = current_kill

    current_live_armed = bool(st.session_state.get("live_trading_armed", False))
    previous_live_armed = bool(st.session_state.get("ibkr_last_notified_live_armed", False))
    if current_live_armed and not previous_live_armed and st.session_state.get("ibkr_notify_live_armed", True):
        send_ibkr_telegram(
            "🚨 JFBP IBKR LIVE Armed",
            "Live trading is armed from the Live IBKR safety panel.",
        )
    st.session_state["ibkr_last_notified_live_armed"] = current_live_armed

    st.divider()

    # =====================================================
    # CONNECTION CONTROLS
    # =====================================================

    st.subheader("Connection Controls")
    ibkr_tip("Connect or disconnect the IBKR gateway. These controls manage connectivity only and do not send orders.")

    st.info(
        "Start TWS or IBKR Gateway before connecting. Paper accounts normally use port 7497; live accounts normally use port 7496."
    )

    st.warning(
        "This page manages connectivity only. It does not execute trades."
    )

    intent_key = st.session_state.get("live_ibkr_intent_reset_id", 0)

    connect_col, disconnect_col, stream_col = responsive_columns(3)

    with connect_col:
        confirm_connect = st.checkbox(
            "Confirm IBKR connect",
            value=False,
            key=f"confirm_ibkr_connect_{intent_key}",
        )

        connect_btn = st.button(
            "Connect Gateway",
            width="stretch",
            disabled=connected or not confirm_connect,
        )

        st.caption(
            "Connect only after TWS/IBKR Gateway is open and logged in."
        )

    with disconnect_col:
        confirm_disconnect = st.checkbox(
            "Confirm IBKR disconnect",
            value=False,
            key=f"confirm_ibkr_disconnect_{intent_key}",
        )

        disconnect_btn = st.button(
            "Disconnect Gateway",
            width="stretch",
            disabled=not connected or not confirm_disconnect,
        )

        st.caption(
            "Disconnecting JFBP does not close TWS/IBKR Gateway or affect existing broker positions."
        )

    with stream_col:
        confirm_stream_stop = st.checkbox(
            "Confirm stream stop",
            value=False,
            key=f"confirm_stream_stop_{intent_key}",
        )

        stop_stream_btn = st.button(
            "Stop Stream",
            width="stretch",
            disabled=not streaming or not confirm_stream_stop,
        )

    if connect_btn:
        if gateway is None:
            ok = False
            reason = "Gateway object missing"

        elif not hasattr(gateway, "connect"):
            ok = False
            reason = "Gateway has no connect() method"

        else:
            try:
                result = gateway.connect(
                    host="127.0.0.1",
                    port=7497,
                    client_id=1,
                )

                ok = bool(result)

                if ok:
                    reason = "OK"
                else:
                    reason = (
                        getattr(gateway, "last_error", "")
                        or getattr(gateway, "error", "")
                        or "gateway.connect() returned False"
                    )

            except Exception as exc:
                ok = False
                reason = str(exc)

        if ok:
            reset_operator_intent()

            st.session_state["live_ibkr_cached_status"] = {
                "connected": True,
                "status": "CONNECTED",
                "detail": "connected after manual gateway connect",
            }
            st.session_state["live_ibkr_status_cached_at"] = 0.0
            st.session_state["live_ibkr_last_refresh"] = now()

            if st.session_state.get("ibkr_notify_connect", True):
                send_ibkr_telegram(
                    "📡 JFBP IBKR Connected",
                    "Gateway connected successfully. Verify broker snapshot before trading.",
                )

            st.success("Gateway connected.")
            st.rerun()
        else:
            st.error(f"Gateway connect failed: {reason}")

    if disconnect_btn:
        ok, reason = call_if_exists(gateway, "disconnect")

        if ok:
            reset_operator_intent()

            st.session_state["live_ibkr_cached_status"] = {
                "connected": False,
                "status": "DISCONNECTED",
                "detail": "disconnected after manual gateway disconnect",
            }
            st.session_state["live_ibkr_status_cached_at"] = 0.0
            st.session_state["live_ibkr_last_refresh"] = now()

            if st.session_state.get("ibkr_notify_disconnect", True):
                send_ibkr_telegram(
                    "📡 JFBP IBKR Disconnected",
                    "Gateway disconnect requested. JFBP broker connection is offline.",
                )

            st.success("Gateway disconnect requested.")
            st.rerun()
        else:
            st.error(f"Gateway disconnect failed: {reason}")

    if stop_stream_btn:
        ok, reason = call_if_exists(stream_engine, "stop")

        if ok:
            reset_operator_intent()

            st.success("Stream stop requested.")
            st.rerun()
        else:
            st.error(f"Stream stop failed: {reason}")

    st.divider()

    # =====================================================
    # BROKER SNAPSHOT SYNC
    # =====================================================

    st.subheader("Broker Snapshot Sync")
    ibkr_tip("Read-only cache pull for broker positions, open orders, account summary rows, and fills. This does not mutate the portfolio automatically.")

    st.info(
        "Manual read-only broker snapshot pull. "
        "This does NOT mutate portfolio runtime automatically."
    )

    sync_col1, sync_col2 = responsive_columns(2)

    with sync_col1:
        confirm_snapshot_pull = st.checkbox(
            "Confirm broker snapshot pull",
            value=False,
            key=f"confirm_snapshot_pull_{intent_key}",
        )

        pull_snapshot_btn = st.button(
            "Pull Broker Snapshot",
            width="stretch",
            disabled=(
                not connected
                or not confirm_snapshot_pull
            ),
        )

    with sync_col2:
        st.caption(
            "Reads cached broker positions, open orders, account summary, "
            "and cached executions into session cache. "
            "No blocking IBKR refresh calls are made here."
        )

    if pull_snapshot_btn:

        broker_positions = []
        broker_open_orders = []
        broker_account_summary = []
        broker_fills = []
        errors = []

        # ---------------------------------------------
        # POSITIONS — CACHE ONLY
        # ---------------------------------------------

        try:
            raw_positions = []

            if hasattr(gateway, "positions_detail_cache"):
                raw_positions = _as_list(
                    getattr(gateway, "positions_detail_cache", [])
                )

            if (
                not raw_positions
                and hasattr(gateway, "positions_cache")
            ):
                cache = getattr(gateway, "positions_cache", {})

                if isinstance(cache, dict):
                    raw_positions = [
                        {
                            "symbol": symbol,
                            "position": qty,
                            "qty": qty,
                        }
                        for symbol, qty in cache.items()
                    ]

            normalized_positions = []

            for p in raw_positions:
                try:
                    if isinstance(p, dict):
                        symbol = (
                            p.get("symbol")
                            or p.get("localSymbol")
                            or ""
                        )

                        qty = (
                            p.get("position")
                            or p.get("qty")
                            or p.get("quantity")
                            or p.get("signed_qty")
                            or 0
                        )

                        avg_cost = (
                            p.get("avg_cost")
                            or p.get("avgCost")
                            or p.get("average_cost")
                            or 0
                        )

                    else:
                        contract = getattr(p, "contract", None)
                        symbol = getattr(contract, "symbol", "")
                        qty = getattr(p, "position", 0)
                        avg_cost = getattr(p, "avgCost", 0)

                    symbol = str(symbol).upper().strip()
                    qty = float(qty or 0)
                    avg_cost = float(avg_cost or 0)

                    if not symbol:
                        continue

                    if abs(qty) <= 0.000001:
                        continue

                    normalized_positions.append({
                        "symbol": symbol,
                        "qty": qty,
                        "position": qty,
                        "signed_qty": qty,
                        "avg_cost": avg_cost,
                        "avgCost": avg_cost,
                        "source": "ibkr_cached_position_snapshot",
                    })

                except Exception as pos_exc:
                    errors.append(f"normalize_position: {pos_exc}")

            broker_positions = normalized_positions

        except Exception as exc:
            errors.append(f"positions: {exc}")

        # ---------------------------------------------
        # OPEN ORDERS — CACHE / NON-BLOCKING ONLY
        # ---------------------------------------------

        try:
            raw_open_orders = []

            if hasattr(gateway, "open_orders_cache"):
                raw_open_orders = _as_list(
                    getattr(gateway, "open_orders_cache", [])
                )

            if (
                not raw_open_orders
                and hasattr(gateway, "submitted_orders")
            ):
                submitted = getattr(gateway, "submitted_orders", {})

                if isinstance(submitted, dict):
                    raw_open_orders = list(submitted.values())

            broker_open_orders = _as_list(raw_open_orders)

        except Exception as exc:
            errors.append(f"open_orders: {exc}")

        # ---------------------------------------------
        # ACCOUNT SUMMARY — CACHE ONLY
        # ---------------------------------------------

        try:
            raw_account_summary = []

            for cache_name in (
                "account_summary_cache",
                "account_cache",
                "account_values_cache",
            ):
                if hasattr(gateway, cache_name):
                    raw_account_summary = _as_list(
                        getattr(gateway, cache_name, [])
                    )

                    if raw_account_summary:
                        break

            broker_account_summary = raw_account_summary

        except Exception as exc:
            errors.append(f"account_summary: {exc}")

        # ---------------------------------------------
        # EXECUTIONS / FILLS — CACHE ONLY
        # ---------------------------------------------

        try:
            raw_fills = []

            if hasattr(gateway, "fills_cache"):
                raw_fills = _as_list(
                    getattr(gateway, "fills_cache", [])
                )

            if (
                not raw_fills
                and hasattr(gateway, "executions_cache")
            ):
                raw_fills = _as_list(
                    getattr(gateway, "executions_cache", [])
                )

            if (
                not raw_fills
                and hasattr(gateway, "fills_snapshot")
            ):
                try:
                    raw_fills = _as_list(
                        gateway.fills_snapshot()
                    )
                except Exception:
                    raw_fills = []

            normalized_fills = []

            for fill in raw_fills:
                try:
                    if isinstance(fill, dict):
                        symbol = str(
                            fill.get("symbol") or ""
                        ).upper().strip()

                        action = str(
                            fill.get("action")
                            or fill.get("side")
                            or ""
                        ).upper().strip()

                        qty = float(
                            fill.get("qty")
                            or fill.get("quantity")
                            or fill.get("filled_qty")
                            or 0
                        )

                        price = float(
                            fill.get("price")
                            or fill.get("fill_price")
                            or fill.get("execution_price")
                            or 0
                        )

                        exec_id = str(
                            fill.get("exec_id")
                            or fill.get("execution_id")
                            or ""
                        )

                        timestamp = str(
                            fill.get("timestamp") or ""
                        )

                        source = str(
                            fill.get("source")
                            or "ibkr_cached_execution_snapshot"
                        )

                    else:
                        execution = getattr(fill, "execution", None)
                        contract = getattr(fill, "contract", None)

                        if execution is None:
                            continue

                        symbol = str(
                            getattr(contract, "symbol", "") or ""
                        ).upper().strip()

                        action = str(
                            getattr(execution, "side", "") or ""
                        ).upper().strip()

                        if action == "BOT":
                            action = "BUY"
                        elif action == "SLD":
                            action = "SELL"

                        qty = float(
                            getattr(execution, "shares", 0) or 0
                        )

                        price = float(
                            getattr(execution, "price", 0) or 0
                        )

                        exec_id = str(
                            getattr(execution, "execId", "") or ""
                        )

                        timestamp = str(
                            getattr(execution, "time", "") or ""
                        )

                        source = "ibkr_cached_fill_object"

                    if not symbol:
                        continue

                    if abs(qty) <= 0.000001:
                        continue

                    normalized_fills.append({
                        "exec_id": exec_id,
                        "execution_id": exec_id,
                        "symbol": symbol,
                        "action": action,
                        "side": action,
                        "qty": qty,
                        "quantity": qty,
                        "filled_qty": qty,
                        "price": price,
                        "fill_price": price,
                        "execution_price": price,
                        "timestamp": timestamp,
                        "status": "FILLED",
                        "execution_status": "FILLED",
                        "source": source,
                        "is_true_fill": True,
                    })

                except Exception as fill_exc:
                    errors.append(f"normalize_fill: {fill_exc}")

            broker_fills = normalized_fills

        except Exception as exc:
            errors.append(f"broker_fills: {exc}")

        # ---------------------------------------------
        # STORE SNAPSHOTS
        # ---------------------------------------------

        st.session_state["broker_snapshot_positions"] = broker_positions
        st.session_state["broker_snapshot_open_orders"] = broker_open_orders
        st.session_state["broker_snapshot_account_summary"] = broker_account_summary
        st.session_state["broker_snapshot_fills"] = broker_fills
        st.session_state["broker_snapshot_timestamp"] = now()
        st.session_state["broker_snapshot_errors"] = errors

        reset_operator_intent()

        if st.session_state.get("ibkr_notify_snapshot", True):
            send_ibkr_telegram(
                "📸 JFBP IBKR Snapshot",
                "\n".join([
                    "Broker snapshot pull completed.",
                    f"Positions: {len(broker_positions)}",
                    f"Open Orders: {len(broker_open_orders)}",
                    f"Account Rows: {len(broker_account_summary)}",
                    f"Fills: {len(broker_fills)}",
                    f"Warnings: {len(errors)}",
                ]),
            )

        if errors:
            st.warning(
                "Broker snapshot completed with partial errors: "
                + " | ".join(str(e) for e in errors)
            )
        else:
            st.success("Broker snapshot pull completed successfully.")

        st.rerun()

    # =====================================================
    # SNAPSHOT STATUS
    # =====================================================

    broker_snapshot_positions = st.session_state.get(
        "broker_snapshot_positions",
        [],
    )

    broker_snapshot_open_orders = st.session_state.get(
        "broker_snapshot_open_orders",
        [],
    )

    broker_snapshot_account_summary = st.session_state.get(
        "broker_snapshot_account_summary",
        [],
    )

    broker_snapshot_fills = st.session_state.get(
        "broker_snapshot_fills",
        [],
    )

    broker_snapshot_timestamp = st.session_state.get(
        "broker_snapshot_timestamp",
        "",
    )

    broker_snapshot_errors = st.session_state.get(
        "broker_snapshot_errors",
        [],
    )

    st.subheader("Broker Snapshot Status")
    ibkr_tip("Shows what broker data is currently cached in the app session after a snapshot pull.")

    snap1, snap2, snap3, snap4, snap5 = responsive_columns(5)

    with snap1:
        ibkr_metric_card("Broker Positions", _safe_len(broker_snapshot_positions), "Cached broker position rows", tone="info")

    with snap2:
        ibkr_metric_card("Broker Open Orders", _safe_len(broker_snapshot_open_orders), "Cached open order rows", tone="info")

    with snap3:
        ibkr_metric_card("Account Summary Rows", _safe_len(broker_snapshot_account_summary), "Cached account rows", tone="info")

    with snap4:
        ibkr_metric_card("Broker Fills", _safe_len(broker_snapshot_fills), "Cached broker fill rows", tone="info")

    with snap5:
        cached_value = "YES" if broker_snapshot_timestamp else "NO"
        ibkr_metric_card("Snapshot Cached", cached_value, "Whether a broker snapshot exists", tone=ibkr_status_tone(cached_value))

    st.subheader("📸 Broker Snapshot Command Center")
    ibkr_tip("Review the cached broker truth without opening diagnostics.")

    with st.expander("View Broker Positions", expanded=False):
        if broker_snapshot_positions:
            st.dataframe(broker_snapshot_positions, width="stretch", hide_index=True)
        else:
            st.info("No cached broker positions yet.")

    with st.expander("View Open Orders", expanded=False):
        if broker_snapshot_open_orders:
            st.dataframe(broker_snapshot_open_orders, width="stretch", hide_index=True)
        else:
            st.info("No cached broker open orders yet.")

    with st.expander("View Broker Fills", expanded=False):
        if broker_snapshot_fills:
            st.dataframe(broker_snapshot_fills, width="stretch", hide_index=True)
        else:
            st.info("No cached broker fills yet.")

    # =====================================================
    # IBKR ACCOUNT BALANCE
    # =====================================================

    st.subheader("IBKR Account Balance")
    ibkr_tip("Account balance values come from cached IBKR account summary/account values. Net Liquidation is total account value; Buying Power and Available Funds show deployable capacity.")

    account_values = merged_account_values(
        broker_snapshot_account_summary
    )

    # -----------------------------------------------------
    # Position value truth
    # -----------------------------------------------------
    # Account summary GrossPositionValue can differ from the
    # visible position-row market value. For the operator UI,
    # show both separately so we do not confuse account-level
    # IBKR values with live position exposure.

    broker_position_value = 0.0

    try:
        for row in broker_snapshot_positions:
            if not isinstance(row, dict):
                continue

            value = safe_float(
                row.get("position_value")
                or row.get("market_value")
                or row.get("marketValue")
                or 0.0,
                0.0,
            )

            if value <= 0:
                qty = safe_float(
                    row.get("signed_qty")
                    or row.get("qty")
                    or row.get("quantity")
                    or row.get("position")
                    or 0.0,
                    0.0,
                )

                price = safe_float(
                    row.get("last_price")
                    or row.get("market_price")
                    or row.get("marketPrice")
                    or row.get("last")
                    or row.get("price")
                    or row.get("avg_price")
                    or row.get("avg_cost")
                    or row.get("avgCost")
                    or 0.0,
                    0.0,
                )

                value = abs(qty) * price

            broker_position_value += abs(value)

    except Exception as exc:
        st.session_state["live_ibkr_position_value_error"] = str(exc)

    net_liq_value = account_value(account_values, "NetLiquidation")
    buying_power_value = account_value(account_values, "BuyingPower")
    available_funds_value = account_value(account_values, "AvailableFunds")
    total_cash_value = account_value(account_values, "TotalCashValue")
    gross_position_value = account_value(account_values, "GrossPositionValue")
    exposure_value = gross_position_value if gross_position_value > 0 else broker_position_value
    cash_deployment = (exposure_value / net_liq_value * 100.0) if net_liq_value > 0 else 0.0

    st.subheader("💰 Account Command Brief")
    ibkr_tip("Fast account read: total equity, deployable funds, current exposure, and cash deployment.")

    ac1, ac2, ac3, ac4, ac5 = responsive_columns(5)
    with ac1:
        ibkr_metric_card("Net Liquidation", _money(net_liq_value), "Total account value", tone="info")
    with ac2:
        ibkr_metric_card("Buying Power", _money(buying_power_value), "Broker buying power", tone="good" if buying_power_value > 0 else "warning")
    with ac3:
        ibkr_metric_card("Available Funds", _money(available_funds_value), "Available to deploy", tone="good" if available_funds_value > 0 else "warning")
    with ac4:
        ibkr_metric_card("Exposure", _money(exposure_value), "Gross position value", tone="info")
    with ac5:
        ibkr_metric_card("Cash Deployment", f"{cash_deployment:.1f}%", "Exposure / net liquidation", tone="risk" if cash_deployment >= 80 else "warning" if cash_deployment >= 60 else "good")

    if readiness_passed:
        st.success("Account and broker operations are ready for controlled OMS execution.")
    elif mode == "LIVE" and connected:
        st.warning("Broker is connected in LIVE workflow, but readiness is incomplete. Verify the checklist before execution.")

    b1, b2, b3, b4, b5 = responsive_columns(5)

    with b1:
        account_metric(
            "Net Liquidation",
            account_values,
            "NetLiquidation",
        )

    with b2:
        account_metric(
            "Total Cash",
            account_values,
            "TotalCashValue",
        )

    with b3:
        account_metric(
            "Available Funds",
            account_values,
            "AvailableFunds",
        )

    with b4:
        account_metric(
            "Buying Power",
            account_values,
            "BuyingPower",
        )

    with b5:
        account_metric(
            "Excess Liquidity",
            account_values,
            "ExcessLiquidity",
        )

    cash1, cash2, cash3, cash4, cash5 = responsive_columns(5)

    with cash1:
        account_metric(
            "Settled Cash",
            account_values,
            "SettledCash",
            currencies=("CAD", "USD", "BASE", ""),
        )

    with cash2:
        account_metric(
            "Accrued Cash",
            account_values,
            "AccruedCash",
            currencies=("CAD", "USD", "BASE", ""),
        )

    with cash3:
        ibkr_metric_card(
            "Broker Position Value",
            _money(broker_position_value, "CAD"),
            "Calculated from broker position rows",
            tone="info",
        )

    with cash4:
        account_metric(
            "IBKR Account Gross Position",
            account_values,
            "GrossPositionValue",
        )

    with cash5:
        account_metric(
            "Cushion",
            account_values,
            "Cushion",
        )

    if not account_values:
        st.warning(
            "No IBKR account balance values are cached yet. "
            "Connect IBKR, then use Pull Broker Snapshot."
        )

    account_error = st.session_state.get(
        "live_ibkr_account_values_error",
        "",
    )

    if account_error:
        st.warning(
            "Account values warning: "
            + str(account_error)
        )

    position_value_error = st.session_state.get(
        "live_ibkr_position_value_error",
        "",
    )

    if position_value_error:
        st.warning(
            "Broker position value warning: "
            + str(position_value_error)
        )

    with st.expander("IBKR account balance values"):
        st.write(account_values)

    with st.expander("Broker position value rows"):
        st.write(
            {
                "broker_position_value": broker_position_value,
                "positions": broker_snapshot_positions,
            }
        )

    st.divider()

    if broker_snapshot_timestamp:
        st.caption(
            f"Last broker snapshot: {broker_snapshot_timestamp}"
        )

    if broker_snapshot_errors:
        st.warning(
            "Last broker snapshot warnings: "
            + " | ".join(str(e) for e in broker_snapshot_errors)
        )

    st.divider()

    # =====================================================
    # COMPONENT STATUS
    # =====================================================

    st.subheader("Component Status")
    ibkr_tip("Diagnostic health check for the gateway, stream, market hub, OMS, pipeline, risk engine, mode, armed state, and kill switch.")

    stream_status = "ONLINE" if stream_engine else "NOT CONFIGURED"
    stream_running_status = "YES" if streaming else "N/A"

    status_rows = {
        "Gateway Object": "ONLINE" if gateway else "MISSING",
        "Gateway Connected": "YES" if connected else "NO",
        "Gateway Status": status.get("status"),
        "Stream Engine": stream_status,
        "Stream Running": stream_running_status,
        "Market Hub": "ONLINE" if market else "MISSING",
        "OMS": "ONLINE" if oms else "MISSING",
        "Pipeline": "READY" if pipeline else "MISSING",
        "Risk Engine": "ONLINE" if risk_engine else "MISSING",
        "Mode": mode,
        "LIVE Armed": "YES" if st.session_state.get("live_trading_armed") else "NO",
        "Kill Switch": "ON" if st.session_state.get("risk_kill_switch") else "OFF",
        "Last Refresh": st.session_state.get("live_ibkr_last_refresh", ""),
    }

    st.table(
        {
            "Component": list(status_rows.keys()),
            "Status": list(status_rows.values()),
        }
    )

    # =====================================================
    # RAW STATUS
    # =====================================================

    with st.expander("Gateway detail"):
        st.write(status.get("detail"))

    with st.expander("Live execution guard summary"):
        st.write(
            {
                "mode": mode,
                "live_trading_armed": st.session_state.get(
                    "live_trading_armed"
                ),
                "risk_kill_switch": st.session_state.get(
                    "risk_kill_switch"
                ),
                "pipeline_ready": pipeline is not None,
                "oms_ready": oms is not None,
                "gateway_connected": connected,
                "streaming": streaming,
            }
        )

    with st.expander("Cached broker snapshot detail"):
        st.write(
            {
                "positions": st.session_state.get(
                    "broker_snapshot_positions",
                    [],
                ),
                "open_orders": st.session_state.get(
                    "broker_snapshot_open_orders",
                    [],
                ),
                "account_summary": st.session_state.get(
                    "broker_snapshot_account_summary",
                    [],
                ),
                "fills": st.session_state.get(
                    "broker_snapshot_fills",
                    [],
                ),
                "timestamp": st.session_state.get(
                    "broker_snapshot_timestamp",
                    "",
                ),
                "errors": st.session_state.get(
                    "broker_snapshot_errors",
                    [],
                ),
            }
        )


def run_page():
    page()