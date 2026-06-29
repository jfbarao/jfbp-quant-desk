# =========================================================
# JFBP APP ENTRYPOINT v24.24
# STABLE ROUTER — SAAS LOGIN GATE ENABLED
# FUTURE ASSET MODULES READY
# =========================================================

from pathlib import Path
import html
import json
import smtplib
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage

import streamlit as st

from core.bootstrap import init_core
from core.ui_utils import scroll_to_top

from pages.Navigation_Guide import run_page as navigation_guide_page

try:
    from pages.Opportunity_Center import run_page as opportunity_center_page
except Exception as opportunity_center_import_error:
    def opportunity_center_page(_err=opportunity_center_import_error):
        st.title("🎯 Opportunity Center")
        st.error("Opportunity Center could not be loaded.")
        st.caption("Make sure Opportunity_Center.py is saved inside the pages folder.")
        st.exception(_err)

try:
    from pages.Options_Center import run_page as options_center_page
except Exception as options_center_import_error:
    def options_center_page(_err=options_center_import_error):
        st.title("🧩 Options Center")
        st.error("Options Center could not be loaded.")
        st.caption("Make sure Options_Center.py is saved inside the pages folder.")
        st.exception(_err)

try:
    from pages.Trade_Command_Center import run_page as trade_command_center_page
except Exception as trade_command_import_error:
    def trade_command_center_page(_err=trade_command_import_error):
        st.title("🎯 Trade Command Center")
        st.error("Trade Command Center could not be loaded.")
        st.caption("Make sure Trade_Command_Center.py is saved inside the pages folder.")
        st.exception(_err)

try:
    from pages.Position_Command_Center import run_page as position_command_center_page
except Exception as position_command_import_error:
    def position_command_center_page(_err=position_command_import_error):
        st.title("🎯 Position Command Center")
        st.error("Position Command Center could not be loaded.")
        st.caption("Make sure Position_Command_Center.py is saved inside the pages folder.")
        st.exception(_err)

from pages.Scanner_page import run_page as scanner_page
from pages.Research_Stock import run_page as research_stock_page
from pages.Automation_Control_Center import run_page as automation_control_page
from pages.OMS_Execution import run_page as oms_page
from pages.page_order_ticket import run_page as order_ticket_page
from pages.Portfolio import run_page as portfolio_page

try:
    from pages.Market_Hub import run_page as market_hub_page
except Exception as market_hub_import_error:
    try:
        # Backward compatibility: keeps the sidebar working if the file has not
        # yet been renamed from Live_Stock.py to Market_Hub.py.
        from pages.Live_Stock import run_page as market_hub_page
    except Exception as live_stock_import_error:
        def market_hub_page(
            _market_hub_err=market_hub_import_error,
            _live_stock_err=live_stock_import_error,
        ):
            st.title("📡 Market Hub")
            st.error("Market Hub could not be loaded.")
            st.caption(
                "Make sure Market_Hub.py is saved inside the pages folder. "
                "Temporary fallback to Live_Stock.py also failed."
            )
            st.exception(_market_hub_err)
            st.exception(_live_stock_err)

from pages.Live_IBKR import run_page as live_ibkr_page
from pages.Journal import run_page as journal_page
from pages.Database import run_page as database_page
from pages.Market_Reaction import run_page as market_pulse_page
from pages.Economic_Calendar import run_page as economic_calendar_page
from pages.Earnings_Calendar import run_page as earnings_calendar_page
from pages.Private_Portfolio_Impact import run_page as private_portfolio_page

try:
    from pages.Crypto_Pulse import run_page as crypto_pulse_page
except Exception as crypto_import_error:
    def crypto_pulse_page(_err=crypto_import_error):
        st.title("₿ Crypto Pulse")
        st.error("Crypto Pulse could not be loaded.")
        st.caption("Make sure Crypto_Pulse.py is saved inside the pages folder.")
        st.exception(_err)

try:
    from pages.Forex_Pulse import run_page as forex_pulse_page
except Exception as forex_import_error:
    def forex_pulse_page(_err=forex_import_error):
        st.title("💱 Forex Pulse")
        st.error("Forex Pulse could not be loaded.")
        st.caption("Make sure Forex_Pulse.py is saved inside the pages folder.")
        st.exception(_err)

try:
    from pages.Gold_Pulse import run_page as gold_pulse_page
except Exception as gold_import_error:
    def gold_pulse_page(_err=gold_import_error):
        st.title("🥇 Gold Pulse")
        st.error("Gold Pulse could not be loaded.")
        st.caption("Make sure Gold_Pulse.py is saved inside the pages folder.")
        st.exception(_err)

try:
    from pages.Oil_Pulse import run_page as oil_pulse_page
except Exception as oil_import_error:
    def oil_pulse_page(_err=oil_import_error):
        st.title("🛢 Oil Pulse")
        st.error("Oil Pulse could not be loaded.")
        st.caption("Make sure Oil_Pulse.py is saved inside the pages folder.")
        st.exception(_err)


try:
    from pages.SaaS_Core import (
        run_page as saas_core_page,
        init_saas_state,
        get_current_user,
        get_supabase_client,
        inject_saas_css,
        render_auth_panel,
        require_page_access,
        supabase_logout,
        remember_active_page,
        restore_active_page,
        clear_active_page_cache,
        is_admin_user,
    )
except Exception as saas_import_error:
    _saas_import_error = saas_import_error

    def saas_core_page(_err=saas_import_error):
        st.title("🔐 SaaS Core")
        st.error("SaaS Core could not be loaded.")
        st.caption("Make sure SaaS_Core.py is saved inside the pages folder.")
        st.exception(_err)

    def init_saas_state():
        st.session_state.setdefault("saas_logged_in", False)
        st.session_state.setdefault("saas_user", None)

    def get_current_user():
        return None

    def get_supabase_client():
        return None

    def inject_saas_css():
        return None

    def render_auth_panel(_err=_saas_import_error):
        st.error("SaaS Core could not be loaded, so login is unavailable.")
        if _err is not None:
            st.exception(_err)

    def require_page_access(page_name: str, _err=_saas_import_error) -> bool:
        st.error("SaaS Core could not be loaded, so access control is unavailable.")
        if _err is not None:
            st.exception(_err)
        return False

    def supabase_logout():
        st.session_state["saas_logged_in"] = False
        st.session_state["saas_user"] = None
        return True, "Logged out."

    def is_admin_user(user):
        return False

    def remember_active_page(page_name: str):
        return None

    def restore_active_page(default_page: str = "Opportunity Center"):
        return default_page

    def clear_active_page_cache():
        return None


try:
    from pages.Admin_Control_Center import run_page as admin_control_center_page
except Exception as admin_control_import_error:
    def admin_control_center_page(_err=admin_control_import_error):
        st.title("🛡️ Admin Control Center")
        st.error("Admin Control Center could not be loaded.")
        st.caption("Make sure Admin_Control_Center.py is saved inside the pages folder.")
        st.exception(_err)


st.set_page_config(
    page_title="JFBP Quant Desk",
    layout="wide",
)


APP_VERSION = "v24.24"
FOUNDER_FEEDBACK_EMAIL = "hello@jfbpquantdesk.com"
FEEDBACK_CATEGORY_OPTIONS = ["Bug", "Suggestion", "Question", "Feature Request"]


# =========================================================
# FALLBACK / FUTURE PAGES
# =========================================================

def empty_page(title: str, description: str = "Page not built yet."):
    st.title(title)
    st.info(description)


def future_asset_page(title: str, asset_class: str):
    st.title(title)
    st.caption("Future JFBP Quant Desk asset module placeholder.")
    st.info(
        f"{asset_class} module is planned for a future build. "
        "The router is already prepared so this page can be upgraded later "
        "without changing the app navigation structure."
    )
    st.markdown(
        """
        **Planned structure:**
        - Market regime
        - Volatility / stress dashboard
        - Leadership and breadth
        - Event catalysts
        - Trade bias / playbook
        - Risk controls
        """
    )


def _founder_plan_label(user) -> str:
    if user is None:
        return "Starter"
    if is_admin_user(user):
        return "Admin"

    plan_value = str(getattr(user, "plan", "") or "").strip().upper()
    if plan_value == "ELITE":
        return "Elite"
    if plan_value == "PRO":
        return "Pro"
    return "Starter"


def _sidebar_role_plan_label(user) -> str:
    plan_label = _founder_plan_label(user)
    if plan_label == "Admin":
        # Keep plan from subscription field even for admin users.
        raw_plan = str(getattr(user, "plan", "") or "").strip().upper()
        if raw_plan == "ELITE":
            plan_label = "Elite"
        elif raw_plan == "PRO":
            plan_label = "Pro"
        else:
            plan_label = "Starter"

    role_value = str(getattr(user, "role", "") or "").strip().upper()
    if role_value == "ADMIN":
        role_label = "Admin"
    else:
        role_label = "User"

    return f"{role_label} · {plan_label}"


def _sidebar_display_name(user) -> str:
    full_name = str(getattr(user, "full_name", "") or "").strip()
    if full_name:
        return full_name

    email = str(getattr(user, "email", "") or "").strip()
    if "@" in email:
        return email.split("@", 1)[0]
    return "JFBP Member"


def _sidebar_initials(name: str, email: str) -> str:
    tokens = [part for part in str(name or "").replace("_", " ").split() if part]
    if len(tokens) >= 2:
        return (tokens[0][0] + tokens[1][0]).upper()
    if len(tokens) == 1 and len(tokens[0]) >= 2:
        return tokens[0][:2].upper()

    clean_email = str(email or "").strip()
    if clean_email:
        local = clean_email.split("@", 1)[0]
        letters = "".join(ch for ch in local if ch.isalpha())
        if len(letters) >= 2:
            return letters[:2].upper()
    return "JB"


def _render_sidebar_profile_card(user) -> None:
    display_name = _sidebar_display_name(user)
    email = str(getattr(user, "email", "") or "").strip()
    role_plan_label = _sidebar_role_plan_label(user)
    initials = _sidebar_initials(display_name, email)

    safe_name = html.escape(display_name)
    safe_email = html.escape(email)
    safe_role_plan = html.escape(role_plan_label)
    safe_initials = html.escape(initials)

    st.sidebar.markdown(
        (
            '<div class="jfbp-profile-card">'
            f'<div class="jfbp-profile-avatar">{safe_initials}</div>'
            '<div class="jfbp-profile-meta">'
            f'<div class="jfbp-profile-name">{safe_name}</div>'
            f'<div class="jfbp-profile-plan">{safe_role_plan}</div>'
            f'<div class="jfbp-profile-email">{safe_email}</div>'
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _apply_sidebar_auth_session(client) -> bool:
    session = st.session_state.get("saas_auth_session")
    if not isinstance(session, dict):
        return False

    access_token = str(session.get("access_token", "") or "").strip()
    refresh_token = str(session.get("refresh_token", "") or "").strip()
    if not access_token:
        return False

    try:
        client.auth.set_session(access_token, refresh_token)
        return True
    except TypeError:
        try:
            client.auth.set_session(access_token=access_token, refresh_token=refresh_token)
            return True
        except Exception:
            return False
    except Exception:
        return False


def _update_logged_in_password(new_password: str) -> tuple[bool, str]:
    client = get_supabase_client()
    if client is None:
        return False, "Supabase client unavailable"

    if not _apply_sidebar_auth_session(client):
        return False, "Authenticated session unavailable"

    try:
        client.auth.update_user({"password": new_password})
        return True, "Password updated"
    except Exception as exc:
        return False, str(exc)


def _guess_current_symbol() -> str:
    symbol_keys = [
        "selected_symbol",
        "trade_command_symbol",
        "research_ticker",
        "research_symbol",
        "tcc_symbol",
        "execution_symbol",
        "position_symbol",
        "oms_order_symbol",
        "position_command_symbol",
    ]
    for key in symbol_keys:
        raw = str(st.session_state.get(key, "") or "").strip().upper()
        if raw:
            return raw
    return "N/A"


def _diagnostics_payload(active_page: str) -> dict:
    return {
        "navigation": str(st.session_state.get("jfbp_main_navigation", "") or ""),
        "active_page": active_page,
        "keys_present": {
            "selected_symbol": "selected_symbol" in st.session_state,
            "trade_command_symbol": "trade_command_symbol" in st.session_state,
            "research_ticker": "research_ticker" in st.session_state,
            "scanner_selected_symbol": "scanner_selected_symbol" in st.session_state,
            "saas_logged_in": bool(st.session_state.get("saas_logged_in", False)),
        },
    }


def _send_feedback_email(subject: str, body: str, reply_to: str, feedback_id: str) -> tuple[bool, str]:
    required_secret_names = [
        "FEEDBACK_SMTP_HOST",
        "FEEDBACK_SMTP_USER",
        "FEEDBACK_SMTP_PASSWORD",
        "FEEDBACK_SMTP_FROM",
    ]

    missing_config = [
        name
        for name in required_secret_names
        if not str(st.secrets.get(name, "") or "").strip()
    ]
    if missing_config:
        print(f"FOUNDER_FEEDBACK {feedback_id}: smtp send failed: missing config {','.join(missing_config)}")
        return False, f"CONFIG_MISSING:{feedback_id}:" + ",".join(missing_config)

    smtp_host = str(st.secrets.get("FEEDBACK_SMTP_HOST", "") or "").strip()
    try:
        smtp_port = int(str(st.secrets.get("FEEDBACK_SMTP_PORT", "587") or "587").strip())
    except Exception:
        smtp_port = 587
    smtp_user = str(st.secrets.get("FEEDBACK_SMTP_USER", "") or "").strip()
    smtp_password = str(st.secrets.get("FEEDBACK_SMTP_PASSWORD", "") or "").strip()
    smtp_from = str(st.secrets.get("FEEDBACK_SMTP_FROM", "") or "").strip()
    founder_feedback_email = str(st.secrets.get("FOUNDER_FEEDBACK_EMAIL", FOUNDER_FEEDBACK_EMAIL) or FOUNDER_FEEDBACK_EMAIL).strip()
    smtp_tls = str(st.secrets.get("FEEDBACK_SMTP_USE_TLS", "true") or "true").strip().lower() in {"1", "true", "yes", "y", "on"}

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = smtp_from
    message["To"] = founder_feedback_email
    if reply_to and "@" in reply_to:
        message["Reply-To"] = reply_to
    message.set_content(body)

    try:
        print(f"FOUNDER_FEEDBACK {feedback_id}: smtp send starting")
        use_ssl = (smtp_port == 465) and (not smtp_tls)
        smtp_client = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP

        with smtp_client(smtp_host, smtp_port, timeout=20) as server:
            if smtp_tls and not use_ssl:
                server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.send_message(message)
        print(f"FOUNDER_FEEDBACK {feedback_id}: smtp send succeeded")
        return True, "Feedback sent."
    except Exception as exc:
        print(f"FOUNDER_FEEDBACK {feedback_id}: smtp send failed: {exc}")
        return False, f"[{feedback_id}] Could not send feedback email: {exc}"


def _feedback_error_message_for_user(raw_error: str, user) -> str:
    text = str(raw_error or "").strip()
    if text.startswith("CONFIG_MISSING:"):
        rest = text.split(":", 1)[1]
        parts = rest.split(":", 1)
        feedback_id = parts[0].strip() if len(parts) > 1 else ""
        missing_csv = parts[1] if len(parts) > 1 else parts[0]
        missing = [
            item.strip()
            for item in missing_csv.split(",")
            if item.strip()
        ]
        if is_admin_user(user):
            bullet_lines = "\n".join([f"• {item}" for item in missing])
            return (
                "⚠️ Feedback email is not configured.\n"
                + (f"Reference: {feedback_id}\n" if feedback_id else "")
                +
                "Missing configuration:\n"
                f"{bullet_lines}\n"
                "Configure these in Streamlit Secrets."
            )
        return "⚠️ Feedback couldn't be sent. Please try again later."

    if is_admin_user(user):
        return f"⚠️ Feedback delivery failed.\n{text or 'Unknown error.'}"

    return "⚠️ Feedback couldn't be sent. Please try again later."


def _submit_founder_feedback(payload: dict, reply_to: str, feedback_id: str) -> tuple[bool, str]:
    def _build_feedback_email_body(data: dict) -> str:
        # Keep body sections explicit so future additions (attachments, logs,
        # screenshots) can be appended without rewriting the submit workflow.
        message_value = str(data.get("message", "") or "").strip()
        if not message_value:
            message_value = "(no message provided)"

        sections = [
            f"Feedback ID: {feedback_id}",
            f"User: {data.get('user', 'unknown')}",
            f"Plan: {data.get('plan', 'Starter')}",
            f"Page: {data.get('page', 'Unknown')}",
            f"Version: {data.get('version', APP_VERSION)}",
            f"Time: {data.get('time', datetime.now(timezone.utc).isoformat())}",
            f"Category: {data.get('category', 'Suggestion')}",
            "Message:",
            message_value,
        ]

        symbol_value = data.get("symbol")
        if symbol_value:
            sections.extend([f"Symbol: {symbol_value}"])

        diagnostics_value = data.get("diagnostics")
        if diagnostics_value:
            sections.extend(["Session Diagnostics:", str(diagnostics_value)])

        sections.extend(
            [
                "",
                "Future Extensions:",
                "- Attachments: Not included",
                "- Screenshots: Not included",
                "- Runtime Logs: Not included",
            ]
        )

        return "\n".join(sections)

    subject = f"[{payload['plan']}][{payload['page']}][{payload['category']}][{feedback_id}]"
    body = _build_feedback_email_body(payload)

    ok, result = _send_feedback_email(
        subject=subject,
        body=body,
        reply_to=reply_to,
        feedback_id=feedback_id,
    )
    # Future:
    # save_feedback_to_supabase(payload)
    return ok, result


def render_founder_feedback_footer(page_key: str) -> None:
    user = get_current_user()
    page_name = ACCESS_NAME_BY_PAGE.get(page_key, page_key)
    plan_label = _founder_plan_label(user)
    feedback_state_key = f"feedback_success_{page_name}"
    feedback_success_once_key = f"feedback_success_once_{page_name}"
    feedback_reference_key = f"feedback_reference_{page_name}"
    feedback_rate_limit_key = "founder_feedback_last_submit_ts"
    symbol_default = _guess_current_symbol()

    st.markdown("---")
    st.markdown("### 💬 Message the Founder")
    st.caption("Help us improve JFBP Quant Desk. Found something confusing, have an idea, or spotted a bug?")

    with st.expander("Send a note to Captain JFBP", expanded=False):
        with st.form(key=f"feedback_form_{page_name}", clear_on_submit=True):
            category = st.radio(
                "Category",
                FEEDBACK_CATEGORY_OPTIONS,
                horizontal=True,
            )
            message_text = st.text_area(
                "Message",
                height=140,
                placeholder="Tell us what happened or what would make this workflow better.",
            )

            include_symbol = st.checkbox("Include current symbol", value=True)
            include_diagnostics = st.checkbox("Include session diagnostics", value=False)

            submit = st.form_submit_button("Submit Feedback", type="primary", use_container_width=True)

        if submit:
            feedback_id = (
                f"FB-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-"
                f"{uuid.uuid4().hex[:6]}"
            )
            print(f"FOUNDER_FEEDBACK {feedback_id}: submit requested")

            # New attempts should never keep stale success UI from older sends.
            st.session_state[feedback_state_key] = False
            st.session_state[feedback_success_once_key] = False
            st.session_state[feedback_reference_key] = ""

            clean_message = str(message_text or "").strip()
            if not clean_message:
                print(f"FOUNDER_FEEDBACK {feedback_id}: blocked by validation")
                st.warning("Please add a message before submitting feedback.")
            else:
                now_ts = datetime.now(timezone.utc).timestamp()
                last_submit_ts = float(st.session_state.get(feedback_rate_limit_key, 0.0) or 0.0)
                if now_ts - last_submit_ts < 30:
                    print(f"FOUNDER_FEEDBACK {feedback_id}: blocked by cooldown")
                    st.warning("Please wait a few seconds before sending another message.")
                else:
                    user_email = str(getattr(user, "email", "") or "unknown")
                    symbol_line = symbol_default if include_symbol else "Not included"
                    diagnostics_block = "Not included"
                    if include_diagnostics:
                        diagnostics_block = json.dumps(_diagnostics_payload(page_name), indent=2)

                    timestamp = datetime.now(timezone.utc).isoformat()

                    feedback_payload = {
                        "user": user_email,
                        "plan": plan_label,
                        "page": page_name,
                        "version": APP_VERSION,
                        "time": timestamp,
                        "category": category,
                        "message": clean_message,
                        "symbol": symbol_line,
                        "diagnostics": diagnostics_block,
                    }

                    ok, result = _submit_founder_feedback(
                        payload=feedback_payload,
                        reply_to=user_email,
                        feedback_id=feedback_id,
                    )
                    st.session_state[feedback_rate_limit_key] = now_ts
                    if ok:
                        st.session_state[feedback_state_key] = True
                        st.session_state[feedback_success_once_key] = False
                        st.session_state[feedback_reference_key] = feedback_id
                        st.rerun()
                    else:
                        st.warning(_feedback_error_message_for_user(result, user))

    if st.session_state.get(feedback_state_key, False):
        already_shown_once = bool(st.session_state.get(feedback_success_once_key, False))
        if already_shown_once:
            st.session_state[feedback_state_key] = False
            st.session_state[feedback_success_once_key] = False
        else:
            feedback_reference = str(st.session_state.get(feedback_reference_key, "") or "").strip()
            st.success(
                "✅ Feedback sent.\n\n"
                f"Reference: {feedback_reference}\n\n"
                "Your message has been sent directly to me.\n\n"
                "I personally read every message, and many improvements in JFBP Quant Desk come directly from our community.\n\n"
                "— **Captain JFBP**"
            )
            st.session_state[feedback_success_once_key] = True


# =========================================================
# SIDEBAR WORKFLOW NAVIGATION
# =========================================================

def inject_sidebar_workflow_css() -> None:
    st.markdown(
        """
        <style>
            section[data-testid="stSidebar"] {
                background: #f8fafc;
            }

            section[data-testid="stSidebar"] > div:first-child {
                display: flex;
                flex-direction: column;
                min-height: 100vh;
            }

            section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] {
                overflow-wrap: anywhere;
            }

            .jfbp-sidebar-footer {
                margin-top: auto;
                padding-top: 0.72rem;
                padding-bottom: 0.52rem;
                background: #f8fafc;
                border-top: 1px solid #d6dbe5;
            }

            .jfbp-sidebar-footer-email {
                margin-top: 0.35rem;
                font-size: 0.74rem;
                color: #64748b;
                line-height: 1.25;
                overflow-wrap: anywhere;
            }

            .jfbp-profile-card {
                display: flex;
                align-items: center;
                gap: 0.62rem;
                margin-top: 0.45rem;
                margin-bottom: 0.35rem;
                padding: 0.58rem 0.56rem;
                border: 1px solid #d6dbe5;
                border-radius: 11px;
                background: #ffffff;
            }

            .jfbp-profile-avatar {
                width: 2.05rem;
                height: 2.05rem;
                border-radius: 999px;
                background: #e2e8f0;
                color: #0f172a;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 700;
                font-size: 0.74rem;
                letter-spacing: 0.03em;
                flex: 0 0 auto;
            }

            .jfbp-profile-meta {
                min-width: 0;
                flex: 1;
            }

            .jfbp-profile-name {
                font-size: 0.84rem;
                font-weight: 650;
                color: #0f172a;
                line-height: 1.2;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .jfbp-profile-plan {
                display: inline-block;
                margin-top: 0.18rem;
                padding: 0.06rem 0.42rem;
                border-radius: 999px;
                background: #dbeafe;
                color: #1e3a8a;
                font-size: 0.68rem;
                font-weight: 640;
                line-height: 1.2;
            }

            .jfbp-profile-email {
                margin-top: 0.2rem;
                font-size: 0.72rem;
                color: #64748b;
                line-height: 1.2;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            /* Sidebar expander cards: uniform border on all sides. */
            section[data-testid="stSidebar"] details {
                background: #f8fafc !important;
                border: 1px solid #d6dbe5 !important;
                border-radius: 12px !important;
                margin: 0.42rem 0 !important;
                padding: 0 !important;
                overflow: hidden !important;
                box-shadow: none !important;
            }

            section[data-testid="stSidebar"] details:first-of-type {
                margin-top: 0.25rem !important;
            }

            section[data-testid="stSidebar"] details > summary {
                min-height: 2.10rem !important;
                padding: 0.46rem 0.72rem !important;
                border: none !important;
                border-bottom: 0 !important;
                font-weight: 640 !important;
                letter-spacing: 0.01em;
                text-transform: none;
                color: #334155 !important;
                font-size: 0.96rem !important;
                background: #f8fafc !important;
                box-shadow: none !important;
            }

            section[data-testid="stSidebar"] details[open] > summary {
                border-bottom: 1px solid #d6dbe5 !important;
            }

            section[data-testid="stSidebar"] details > div {
                padding: 0.36rem 0.64rem 0.44rem 0.64rem !important;
            }

            section[data-testid="stSidebar"] details::before,
            section[data-testid="stSidebar"] details::after,
            section[data-testid="stSidebar"] summary::before,
            section[data-testid="stSidebar"] summary::after {
                border-top: none !important;
                box-shadow: none !important;
            }

            .jfbp-sidebar-caption {
                margin-top: 0;
                margin-bottom: 0.26rem;
                font-size: 0.76rem;
                color: #64748b;
                line-height: 1.35;
            }

            section[data-testid="stSidebar"] .stButton > button {
                width: 100%;
                justify-content: flex-start;
                text-align: left;
                min-height: 2.50rem;
                border-radius: 9px;
                font-weight: 620;
                font-size: 0.90rem;
                padding-left: 0.64rem;
                padding-right: 0.64rem;
                margin-bottom: 0.14rem;
                white-space: normal;
                line-height: 1.25;
            }

            section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
                background: #2563eb !important;
                border-color: #2563eb !important;
                color: white !important;
            }

            @media (max-width: 760px) {
                section[data-testid="stSidebar"] summary {
                    font-size: 0.80rem !important;
                }

                section[data-testid="stSidebar"] .stButton > button {
                    min-height: 2.40rem;
                    font-size: 0.88rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _sidebar_nav_button(label: str, page_key: str, container=st.sidebar) -> None:
    current = st.session_state.get("jfbp_main_navigation", "Opportunity Center")
    selected = current == page_key

    if container.button(
        ("✓ " if selected else "") + label,
        key=f"nav_btn_{page_key}",
        width="stretch",
        type="primary" if selected else "secondary",
    ):
        navigate_to_page(page_key)


def navigate_to_page(page_key: str) -> None:
    st.session_state["jfbp_main_navigation"] = page_key
    try:
        remember_active_page(page_key)
    except Exception:
        pass
    st.rerun()


def _section_is_active(current: str, page_keys: list[str]) -> bool:
    return current in page_keys


def _sidebar_group(title: str, caption: str, page_items: list[tuple[str, str]], expanded: bool = False) -> None:
    with st.sidebar.expander(title, expanded=expanded):
        if caption:
            st.markdown(
                f'<div class="jfbp-sidebar-caption">{caption}</div>',
                unsafe_allow_html=True,
            )

        for label, page_key in page_items:
            _sidebar_nav_button(label, page_key, container=st)


def workflow_sidebar_navigation() -> str:
    st.session_state.setdefault("jfbp_main_navigation", "Opportunity Center")
    current = st.session_state.get("jfbp_main_navigation", "Opportunity Center")
    current_user = get_current_user()
    admin_pages = {"SaaS Core", "Admin Control Center"}

    # Never expose internal admin pages to regular users. If a non-admin
    # session was previously parked on an admin page, move it back to the
    # normal workflow start page before rendering the sidebar.
    if current in admin_pages and not is_admin_user(current_user):
        current = "Opportunity Center"
        st.session_state["jfbp_main_navigation"] = current

    groups = [
        {
            "title": "🧭 Workflow",
            "caption": "Start here and understand the desk.",
            "items": [
                ("🧭 Navigation Guide", "🧭 Navigation Guide"),
                ("🎯 Opportunity Center", "Opportunity Center"),
            ],
            "always_open": True,
        },
        {
            "title": "📈 Market Intelligence",
            "caption": "Understand the market first.",
            "items": [
                ("Market Pulse", "Market Pulse"),
                ("Economic Calendar", "Economic Calendar"),
                ("Earnings Calendar", "Earnings Calendar"),
            ],
            "always_open": False,
        },
        {
            "title": "🎯 Opportunity Discovery",
            "caption": "Find, validate, and prepare trade ideas.",
            "items": [
                ("Scanner", "Scanner"),
                ("Research Stock", "Research Stock"),
                ("🧩 Options Center", "Options Center"),
                ("🎯 Trade Command Center", "Trade Command Center"),
            ],
            "always_open": False,
        },
        {
            "title": "⚙ Execution",
            "caption": "Control routing, automation, and open risk.",
            "items": [
                ("Automation Control Center", "Automation Control Center"),
                ("OMS Execution", "OMS Execution"),
                ("🎯 Position Command Center", "Position Command Center"),
                ("Live IBKR", "Live IBKR"),
                ("Manual Order Ticket", "Manual Order Ticket"),
            ],
            "always_open": False,
        },
        {
            "title": "💼 Portfolio",
            "caption": "Monitor exposure and performance.",
            "items": [
                ("Portfolio", "Portfolio"),
                ("Private Portfolio", "Private Portfolio"),
                ("📡 Market Hub", "Market Hub"),
            ],
            "always_open": False,
        },
        {
            "title": "📝 Review",
            "caption": "Review trades and system data.",
            "items": [
                ("Journal", "Journal"),
                ("Database", "Database"),
            ],
            "always_open": False,
        },
        {
            "title": "🌍 Multi-Asset",
            "caption": "Crypto, forex, commodities, and macro regimes.",
            "items": [
                ("₿ Crypto Pulse", "Crypto Pulse"),
                ("💱 Forex Pulse", "Forex Pulse"),
                ("🥇 Gold Pulse", "Gold Pulse"),
                ("🛢 Oil Pulse", "Oil Pulse"),
            ],
            "always_open": False,
        },
        {
            "title": "🔐 Admin",
            "caption": "SaaS infrastructure and subscription controls.",
            "items": [
                ("🔐 SaaS Core", "SaaS Core"),
                ("🛡️ Admin Control Center", "Admin Control Center"),
            ],
            "always_open": False,
        },
    ]

    for group in groups:
        if group["title"] == "🔐 Admin" and not is_admin_user(current_user):
            continue

        page_keys = [page_key for _, page_key in group["items"]]
        expanded = bool(group.get("always_open")) or _section_is_active(current, page_keys)
        _sidebar_group(
            group["title"],
            group["caption"],
            group["items"],
            expanded=expanded,
        )

    return st.session_state.get("jfbp_main_navigation", "Opportunity Center")



# =========================================================
# SAAS FRONT-DOOR GATE
# =========================================================

ACCESS_NAME_BY_PAGE = {
    "🧭 Navigation Guide": "Navigation Guide",
    "Opportunity Center": "Opportunity Center",
    "Scanner": "Scanner",
    "Market Hub": "Market Hub",
    "Research Stock": "Research Stock",
    "Trade Command Center": "Trade Command Center",
    "Options Center": "Options Center",
    "Market Pulse": "Market Pulse",
    "Economic Calendar": "Economic Calendar",
    "Earnings Calendar": "Earnings Calendar",
    "Automation Control Center": "Automation Control Center",
    "OMS Execution": "OMS Execution",
    "Position Command Center": "Position Command Center",
    "Manual Order Ticket": "Manual Order Ticket",
    "Portfolio": "Portfolio",
    "Live IBKR": "Live IBKR",
    "Journal": "Journal",
    "Database": "Database",
    "Private Portfolio": "Private Portfolio",
    "Crypto Pulse": "Crypto Pulse",
    "Forex Pulse": "Forex Pulse",
    "Gold Pulse": "Gold Pulse",
    "Oil Pulse": "Oil Pulse",
    "SaaS Core": "SaaS Core",
    "Admin Control Center": "Admin Control Center",
}

# Internal operating pages must be admin-only. They are hidden from regular
# users in the sidebar and blocked again here at the router layer.
ALWAYS_ALLOW_AFTER_LOGIN = set()
ADMIN_ONLY_PAGES = {"SaaS Core", "Admin Control Center"}


def render_front_door() -> None:
    """Public landing screen shown before the platform is unlocked."""
    inject_saas_css()

    logo_path = Path(__file__).parent / "JFBP_Quant_Desk.png"
    if logo_path.exists():
        st.image(str(logo_path), width=130)

    st.markdown(
        """
        <div class="saas-hero">
            <div class="saas-kicker">JFBP Quant Desk · Secure Access</div>
            <div class="saas-title">Start your 30-Day Free Trial</div>
            <div class="saas-text">
                Create your account or log in to access the platform. No credit card required for the trial.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_auth_panel()


def enforce_app_login() -> bool:
    """Stop the app before sidebar/page rendering unless a real user is logged in."""
    init_saas_state()
    if get_current_user() is not None:
        return True

    render_front_door()
    st.stop()
    return False


def run_protected_page(page_key: str, runner) -> None:
    """Run a page only when the logged-in user has plan or admin access."""
    access_name = ACCESS_NAME_BY_PAGE.get(page_key, page_key)
    current_user = get_current_user()

    if access_name in ADMIN_ONLY_PAGES and not is_admin_user(current_user):
        st.error("Admin access required.")
        return

    if access_name not in ALWAYS_ALLOW_AFTER_LOGIN:
        if not require_page_access(access_name):
            return

    runner()

# =========================================================
# APP ROUTER
# =========================================================

def app():

    init_core()
    enforce_app_login()
    inject_sidebar_workflow_css()

    current_navigation = str(st.session_state.get("jfbp_main_navigation", "") or "").strip()
    if not current_navigation:
        st.session_state["jfbp_main_navigation"] = restore_active_page("Opportunity Center")

    logo_path = Path(__file__).parent / "JFBP_Quant_Desk.png"

    if logo_path.exists():
        st.sidebar.image(
            str(logo_path),
            width=150,
        )
    else:
        st.sidebar.title("JFBP Desk")

    page = workflow_sidebar_navigation()

    # UI infrastructure: enforce top-of-page viewport on every routed module load.
    scroll_to_top()

    st.error(
        """
🚨 GLOBAL DEPLOYMENT TEST

Build: 2026-06-29-1645
Commit: 12dd97c

If you can read this, Streamlit Cloud is serving the latest build path.
"""
    )

    st.markdown(
        """
        <style>
        /* Force deployed-safe scorecard typography for both legacy and new class variants. */
        .pf-decision-card .pf-label,
        .opportunity-scorecard .scorecard-heading {
            font-size: 14px !important;
            line-height: 1.2 !important;
            font-weight: 800 !important;
        }
        .pf-decision-card .pf-value,
        .opportunity-scorecard .scorecard-role-value,
        .opportunity-scorecard .scorecard-allocation-value {
            font-size: 20px !important;
            line-height: 1.2 !important;
            font-weight: 800 !important;
        }
        .pf-decision-card .pf-review-value,
        .opportunity-scorecard .scorecard-review-value {
            font-size: 16px !important;
            line-height: 1.2 !important;
            font-weight: 800 !important;
        }
        .pf-decision-card .pf-sub,
        .opportunity-scorecard .scorecard-description {
            font-size: 14px !important;
            line-height: 1.32 !important;
        }
        .pf-decision-card,
        .opportunity-scorecard,
        .opportunity-scorecard * {
            word-break: normal !important;
            overflow-wrap: normal !important;
            hyphens: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    current_user = get_current_user()
    if current_user is not None:
        st.sidebar.markdown(
            '<div class="jfbp-sidebar-footer">',
            unsafe_allow_html=True,
        )

        st.sidebar.link_button(
            "💳 Manage Plan",
            "https://billing.stripe.com/p/login/3cIcN63Kpe2GcELaKp7IY00",
            use_container_width=True,
        )

        _render_sidebar_profile_card(current_user)

        st.session_state.setdefault("sidebar_show_change_password", False)
        st.sidebar.markdown("**👤 Account**")

        if st.sidebar.button(
            "🔑 Change Password",
            key="sidebar_change_password_btn",
            use_container_width=True,
        ):
            st.session_state["sidebar_show_change_password"] = not bool(
                st.session_state.get("sidebar_show_change_password", False)
            )

        if st.sidebar.button("🚪 Logout", key="sidebar_saas_logout", use_container_width=True):
            supabase_logout()
            clear_active_page_cache()
            st.rerun()

        if st.session_state.get("sidebar_show_change_password", False):
            with st.sidebar.form("sidebar_change_password_form", clear_on_submit=True):
                new_password = st.text_input("New Password", type="password")
                confirm_password = st.text_input("Confirm New Password", type="password")
                update_password = st.form_submit_button("Update Password", use_container_width=True)

            if update_password:
                new_password = str(new_password or "")
                confirm_password = str(confirm_password or "")

                if not new_password.strip():
                    st.sidebar.warning("New password cannot be empty.")
                elif len(new_password) < 8:
                    st.sidebar.warning("New password must be at least 8 characters.")
                elif new_password != confirm_password:
                    st.sidebar.warning("New password and confirm password must match.")
                else:
                    ok, detail = _update_logged_in_password(new_password)
                    if ok:
                        st.sidebar.success("✅ Password updated successfully.")
                        st.session_state["sidebar_show_change_password"] = False
                    else:
                        if is_admin_user(current_user):
                            st.sidebar.error(
                                "Password could not be updated. Please try again.\n"
                                f"{detail}"
                            )
                        else:
                            st.sidebar.error("Password could not be updated. Please try again.")

        st.sidebar.markdown("</div>", unsafe_allow_html=True)

    if page == "🧭 Navigation Guide":
        run_protected_page(page, navigation_guide_page)

    elif page == "Opportunity Center":
        run_protected_page(page, opportunity_center_page)

    elif page == "Scanner":
        run_protected_page(page, scanner_page)

    elif page == "Market Hub":
        run_protected_page(page, market_hub_page)

    elif page == "Research Stock":
        run_protected_page(page, research_stock_page)

    elif page == "Trade Command Center":
        run_protected_page(page, trade_command_center_page)

    elif page == "Options Center":
        run_protected_page(page, options_center_page)

    elif page == "Market Pulse":
        run_protected_page(page, market_pulse_page)

    elif page == "Economic Calendar":
        run_protected_page(page, economic_calendar_page)

    elif page == "Earnings Calendar":
        run_protected_page(page, earnings_calendar_page)

    elif page == "Automation Control Center":
        run_protected_page(page, automation_control_page)

    elif page == "OMS Execution":
        run_protected_page(page, oms_page)

    elif page == "Position Command Center":
        run_protected_page(page, position_command_center_page)

    elif page == "Manual Order Ticket":
        run_protected_page(page, order_ticket_page)

    elif page == "Portfolio":
        run_protected_page(page, portfolio_page)

    elif page == "Live IBKR":
        run_protected_page(page, live_ibkr_page)

    elif page == "Journal":
        run_protected_page(page, journal_page)

    elif page == "Database":
        run_protected_page(page, database_page)

    elif page == "Private Portfolio":
        run_protected_page(page, private_portfolio_page)

    elif page == "Crypto Pulse":
        run_protected_page(page, crypto_pulse_page)

    elif page == "Forex Pulse":
        run_protected_page(page, forex_pulse_page)

    elif page == "Gold Pulse":
        run_protected_page(page, gold_pulse_page)

    elif page == "Oil Pulse":
        run_protected_page(page, oil_pulse_page)

    elif page == "SaaS Core":
        run_protected_page(page, saas_core_page)

    elif page == "Admin Control Center":
        run_protected_page(page, admin_control_center_page)

    else:
        empty_page("Unknown Page")

    render_founder_feedback_footer(page)

    remember_active_page(page)


if __name__ == "__main__":
    app()
