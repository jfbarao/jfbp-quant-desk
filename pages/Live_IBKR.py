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
from core.responsive import inject_responsive_css
from core.ui_cards import inject_card_css


# =========================================================
# RESPONSIVE UI HELPERS
# =========================================================

def inject_live_ibkr_responsive_css() -> None:
    """Visual-only responsive guardrails for Live IBKR."""

    inject_responsive_css(max_width=1500)
    inject_card_css()

    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1.15rem !important;
                padding-bottom: 1.75rem !important;
                max-width: 1500px !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }

            h1 {
                font-size: var(--jfbp-type-h1, clamp(1.75rem, 3.6vw, 2.45rem)) !important;
                font-weight: 850 !important;
                line-height: 1.12 !important;
                color: #1f2937 !important;
            }

            h2, h3 {
                font-size: var(--jfbp-type-h2, clamp(1.08rem, 2.2vw, 1.45rem)) !important;
                font-weight: 850 !important;
                line-height: 1.18 !important;
                color: #1f2937 !important;
                margin-top: 0.48rem !important;
                margin-bottom: 0.22rem !important;
            }

            div[data-testid="stHorizontalBlock"] {
                gap: 0.72rem !important;
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
                margin-bottom: 0.36rem;
                overflow-wrap: anywhere;
            }

            .ibkr-flow {
                background: #eff6ff;
                border: 1px solid #bfdbfe;
                border-radius: 12px;
                padding: 0.56rem 0.68rem;
                margin: 0.34rem 0 0.52rem 0;
                color: #1e3a8a;
                font-weight: 750;
                line-height: 1.4;
            }

            .ibkr-pill {
                display: inline-flex;
                align-items: center;
                gap: 0.45rem;
                padding: 0.24rem 0.56rem;
                margin: 0.16rem 0 0.44rem 0;
                border-radius: 999px;
                background: #eef6ff;
                border: 1px solid #bfdbfe;
                color: #1d4ed8;
                font-weight: 780;
                font-size: 0.84rem;
            }

            .ibkr-exec-emphasis {
                border: 1px solid #bfdbfe;
                border-radius: 14px;
                padding: 0.56rem 0.72rem;
                margin-bottom: 0.42rem;
                background: #eff6ff;
                font-size: 0.86rem;
                font-weight: 820;
                color: #1d4ed8;
            }

            .ibkr-system-health {
                border: 1px solid #dbe3ef;
                border-radius: 12px;
                padding: 0.58rem 0.68rem;
                margin-bottom: 0.42rem;
                background: #ffffff;
            }

            .ibkr-system-health-label {
                font-size: 0.75rem;
                letter-spacing: 0.04em;
                text-transform: uppercase;
                font-weight: 820;
                color: #64748b;
            }

            .ibkr-system-health-value {
                font-size: 0.98rem;
                font-weight: 850;
                margin-top: 0.16rem;
            }

            .ibkr-utility-title {
                font-size: 0.93rem;
                font-weight: 760;
                color: #475569;
                letter-spacing: 0.01em;
                margin: 0.18rem 0 0.22rem 0;
            }

            .ibkr-hero {
                border: 1px solid;
                border-radius: 18px;
                padding: 0.76rem 0.82rem;
                margin: 0.48rem 0 0.64rem 0;
                box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05);
                overflow-wrap: anywhere;
            }

            div[data-testid="stDivider"] {
                margin: 0.42rem 0 !important;
            }

            .ibkr-hero-kicker {
                font-size: var(--jfbp-type-card-label, 0.72rem);
                font-weight: 850;
                letter-spacing: 0.055em;
                text-transform: uppercase;
                color: #64748b;
                margin-bottom: 0.24rem;
            }

            .ibkr-hero-title {
                font-size: clamp(1.22rem, 2.35vw, 1.62rem);
                font-weight: 880;
                line-height: 1.14;
                margin-bottom: 0.30rem;
            }

            .ibkr-hero-text {
                font-size: var(--jfbp-type-body, 0.94rem);
                font-weight: 700;
                color: #334155;
                line-height: 1.38;
                margin-bottom: 0.36rem;
            }

            .ibkr-hero-action {
                border-radius: 12px;
                padding: 0.60rem 0.78rem;
                background: rgba(255,255,255,0.75);
                border: 1px solid rgba(148, 163, 184, 0.35);
                color: #111827;
                font-size: var(--jfbp-type-body, 0.94rem);
                font-weight: 820;
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
        f'<div style="font-size:var(--jfbp-type-caption,0.82rem);color:#64748b;margin-top:0.35rem;line-height:1.35;">{detail_text}</div>'
        if detail_text
        else ""
    )

    st.markdown(
        f"""
        <div class="ibkr-card" style="background:{background};border:1px solid {border};">
            <div style="font-size:var(--jfbp-type-card-label,0.72rem);text-transform:uppercase;letter-spacing:0.04em;color:#64748b;font-weight:850;margin-bottom:0.25rem;">
                {label_text}
            </div>
            <div style="font-size:var(--jfbp-type-card-value,clamp(1.05rem,2.2vw,1.35rem));line-height:1.15;font-weight:880;color:{value_color};">
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

    st.title("Live IBKR")
    st.caption("Institutional broker command bridge for connection state, account readiness, and controlled execution handoff.")

    with st.expander("ℹ️ How to Use This Page", expanded=False):
        st.markdown(
            """
            The Live IBKR page manages the connection between JFBP Quant Desk and Interactive
            Brokers. After the OMS Execution Mode has been selected (Simulation, Paper, or Live),
            this page verifies the broker connection before approved orders are submitted.

            **Recommended workflow:**

            1. **Market Pulse** - Assess overall market conditions.
            2. **Opportunity Center** - Identify high-probability trading opportunities.
            3. **Options Trade Construction Center** - Select option contracts, construct the trade,
               validate risk, and obtain approval.
            4. **OMS Execution Mode** - Choose where the order will be routed:

            - Simulation
            - Paper Trading
            - Live Trading

            5. **Live IBKR** - Connect JFBP Quant Desk to Interactive Brokers and verify communication.
            6. **Execution Package** - Review the OMS ticket and submit the approved order to IBKR.

            **Notes**

            - OMS Execution Mode determines whether orders are routed to **Simulation, Paper, or Live**.
            - Live IBKR verifies connectivity only - it does **not** determine the execution destination.
            - JFBP Quant Desk performs the analysis, construction, validation, approval, and order generation.
            - Interactive Brokers is the execution venue.
            - A green connection status confirms communication with IBKR.
            - Keep IBKR Gateway or TWS running while executing or monitoring trades.
            - If the connection is lost, reconnect here before attempting to submit orders.

            **Institutional Workflow**

            Market Pulse
            ↓
            Opportunity Center
            ↓
            Options Trade Construction Center
            ↓
            OMS Execution Mode (Simulation | Paper | Live)
            ↓
            Live IBKR Connection
            ↓
            Execution Package
            ↓
            IBKR Order Submission
            ↓
            Position Monitoring
            """
        )

    st.markdown(
        """
        <div class="ibkr-flow">
            Workflow: IBKR Connection Command → Broker Readiness Panel → Live Account Snapshot → Positions → Orders → Risk Gate → Execution Handoff → Emergency Controls
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_ibkr_hero(
        broker_status_label,
        broker_status_summary,
        broker_action,
        broker_status_tone,
    )

    # =====================================================
    # CONNECTION CONTROLS (PRIMARY WORKFLOW)
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

    quick_sync_btn = st.button(
        "Load Account Snapshot / Synchronize Account",
        width="stretch",
        type="primary",
        disabled=not connected,
        help="Primary action: pull the read-only broker account snapshot into session cache.",
        key="live_ibkr_quick_sync_top",
    )
    st.caption("Connect -> Synchronize -> Validate -> Trade")
    st.divider()

    exec_status = "READY" if readiness_passed else "NOT READY"
    snapshot_loaded = "LOADED" if snapshot_cached else "NOT LOADED"
    if not connected:
        next_action = "Start TWS/IBKR Gateway, connect the gateway, and verify connection state."
    elif not snapshot_cached:
        next_action = "Pull account synchronization to load positions, orders, and account state."
    elif mode != "LIVE" or not live_armed or kill_switch:
        next_action = "Validate mode, arming, and kill-switch posture before routing any execution."
    else:
        next_action = "Execution posture is ready. Proceed with controlled OMS workflow."

    st.subheader("Broker Executive Summary")
    ex1, ex2, ex3, ex4 = responsive_columns(4)
    with ex1:
        ibkr_metric_card("Connection", "CONNECTED" if connected else "DISCONNECTED", "Gateway status", tone="good" if connected else "risk")
    with ex2:
        ibkr_metric_card("Mode", mode, "SIM / LIVE", tone="warning" if mode == "LIVE" else "info")
    with ex3:
        ibkr_metric_card("Snapshot", snapshot_loaded, "Broker cache state", tone="good" if snapshot_cached else "warning")
    with ex4:
        ibkr_metric_card("Execution", exec_status, "Overall readiness", tone="good" if readiness_passed else "risk")
    st.markdown(
        f"""
        <div class="ibkr-exec-emphasis">
            NEXT ACTION: {html.escape(next_action)}
        </div>
        """,
        unsafe_allow_html=True,
    )


    with st.expander("Interactive Brokers Connection Guide", expanded=False):
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

    with st.expander("Page Map", expanded=False):
        st.markdown(
            """
            - **Live Connectivity Safety Panel** shows connection status, stream status, cached symbols, and runtime mode.
            - **Broker Recovery** attempts to recover broker executions that may have occurred while the app was offline or disconnected.
            - **Safety Locks** arms live trading and controls the kill switch.
            - **Connection Controls** connects/disconnects the IBKR gateway.
            - **Account Synchronization** pulls read-only cached broker data into the app session.
            - **Broker Account Details** shows expanded broker account values and diagnostics.
            - **Institutional System Health** confirms whether gateway and execution infrastructure are operational.
            """
        )

    st.subheader("IBKR Connection Command")

    status = gateway_status()
    connected = status.get("connected", False)
    streaming = stream_running()

    st.markdown(
        f'<div class="ibkr-pill">📡 {mode} mode • Gateway {"connected" if connected else "disconnected"} • Stream {"running" if streaming else "stopped"}</div>',
        unsafe_allow_html=True,
    )

    if mode == "LIVE":
        st.error("LIVE MODE WARNING: This environment can interact with live broker execution when OMS is armed.")

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
    # CONNECTION STATUS STRIP
    # =====================================================

    snapshot_rows_cached = st.session_state.get("broker_snapshot_account_summary", [])
    account_detected = bool(snapshot_rows_cached)
    sync_reference = broker_snapshot_timestamp or st.session_state.get("live_ibkr_last_refresh", "")
    last_sync_text = snapshot_age_label(sync_reference)
    market_data_status = "AVAILABLE" if (streaming or market_snapshot_count() > 0) else "LIMITED"

    c1, c2, c3, c4, c5 = responsive_columns(5)

    with c1:
        gateway_value = "CONNECTED" if connected else "DISCONNECTED"
        ibkr_metric_card("Connection Status", gateway_value, "IBKR gateway state", tone=ibkr_status_tone(gateway_value))

    with c2:
        ibkr_metric_card("Mode", mode, "Paper / Live", tone="warning" if mode == "LIVE" else "info")

    with c3:
        ibkr_metric_card("Account Detected", "YES" if account_detected else "NO", "Account snapshot loaded", tone="good" if account_detected else "warning")

    with c4:
        ibkr_metric_card("Market Data", market_data_status, "Stream/cache status", tone="good" if market_data_status == "AVAILABLE" else "warning")

    with c5:
        ibkr_metric_card("Last Sync", last_sync_text, "Latest broker state sync", tone="info" if sync_reference else "warning")

    st.subheader("Broker Readiness Panel")
    ibkr_tip("Immediate go/no-go view for broker operations and execution readiness.")

    r_left, r_right = responsive_columns([0.58, 0.42], gap="large")
    with r_left:
        render_readiness_check("API Connected", bool(connected), "IBKR gateway link")
        render_readiness_check("Account Loaded", bool(snapshot_rows_cached), "Broker account rows")
        render_readiness_check("Market Data Available", bool(streaming or market_snapshot_count() > 0), "Stream or cache")
        render_readiness_check("Trading Permission Status", bool(mode == "LIVE" and live_armed and not kill_switch), "LIVE + armed + kill switch OFF")
        render_readiness_check("Order Routing Readiness", bool(readiness_passed), "Gateway/OMS/Risk/Snapshot checks")
    with r_right:
        st.markdown(
            """
            <div class="ibkr-exec-emphasis">
                EXECUTION READINESS VERDICT
            </div>
            """,
            unsafe_allow_html=True,
        )
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
    # INSTITUTIONAL SYSTEM HEALTH
    # =====================================================

    ibkr_telegram_panel()

    st.subheader("Institutional System Health")
    ibkr_tip("Operational health map across broker and execution infrastructure.")

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

    health_cards = [
        ("Gateway", "OPERATIONAL" if connected else "OFFLINE", "good" if connected else "risk"),
        ("OMS", "OPERATIONAL" if oms else "OFFLINE", "good" if oms else "risk"),
        ("Risk Engine", "OPERATIONAL" if risk_engine else "OFFLINE", "good" if risk_engine else "risk"),
        ("Pipeline", "OPERATIONAL" if pipeline else "WARNING", "good" if pipeline else "warning"),
        ("Market Hub", "OPERATIONAL" if market else "OFFLINE", "good" if market else "risk"),
        ("Stream Engine", "OPERATIONAL" if stream_engine and streaming else "WARNING" if stream_engine else "OFFLINE", "good" if stream_engine and streaming else "warning" if stream_engine else "risk"),
        ("Telegram", "OPERATIONAL" if ibkr_telegram_ready() else "WARNING", "good" if ibkr_telegram_ready() else "warning"),
        ("LIVE Armed", "OPERATIONAL" if st.session_state.get("live_trading_armed") else "WARNING", "good" if st.session_state.get("live_trading_armed") else "warning"),
        ("Kill Switch", "OFFLINE" if st.session_state.get("risk_kill_switch") else "OPERATIONAL", "risk" if st.session_state.get("risk_kill_switch") else "good"),
    ]

    for i in range(0, len(health_cards), 3):
        row = responsive_columns(3)
        for col, (label, value, tone) in zip(row, health_cards[i:i + 3]):
            with col:
                _, _, value_color = ibkr_tone_palette(tone)
                st.markdown(
                    f"""
                    <div class="ibkr-system-health">
                        <div class="ibkr-system-health-label">{html.escape(label)}</div>
                        <div class="ibkr-system-health-value" style="color:{value_color};">{html.escape(value)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.divider()

    # =====================================================
    # BROKER SNAPSHOT SYNC
    # =====================================================

    st.subheader("Account Synchronization")
    ibkr_tip("Read-only cache pull for broker positions, open orders, account summary rows, and fills. This does not mutate the portfolio automatically.")

    st.info(
        "Manual read-only broker snapshot pull. "
        "This does NOT mutate portfolio runtime automatically."
    )

    intent_key = st.session_state.get("live_ibkr_intent_reset_id", 0)

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

    if pull_snapshot_btn or quick_sync_btn:

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

    st.subheader("Cached Broker State")
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

    if broker_snapshot_timestamp:
        st.caption(
            f"Last broker snapshot: {broker_snapshot_timestamp}"
        )

    if broker_snapshot_errors:
        st.warning(
            "Last broker snapshot warnings: "
            + " | ".join(str(e) for e in broker_snapshot_errors)
        )

    st.subheader("Live Account Snapshot")
    ibkr_tip("Immediate account state for net liquidation, cash, buying power, liquidity buffer, and P&L.")

    account_values_headline = merged_account_values(broker_snapshot_account_summary)
    net_liq_headline = account_value(account_values_headline, "NetLiquidation")
    cash_headline = account_value(account_values_headline, "TotalCashValue")
    buying_power_headline = account_value(account_values_headline, "BuyingPower")
    excess_liq_headline = account_value(account_values_headline, "ExcessLiquidity")
    open_pnl_headline = account_value(account_values_headline, "UnrealizedPnL")
    day_pnl_headline = account_value(account_values_headline, "RealizedPnL")

    hs1, hs2, hs3, hs4, hs5, hs6 = responsive_columns(6)
    with hs1:
        ibkr_metric_card("Net Liquidation", _money(net_liq_headline), "Total account value", tone="info")
    with hs2:
        ibkr_metric_card("Cash", _money(cash_headline), "Total cash value", tone="info")
    with hs3:
        ibkr_metric_card("Buying Power", _money(buying_power_headline), "Deployable capacity", tone="good" if buying_power_headline > 0 else "warning")
    with hs4:
        ibkr_metric_card("Margin / Excess Liquidity", _money(excess_liq_headline), "Liquidity buffer", tone="good" if excess_liq_headline > 0 else "warning")
    with hs5:
        ibkr_metric_card("Open P&L", _money(open_pnl_headline), "Unrealized P&L", tone="good" if open_pnl_headline >= 0 else "risk")
    with hs6:
        ibkr_metric_card("Day P&L", _money(day_pnl_headline), "Realized P&L", tone="good" if day_pnl_headline >= 0 else "risk")

    st.subheader("Positions")
    ibkr_tip("Current live IBKR positions from cached broker snapshot.")

    position_rows = []
    total_market_value = 0.0

    for row in _as_list(broker_snapshot_positions):
        if not isinstance(row, dict):
            continue

        symbol = str(row.get("symbol") or row.get("localSymbol") or "").upper().strip()
        qty = safe_float(row.get("signed_qty") or row.get("qty") or row.get("quantity") or row.get("position") or 0.0, 0.0)
        cost_basis = safe_float(row.get("avg_cost") or row.get("avgCost") or row.get("cost_basis") or 0.0, 0.0)
        market_value = safe_float(row.get("market_value") or row.get("marketValue") or row.get("position_value") or 0.0, 0.0)
        if market_value == 0.0:
            last_price = safe_float(row.get("last_price") or row.get("market_price") or row.get("last") or row.get("price") or cost_basis, 0.0)
            market_value = qty * last_price
        unrealized = safe_float(row.get("unrealized_pnl") or row.get("unrealizedPnL") or row.get("pnl") or 0.0, 0.0)

        if symbol:
            total_market_value += abs(market_value)
            position_rows.append(
                {
                    "Symbol": symbol,
                    "Quantity": round(qty, 4),
                    "Cost Basis": round(cost_basis, 4),
                    "Market Value": round(market_value, 2),
                    "Unrealized P&L": round(unrealized, 2),
                    "_alloc_raw": abs(market_value),
                }
            )

    if position_rows:
        for row in position_rows:
            alloc = (row.pop("_alloc_raw", 0.0) / total_market_value * 100.0) if total_market_value > 0 else 0.0
            row["Allocation %"] = f"{alloc:.1f}%"
        st.dataframe(position_rows, width="stretch", hide_index=True)
    else:
        st.info("No cached broker positions yet.")

    st.subheader("Orders")
    ibkr_tip("Open, submitted, filled, and cancelled broker order state with timestamp visibility.")

    open_order_rows = []
    for order in _as_list(broker_snapshot_open_orders):
        if not isinstance(order, dict):
            continue
        open_order_rows.append(
            {
                "Symbol": str(order.get("symbol") or order.get("localSymbol") or "").upper().strip(),
                "Status": str(order.get("status") or order.get("order_status") or "SUBMITTED").upper(),
                "Side": str(order.get("action") or order.get("side") or "").upper(),
                "Quantity": order.get("totalQuantity") or order.get("qty") or order.get("quantity") or "",
                "Order Type": order.get("orderType") or order.get("type") or "",
                "Limit Price": order.get("lmtPrice") or order.get("limit_price") or "",
                "Timestamp": order.get("timestamp") or order.get("time") or "",
            }
        )

    fill_rows = []
    for fill in _as_list(broker_snapshot_fills):
        if not isinstance(fill, dict):
            continue
        fill_rows.append(
            {
                "Symbol": str(fill.get("symbol") or "").upper().strip(),
                "Status": str(fill.get("status") or fill.get("execution_status") or "FILLED").upper(),
                "Side": str(fill.get("action") or fill.get("side") or "").upper(),
                "Quantity": fill.get("qty") or fill.get("quantity") or fill.get("filled_qty") or "",
                "Fill Price": fill.get("price") or fill.get("fill_price") or "",
                "Timestamp": fill.get("timestamp") or "",
            }
        )

    o1, o2 = responsive_columns(2)
    with o1:
        st.markdown("**Open / Submitted Orders**")
        if open_order_rows:
            st.dataframe(open_order_rows, width="stretch", hide_index=True)
        else:
            st.info("No cached open/submitted orders.")
    with o2:
        st.markdown("**Filled / Cancelled Status**")
        if fill_rows:
            st.dataframe(fill_rows, width="stretch", hide_index=True)
        else:
            st.info("No cached fill/cancel records.")

    # =====================================================
    # IBKR ACCOUNT BALANCE
    # =====================================================

    st.subheader("Broker Account Details")
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

    account_error = st.session_state.get(
        "live_ibkr_account_values_error",
        "",
    )
    position_value_error = st.session_state.get(
        "live_ibkr_position_value_error",
        "",
    )

    ibkr_tip("Detailed broker-account inspection with expanded account metrics and valuation diagnostics.")

    d1, d2, d3 = responsive_columns(3)
    with d1:
        ibkr_metric_card("Inspection Mode", "DETAILED METRICS", "Expanded broker-account inspection", tone="info")
    with d2:
        ibkr_metric_card("Account Rows", _safe_len(broker_snapshot_account_summary), "Cached IBKR account summary rows", tone="info")
    with d3:
        ibkr_metric_card("Snapshot Reference", snapshot_age_label(broker_snapshot_timestamp), "Broker account cache timing", tone="good" if broker_snapshot_timestamp else "warning")

    if readiness_passed:
        st.success("Account and broker operations are ready for controlled OMS execution.")
    elif mode == "LIVE" and connected:
        st.warning("Broker is connected in LIVE workflow, but readiness is incomplete. Verify the checklist before execution.")

    b1, b2, b3, b4 = responsive_columns(4)

    with b1:
        account_metric(
            "Available Funds",
            account_values,
            "AvailableFunds",
        )

    with b2:
        account_metric(
            "Total Cash",
            account_values,
            "TotalCashValue",
        )

    with b3:
        account_metric(
            "Excess Liquidity",
            account_values,
            "ExcessLiquidity",
        )

    with b4:
        account_metric(
            "Gross Position",
            account_values,
            "GrossPositionValue",
        )

    cash1, cash2, cash3, cash4 = responsive_columns(4)

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
            "Cushion",
            account_values,
            "Cushion",
        )

    if not account_values:
        st.warning(
            "No IBKR account balance values are cached yet. "
            "Connect IBKR, then use Pull Broker Snapshot."
        )

    if account_error:
        st.warning(
            "Account values warning: "
            + str(account_error)
        )

    if position_value_error:
        st.warning(
            "Broker position value warning: "
            + str(position_value_error)
        )

    with st.expander("Account Balance Details"):
        st.write(account_values)

    with st.expander("Broker Position Summary"):
        st.write(
            {
                "broker_position_value": broker_position_value,
                "positions": broker_snapshot_positions,
            }
        )

    st.subheader("Risk Gate")
    ibkr_tip("Pre-trade exposure, concentration, and cash-buffer gate for live execution safety.")

    risk_concentration = 0.0
    if position_rows and total_market_value > 0:
        try:
            risk_concentration = max(
                (safe_float(str(r.get("Allocation %", "0")).replace("%", ""), 0.0) for r in position_rows),
                default=0.0,
            )
        except Exception:
            risk_concentration = 0.0

    cash_buffer_pct = (available_funds_value / net_liq_value * 100.0) if net_liq_value > 0 else 0.0
    risk_badge = "READY" if readiness_passed else "NOT READY"

    rg1, rg2, rg3, rg4, rg5 = responsive_columns(5)
    with rg1:
        ibkr_metric_card("Account Exposure", f"{cash_deployment:.1f}%", "Gross exposure / net liq", tone="risk" if cash_deployment >= 80 else "warning" if cash_deployment >= 60 else "good")
    with rg2:
        ibkr_metric_card("Concentration", f"{risk_concentration:.1f}%", "Largest position allocation", tone="risk" if risk_concentration >= 30 else "warning" if risk_concentration >= 20 else "good")
    with rg3:
        ibkr_metric_card("Cash Buffer", f"{cash_buffer_pct:.1f}%", "Available funds / net liq", tone="good" if cash_buffer_pct >= 20 else "warning" if cash_buffer_pct >= 10 else "risk")
    with rg4:
        ibkr_metric_card("Live Trading Warning", "LIVE" if mode == "LIVE" else "PAPER/SIM", "Mode visibility guard", tone="risk" if mode == "LIVE" else "info")
    with rg5:
        ibkr_metric_card("Risk Gate", risk_badge, "Ready / Not Ready", tone="good" if readiness_passed else "risk")

    st.subheader("Execution Handoff")
    ibkr_tip("Send selected symbol/order context to OMS, Position Command, or Journal.")

    preferred_symbol = st.session_state.get("selected_symbol", "")
    if not preferred_symbol and position_rows:
        preferred_symbol = str(position_rows[0].get("Symbol") or "")
    if not preferred_symbol and fill_rows:
        preferred_symbol = str(fill_rows[0].get("Symbol") or "")
    preferred_symbol = str(preferred_symbol or "AAPL").upper().strip()

    h1, h2, h3 = responsive_columns(3)
    with h1:
        if st.button("Send to OMS", width="stretch", key="live_ibkr_handoff_oms"):
            st.session_state["selected_symbol"] = preferred_symbol
            st.session_state["oms_order_symbol"] = preferred_symbol
            st.session_state["jfbp_main_navigation"] = "OMS Execution"
            st.rerun()
    with h2:
        if st.button("Send to Position Command", width="stretch", key="live_ibkr_handoff_position"):
            st.session_state["selected_symbol"] = preferred_symbol
            st.session_state["position_command_symbol"] = preferred_symbol
            st.session_state["jfbp_main_navigation"] = "Position Command Center"
            st.rerun()
    with h3:
        if st.button("Send to Journal", width="stretch", key="live_ibkr_handoff_journal"):
            last_fill = fill_rows[0] if fill_rows else {"Symbol": preferred_symbol, "Status": "NO FILL", "Timestamp": now()}
            st.session_state["journal_trade_record"] = last_fill
            st.session_state["selected_symbol"] = preferred_symbol
            st.session_state["jfbp_main_navigation"] = "Journal"
            st.rerun()

    st.subheader("Emergency Controls")
    ibkr_tip("Danger zone for live broker operations: refresh broker state, cancel open orders, and disconnect session.")

    if mode == "LIVE":
        st.error("LIVE SESSION WARNING: Dangerous actions are isolated below. Confirm intent before use.")

    e1, e2, e3 = responsive_columns(3)
    with e1:
        emergency_refresh = st.button("Refresh Broker State", width="stretch", key="live_ibkr_emergency_refresh")
    with e2:
        emergency_cancel_orders = st.button("Cancel Open Orders", width="stretch", key="live_ibkr_emergency_cancel_orders")
    with e3:
        emergency_disconnect = st.button("Disconnect Session", width="stretch", key="live_ibkr_emergency_disconnect")

    if emergency_refresh:
        reset_operator_intent()
        st.session_state["live_ibkr_cached_status"] = None
        st.session_state["live_ibkr_status_cached_at"] = 0.0
        st.session_state["live_ibkr_last_refresh"] = now()
        st.rerun()

    if emergency_cancel_orders:
        ok, reason = call_if_exists(gateway, "cancel_all_open_orders")
        if not ok:
            ok, reason = call_if_exists(gateway, "cancel_all_orders")
        if ok:
            st.success("Cancel open orders requested.")
        else:
            st.warning(f"Cancel open orders unavailable: {reason}")

    if emergency_disconnect:
        ok, reason = call_if_exists(gateway, "disconnect")
        if ok:
            st.session_state["live_ibkr_cached_status"] = {
                "connected": False,
                "status": "DISCONNECTED",
                "detail": "disconnected from emergency controls",
            }
            st.session_state["live_ibkr_status_cached_at"] = 0.0
            st.session_state["live_ibkr_last_refresh"] = now()
            st.success("Gateway disconnect requested.")
            st.rerun()
        else:
            st.error(f"Disconnect failed: {reason}")

    st.caption("Paper/Live warning: LIVE mode with gateway connectivity can route real broker orders from execution modules when armed.")

    
    # =====================================================
    # SAFETY LOCKS
    # =====================================================

    st.subheader("Safety Locks")
    ibkr_tip("Core live arming and kill-switch controls.")

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
            "Refresh Status Cache",
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
    # TECHNICAL DIAGNOSTICS
    # =====================================================

    st.markdown('<div class="ibkr-utility-title">Technical Diagnostics</div>', unsafe_allow_html=True)

    with st.expander("Gateway detail"):
        st.write(status.get("detail"))
        st.table(
            {
                "Component": list(status_rows.keys()),
                "Status": list(status_rows.values()),
            }
        )

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


def run_page():
    page()