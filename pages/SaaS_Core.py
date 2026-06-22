# =========================================================
# 🚢 JFBP QUANT DESK — SaaS CORE v1.3.4
# Supabase Auth + Admin Captain Pass + Verified Trial Workspace Provisioning
# Fix: do not run RLS-protected onboarding until a real auth session exists.
# =========================================================

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import streamlit as st

try:
    from supabase import create_client
except Exception:  # pragma: no cover
    create_client = None


# =========================================================
# PRODUCT PLANS
# =========================================================

PLAN_MARKET_PULSE = "MARKET_PULSE"
PLAN_PRO = "PRO"
PLAN_ELITE = "ELITE"

ACCOUNT_TRIAL = "TRIAL"
ACCOUNT_ACTIVE = "ACTIVE"
ACCOUNT_PAST_DUE = "PAST_DUE"
ACCOUNT_CANCELLED = "CANCELLED"
ACCOUNT_EXPIRED = "EXPIRED"
ACCOUNT_SUSPENDED = "SUSPENDED"

PLAN_LABELS = {
    PLAN_MARKET_PULSE: "Market Pulse",
    PLAN_PRO: "Quant Desk Pro",
    PLAN_ELITE: "Quant Desk Elite",
}

PLAN_PRICES = {
    PLAN_MARKET_PULSE: "$39/month",
    PLAN_PRO: "$99/month",
    PLAN_ELITE: "$199/month",
}

PLAN_PAGES = {
    PLAN_MARKET_PULSE: {
        "Market Pulse",
        "Scanner",
        "Research Stock",
        "Opportunity Center",
        "Economic Calendar",
        "Earnings Calendar",
    },
    PLAN_PRO: {
        "Market Pulse",
        "Scanner",
        "Research Stock",
        "Opportunity Center",
        "Economic Calendar",
        "Earnings Calendar",
        "Portfolio",
        "Private Portfolio",
        "Position Command Center",
        "Portfolio Analytics",
        "Journal",
        "Database",
        "Trade Command Center",
        "Options Center",
        "Navigation Guide",
        "User Guide Center",
    },
    PLAN_ELITE: {
        "Market Pulse",
        "Scanner",
        "Research Stock",
        "Opportunity Center",
        "Economic Calendar",
        "Earnings Calendar",
        "Portfolio",
        "Private Portfolio",
        "Position Command Center",
        "Portfolio Analytics",
        "Journal",
        "Database",
        "Trade Command Center",
        "Options Center",
        "Navigation Guide",
        "User Guide Center",
        "Quant Executor",
        "OMS Execution",
        "Live IBKR",
        "Automation Control Center",
        "Crypto Pulse",
        "Forex Pulse",
        "Gold Pulse",
        "Oil Pulse",
        "Telegram Alerts",
        "Signal Watcher",
        "Future AI Trading Models",
    },
}

PLAN_TRADING_MODE = {
    PLAN_MARKET_PULSE: "SIM ONLY",
    PLAN_PRO: "SIM + PAPER",
    PLAN_ELITE: "LIVE ENABLED",
}


# =========================================================
# DATA MODELS
# =========================================================

@dataclass
class SaaSUser:
    user_id: str
    email: str
    full_name: str
    plan: str
    account_status: str
    trial_start: datetime
    trial_end: datetime
    created_at: datetime
    source: str = "supabase"
    role: str = "user"


# =========================================================
# HELPERS
# =========================================================

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: Any, fallback: Optional[datetime] = None) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    if isinstance(value, str) and value.strip():
        try:
            cleaned = value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(cleaned)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except Exception:
            pass

    return fallback or _utc_now()




def _admin_email_set() -> set[str]:
    """Emails that receive founder/admin access.

    Configure in Streamlit Secrets as either:
    ADMIN_EMAILS = "jfbarao@icloud.com, another@email.com"

    The founder email is included as a safe fallback so the owner cannot be
    locked out while Stripe/admin roles are still being wired.
    """
    raw = str(st.secrets.get("ADMIN_EMAILS", "") or "")
    emails = {e.strip().lower() for e in raw.replace(";", ",").split(",") if e.strip()}
    emails.add("jfbarao@icloud.com")
    return emails


def is_admin_email(email: str) -> bool:
    return str(email or "").strip().lower() in _admin_email_set()


def is_admin_user(user: "SaaSUser | None") -> bool:
    if user is None:
        return False
    return str(getattr(user, "role", "user") or "user").upper() == "ADMIN" or is_admin_email(user.email)

def init_saas_state() -> None:
    st.session_state.setdefault("saas_logged_in", False)
    st.session_state.setdefault("saas_user", None)
    st.session_state.setdefault("saas_selected_plan", PLAN_MARKET_PULSE)
    st.session_state.setdefault("saas_admin_override", False)
    st.session_state.setdefault("saas_auth_session", None)
    st.session_state.setdefault("saas_auth_last_message", "")
    st.session_state.setdefault("saas_onboarding_ready", False)
    st.session_state.setdefault("saas_onboarding_debug", {})


# =========================================================
# SUPABASE CLIENT
# =========================================================

@st.cache_resource(show_spinner=False)
def get_supabase_client():
    if create_client is None:
        return None

    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_ANON_KEY", "")

    if not url or not key:
        return None

    try:
        return create_client(url, key)
    except Exception:
        return None


def supabase_ready() -> tuple[bool, str]:
    if create_client is None:
        return False, "Python package `supabase` is not installed. Add `supabase` to requirements.txt."

    if not st.secrets.get("SUPABASE_URL", ""):
        return False, "Missing SUPABASE_URL in streamlit/secrets.toml."

    if not st.secrets.get("SUPABASE_ANON_KEY", ""):
        return False, "Missing SUPABASE_ANON_KEY in streamlit/secrets.toml."

    if get_supabase_client() is None:
        return False, "Could not create Supabase client. Check URL and publishable key."

    return True, "Supabase client ready."


def _response_data(response: Any) -> list:
    data = getattr(response, "data", None)
    if data is None:
        return []
    return data if isinstance(data, list) else [data]


def _get_session_tokens(session: Any) -> tuple[str, str]:
    if session is None:
        return "", ""

    access_token = str(getattr(session, "access_token", "") or "").strip()
    refresh_token = str(getattr(session, "refresh_token", "") or "").strip()

    if isinstance(session, dict):
        access_token = str(session.get("access_token", access_token) or "").strip()
        refresh_token = str(session.get("refresh_token", refresh_token) or "").strip()

    return access_token, refresh_token


def _auth_response_session(auth_response: Any) -> Any:
    try:
        return getattr(auth_response, "session", None)
    except Exception:
        return None


def _auth_response_user(auth_response: Any) -> Any:
    try:
        user = getattr(auth_response, "user", None)
        session = _auth_response_session(auth_response)
        if user is None and session is not None:
            user = getattr(session, "user", None)
        return user
    except Exception:
        return None


def _apply_auth_session_to_client(client: Any, session: Any) -> bool:
    """Attach the authenticated user's JWT to the Supabase client.

    RLS policies use auth.uid() = user_id, so writes must happen with a real
    authenticated session. If signup returns no session, onboarding must wait
    until the user logs in.
    """
    access_token, refresh_token = _get_session_tokens(session)
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


def _verified_user_row(client: Any, table_name: str, user_id: str) -> list:
    response = (
        client.table(table_name)
        .select("*")
        .eq("user_id", user_id)
        .limit(5)
        .execute()
    )
    return _response_data(response)


def _create_profile_record(
    client: Any,
    user_id: str,
    email: str,
    full_name: str,
    plan: str,
    account_status: str,
    trial_start: datetime,
    trial_end: datetime,
) -> list:
    existing = _verified_user_row(client, "user_profiles", user_id)
    if existing:
        return existing

    client.table("user_profiles").insert(
        {
            "user_id": user_id,
            "email": email.strip().lower(),
            "full_name": full_name.strip() or "JFBP User",
            "plan": plan,
            "account_status": account_status,
            "trial_start": trial_start.isoformat(),
            "trial_end": trial_end.isoformat(),
        }
    ).execute()

    return _verified_user_row(client, "user_profiles", user_id)


def _create_subscription_record(client: Any, user_id: str, plan: str, status: str) -> list:
    existing = _verified_user_row(client, "subscriptions", user_id)
    if existing:
        return existing

    client.table("subscriptions").insert(
        {
            "user_id": user_id,
            "plan": plan,
            "status": status,
        }
    ).execute()

    return _verified_user_row(client, "subscriptions", user_id)


def _create_workspace_record(client: Any, user_id: str, workspace_name: str = "Personal Workspace") -> list:
    existing = _verified_user_row(client, "workspaces", user_id)
    if existing:
        return existing

    client.table("workspaces").insert(
        {
            "user_id": user_id,
            "workspace_name": workspace_name,
        }
    ).execute()

    return _verified_user_row(client, "workspaces", user_id)


def ensure_user_workspace_records(
    auth_user: Any,
    selected_plan: str | None = None,
    auth_session: Any = None,
) -> tuple[bool, str]:
    """Create and verify SaaS database rows for the authenticated user."""
    ready, message = supabase_ready()
    if not ready:
        st.session_state["saas_onboarding_debug"] = {"ready": False, "message": message}
        return False, message

    client = get_supabase_client()
    if client is None:
        return False, "Supabase client unavailable."

    session_applied = _apply_auth_session_to_client(client, auth_session)

    user_id = _auth_user_id(auth_user)
    email = _auth_user_email(auth_user)
    meta = _user_metadata(auth_user)

    debug: Dict[str, Any] = {
        "user_id": user_id,
        "email": email,
        "session_applied_to_client": session_applied,
        "supabase_url": st.secrets.get("SUPABASE_URL", "NOT FOUND"),
    }

    if not user_id:
        debug["error"] = "missing_user_id"
        st.session_state["saas_onboarding_debug"] = debug
        return False, "User ID missing. Cannot create SaaS workspace records."

    if not session_applied:
        debug["error"] = "missing_authenticated_session"
        st.session_state["saas_onboarding_debug"] = debug
        return (
            False,
            "Onboarding paused: Supabase did not return an authenticated session yet. "
            "Please verify the email if required, then log in to finish creating profile, subscription, and workspace records.",
        )

    now = _utc_now()
    full_name = str(meta.get("full_name") or meta.get("name") or "JFBP User")
    plan = str(meta.get("plan") or selected_plan or PLAN_MARKET_PULSE)
    account_status = str(meta.get("account_status") or ACCOUNT_TRIAL)
    trial_start = _parse_dt(meta.get("trial_start"), fallback=now)
    trial_end = _parse_dt(meta.get("trial_end"), fallback=trial_start + timedelta(days=30))

    debug.update(
        {
            "plan": plan,
            "account_status": account_status,
        }
    )

    try:
        profile_rows = _create_profile_record(
            client=client,
            user_id=user_id,
            email=email,
            full_name=full_name,
            plan=plan,
            account_status=account_status,
            trial_start=trial_start,
            trial_end=trial_end,
        )
        subscription_rows = _create_subscription_record(
            client=client,
            user_id=user_id,
            plan=plan,
            status=account_status,
        )
        workspace_rows = _create_workspace_record(
            client=client,
            user_id=user_id,
            workspace_name=f"{full_name.strip() or 'Personal'} Workspace",
        )

        debug.update(
            {
                "user_profiles_rows": len(profile_rows),
                "subscriptions_rows": len(subscription_rows),
                "workspaces_rows": len(workspace_rows),
            }
        )
        st.session_state["saas_onboarding_debug"] = debug

        if not profile_rows or not subscription_rows or not workspace_rows:
            return (
                False,
                "Onboarding incomplete. Auth works, but one or more database rows could not be verified. "
                "Check RLS policies and the active Supabase session.",
            )

        return True, "Profile, subscription, and workspace records are verified."

    except Exception as exc:
        debug["error"] = str(exc)
        st.session_state["saas_onboarding_debug"] = debug
        return False, f"Workspace record creation failed: {exc}"


# =========================================================
# AUTH NORMALIZATION
# =========================================================

def _user_metadata(auth_user: Any) -> dict:
    try:
        meta = getattr(auth_user, "user_metadata", None) or {}
    except Exception:
        meta = {}
    return meta if isinstance(meta, dict) else {}


def _auth_user_email(auth_user: Any) -> str:
    try:
        return str(getattr(auth_user, "email", "") or getattr(auth_user, "user_email", "") or "").strip().lower()
    except Exception:
        return ""


def _auth_user_id(auth_user: Any) -> str:
    try:
        return str(getattr(auth_user, "id", "") or getattr(auth_user, "user_id", "") or "").strip()
    except Exception:
        return ""


def build_saas_user_from_auth(auth_user: Any, selected_plan: str | None = None) -> SaaSUser:
    meta = _user_metadata(auth_user)
    now = _utc_now()

    email = _auth_user_email(auth_user)
    full_name = meta.get("full_name") or meta.get("name") or "JFBP User"
    role = str(meta.get("role") or "user").strip().lower()
    plan = meta.get("plan") or selected_plan or st.session_state.get("saas_selected_plan") or PLAN_MARKET_PULSE
    account_status = str(meta.get("account_status") or ACCOUNT_TRIAL)

    # Founder/Admin pass: the captain must never be blocked by trials, plan
    # limits, or Stripe while the SaaS engine is under construction.
    if is_admin_email(email) or role == "admin":
        role = "admin"
        plan = PLAN_ELITE
        account_status = ACCOUNT_ACTIVE

    trial_start = _parse_dt(meta.get("trial_start"), fallback=now)
    trial_end = _parse_dt(meta.get("trial_end"), fallback=trial_start + timedelta(days=3650) if role == "admin" else trial_start + timedelta(days=30))

    return SaaSUser(
        user_id=_auth_user_id(auth_user),
        email=email,
        full_name=str(full_name),
        plan=str(plan),
        account_status=str(account_status),
        trial_start=trial_start,
        trial_end=trial_end,
        created_at=_parse_dt(getattr(auth_user, "created_at", None), fallback=now),
        source="supabase",
        role=role,
    )


def set_authenticated_session(auth_response: Any, selected_plan: str | None = None) -> bool:
    """Store a real logged-in session and run onboarding.

    v1.3.2 fix: signup responses may contain a user but no session when email
    confirmation is required. In that case we must NOT mark the user as logged
    in and must NOT attempt RLS-protected inserts.
    """
    try:
        session = _auth_response_session(auth_response)
        user = _auth_response_user(auth_response)

        if user is None:
            return False

        access_token, _ = _get_session_tokens(session)
        if not access_token:
            st.session_state["saas_logged_in"] = False
            st.session_state["saas_user"] = None
            st.session_state["saas_auth_session"] = None
            st.session_state["saas_onboarding_ready"] = False
            st.session_state["saas_auth_last_message"] = (
                "Account exists, but Supabase has not returned an authenticated session yet. "
                "Please verify the email if required, then log in."
            )
            st.session_state["saas_onboarding_debug"] = {
                "user_id": _auth_user_id(user),
                "email": _auth_user_email(user),
                "session_applied_to_client": False,
                "error": "no_session_returned_by_supabase",
            }
            return False

        st.session_state["saas_auth_session"] = session
        st.session_state["saas_user"] = build_saas_user_from_auth(user, selected_plan=selected_plan)
        st.session_state["saas_logged_in"] = True

        onboarding_ok, onboarding_message = ensure_user_workspace_records(
            user,
            selected_plan=selected_plan,
            auth_session=session,
        )
        st.session_state["saas_auth_last_message"] = onboarding_message
        st.session_state["saas_onboarding_ready"] = onboarding_ok
        return True

    except Exception as exc:
        st.session_state["saas_auth_last_message"] = f"Session setup failed: {exc}"
        return False


def clear_authenticated_session() -> None:
    st.session_state["saas_logged_in"] = False
    st.session_state["saas_user"] = None
    st.session_state["saas_auth_session"] = None
    st.session_state["saas_onboarding_ready"] = False
    st.session_state["saas_onboarding_debug"] = {}


# =========================================================
# AUTH ACTIONS
# =========================================================

def supabase_sign_up(email: str, password: str, full_name: str, plan: str) -> tuple[bool, str]:
    ready, message = supabase_ready()
    if not ready:
        return False, message

    client = get_supabase_client()
    now = _utc_now()
    trial_end = now + timedelta(days=30)
    clean_email = email.strip().lower()

    try:
        response = client.auth.sign_up(
            {
                "email": clean_email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name.strip() or "JFBP User",
                        "plan": plan,
                        "account_status": ACCOUNT_TRIAL,
                        "trial_start": now.isoformat(),
                        "trial_end": trial_end.isoformat(),
                    }
                },
            }
        )

        # If Supabase returns a real authenticated session, finish onboarding now.
        if set_authenticated_session(response, selected_plan=plan):
            return True, "Account created. 30-day trial and workspace are ready."

        # Supabase may intentionally return a generic success response when an
        # email already exists. Try a login with the supplied password. If it
        # succeeds, treat this as an existing account and finish onboarding.
        try:
            login_response = client.auth.sign_in_with_password(
                {"email": clean_email, "password": password}
            )
            if set_authenticated_session(login_response, selected_plan=plan):
                return True, "This email already has an account. Logged in and verified workspace records."
        except Exception:
            pass

        # No active session and immediate login failed. Do not say the account
        # was definitely created, because Supabase may be protecting an existing
        # email address from account enumeration.
        return (
            False,
            "Account not completed. This email may already be registered, or it may need email verification. "
            "Try Login first, or use Reset Password if this email is already on file.",
        )

    except Exception as exc:
        error_text = str(exc)
        lowered = error_text.lower()
        if "already" in lowered or "registered" in lowered or "exists" in lowered:
            return False, "This email is already on file. Please use Login or Reset Password."
        return False, f"Sign up failed: {exc}"


def supabase_login(email: str, password: str) -> tuple[bool, str]:
    ready, message = supabase_ready()
    if not ready:
        return False, message

    client = get_supabase_client()

    try:
        response = client.auth.sign_in_with_password(
            {
                "email": email.strip().lower(),
                "password": password,
            }
        )

        if set_authenticated_session(response):
            onboarding_message = st.session_state.get("saas_auth_last_message", "")
            if st.session_state.get("saas_onboarding_ready", False):
                return True, "Login successful. " + onboarding_message
            return True, "Login successful. " + onboarding_message

        return False, "Login failed. No authenticated user session returned."

    except Exception as exc:
        return False, f"Login failed: {exc}"


def supabase_logout() -> tuple[bool, str]:
    client = get_supabase_client()
    try:
        if client is not None:
            client.auth.sign_out()
    except Exception:
        pass

    clear_authenticated_session()
    return True, "Logged out."


def supabase_reset_password(email: str) -> tuple[bool, str]:
    ready, message = supabase_ready()
    if not ready:
        return False, message

    client = get_supabase_client()

    try:
        client.auth.reset_password_email(email.strip().lower())
        return True, "Password reset email sent."
    except Exception as exc:
        return False, f"Password reset failed: {exc}"


# =========================================================
# ACCESS CONTROL
# =========================================================

def get_current_user() -> SaaSUser | None:
    user = st.session_state.get("saas_user")
    return user if isinstance(user, SaaSUser) else None


def trial_days_remaining(user: SaaSUser) -> int:
    remaining = user.trial_end - _utc_now()
    return max(0, remaining.days)


def is_account_open(user: SaaSUser) -> bool:
    if is_admin_user(user):
        return True

    if user.account_status in {ACCOUNT_SUSPENDED, ACCOUNT_EXPIRED, ACCOUNT_PAST_DUE}:
        return False

    if user.account_status == ACCOUNT_TRIAL and _utc_now() > user.trial_end:
        return False

    return user.account_status in {ACCOUNT_TRIAL, ACCOUNT_ACTIVE, ACCOUNT_CANCELLED}


def can_access_page(user: SaaSUser, page_name: str) -> bool:
    if is_admin_user(user):
        return True

    if st.session_state.get("saas_admin_override", False):
        return True

    if not is_account_open(user):
        return False

    return page_name in PLAN_PAGES.get(user.plan, set())


def require_page_access(page_name: str) -> bool:
    user = get_current_user()

    if user is None:
        render_login_required(page_name)
        return False

    if not is_account_open(user):
        render_account_locked(user)
        return False

    if not can_access_page(user, page_name):
        render_upgrade_required(user, page_name)
        return False

    return True


# =========================================================
# UI
# =========================================================

def inject_saas_css() -> None:
    st.markdown(
        """
        <style>
            .saas-hero {border:1px solid #bfdbfe;background:linear-gradient(135deg,#eff6ff,#ffffff);border-radius:22px;padding:1.25rem 1.35rem;margin:0.75rem 0 1rem 0;}
            .saas-kicker {font-size:0.72rem;text-transform:uppercase;letter-spacing:0.08em;color:#64748b;font-weight:950;margin-bottom:0.3rem;}
            .saas-title {font-size:clamp(1.8rem,4vw,2.8rem);line-height:1.04;font-weight:1000;color:#0f172a;margin-bottom:0.55rem;}
            .saas-text {font-size:1rem;line-height:1.45;color:#334155;font-weight:750;}
            .saas-card-grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,230px),1fr));gap:0.85rem;margin:0.7rem 0 1rem 0;}
            .saas-card {border:1px solid #dbe3ef;border-radius:16px;background:#f8fafc;padding:0.9rem 1rem;min-height:105px;}
            .saas-label {font-size:0.72rem;color:#64748b;letter-spacing:0.05em;text-transform:uppercase;font-weight:900;margin-bottom:0.35rem;}
            .saas-value {font-size:1.35rem;line-height:1.12;color:#111827;font-weight:950;overflow-wrap:anywhere;}
            .saas-detail {margin-top:0.35rem;color:#475569;font-size:0.82rem;line-height:1.35;}
            .saas-lock {border:1px solid #fecaca;background:#fef2f2;border-radius:18px;padding:1rem;margin:1rem 0;}
            .saas-upgrade {border:1px solid #fde68a;background:#fffbeb;border-radius:18px;padding:1rem;margin:1rem 0;}
            .saas-ok {border:1px solid #bbf7d0;background:#ecfdf5;border-radius:18px;padding:0.85rem 1rem;margin:0.75rem 0;color:#166534;font-weight:850;}
            .saas-warn {border:1px solid #fde68a;background:#fffbeb;border-radius:18px;padding:0.85rem 1rem;margin:0.75rem 0;color:#92400e;font-weight:850;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def card(label: str, value: str, detail: str = "") -> str:
    return (
        '<div class="saas-card">'
        f'<div class="saas-label">{label}</div>'
        f'<div class="saas-value">{value}</div>'
        f'<div class="saas-detail">{detail}</div>'
        '</div>'
    )


def render_login_required(page_name: str) -> None:
    inject_saas_css()
    st.markdown(
        f'<div class="saas-lock"><strong>Login required.</strong><br>Please sign in to access <strong>{page_name}</strong>.</div>',
        unsafe_allow_html=True,
    )


def render_account_locked(user: SaaSUser) -> None:
    inject_saas_css()
    st.markdown(
        f'<div class="saas-lock"><strong>Account locked.</strong><br>Status: <strong>{user.account_status}</strong><br>Please update your subscription to continue.</div>',
        unsafe_allow_html=True,
    )


def render_upgrade_required(user: SaaSUser, page_name: str) -> None:
    inject_saas_css()
    st.markdown(
        f'<div class="saas-upgrade"><strong>Upgrade required.</strong><br>Your current plan is <strong>{PLAN_LABELS.get(user.plan, user.plan)}</strong>.<br><strong>{page_name}</strong> is not included in your current subscription.</div>',
        unsafe_allow_html=True,
    )


def render_auth_status() -> None:
    ready, message = supabase_ready()
    css = "saas-ok" if ready else "saas-warn"
    label = "Supabase Ready" if ready else "Supabase Not Ready"
    st.markdown(f'<div class="{css}"><strong>{label}</strong><br>{message}</div>', unsafe_allow_html=True)


def render_auth_panel() -> None:
    st.subheader("🔐 Supabase Authentication")
    st.caption("Real account creation and login. Subscription status is still local until Stripe wiring.")
    render_auth_status()

    mode = st.radio("Choose action", ["Login", "Create Account", "Reset Password"], horizontal=True)

    if mode == "Login":
        with st.form("saas_login_form"):
            email = st.text_input("Email", value="")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            ok, message = supabase_login(email=email, password=password)
            if ok:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    elif mode == "Create Account":
        with st.form("saas_signup_form"):
            email = st.text_input("Email", value="")
            full_name = st.text_input("Full Name", value="")
            password = st.text_input("Password", type="password")
            password_confirm = st.text_input("Confirm Password", type="password")
            plan = st.selectbox(
                "Plan",
                options=[PLAN_MARKET_PULSE, PLAN_PRO, PLAN_ELITE],
                format_func=lambda p: f"{PLAN_LABELS[p]} — {PLAN_PRICES[p]}",
                index=0,
            )
            st.success("🚀 Start your 30-Day Free Trial today. No credit card required.")

            submitted = st.form_submit_button("Create Free Account & Start Trial", use_container_width=True)

        if submitted:
            if not email or "@" not in email:
                st.error("Enter a valid email.")
            elif len(password or "") < 8:
                st.error("Password must be at least 8 characters.")
            elif password != password_confirm:
                st.error("Passwords do not match.")
            else:
                ok, message = supabase_sign_up(email=email, password=password, full_name=full_name, plan=plan)
                if ok:
                    st.success(message)
                    if st.session_state.get("saas_logged_in", False):
                        st.rerun()
                else:
                    st.error(message)

    else:
        with st.form("saas_reset_form"):
            email = st.text_input("Email", value="")
            submitted = st.form_submit_button("Send Password Reset Email", use_container_width=True)

        if submitted:
            if not email or "@" not in email:
                st.error("Enter a valid email.")
            else:
                ok, message = supabase_reset_password(email=email)
                if ok:
                    st.success(message)
                else:
                    st.error(message)


def render_user_status(user: SaaSUser) -> None:
    days_left = trial_days_remaining(user)
    role_label = "Admin / Founder" if is_admin_user(user) else "User"
    cards = [
        card("User", user.email, user.full_name),
        card("Role", role_label, "Full platform access" if is_admin_user(user) else "Plan-based access"),
        card("Plan", PLAN_LABELS.get(user.plan, user.plan), PLAN_PRICES.get(user.plan, "")),
        card("Account Status", user.account_status, "Lifetime admin access" if is_admin_user(user) else f"Trial days remaining: {days_left}"),
        card("Trading Mode", PLAN_TRADING_MODE.get(user.plan, "N/A"), "Controlled by subscription plan"),
    ]
    st.markdown('<div class="saas-card-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)


def render_permissions_matrix(user: SaaSUser) -> None:
    st.subheader("🧭 Page Permission Matrix")
    all_pages = sorted(set().union(*PLAN_PAGES.values()))
    rows: List[Dict[str, str]] = []
    for page in all_pages:
        rows.append({"Page": page, "Allowed": "YES" if can_access_page(user, page) else "NO", "Current Plan": PLAN_LABELS.get(user.plan, user.plan)})
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_saas_core_dashboard() -> None:
    init_saas_state()
    inject_saas_css()

    st.markdown(
        """
        <div class="saas-hero">
            <div class="saas-kicker">JFBP Quant Desk · SaaS Core v1.3.3</div>
            <div class="saas-title">Supabase Auth & User Workspace Control</div>
            <div class="saas-text">Real authentication foundation for user sign up, login, password reset, trial control, plan permissions, and private-user access rules.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    user = get_current_user()
    if user is None:
        render_auth_panel()
        return

    top_left, top_right = st.columns([0.72, 0.28], gap="large")
    with top_left:
        render_user_status(user)
    with top_right:
        st.subheader("Session Controls")
        st.toggle("Admin Override", key="saas_admin_override")
        if st.button("Logout", use_container_width=True):
            ok, message = supabase_logout()
            st.success(message)
            st.rerun()

    st.divider()
    tabs = st.tabs(["Permissions", "Access Tests", "Auth Session", "Next Wiring"])

    with tabs[0]:
        render_permissions_matrix(user)

    with tabs[1]:
        st.subheader("🔎 Test Page Access")
        test_page = st.selectbox("Choose a page to test", options=sorted(set().union(*PLAN_PAGES.values())))
        if can_access_page(user, test_page):
            st.success(f"Access granted: {test_page}")
        else:
            st.warning(f"Access denied: {test_page}")

    with tabs[2]:
        st.subheader("🔐 Auth Session Snapshot")
        st.caption("Safe operational view. Secret tokens are not displayed.")
        st.json(
            {
                "logged_in": bool(st.session_state.get("saas_logged_in")),
                "user_id": user.user_id,
                "email": user.email,
                "source": user.source,
                "role": user.role,
                "admin_access": is_admin_user(user),
                "plan": user.plan,
                "account_status": user.account_status,
                "trial_start": user.trial_start.isoformat(),
                "trial_end": user.trial_end.isoformat(),
                "onboarding_records_ready": bool(st.session_state.get("saas_onboarding_ready", False)),
                "onboarding_message": st.session_state.get("saas_auth_last_message", ""),
                "onboarding_debug": st.session_state.get("saas_onboarding_debug", {}),
            }
        )

    with tabs[3]:
        st.subheader("⚙ Next Wiring Steps")

        st.markdown("### Database Verification")
        if st.button("Verify my SaaS onboarding rows", use_container_width=True):
            session = st.session_state.get("saas_auth_session")
            auth_user = getattr(session, "user", None) if session is not None else None
            if auth_user is None:
                auth_user = user

            ok, message = ensure_user_workspace_records(
                auth_user=auth_user,
                selected_plan=user.plan,
                auth_session=session,
            )
            st.session_state["saas_onboarding_ready"] = ok
            st.session_state["saas_auth_last_message"] = message
            if ok:
                st.success(message)
            else:
                st.error(message)
            st.json(st.session_state.get("saas_onboarding_debug", {}))

        st.markdown(
            """
            **Current pass: SaaS Core v1.3.2 Automated Onboarding**

            1. Supabase Auth creates the user account. ✅
            2. If Supabase returns a real session, onboarding rows are created immediately. ✅
            3. If email verification delays the session, onboarding waits until login. ✅
            4. `user_profiles`, `subscriptions`, and `workspaces` rows are verified after write. ✅
            5. RLS policies keep user-owned rows private. ✅

            **Next development pass: SaaS Core v1.4 Stripe + Website Login**

            1. Connect Stripe checkout and billing portal.
            2. Use Stripe webhooks to update subscription status.
            3. Move public signup/login to the website.
            4. Hide SaaS Core as an admin-only control room.
            5. Move Portfolio, Journal, Watchlists, and Settings into user-owned tables.
            """
        )


def run_page() -> None:
    render_saas_core_dashboard()


def page() -> None:
    run_page()
