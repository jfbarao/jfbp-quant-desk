# =========================================================
# 🚢 JFBP QUANT DESK — SaaS CORE v1.4.5
# Supabase Auth + Admin Captain Pass + Verified Trial Workspace Provisioning
# Fix: do not run RLS-protected onboarding until a real auth session exists.
# =========================================================

from __future__ import annotations

import base64
import hmac
import hashlib
import json
import logging
import os
import smtplib
import re
import time
import uuid
from urllib.parse import urlparse
from types import SimpleNamespace

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

from core.canonical_schema import canonical_supports_column, filter_canonical_payload
from core.environment_validation import (
    build_runtime_config_from_secrets,
    default_password_reset_redirect_for_env,
    default_signup_redirect_for_env,
    validate_runtime_environment,
)
from core.session_store import (
    SessionCreationInput,
    SessionLookupStatus,
    SessionStore,
    SessionStoreError,
)
from core.responsive import inject_responsive_css
from core.ui_cards import inject_card_css

try:
    import stripe
    STRIPE_IMPORT_ERROR = None
except ImportError as exc:  # pragma: no cover
    stripe = None
    STRIPE_IMPORT_ERROR = exc

try:
    from supabase import create_client
except Exception:  # pragma: no cover
    create_client = None

try:
    import extra_streamlit_components as stx
except Exception:  # pragma: no cover
    stx = None


# =========================================================
# PRODUCT PLANS
# =========================================================

PLAN_MARKET_PULSE = "MARKET_PULSE"
PLAN_PRO = "PRO"
PLAN_ELITE = "ELITE"
TRIAL_LENGTH_DAYS = 30

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

# =========================================================
# STRIPE CHECKOUT CONFIG
# =========================================================
# Checkout is created dynamically from Stripe Price IDs.
# Required Streamlit Secrets:
# STRIPE_SECRET_KEY = "sk_live_..."
# MARKET_PULSE_PRICE_ID = "price_..."
# PRO_PRICE_ID = "price_..."
# ELITE_PRICE_ID = "price_..."
# Optional:
# STRIPE_SUCCESS_URL = "https://jfbp-quant-desk.streamlit.app/?checkout=success"
# STRIPE_CANCEL_URL = "https://jfbp-quant-desk.streamlit.app/?checkout=cancelled"

STRIPE_PRICE_SECRET_KEYS = {
    PLAN_MARKET_PULSE: "MARKET_PULSE_PRICE_ID",
    PLAN_PRO: "PRO_PRICE_ID",
    PLAN_ELITE: "ELITE_PRICE_ID",
}

PLAN_RANK = {
    PLAN_MARKET_PULSE: 1,
    PLAN_PRO: 2,
    PLAN_ELITE: 3,
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

# Canonical human-facing Elite feature bullets used across upgrade surfaces.
ELITE_FEATURE_BULLETS: tuple[str, ...] = (
    "Everything in Pro + live execution suite",
    "Quant Executor, OMS Execution, Live IBKR",
    "Automation Control Center",
    "Crypto, Forex, Gold, and Oil Pulse",
    "Telegram Alerts + Signal Watcher",
)

ELITE_FEATURE_MARKDOWN = "\n".join(
    f"✓ {feature}  " for feature in ELITE_FEATURE_BULLETS
)

TRIAL_RISK_LOW = "LOW"
TRIAL_RISK_MEDIUM = "MEDIUM"
TRIAL_RISK_HIGH = "HIGH"

DISPOSABLE_EMAIL_DOMAINS = {
    "10minutemail.com",
    "guerrillamail.com",
    "mailinator.com",
    "tempmail.com",
    "temp-mail.org",
    "yopmail.com",
}

# Temporary launch hardening flag for auth/metadata diagnostics.
AUTH_DEBUG = False
RESET_PASSWORD_BACKOFF_STEPS = (15, 30, 60)
RESET_PASSWORD_RATE_LIMIT_MESSAGE = "Too many password reset requests. Please wait before trying again."
SIGNUP_RATE_LIMIT_MESSAGE = (
    "Too many verification emails have been requested recently. "
    "Please wait a little while before trying again."
)
SIGNUP_GENERIC_FAILURE_MESSAGE = "Sign up failed. Please try again."
FOUNDER_TRIAL_EMAIL = "support@jfbpquantdesk.com"
FOUNDER_TRIAL_SUBJECT = "New JFBP Quant Desk trial started"

SESSION_COOKIE_NAME = "opaque_session_handle"
SESSION_COOKIE_VERSION = "v1"
SESSION_COOKIE_SIGNATURE_SEP = "."
COOKIE_READINESS_NOT_READY = "COOKIE_NOT_READY"
COOKIE_READINESS_ABSENT = "COOKIE_ABSENT"
COOKIE_READINESS_PRESENT = "COOKIE_PRESENT"
COOKIE_READINESS_STATE_KEY = "saas_cookie_readiness_state"
COOKIE_READINESS_ATTEMPTS_KEY = "saas_cookie_readiness_attempts"

PHASE10B_REDIRECT_DIAGNOSTIC_PREFIX = "PHASE10B_REDIRECT_DIAGNOSTIC"
PHASE10B_REDIRECT_DIAGNOSTIC_REACHABLE = "PHASE10B_REDIRECT_DIAGNOSTIC_REACHABLE"
PRODUCTION_AUTH_TRACE_PREFIX = "PRODUCTION_AUTH_TRACE"

logger = logging.getLogger(__name__)

_PHASE10B_REACHABILITY_EMITTED = False


def _trace_exception_fields(exc: Exception | None) -> Dict[str, str]:
    if exc is None:
        return {
            "exception_class": "",
            "exception_message": "",
        }

    message = " ".join(str(exc).split())[:240]
    return {
        "exception_class": exc.__class__.__name__,
        "exception_message": message,
    }


def _trace_value(value: Any) -> Any:
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    if isinstance(value, str):
        return " ".join(value.split())[:240]
    return str(type(value).__name__)


def _new_auth_attempt_id() -> str:
    attempt_id = uuid.uuid4().hex
    st.session_state["saas_auth_attempt_id"] = attempt_id
    st.session_state["saas_auth_attempt_started_at"] = datetime.now(timezone.utc).isoformat()
    return attempt_id


def _current_auth_attempt_id() -> str:
    return str(st.session_state.get("saas_auth_attempt_id", "") or "").strip()


def production_auth_trace(stage: str, source_function: str, *, exc: Exception | None = None, **metadata: Any) -> None:
    payload: Dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "stage": str(stage or "UNKNOWN"),
        "source_function": str(source_function or "UNKNOWN"),
        "attempt_id": _current_auth_attempt_id(),
    }

    payload.update(_trace_exception_fields(exc))

    safe_metadata = {str(key): _trace_value(value) for key, value in metadata.items()}
    payload.update(safe_metadata)

    line = f"{PRODUCTION_AUTH_TRACE_PREFIX} {json.dumps(payload, sort_keys=True)}"
    print(line, flush=True)
    logger.info("%s", line)


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
    subscription_status: str = ""
    provisioning_required: bool = False


@dataclass(frozen=True)
class CookieReadResult:
    state: str
    value: str = ""


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





def _secret_value(name: str, default: str = "") -> str:
    """Read a secret safely from Streamlit Secrets, then environment variables.

    This avoids false negatives when Streamlit Cloud exposes secrets differently
    and keeps secret values out of the UI.
    """
    value = ""
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""

    if value is None or str(value).strip() == "":
        value = os.environ.get(name, default)

    return str(value or default).strip()


def _classify_redirect_value(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "EMPTY"

    try:
        parsed = urlparse(raw)
    except Exception:
        return "EMPTY"

    host = str(parsed.hostname or "").strip().lower()
    if not host:
        return "EMPTY"
    if host == "www.jfbpquantdesk.com":
        return "MARKETING_HOST_WWW"
    if host == "jfbpquantdesk.com":
        return "MARKETING_HOST_NON_WWW"
    if host == "streamlit.app" or host.endswith(".streamlit.app"):
        return "STREAMLIT_HOST"
    if str(parsed.scheme or "").strip().lower() == "https":
        return "OTHER_HTTPS_HOST"
    return "EMPTY"


def _phase10b_redirect_diagnostic_enabled() -> bool:
    flag = str(_secret_value("PHASE10B_REDIRECT_DIAGNOSTIC", "") or "").strip().lower()
    return flag in {"1", "true", "yes", "on"}


def _runtime_commit_hash() -> str:
    candidate_keys = (
        "STREAMLIT_GIT_COMMIT",
        "STREAMLIT_GIT_HASH",
        "GIT_COMMIT",
        "COMMIT_SHA",
        "SOURCE_COMMIT",
        "SOURCE_VERSION",
        "RENDER_GIT_COMMIT",
    )
    for key in candidate_keys:
        value = str(os.environ.get(key, "") or "").strip()
        if not value:
            continue
        compact = value.lower()
        if 7 <= len(compact) <= 64 and all(ch in "0123456789abcdef" for ch in compact):
            return compact
        return "NON_HEX"
    return "UNAVAILABLE"


def _runtime_app_hostname() -> str:
    candidate_keys = (
        "STREAMLIT_APP_URL",
        "APP_URL",
        "SITE_URL",
        "HOSTNAME",
        "HOST",
    )
    for key in candidate_keys:
        value = str(os.environ.get(key, "") or "").strip()
        if not value:
            continue
        parsed = urlparse(value)
        host = str(parsed.hostname or "").strip().lower()
        if host:
            return host
        if "/" not in value and ":" not in value and " " not in value:
            return value.lower()
    return "UNAVAILABLE"


def _log_phase10b_redirect_diagnostic(event: str, payload: Dict[str, Any]) -> None:
    if not _phase10b_redirect_diagnostic_enabled():
        return
    safe_payload = {
        "event": str(event or "").strip() or "UNKNOWN",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    line = f"{PHASE10B_REDIRECT_DIAGNOSTIC_PREFIX} {json.dumps(safe_payload, sort_keys=True)}"
    print(line, flush=True)
    logger.info("%s", line)


def _emit_phase10b_reachability_marker_once() -> None:
    global _PHASE10B_REACHABILITY_EMITTED

    if _PHASE10B_REACHABILITY_EMITTED:
        return
    if not _phase10b_redirect_diagnostic_enabled():
        return

    marker_payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "commit_hash": _runtime_commit_hash(),
        "app_hostname": _runtime_app_hostname(),
    }
    line = f"{PHASE10B_REDIRECT_DIAGNOSTIC_REACHABLE} {json.dumps(marker_payload, sort_keys=True)}"
    print(line, flush=True)
    logger.info("%s", line)
    _PHASE10B_REACHABILITY_EMITTED = True


def _resolve_secret_value_with_source(name: str, default: str = "") -> Dict[str, Any]:
    secret_exists = False
    secret_value = ""
    try:
        secret_exists = name in st.secrets
        secret_value = str(st.secrets.get(name, "") or "")
    except Exception:
        secret_exists = False
        secret_value = ""

    env_exists = name in os.environ
    env_value = str(os.environ.get(name, "") or "")

    selected_value = str(default or "")
    selected_source = "FALLBACK"

    if secret_value.strip():
        selected_value = secret_value
        selected_source = "ST_SECRETS"
    elif env_value.strip():
        selected_value = env_value
        selected_source = "ENVIRONMENT"

    return {
        "value": str(selected_value or "").strip(),
        "selected_source": selected_source,
        "secret_exists": bool(secret_exists),
        "environment_exists": bool(env_exists),
    }


def _secret_status(name: str) -> str:
    """Return safe diagnostics without exposing the secret value."""
    value = _secret_value(name, "")
    if not value:
        return "MISSING"
    return f"FOUND len={len(value)} prefix={value[:3]}..."


def _session_signing_key() -> bytes:
    raw = _secret_value("SESSION_COOKIE_SIGNING_KEY", "")
    if not raw:
        raw = _secret_value("SESSION_ENCRYPTION_KEY", "")
    if not raw:
        raise SessionStoreError("Missing SESSION_COOKIE_SIGNING_KEY/SESSION_ENCRYPTION_KEY")
    return raw.encode("utf-8")


def _is_production_runtime() -> bool:
    env = str(build_runtime_config_from_secrets().get("APP_ENV", "") or "").strip().lower()
    return env in {"production", "prod", "live"}


def _cookie_manager():
    if stx is None:
        return None
    manager = st.session_state.get("_saas_cookie_manager")
    if manager is not None:
        return manager
    manager = stx.CookieManager()
    st.session_state["_saas_cookie_manager"] = manager
    return manager


def _session_cookie_name() -> str:
    env = str(build_runtime_config_from_secrets().get("APP_ENV", "") or "").strip().lower()
    if env in {"production", "prod", "live"}:
        return f"{SESSION_COOKIE_NAME}_prod"
    if env in {"development", "dev", "local"}:
        return f"{SESSION_COOKIE_NAME}_dev"
    return f"{SESSION_COOKIE_NAME}_unknown"


def _clear_cookie_readiness_state() -> None:
    st.session_state.pop(COOKIE_READINESS_STATE_KEY, None)
    st.session_state.pop(COOKIE_READINESS_ATTEMPTS_KEY, None)


def _mark_cookie_readiness_present() -> None:
    st.session_state[COOKIE_READINESS_STATE_KEY] = COOKIE_READINESS_PRESENT
    st.session_state[COOKIE_READINESS_ATTEMPTS_KEY] = 0


def _mark_cookie_readiness_not_ready() -> None:
    st.session_state[COOKIE_READINESS_STATE_KEY] = COOKIE_READINESS_NOT_READY
    st.session_state[COOKIE_READINESS_ATTEMPTS_KEY] = 1


def _mark_cookie_readiness_absent() -> None:
    st.session_state[COOKIE_READINESS_STATE_KEY] = COOKIE_READINESS_ABSENT
    st.session_state[COOKIE_READINESS_ATTEMPTS_KEY] = 0


def _read_session_cookie_result() -> CookieReadResult:
    manager = _cookie_manager()
    if manager is None:
        return CookieReadResult(COOKIE_READINESS_ABSENT, "")

    scoped_cookie_name = _session_cookie_name()
    try:
        raw = str(manager.get(scoped_cookie_name) or "").strip()
        if not raw:
            raw = str(manager.get(SESSION_COOKIE_NAME) or "").strip()
    except Exception:
        raw = ""

    if raw:
        _mark_cookie_readiness_present()
        return CookieReadResult(COOKIE_READINESS_PRESENT, raw)

    current_state = str(st.session_state.get(COOKIE_READINESS_STATE_KEY, "") or "").strip()
    attempts = int(st.session_state.get(COOKIE_READINESS_ATTEMPTS_KEY, 0) or 0)

    if current_state == COOKIE_READINESS_PRESENT:
        _mark_cookie_readiness_absent()
        return CookieReadResult(COOKIE_READINESS_ABSENT, "")

    if current_state == COOKIE_READINESS_ABSENT:
        return CookieReadResult(COOKIE_READINESS_ABSENT, "")

    if current_state == COOKIE_READINESS_NOT_READY or attempts >= 1:
        _mark_cookie_readiness_absent()
        return CookieReadResult(COOKIE_READINESS_ABSENT, "")

    _mark_cookie_readiness_not_ready()
    return CookieReadResult(COOKIE_READINESS_NOT_READY, "")


def _sign_session_handle(raw_handle: str) -> str:
    payload = f"{SESSION_COOKIE_VERSION}:{raw_handle}".encode("utf-8")
    sig = hmac.new(_session_signing_key(), payload, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")
    return f"{SESSION_COOKIE_VERSION}:{raw_handle}{SESSION_COOKIE_SIGNATURE_SEP}{sig_b64}"


def _unsign_session_handle(cookie_value: str) -> str:
    value = str(cookie_value or "").strip()
    if not value or SESSION_COOKIE_SIGNATURE_SEP not in value:
        raise SessionStoreError("Malformed session cookie")

    signed_payload, sig_b64 = value.rsplit(SESSION_COOKIE_SIGNATURE_SEP, 1)
    if ":" not in signed_payload:
        raise SessionStoreError("Malformed session cookie")

    version, raw_handle = signed_payload.split(":", 1)
    if version != SESSION_COOKIE_VERSION or not raw_handle:
        raise SessionStoreError("Unsupported session cookie version")

    payload = signed_payload.encode("utf-8")
    expected_sig = hmac.new(_session_signing_key(), payload, hashlib.sha256).digest()
    expected_b64 = base64.urlsafe_b64encode(expected_sig).decode("utf-8").rstrip("=")

    if not hmac.compare_digest(expected_b64, sig_b64):
        raise SessionStoreError("Invalid session cookie signature")

    return raw_handle


def _set_session_cookie(raw_handle: str, remember_me: bool = False) -> bool:
    manager = _cookie_manager()
    expires_days = 30 if remember_me else 1
    expires_at = _utc_now() + timedelta(days=expires_days)
    secure_flag = _is_production_runtime()
    same_site_value = "lax"
    path_value = "/"

    if manager is None:
        return False

    try:
        signed_value = _sign_session_handle(raw_handle)
        scoped_cookie_name = _session_cookie_name()
        manager.set(
            scoped_cookie_name,
            signed_value,
            expires_at=expires_at,
            secure=secure_flag,
            same_site=same_site_value,
            path=path_value,
        )
        if scoped_cookie_name != SESSION_COOKIE_NAME:
            try:
                manager.delete(SESSION_COOKIE_NAME)
            except Exception:
                pass
        return True
    except Exception as exc:
        return False


def _read_session_cookie() -> str:
    manager = _cookie_manager()
    if manager is None:
        return ""

    scoped_cookie_name = _session_cookie_name()
    try:
        raw = manager.get(scoped_cookie_name)
        value = str(raw or "").strip()
        if value:
            return value
        raw = manager.get(SESSION_COOKIE_NAME)
        return str(raw or "").strip()
    except Exception as exc:
        return ""


def _clear_session_cookie() -> None:
    manager = _cookie_manager()
    if manager is None:
        return

    try:
        manager.delete(_session_cookie_name())
    except Exception:
        pass

    try:
        manager.delete(SESSION_COOKIE_NAME)
    except Exception:
        pass


def _session_store() -> Optional[SessionStore]:
    try:
        return SessionStore()
    except Exception:
        return None


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


def _normalized_role_value(value: Any) -> str:
    return str(value or "").strip().upper()


def _auth_app_metadata(auth_user: Any) -> Dict[str, Any]:
    if isinstance(auth_user, dict):
        raw = auth_user.get("app_metadata")
        return raw if isinstance(raw, dict) else {}
    raw = getattr(auth_user, "app_metadata", None)
    return raw if isinstance(raw, dict) else {}


def _authoritative_role_from_auth_user(auth_user: Any) -> str:
    app_meta = _auth_app_metadata(auth_user)
    # Canonical admin role source is auth.app_metadata.role only.
    return _normalized_role_value(app_meta.get("role"))


def _current_authenticated_identity() -> tuple[str, str]:
    client = get_supabase_client()
    if client is None:
        return "", ""

    try:
        current_auth_user = _auth_response_user(client.auth.get_user())
    except Exception:
        current_auth_user = None

    if current_auth_user is None:
        return "", ""

    return _auth_user_id(current_auth_user), _auth_user_email(current_auth_user)


def admin_access_allowed(user: "SaaSUser | None" = None) -> tuple[bool, str]:
    current_user = user or get_current_user()
    if current_user is None:
        return False, "no_authenticated_user"

    role_value = _normalized_role_value(getattr(current_user, "role", ""))
    if role_value != "ADMIN":
        return False, "role_not_admin"

    current_auth_user_id, current_auth_email = _current_authenticated_identity()
    expected_user_id = str(getattr(current_user, "user_id", "") or "").strip()
    expected_email = str(getattr(current_user, "email", "") or "").strip().lower()

    if not current_auth_user_id or not expected_user_id:
        return False, "missing_authenticated_identity"
    if current_auth_user_id != expected_user_id:
        return False, "authenticated_identity_mismatch"
    if current_auth_email and expected_email and current_auth_email != expected_email:
        return False, "authenticated_email_mismatch"

    return True, "ok"


def is_admin_user(user: "SaaSUser | None") -> bool:
    allowed, _reason = admin_access_allowed(user)
    return allowed

def init_saas_state() -> None:
    _emit_phase10b_reachability_marker_once()

    st.session_state.setdefault("saas_logged_in", False)
    st.session_state.setdefault("saas_user", None)
    st.session_state.setdefault("saas_selected_plan", PLAN_MARKET_PULSE)
    st.session_state.setdefault("saas_admin_override", False)
    st.session_state.setdefault("saas_auth_session", None)
    st.session_state.setdefault("saas_auth_last_message", "")
    st.session_state.setdefault("saas_onboarding_ready", False)
    st.session_state.setdefault("saas_onboarding_debug", {})
    st.session_state.setdefault("saas_metadata_debug_message", "")
    st.session_state.setdefault("saas_auth_debug", {})
    st.session_state.setdefault("saas_trial_warning_message", "")
    st.session_state.setdefault("saas_trial_protection", {})
    st.session_state.setdefault("saas_provisioning_repair_attempts", {})
    st.session_state.setdefault("saas_app_session_id", "")
    st.session_state.setdefault("saas_identity_bound_user_id", "")
    st.session_state.setdefault("saas_rehydrate_blocked", False)
    st.session_state.setdefault("saas_remember_me", False)
    if not st.session_state.get("saas_logged_in", False):
        rehydrate_result = _rehydrate_authenticated_session()
        if rehydrate_result is None:
            return


@st.cache_resource(show_spinner=False)
def _auth_session_cache() -> Dict[str, Dict[str, Any]]:
    """In-memory auth cache keyed by browser fingerprint for refresh persistence."""
    return {}


def _browser_auth_cache_key() -> str:
    headers = _request_headers()
    if not headers:
        return ""

    client_ip = _client_ip(headers)
    user_agent = _user_agent(headers)

    if client_ip == "UNKNOWN" and user_agent == "UNKNOWN":
        return ""

    raw = "|".join(
        [
            client_ip,
            user_agent,
            _request_header(headers, "accept-language"),
            _request_header(headers, "sec-ch-ua"),
            _request_header(headers, "x-forwarded-proto"),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@st.cache_resource(show_spinner=False)
def _password_reset_cooldown_cache() -> Dict[str, Dict[str, float]]:
    """Cache reset-password cooldown state by browser fingerprint."""
    return {}


def _reset_password_backoff_level() -> int:
    session_level = int(st.session_state.get("saas_reset_password_backoff_level", 0) or 0)
    cache_level = 0

    browser_key = _browser_auth_cache_key()
    if browser_key:
        cached = _password_reset_cooldown_cache().get(browser_key, {})
        cache_level = int(cached.get("level", 0) or 0)

    level = max(session_level, cache_level)
    st.session_state["saas_reset_password_backoff_level"] = level
    return level


def _reset_password_cooldown_expires_at() -> float:
    session_expiry = float(st.session_state.get("saas_reset_password_cooldown_expires_at", 0.0) or 0.0)
    cache_expiry = 0.0

    browser_key = _browser_auth_cache_key()
    if browser_key:
        cached = _password_reset_cooldown_cache().get(browser_key, {})
        cache_expiry = float(cached.get("expires_at", 0.0) or 0.0)

    expires_at = max(session_expiry, cache_expiry)
    if expires_at <= time.time():
        st.session_state["saas_reset_password_cooldown_expires_at"] = 0.0
        if browser_key:
            cached = _password_reset_cooldown_cache().get(browser_key, {})
            _password_reset_cooldown_cache()[browser_key] = {
                "expires_at": 0.0,
                "level": float(cached.get("level", 0) or 0),
            }
        return 0.0

    if expires_at != session_expiry:
        st.session_state["saas_reset_password_cooldown_expires_at"] = expires_at

    return expires_at


def _reset_password_cooldown_remaining() -> int:
    expires_at = _reset_password_cooldown_expires_at()
    if expires_at <= 0:
        return 0
    return max(0, int(expires_at - time.time() + 0.999))


def _set_reset_password_cooldown(level: int, seconds: int) -> None:
    bounded_level = max(1, min(int(level or 1), len(RESET_PASSWORD_BACKOFF_STEPS)))
    cooldown_seconds = max(1, int(seconds or RESET_PASSWORD_BACKOFF_STEPS[bounded_level - 1]))
    expires_at = time.time() + cooldown_seconds
    st.session_state["saas_reset_password_cooldown_expires_at"] = expires_at
    st.session_state["saas_reset_password_backoff_level"] = bounded_level

    browser_key = _browser_auth_cache_key()
    if browser_key:
        _password_reset_cooldown_cache()[browser_key] = {
            "expires_at": expires_at,
            "level": float(bounded_level),
        }


def _reset_password_backoff_seconds_for_next_429() -> tuple[int, int]:
    current_level = _reset_password_backoff_level()
    next_level = min(current_level + 1, len(RESET_PASSWORD_BACKOFF_STEPS))
    return next_level, RESET_PASSWORD_BACKOFF_STEPS[next_level - 1]


def _reset_password_backoff_reset() -> None:
    st.session_state["saas_reset_password_backoff_level"] = 0
    st.session_state["saas_reset_password_cooldown_expires_at"] = 0.0

    browser_key = _browser_auth_cache_key()
    if browser_key:
        _password_reset_cooldown_cache()[browser_key] = {
            "expires_at": 0.0,
            "level": 0.0,
        }


def _format_mmss(seconds: int) -> str:
    minutes, remaining_seconds = divmod(max(0, int(seconds or 0)), 60)
    return f"{minutes:02d}:{remaining_seconds:02d}"


def _supabase_reset_rate_limit_kind(meta: Dict[str, Any]) -> str:
    status_code = int(meta.get("status_code", 0) or 0)
    error_code = str(meta.get("error_code", "") or "").strip().lower()
    if status_code != 429:
        return ""
    if error_code == "over_request_rate_limit":
        return "request"
    if error_code == "over_email_send_rate_limit":
        return "email"
    return ""


def _session_cache_payload(session: Any) -> Dict[str, Any]:
    access_token, refresh_token = _get_session_tokens(session)

    expires_at = None
    try:
        expires_at = getattr(session, "expires_at", None)
    except Exception:
        expires_at = None

    if isinstance(session, dict):
        expires_at = session.get("expires_at", expires_at)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
    }


def _cache_authenticated_session(session: Any) -> None:
    payload = _session_cache_payload(session)
    if not payload.get("access_token"):
        return

    app_session_id = str(st.session_state.get("saas_app_session_id", "") or "").strip()
    if app_session_id:
        payload["app_session_id"] = app_session_id

    key = _browser_auth_cache_key()
    if not key:
        return

    cache = _auth_session_cache()
    cache[key] = payload


def _clear_cached_authenticated_session() -> None:
    key = _browser_auth_cache_key()
    if not key:
        return

    cache = _auth_session_cache()
    cache.pop(key, None)


@st.cache_resource(show_spinner=False)
def _active_page_cache() -> Dict[str, str]:
    return {}


def _browser_page_cache_key() -> str:
    key = _browser_auth_cache_key()
    return key


def remember_active_page(page_name: str) -> None:
    page_name = str(page_name or "").strip()
    key = _browser_page_cache_key()
    if not page_name or not key:
        return
    _active_page_cache()[key] = page_name


def restore_active_page(default_page: str = "Opportunity Center") -> str:
    key = _browser_page_cache_key()
    if not key:
        return default_page

    saved_page = str(_active_page_cache().get(key, "") or "").strip()
    if not saved_page:
        return default_page

    user = get_current_user()
    if user is None:
        return default_page

    if can_access_page(user, saved_page):
        return saved_page

    _active_page_cache().pop(key, None)
    return default_page


def clear_active_page_cache() -> None:
    key = _browser_page_cache_key()
    if not key:
        return
    _active_page_cache().pop(key, None)


def _rehydrate_authenticated_session() -> bool | None:
    if bool(st.session_state.get("saas_rehydrate_blocked", False)):
        return False

    if st.session_state.get("saas_logged_in", False) and isinstance(
        st.session_state.get("saas_user"),
        SaaSUser,
    ):
        _mark_cookie_readiness_present()
        return True

    # Primary: durable app-session restoration using signed opaque cookie.
    store = _session_store()
    cookie_result = _read_session_cookie_result()
    if cookie_result.state == COOKIE_READINESS_NOT_READY:
        try:
            st.rerun()
        except Exception:
            pass
        return None

    cookie_value = cookie_result.value
    if store is not None and cookie_value:
        try:
            raw_handle = _unsign_session_handle(cookie_value)
        except Exception:
            _clear_session_cookie()
            _mark_cookie_readiness_absent()
            raw_handle = ""

        if raw_handle:
            lookup = store.get_session_by_handle(raw_handle)
            if lookup.status == SessionLookupStatus.VALID and lookup.record is not None:
                refresh_material = store.get_refresh_material_for_handle(raw_handle)
                if refresh_material:
                    client = get_supabase_client()
                    if client is not None:
                        try:
                            restored = client.auth.refresh_session(refresh_material)
                        except Exception:
                            restored = None

                        session = _auth_response_session(restored)
                        auth_user = _auth_response_user(restored)

                        if session is not None and auth_user is not None:
                            session_payload = _session_cache_payload(session)
                            st.session_state["saas_auth_session"] = session_payload
                            st.session_state["saas_user"] = build_saas_user_from_auth(
                                auth_user,
                                selected_plan=st.session_state.get("saas_selected_plan"),
                            )
                            st.session_state["saas_logged_in"] = True
                            st.session_state["saas_app_session_id"] = lookup.record.id
                            _cache_authenticated_session(session_payload)
                            if not _enforce_identity_binding_contract(
                                "rehydrate_durable",
                                login_user=auth_user,
                                login_session=session,
                                expected_durable_user_id=str(getattr(lookup.record, "user_id", "") or "").strip(),
                                client=client,
                            ):
                                return False
                            _mark_cookie_readiness_present()
                            return True

                # Session exists but restoration cannot complete.
                try:
                    store.revoke_session(lookup.record.id, reason="RESTORE_FAILED")
                except Exception:
                    pass
                _clear_session_cookie()
                _mark_cookie_readiness_absent()
            elif lookup.status in {
                SessionLookupStatus.MISSING,
                SessionLookupStatus.REVOKED,
                SessionLookupStatus.IDLE_EXPIRED,
                SessionLookupStatus.ABSOLUTE_EXPIRED,
                SessionLookupStatus.MALFORMED,
            }:
                _clear_session_cookie()
                _mark_cookie_readiness_absent()

    # Secondary optimization: existing in-memory cache.
    key = _browser_auth_cache_key()
    if not key:
        return False

    cache = _auth_session_cache()
    session_payload = cache.get(key)
    if not isinstance(session_payload, dict):
        return False

    access_token = str(session_payload.get("access_token", "") or "").strip()
    if not access_token:
        return False

    client = get_supabase_client()
    if client is None:
        return False

    if not _apply_auth_session_to_client(client, session_payload):
        _clear_cached_authenticated_session()
        return False

    auth_user = None
    try:
        auth_user = _auth_response_user(client.auth.get_user())
    except Exception:
        auth_user = None

    if auth_user is None:
        _clear_cached_authenticated_session()
        return False

    st.session_state["saas_auth_session"] = session_payload
    st.session_state["saas_user"] = build_saas_user_from_auth(
        auth_user,
        selected_plan=st.session_state.get("saas_selected_plan"),
    )
    st.session_state["saas_logged_in"] = True
    cached_app_session_id = str(session_payload.get("app_session_id", "") or "").strip()
    if cached_app_session_id:
        st.session_state["saas_app_session_id"] = cached_app_session_id
    if store is not None:
        resolved_session_id, _resolved_source = _resolve_current_app_session_id(store)
        if resolved_session_id:
            st.session_state["saas_app_session_id"] = resolved_session_id
            _cache_authenticated_session(session_payload)
    if not _enforce_identity_binding_contract(
        "rehydrate_cache",
        login_user=auth_user,
        login_session=session_payload,
        client=client,
    ):
        return False
    _mark_cookie_readiness_present()
    return True


def _jwt_claims(access_token: str) -> Dict[str, Any]:
    token = str(access_token or "").strip()
    if not token or token.count(".") < 2:
        return {}

    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
        decoded = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
        payload = json.loads(decoded.decode("utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _safe_auth_user_via_get_user(client: Any, access_token: str = "") -> Any:
    if client is None:
        return None

    token = str(access_token or "").strip()
    try:
        if token:
            try:
                return _auth_response_user(client.auth.get_user(token))
            except TypeError:
                return _auth_response_user(client.auth.get_user(jwt=token))
        return _auth_response_user(client.auth.get_user())
    except Exception:
        return None


def _durable_session_owner_user_id(store: Any, session_id: str) -> str:
    sid = str(session_id or "").strip()
    if not sid or store is None:
        return ""

    try:
        row = store._select_single_by_id(sid)  # type: ignore[attr-defined]
    except Exception:
        return ""

    if isinstance(row, dict):
        return str(row.get("user_id", "") or "").strip()
    return str(getattr(row, "user_id", "") or "").strip()


def _identity_mismatch_fail_closed(reason: str) -> bool:
    clear_authenticated_session(revoke_current=True, reason="IDENTITY_MISMATCH")
    st.session_state["saas_identity_bound_user_id"] = ""
    st.session_state["saas_auth_last_message"] = "Your session could not be verified. Please sign in again."
    _set_auth_debug("identity_mismatch", {"reason": str(reason or "unknown")})
    return False


def _enforce_identity_binding_contract(
    context: str,
    *,
    login_user: Any = None,
    login_session: Any = None,
    expected_durable_user_id: str = "",
    client: Any = None,
) -> bool:
    client_obj = client if client is not None else get_supabase_client()
    if client_obj is None:
        return _identity_mismatch_fail_closed(f"{context}:missing_client")

    access_token, _refresh_token = _get_session_tokens(login_session)
    if not access_token:
        access_token, _ = _get_session_tokens(st.session_state.get("saas_auth_session"))

    auth_user = _safe_auth_user_via_get_user(client_obj, access_token)
    auth_user_id = _auth_user_id(auth_user)
    auth_email = _auth_user_email(auth_user)
    if not auth_user_id:
        return _identity_mismatch_fail_closed(f"{context}:missing_authenticated_user")

    login_user_id = _auth_user_id(login_user)
    if login_user_id and login_user_id != auth_user_id:
        return _identity_mismatch_fail_closed(f"{context}:login_user_mismatch")

    token_claims = _jwt_claims(access_token)
    token_sub = str(token_claims.get("sub", "") or "").strip()
    token_email = str(token_claims.get("email", "") or "").strip().lower()
    if token_sub and token_sub != auth_user_id:
        return _identity_mismatch_fail_closed(f"{context}:token_subject_mismatch")
    if token_email and auth_email and token_email != auth_email:
        return _identity_mismatch_fail_closed(f"{context}:token_email_mismatch")

    state_user = get_current_user()
    state_user_id = str(getattr(state_user, "user_id", "") or "").strip() if state_user is not None else ""
    state_user_email = str(getattr(state_user, "email", "") or "").strip().lower() if state_user is not None else ""
    if state_user_id and state_user_id != auth_user_id:
        return _identity_mismatch_fail_closed(f"{context}:state_user_mismatch")
    if state_user_email and auth_email and state_user_email != auth_email:
        return _identity_mismatch_fail_closed(f"{context}:state_email_mismatch")

    store = _session_store()
    durable_owner_user_id = str(expected_durable_user_id or "").strip()
    if not durable_owner_user_id:
        durable_session_id = str(st.session_state.get("saas_app_session_id", "") or "").strip()
        durable_owner_user_id = _durable_session_owner_user_id(store, durable_session_id)
    if durable_owner_user_id and durable_owner_user_id != auth_user_id:
        return _identity_mismatch_fail_closed(f"{context}:durable_owner_mismatch")

    profile_row = _profile_row_for_auth_user(client_obj, auth_user_id, "")
    profile_user_id = str(profile_row.get("user_id", "") or "").strip() if isinstance(profile_row, dict) else ""
    if profile_user_id and profile_user_id != auth_user_id:
        return _identity_mismatch_fail_closed(f"{context}:profile_owner_mismatch")

    workspace_user_id = ""
    try:
        workspace_rows = _verified_user_row(client_obj, "workspaces", auth_user_id)
        if workspace_rows and isinstance(workspace_rows[0], dict):
            workspace_user_id = str(workspace_rows[0].get("user_id", "") or "").strip()
    except Exception:
        workspace_user_id = ""
    if workspace_user_id and workspace_user_id != auth_user_id:
        return _identity_mismatch_fail_closed(f"{context}:workspace_owner_mismatch")

    bound_user_id = str(st.session_state.get("saas_identity_bound_user_id", "") or "").strip()
    if bound_user_id and bound_user_id != auth_user_id:
        st.session_state["saas_admin_override"] = False

    st.session_state["saas_identity_bound_user_id"] = auth_user_id
    return True


def clear_stripe_checkout_state() -> None:
    """Remove cached Stripe Checkout links when users change or log out.

    Checkout URLs are bound to the user and metadata used when they were
    created. Keeping an old URL in session state can show the wrong customer
    email on Stripe Checkout after switching accounts.
    """
    for key in list(st.session_state.keys()):
        if str(key).startswith("stripe_checkout_url_"):
            del st.session_state[key]
        elif str(key).startswith("stripe_checkout_owner_"):
            del st.session_state[key]


def _request_headers() -> Dict[str, str]:
    ctx = getattr(st, "context", None)
    headers = getattr(ctx, "headers", None)
    if headers is None:
        return {}

    try:
        return {str(key).lower(): str(value) for key, value in headers.items()}
    except Exception:
        return {}


def _request_header(headers: Dict[str, str], *names: str) -> str:
    for name in names:
        value = str(headers.get(name.lower(), "") or "").strip()
        if value:
            return value
    return ""


def _project_ref_from_url(url: str) -> str:
    host = str(urlparse(str(url or "").strip()).hostname or "").strip().lower()
    if not host:
        return ""
    return host.split(".", 1)[0]


def _sanitize_auth_error(exc: Exception) -> tuple[str, str]:
    text = str(exc or "")
    compact = " ".join(text.split())
    lowered = compact.lower()

    if "invalid login credentials" in lowered:
        return "invalid_credentials", "Invalid login credentials"
    if "email not confirmed" in lowered:
        return "email_not_confirmed", "Email not confirmed"
    if "too many" in lowered and "request" in lowered:
        return "rate_limited", "Too many requests"
    if "network" in lowered or "timeout" in lowered:
        return "network_error", "Network or timeout error"

    if not compact:
        return "unknown_error", "Unknown auth error"

    return "auth_error", compact[:160]


def _redact_signup_error_text(value: Any) -> str:
    compact = " ".join(str(value or "").split())
    if not compact:
        return ""

    redacted = re.sub(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        "[redacted-email]",
        compact,
    )
    redacted = re.sub(
        r"\b(?:eyJ[A-Za-z0-9_\-]+|sk_(?:live|test)_[A-Za-z0-9_\-]+|sbp_[A-Za-z0-9_\-]+|supabase_[A-Za-z0-9_\-]+)\b",
        "[redacted-token]",
        redacted,
    )
    redacted = re.sub(
        r"(?i)\b(password|passphrase|secret|token|refresh_token|access_token|api_key|apikey)\s*[:=]\s*([^\s,;]+)",
        r"\1=[redacted]",
        redacted,
    )
    return redacted[:220]


def _signup_error_response(exc: Exception) -> tuple[str, str, str]:
    sanitized_error = _redact_signup_error_text(exc)
    lowered = sanitized_error.lower()

    if (
        "over_email_send_rate_limit" in lowered
        or "email send rate limit" in lowered
        or ("verification email" in lowered and "rate limit" in lowered)
    ):
        return "rate_limited", SIGNUP_RATE_LIMIT_MESSAGE, sanitized_error

    if "already" in lowered or "registered" in lowered or "exists" in lowered:
        return "duplicate_email", "This email is already on file. Please use Login or Reset Password.", sanitized_error

    return "unknown_error", SIGNUP_GENERIC_FAILURE_MESSAGE, sanitized_error


def _log_signup_failure_diagnostic(classification: str, sanitized_error: str) -> None:
    payload = {
        "app_hostname": _runtime_app_hostname(),
        "classification": str(classification or "unknown_error"),
        "commit_hash": _runtime_commit_hash(),
        "event": "supabase_sign_up_error",
        "error_preview": str(sanitized_error or "")[:180],
    }
    line = f"SUPABASE_SIGNUP_DIAGNOSTIC {json.dumps(payload, sort_keys=True)}"
    print(line, flush=True)
    logger.warning("%s", line)


def _direct_password_grant_probe(email: str, password: str) -> Dict[str, Any]:
    url = str(st.secrets.get("SUPABASE_URL", "") or "").strip().rstrip("/")
    key = str(st.secrets.get("SUPABASE_ANON_KEY", "") or "").strip()
    endpoint = f"{url}/auth/v1/token"
    meta: Dict[str, Any] = {
        "status": 0,
        "user_present": False,
        "access_present": False,
        "refresh_present": False,
        "user_id": "",
        "error_code": "",
        "error_message": "",
        "project_ref": _project_ref_from_url(url),
    }

    if not url or not key:
        meta["error_code"] = "missing_supabase_config"
        meta["error_message"] = "Missing Supabase URL or anon key"
        return meta

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "email": email,
        "password": password,
    }
    query = {
        "grant_type": "password",
    }

    try:
        response = requests.post(endpoint, headers=headers, params=query, json=payload, timeout=30)
        meta["status"] = int(response.status_code)

        body = {}
        try:
            body = response.json() if response.text else {}
        except Exception:
            body = {}

        if isinstance(body, dict):
            user_obj = body.get("user") if isinstance(body.get("user"), dict) else {}
            meta["user_present"] = bool(user_obj)
            meta["user_id"] = str(user_obj.get("id", "") or "").strip()
            meta["access_present"] = bool(str(body.get("access_token", "") or "").strip())
            meta["refresh_present"] = bool(str(body.get("refresh_token", "") or "").strip())
            meta["error_code"] = str(body.get("error_code", "") or "").strip().lower()
            raw_message = str(body.get("msg", "") or body.get("message", "") or "").strip()
            meta["error_message"] = " ".join(raw_message.split())[:160]

        if response.status_code >= 400 and not meta["error_code"]:
            meta["error_code"] = f"http_{response.status_code}"
            if not meta["error_message"]:
                meta["error_message"] = "Password grant request failed"

    except Exception as exc:
        code, message = _sanitize_auth_error(exc)
        meta["error_code"] = code
        meta["error_message"] = message

    return meta


def _client_ip(headers: Dict[str, str]) -> str:
    raw = _request_header(
        headers,
        "x-forwarded-for",
        "x-real-ip",
        "cf-connecting-ip",
        "x-client-ip",
        "forwarded",
    )
    if not raw:
        return "UNKNOWN"

    if "," in raw:
        return raw.split(",", 1)[0].strip() or "UNKNOWN"
    return raw.strip() or "UNKNOWN"


def _signup_country(headers: Dict[str, str]) -> str:
    country = _request_header(
        headers,
        "cf-ipcountry",
        "cloudfront-viewer-country",
        "x-appengine-country",
        "x-country-code",
    )
    return country.upper() if country else "UNKNOWN"


def _signup_city(headers: Dict[str, str]) -> str:
    city = _request_header(
        headers,
        "x-vercel-ip-city",
        "cloudfront-viewer-city",
        "x-appengine-city",
        "cf-ipcity",
        "x-city",
    )
    return city.strip() if city else "UNKNOWN"


def _user_agent(headers: Dict[str, str]) -> str:
    return _request_header(headers, "user-agent") or "UNKNOWN"


def _browser_from_user_agent(user_agent: Any) -> str:
    text = str(user_agent or "").lower()
    if not text or text == "unknown":
        return "UNKNOWN"
    if "edg/" in text:
        return "Edge"
    if "chrome/" in text and "edg/" not in text:
        return "Chrome"
    if "safari/" in text and "chrome/" not in text:
        return "Safari"
    if "firefox/" in text:
        return "Firefox"
    if "opr/" in text or "opera" in text:
        return "Opera"
    return "Other"


def _os_from_user_agent(user_agent: Any) -> str:
    text = str(user_agent or "").lower()
    if not text or text == "unknown":
        return "UNKNOWN"
    if "windows" in text:
        return "Windows"
    if "iphone" in text or "ipad" in text or "ios" in text:
        return "iOS"
    if "android" in text:
        return "Android"
    if "macintosh" in text or "mac os" in text:
        return "macOS"
    if "linux" in text:
        return "Linux"
    return "Other"


def _device_id(headers: Dict[str, str]) -> str:
    fingerprint_parts = [
        _request_header(headers, "user-agent"),
        _request_header(headers, "accept-language"),
        _request_header(headers, "sec-ch-ua"),
        _request_header(headers, "sec-ch-ua-platform"),
        _request_header(headers, "accept-encoding"),
    ]
    normalized = "|".join(part.strip() for part in fingerprint_parts if str(part or "").strip())
    if not normalized:
        return "fallback:unknown-device"
    return "fallback:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]


def _proxy_or_vpn_signal(headers: Dict[str, str]) -> bool:
    via_header = _request_header(headers, "via")
    forwarded_for = _request_header(headers, "x-forwarded-for")
    forwarded = _request_header(headers, "forwarded")
    return bool(via_header or forwarded or (forwarded_for and "," in forwarded_for))


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _parse_dt_or_none(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    if isinstance(value, str) and value.strip():
        try:
            cleaned = value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(cleaned)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except Exception:
            return None

    return None


def auth_user_created_at(auth_user: Any) -> Optional[datetime]:
    if isinstance(auth_user, dict):
        return _parse_dt_or_none(auth_user.get("created_at"))
    return _parse_dt_or_none(getattr(auth_user, "created_at", None))


def canonical_trial_window(auth_user: Any) -> tuple[Optional[datetime], Optional[datetime], str]:
    auth_created = auth_user_created_at(auth_user)
    if auth_created is None:
        return None, None, "missing_auth_created_at"
    return auth_created, auth_created + timedelta(days=TRIAL_LENGTH_DAYS), "auth.users.created_at"


def trial_dates_consistent(auth_created_at_value: Any, trial_start_value: Any, trial_end_value: Any) -> bool:
    auth_created = _parse_dt_or_none(auth_created_at_value)
    trial_start = _parse_dt_or_none(trial_start_value)
    trial_end = _parse_dt_or_none(trial_end_value)
    if auth_created is None or trial_start is None or trial_end is None:
        return False

    expected_end = auth_created + timedelta(days=TRIAL_LENGTH_DAYS)
    return trial_start.date() == auth_created.date() and trial_end.date() == expected_end.date()


def _dt_text(value: Any) -> str:
    if isinstance(value, datetime):
        parsed = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            return str(value).strip()
    return "N/A"


def _send_founder_trial_started_email(payload: Dict[str, Any]) -> tuple[bool, str]:
    smtp_host = _secret_value("TRIAL_ALERT_SMTP_HOST") or _secret_value("FEEDBACK_SMTP_HOST")
    smtp_user = _secret_value("TRIAL_ALERT_SMTP_USER") or _secret_value("FEEDBACK_SMTP_USER")
    smtp_password = _secret_value("TRIAL_ALERT_SMTP_PASSWORD") or _secret_value("FEEDBACK_SMTP_PASSWORD")
    smtp_from = _secret_value("TRIAL_ALERT_SMTP_FROM") or _secret_value("FEEDBACK_SMTP_FROM")
    smtp_port_raw = _secret_value("TRIAL_ALERT_SMTP_PORT") or _secret_value("FEEDBACK_SMTP_PORT", "587")
    smtp_tls_raw = _secret_value("TRIAL_ALERT_SMTP_USE_TLS") or _secret_value("FEEDBACK_SMTP_USE_TLS", "true")
    founder_email = _secret_value("FOUNDER_TRIAL_EMAIL", FOUNDER_TRIAL_EMAIL) or FOUNDER_TRIAL_EMAIL

    missing = []
    if not smtp_host:
        missing.append("SMTP_HOST")
    if not smtp_from:
        missing.append("SMTP_FROM")
    if missing:
        print(f"FOUNDER_TRIAL_NOTIFY: skipped, missing config: {','.join(missing)}")
        return False, f"Missing SMTP config: {', '.join(missing)}"

    try:
        smtp_port = int(str(smtp_port_raw or "587").strip())
    except Exception:
        smtp_port = 587

    smtp_tls = str(smtp_tls_raw or "true").strip().lower() in {"1", "true", "yes", "y", "on"}

    message = EmailMessage()
    message["Subject"] = FOUNDER_TRIAL_SUBJECT
    message["From"] = smtp_from
    message["To"] = founder_email
    message.set_content(
        "\n".join(
            [
                "New JFBP Quant Desk trial started.",
                "",
                f"Name: {payload.get('name', 'N/A')}",
                f"Email: {payload.get('email', 'N/A')}",
                f"Plan: {payload.get('plan', 'N/A')}",
                f"Trial Start: {payload.get('trial_start', 'N/A')}",
                f"Trial End: {payload.get('trial_end', 'N/A')}",
                f"Created At: {payload.get('created_at', 'N/A')}",
                f"Last Login: {payload.get('last_login', 'N/A')}",
                f"Onboarding Progress: {payload.get('onboarding_progress', 'N/A')}",
                f"Provisioning Status: {payload.get('provisioning_status', 'N/A')}",
            ]
        )
    )

    try:
        use_ssl = (smtp_port == 465) and (not smtp_tls)
        smtp_client = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
        with smtp_client(smtp_host, smtp_port, timeout=20) as server:
            if smtp_tls and not use_ssl:
                server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.send_message(message)
        print(f"FOUNDER_TRIAL_NOTIFY: sent to {founder_email}")
        return True, "Founder notification sent."
    except Exception as exc:
        print(f"FOUNDER_TRIAL_NOTIFY: failed: {exc}")
        return False, str(exc)


def _signup_fingerprint() -> Dict[str, Any]:
    headers = _request_headers()
    now = _utc_now()
    user_agent = _user_agent(headers)
    device_fingerprint = _device_id(headers)
    return {
        "signup_ip": _client_ip(headers),
        "signup_country": _signup_country(headers),
        "signup_city": _signup_city(headers),
        "city": _signup_city(headers),
        "device_id": device_fingerprint,
        "device_fingerprint": device_fingerprint,
        "user_agent": user_agent,
        "browser": _browser_from_user_agent(user_agent),
        "operating_system": _os_from_user_agent(user_agent),
        "trial_started_at": now.isoformat(),
        "last_ip_activity": now.isoformat(),
        "vpn_or_proxy": _proxy_or_vpn_signal(headers),
        "captured_at": now.isoformat(),
    }


def _login_metadata() -> Dict[str, Any]:
    headers = _request_headers()
    now = _utc_now()
    user_agent = _user_agent(headers)
    country = _signup_country(headers)
    city = _signup_city(headers)
    login_ip = _client_ip(headers)
    device_fingerprint = _device_id(headers)
    return {
        "last_login_ip": login_ip,
        "last_login_country": country,
        "last_login_city": city,
        "user_agent": user_agent,
        "browser": _browser_from_user_agent(user_agent),
        "operating_system": _os_from_user_agent(user_agent),
        "device_id": device_fingerprint,
        "device_fingerprint": device_fingerprint,
        "last_login_at": now.isoformat(),
        "last_ip_activity": now.isoformat(),
    }


def _collect_login_metadata() -> Dict[str, Any]:
    """Collect request/session metadata only; no database writes here."""
    metadata = _login_metadata()
    metadata["timestamp"] = str(metadata.get("last_login_at") or _utc_now().isoformat())
    return metadata


def _merge_profile_metadata(base_profile: Dict[str, Any], runtime_metadata: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(runtime_metadata)
    merged["signup_ip"] = str(base_profile.get("signup_ip") or runtime_metadata.get("signup_ip") or "UNKNOWN")
    merged["signup_country"] = str(base_profile.get("signup_country") or runtime_metadata.get("signup_country") or "UNKNOWN")
    merged["signup_city"] = str(base_profile.get("signup_city") or base_profile.get("city") or runtime_metadata.get("signup_city") or runtime_metadata.get("last_login_city") or "UNKNOWN")
    merged["city"] = str(base_profile.get("city") or merged["signup_city"] or "UNKNOWN")
    merged["user_agent"] = str(runtime_metadata.get("user_agent") or base_profile.get("user_agent") or "UNKNOWN")
    merged["browser"] = str(runtime_metadata.get("browser") or base_profile.get("browser") or _browser_from_user_agent(merged["user_agent"]))
    merged["operating_system"] = str(runtime_metadata.get("operating_system") or base_profile.get("operating_system") or _os_from_user_agent(merged["user_agent"]))
    merged["device_id"] = str(runtime_metadata.get("device_id") or base_profile.get("device_id") or "fallback:unknown-device")
    merged["device_fingerprint"] = str(runtime_metadata.get("device_fingerprint") or base_profile.get("device_fingerprint") or merged["device_id"])
    return merged


def _prefer_known(collected: Any, existing: Any, fallback: str = "UNKNOWN") -> str:
    collected_text = str(collected or "").strip()
    existing_text = str(existing or "").strip()
    if collected_text and collected_text.upper() != "UNKNOWN":
        return collected_text
    if existing_text:
        return existing_text
    return fallback


def _save_login_metadata(
    client: Any,
    user_id: str,
    profile_row: Dict[str, Any],
    login_metadata: Dict[str, Any],
) -> tuple[bool, str, Dict[str, Any], Any]:
    """Persist login metadata to user_profiles with minimal, non-destructive updates."""
    if client is None or not user_id:
        return False, "Missing client or user_id", {}, None

    now_iso = str(login_metadata.get("timestamp") or login_metadata.get("last_login_at") or _utc_now().isoformat())
    current_total = _safe_int(profile_row.get("total_logins"), 0)
    payload: Dict[str, Any] = {}

    target_last_login = {
        "last_login_ip": _prefer_known(login_metadata.get("last_login_ip"), profile_row.get("last_login_ip")),
        "last_login_country": _prefer_known(login_metadata.get("last_login_country"), profile_row.get("last_login_country")),
        "last_login_city": _prefer_known(login_metadata.get("last_login_city"), profile_row.get("last_login_city")),
        "browser": _prefer_known(login_metadata.get("browser"), profile_row.get("browser")),
        "operating_system": _prefer_known(login_metadata.get("operating_system"), profile_row.get("operating_system")),
        "user_agent": _prefer_known(login_metadata.get("user_agent"), profile_row.get("user_agent")),
        "device_id": _prefer_known(login_metadata.get("device_id"), profile_row.get("device_id"), "fallback:unknown-device"),
        "device_fingerprint": _prefer_known(
            login_metadata.get("device_fingerprint") or login_metadata.get("device_id"),
            profile_row.get("device_fingerprint") or profile_row.get("device_id"),
            "fallback:unknown-device",
        ),
    }

    for key, target_value in target_last_login.items():
        existing = str(profile_row.get(key) or "").strip()
        if target_value != existing:
            payload[key] = target_value

    payload["last_login_at"] = now_iso
    payload["last_ip_activity"] = now_iso
    payload["total_logins"] = current_total + 1

    if not str(profile_row.get("first_login_at") or "").strip():
        payload["first_login_at"] = now_iso

    if not str(profile_row.get("signup_ip") or "").strip():
        payload["signup_ip"] = _prefer_known(login_metadata.get("last_login_ip"), None)
    if not str(profile_row.get("signup_country") or "").strip():
        payload["signup_country"] = _prefer_known(login_metadata.get("last_login_country"), None)
    if not str(profile_row.get("signup_city") or profile_row.get("city") or "").strip():
        signup_city = _prefer_known(login_metadata.get("last_login_city"), None)
        payload["signup_city"] = signup_city
        payload["city"] = signup_city

    payload, dropped = filter_canonical_payload(
        "user_profiles",
        payload,
        context="_save_login_metadata",
        logger=_canonical_log,
    )

    if not payload and dropped:
        return True, "Login metadata skipped (non-canonical telemetry).", {}, None

    try:
        response = client.table("user_profiles").update(payload).eq("user_id", user_id).execute()
        return True, "Login metadata updated.", payload, response
    except Exception as exc:
        return False, str(exc), payload, None


def _update_login_metadata(client: Any, user_id: str, profile_row: Dict[str, Any], login_metadata: Dict[str, Any]) -> tuple[bool, str]:
    ok, message, _, _ = _save_login_metadata(client, user_id, profile_row, login_metadata)
    return ok, message


def _record_metadata_debug(success: bool, message: str, payload: Optional[Dict[str, Any]] = None) -> None:
    debug_payload = dict(st.session_state.get("saas_onboarding_debug", {}))
    debug_payload["metadata_write"] = {
        "ok": bool(success),
        "message": str(message or ""),
        "payload": payload or {},
    }
    st.session_state["saas_onboarding_debug"] = debug_payload


def _set_auth_debug(stage: str, data: Dict[str, Any]) -> None:
    if not AUTH_DEBUG:
        return
    debug_state = dict(st.session_state.get("saas_auth_debug", {}))
    debug_state[str(stage)] = data
    st.session_state["saas_auth_debug"] = debug_state


def _reset_auth_debug() -> None:
    if AUTH_DEBUG:
        st.session_state["saas_auth_debug"] = {}


def _service_role_rest_config() -> tuple[str, str]:
    url = _secret_value("SUPABASE_URL").rstrip("/")
    key = _secret_value("SUPABASE_SERVICE_ROLE_KEY")
    return url, key


def _service_role_headers() -> Dict[str, str]:
    _, key = _service_role_rest_config()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _trial_profile_snapshot() -> List[Dict[str, Any]]:
    url, key = _service_role_rest_config()
    if not url or not key:
        return []

    endpoint = f"{url}/rest/v1/user_profiles"
    params = {
        "select": "user_id,email,trial_start,trial_end,account_status,created_at",
        "trial_start": "not.is.null",
        "limit": "5000",
        "order": "trial_start.desc",
    }

    try:
        response = requests.get(
            endpoint,
            headers=_service_role_headers(),
            params=params,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _risk_level(score: int) -> str:
    if score > 60:
        return TRIAL_RISK_HIGH
    if score >= 30:
        return TRIAL_RISK_MEDIUM
    return TRIAL_RISK_LOW


def _email_domain(email: str) -> str:
    parts = str(email or "").strip().lower().split("@")
    return parts[-1] if len(parts) == 2 else ""


def _is_disposable_email(email: str) -> bool:
    return _email_domain(email) in DISPOSABLE_EMAIL_DOMAINS


def evaluate_trial_protection(email: str, signup_context: Dict[str, Any]) -> Dict[str, Any]:
    clean_email = str(email or "").strip().lower()
    now = _utc_now()
    profiles = _trial_profile_snapshot()

    # Telemetry remains available in-memory, but persistence is canonical-only.
    same_ip_rows_30d: List[Dict[str, Any]] = []
    same_ip_rows_24h: List[Dict[str, Any]] = []
    same_device_rows: List[Dict[str, Any]] = []
    email_rows = []
    same_device_other_email_rows: List[Dict[str, Any]] = []

    for row in profiles:
        trial_started_at = _parse_dt(row.get("trial_start"), fallback=None)
        row_email = str(row.get("email") or "").strip().lower()

        if clean_email and row_email == clean_email:
            email_rows.append(row)

    # Explicit deny rule preserved using canonical evidence of prior trial by email.
    blocked_existing = bool(email_rows)

    score = 0
    fraud_flags: List[str] = []
    if bool(signup_context.get("vpn_or_proxy")):
        score += 25
        fraud_flags.append("VPN_PROXY")
    if _is_disposable_email(clean_email):
        score += 15
        fraud_flags.append("DISPOSABLE_EMAIL")

    risk = _risk_level(score)
    prior_attempts = max(len(email_rows), 0)
    trial_attempts = prior_attempts + 1
    last_ip_activity = signup_context.get("last_ip_activity")

    blocked = blocked_existing or score > 80
    warning = not blocked and score > 60
    allow = not blocked

    if score > 60 and "HIGH_RISK" not in fraud_flags:
        fraud_flags.append("HIGH_RISK")
    if blocked and "BLOCK_TRIAL" not in fraud_flags:
        fraud_flags.append("BLOCK_TRIAL")

    message = ""
    if blocked:
        message = "The free trial has already been used. Please subscribe or contact support if you believe this is an error."
    elif warning:
        message = "It looks like a trial has already been used from this network."

    result = {
        "allow": allow,
        "blocked": blocked,
        "warning": warning,
        "risk": risk,
        "risk_score": score,
        "trial_attempts": trial_attempts,
        "repeat_ips": len(same_ip_rows_30d),
        "repeat_devices": len(same_device_other_email_rows),
        "same_ip_trials_30d": len(same_ip_rows_30d),
        "same_ip_trials_24h": len(same_ip_rows_24h),
        "same_device_trials": len(same_device_rows),
        "disposable_email": _is_disposable_email(clean_email),
        "vpn_or_proxy": bool(signup_context.get("vpn_or_proxy")),
        "fraud_flags": ",".join(fraud_flags),
        "last_ip_activity": last_ip_activity,
        "message": message,
    }
    st.session_state["saas_trial_protection"] = result
    return result


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
    try:
        validate_runtime_environment()
    except Exception as exc:
        return False, f"Environment validation failed: {exc}"

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


def _signup_email_redirect_to() -> str:
    """Return explicit signup confirmation redirect URL from environment config."""
    resolved = _resolve_secret_value_with_source("SUPABASE_EMAIL_REDIRECT_TO", "")
    explicit = str(resolved.get("value", "") or "").strip()
    selected_source = str(resolved.get("selected_source", "FALLBACK") or "FALLBACK")
    secret_exists = bool(resolved.get("secret_exists", False))
    environment_exists = bool(resolved.get("environment_exists", False))

    if explicit:
        selected_classification = _classify_redirect_value(explicit)
        st.session_state["_phase10b_signup_redirect_meta"] = {
            "selected_source": selected_source,
            "email_redirect_to_classification": selected_classification,
            "redirect_to_classification": selected_classification,
        }
        _log_phase10b_redirect_diagnostic(
            "_signup_email_redirect_to",
            {
                "secret_exists": secret_exists,
                "environment_exists": environment_exists,
                "selected_source": selected_source,
                "selected_classification": selected_classification,
                "commit_hash": _runtime_commit_hash(),
                "app_hostname": _runtime_app_hostname(),
            },
        )
        return explicit

    runtime_config = build_runtime_config_from_secrets()
    fallback_value = default_signup_redirect_for_env(runtime_config.get("APP_ENV", "development"))
    fallback_classification = _classify_redirect_value(fallback_value)
    st.session_state["_phase10b_signup_redirect_meta"] = {
        "selected_source": "FALLBACK",
        "email_redirect_to_classification": fallback_classification,
        "redirect_to_classification": fallback_classification,
    }
    _log_phase10b_redirect_diagnostic(
        "_signup_email_redirect_to",
        {
            "secret_exists": secret_exists,
            "environment_exists": environment_exists,
            "selected_source": "FALLBACK",
            "selected_classification": fallback_classification,
            "commit_hash": _runtime_commit_hash(),
            "app_hostname": _runtime_app_hostname(),
        },
    )
    return fallback_value


def _password_reset_redirect_to() -> str:
    explicit = str(_secret_value("SUPABASE_PASSWORD_RESET_REDIRECT_TO", "") or "").strip()
    if explicit:
        return explicit

    runtime_config = build_runtime_config_from_secrets()
    return default_password_reset_redirect_for_env(runtime_config.get("APP_ENV", "development"))


def _query_param_value(name: str) -> str:
    try:
        value = st.query_params.get(name, "")
    except Exception:
        return ""

    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value or "").strip()


RECOVERY_QUERY_PARAM_NAMES = (
    "type",
    "token_hash",
    "token",
    "email",
    "phone",
    "code",
    "access_token",
    "refresh_token",
    "token_type",
    "expires_in",
    "expires_at",
    "error",
    "error_code",
)


def _clear_recovery_query_params() -> None:
    try:
        for name in RECOVERY_QUERY_PARAM_NAMES:
            try:
                del st.query_params[name]
            except Exception:
                pass
    except Exception:
        return


def _clear_auth_callback_query_params() -> None:
    """Clear callback parameters that may contain sensitive auth values."""
    _clear_recovery_query_params()


def _bridge_fragment_auth_callback_to_query() -> None:
    """Bridge URL fragments into query params so Streamlit can consume callbacks.

    Streamlit server code cannot read URL fragments directly. This bridge runs in
    a sandboxed iframe, reads the parent page fragment, copies supported callback
    keys into the query string, removes the fragment from the address bar, and
    reloads once so Python receives the callback through st.query_params.
    """
    bridge_html = """
        <script>
        (function () {
            try {
                var parentWin = window;
                try {
                    while (parentWin.parent && parentWin.parent !== parentWin) {
                        parentWin = parentWin.parent;
                    }
                } catch (_walkErr) {
                    parentWin = (window.parent && window.parent !== window) ? window.parent : window;
                }

                var hash = String(parentWin.location.hash || '');
                if (!hash || hash.length <= 1) {
                    return;
                }

                var hashParams = new URLSearchParams(hash.slice(1));
                var callbackKeys = [
                    'type',
                    'code',
                    'token_hash',
                    'token',
                    'access_token',
                    'refresh_token',
                    'error',
                    'error_code',
                    'token_type',
                    'expires_in',
                    'expires_at'
                ];

                var hasCallbackPayload = callbackKeys.some(function (key) {
                    return Boolean(hashParams.get(key));
                });
                if (!hasCallbackPayload) {
                    return;
                }

                var queryParams = new URLSearchParams(parentWin.location.search || '');
                var changed = false;
                callbackKeys.forEach(function (key) {
                    var value = hashParams.get(key);
                    if (!value) {
                        return;
                    }
                    if (!queryParams.get(key)) {
                        queryParams.set(key, value);
                        changed = true;
                    }
                });

                var basePath = parentWin.location.pathname;
                var nextSearch = queryParams.toString();
                var nextUrl = nextSearch ? (basePath + '?' + nextSearch) : basePath;

                // Remove fragment immediately so tokens do not remain in the bar.
                parentWin.history.replaceState({}, '', nextUrl);

                if (changed) {
                    // In Streamlit's sandboxed component runtime, top-level
                    // navigation APIs (reload/assign/replace) can be blocked.
                    // Emit URL-change events so the host runtime can observe
                    // updated query params and trigger a rerun safely.
                    try {
                        parentWin.dispatchEvent(new PopStateEvent('popstate'));
                    } catch (_popErr) {
                        // Ignore event dispatch errors.
                    }
                    try {
                        parentWin.dispatchEvent(new Event('hashchange'));
                    } catch (_hashErr) {
                        // Ignore event dispatch errors.
                    }
                }
            } catch (_err) {
                // Never raise client-side callback bridge errors into the app.
            }
        })();
        </script>
    """

    try:
        st.components.v1.html(bridge_html, height=0)
    except Exception:
        return


def _recovery_flow_type() -> str:
    return _query_param_value("type").lower()


def _has_recovery_callback_params() -> bool:
    keys = (
        "code",
        "token_hash",
        "token",
        "access_token",
        "refresh_token",
        "error",
        "error_code",
    )
    return any(bool(_query_param_value(name)) for name in keys)


def _has_auth_callback_params() -> bool:
    keys = (
        "code",
        "token_hash",
        "token",
        "access_token",
        "refresh_token",
        "error",
        "error_code",
    )
    return any(bool(_query_param_value(name)) for name in keys)


def _is_recovery_callback() -> bool:
    return _recovery_flow_type() == "recovery"


def _recovery_error_summary() -> tuple[str, str]:
    code = _query_param_value("error_code").lower()
    err = _query_param_value("error").lower()

    if code == "otp_expired":
        return "otp_expired", "Recovery link expired. Request a new password reset email and open it immediately."
    if err == "access_denied":
        return "access_denied", "Recovery link denied. Request a new password reset email and open it immediately."
    if code or err:
        text = code or err
        return text, f"Recovery link error: {text}."
    return "", ""


def _sanitize_reset_error(exc: Exception) -> str:
    _code, message = _sanitize_auth_error(exc)
    return message


def _establish_non_recovery_session_from_query(client: Any) -> tuple[bool, bool, str]:
    """Consume non-recovery auth callbacks from query parameters.

    Returns: (consumed, ok, message)
    - consumed=False means no relevant callback was present for this handler.
    - consumed=True means callback params were present and handled.
    """
    if not _has_auth_callback_params():
        return False, False, ""

    callback_type = _recovery_flow_type()
    if callback_type == "recovery":
        return False, False, ""

    if client is None:
        _clear_auth_callback_query_params()
        return True, False, "Supabase client unavailable for callback session handling."

    code = _query_param_value("code")
    token_hash = _query_param_value("token_hash")
    token = _query_param_value("token")
    callback_email = _query_param_value("email").strip().lower()
    access_token = _query_param_value("access_token")
    refresh_token = _query_param_value("refresh_token")
    err = _query_param_value("error")
    err_code = _query_param_value("error_code")

    if err or err_code:
        _clear_auth_callback_query_params()
        text = str(err_code or err).strip().lower()
        if text == "access_denied":
            return True, False, "Confirmation link denied. Request a fresh link and try again."
        return True, False, f"Confirmation callback error: {text or 'unknown error'}."

    try:
        if code and hasattr(client.auth, "exchange_code_for_session"):
            client.auth.exchange_code_for_session(code)
        elif token_hash and hasattr(client.auth, "verify_otp"):
            verify_type = callback_type or "signup"
            try:
                client.auth.verify_otp({"type": verify_type, "token_hash": token_hash})
            except TypeError:
                client.auth.verify_otp({"type": verify_type, "token": token_hash})
        elif token and hasattr(client.auth, "verify_otp"):
            verify_type = callback_type or "signup"
            payload: Dict[str, Any] = {"type": verify_type, "token": token}
            if callback_email:
                payload["email"] = callback_email
            client.auth.verify_otp(payload)
        elif access_token or refresh_token:
            if not access_token or not refresh_token:
                _clear_auth_callback_query_params()
                return True, False, "Callback session requires both access and refresh tokens."
            if not _apply_auth_session_to_client(
                client,
                {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                },
            ):
                _clear_auth_callback_query_params()
                return True, False, "Callback session could not be established."
        else:
            _clear_auth_callback_query_params()
            return True, False, "Confirmation callback is missing required parameters."

        session = client.auth.get_session()
        auth_response = SimpleNamespace(
            user=_auth_response_user(SimpleNamespace(session=session, user=None)),
            session=session,
        )
        ok = set_authenticated_session(auth_response)
        _clear_auth_callback_query_params()
        if ok:
            return True, True, "Confirmation callback consumed. Session established."
        return True, False, "Confirmation callback consumed but no authenticated session was returned."
    except Exception as exc:
        _clear_auth_callback_query_params()
        return True, False, f"Confirmation callback failed: {exc}"


def _has_active_recovery_session(client: Any) -> bool:
    if client is None:
        return False

    try:
        session = client.auth.get_session()
    except Exception:
        session = None

    access, _refresh = _get_session_tokens(session)
    return bool(access)


def _establish_recovery_session_from_query(client: Any) -> tuple[bool, str]:
    """Establish a recovery session from server-visible URL query parameters.

    Intentionally supported callback formats:
    - `?type=recovery&token_hash=...`
      Uses `client.auth.verify_otp({"type": "recovery", "token_hash": ...})`.
      This matches the installed gotrue Python client, which supports token-hash
      verification for email recovery without requiring `email`.
    - `?type=recovery&token=...&email=...`
      Uses `client.auth.verify_otp({"type": "recovery", "token": ..., "email": ...})`.
      This matches the installed client branch for email OTP verification, where
      a plain token must be paired with exactly one identity field.
    - `?type=recovery&code=...`
      Uses `client.auth.exchange_code_for_session(...)` when the runtime/client
      exposes a PKCE-style code exchange entry point.
    - `?type=recovery&access_token=...&refresh_token=...`
      Applies an already-issued session directly to the Supabase client.

    Intentionally unsupported format:
    - URL fragments such as `#access_token=...&refresh_token=...`
      Streamlit's Python runtime only receives query parameters via
      `st.query_params`; fragment identifiers are browser-local and are not
      delivered to the server. Supporting fragments would require a dedicated
      front-end callback bridge or a different recovery email template.
    """
    if client is None:
        return False, "Supabase client unavailable for recovery."

    if not _is_recovery_callback():
        return False, "Recovery flow not detected."

    code = _query_param_value("code")
    token_hash = _query_param_value("token_hash")
    token = _query_param_value("token")
    recovery_email = _query_param_value("email").strip().lower()
    recovery_phone = _query_param_value("phone").strip()
    access_token = _query_param_value("access_token")
    refresh_token = _query_param_value("refresh_token")

    try:
        if code and hasattr(client.auth, "exchange_code_for_session"):
            client.auth.exchange_code_for_session(code)

        elif token_hash and hasattr(client.auth, "verify_otp"):
            try:
                client.auth.verify_otp({"type": "recovery", "token_hash": token_hash})
            except TypeError:
                client.auth.verify_otp({"type": "recovery", "token": token_hash})

        elif token and hasattr(client.auth, "verify_otp"):
            if recovery_email and recovery_phone:
                return False, "Recovery token must include exactly one identity field."
            if not recovery_email:
                return False, "Recovery token callback requires the email address."

            payload = {
                "type": "recovery",
                "token": token,
            }
            payload["email"] = recovery_email
            client.auth.verify_otp(payload)

        elif access_token or refresh_token:
            if not access_token or not refresh_token:
                return False, "Recovery session callback requires both access and refresh tokens."
            if not _apply_auth_session_to_client(
                client,
                {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                },
            ):
                return False, "Recovery session could not be established."

        else:
            return False, "Recovery link is missing required parameters."

        session = None
        try:
            session = client.auth.get_session()
        except Exception:
            session = None

        access, _refresh = _get_session_tokens(session)
        if not access:
            return False, "Recovery session is not active."

        return True, "Recovery session established."
    except Exception as exc:
        return False, _sanitize_reset_error(exc)


def _validate_password_recovery_inputs(new_password: str, confirm_password: str) -> tuple[bool, str]:
    password_value = str(new_password or "")
    confirm_value = str(confirm_password or "")

    if len(password_value) < 8:
        return False, "Password must be at least 8 characters."
    if password_value != confirm_value:
        return False, "Passwords do not match."
    return True, ""


def _complete_password_recovery(client: Any, new_password: str) -> tuple[bool, str]:
    if client is None:
        return False, "Supabase client unavailable for password update."

    try:
        if not hasattr(client.auth, "update_user"):
            return False, "Supabase password update is unavailable in this runtime."

        try:
            client.auth.update_user({"password": new_password})
        except TypeError:
            client.auth.update_user(password=new_password)

        return True, "Password updated successfully. Please log in with your new password."
    except Exception as exc:
        return False, f"Password update failed: {_sanitize_reset_error(exc)}"


def _validate_signup_inputs(
    email: str,
    full_name: str,
    password: str,
    password_confirm: str,
    plan: str,
) -> tuple[bool, str]:
    clean_email = str(email or "").strip()
    clean_name = str(full_name or "").strip()
    clean_password = str(password or "")
    clean_confirm = str(password_confirm or "")
    clean_plan = str(plan or "").strip().upper()

    if not clean_name:
        return False, "Enter your full name."
    if not clean_email or clean_email.count("@") != 1:
        return False, "Enter a valid email address."

    local_part, domain_part = clean_email.split("@", 1)
    if not local_part or not domain_part or "." not in domain_part or domain_part.startswith(".") or domain_part.endswith("."):
        return False, "Enter a valid email address."

    if len(clean_password) < 8:
        return False, "Password must be at least 8 characters."
    if clean_password != clean_confirm:
        return False, "Passwords do not match."
    if clean_plan not in PLAN_LABELS:
        return False, "Select a valid plan."

    return True, ""


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


def _verified_row_by_email(client: Any, table_name: str, email: str) -> list:
    if not canonical_supports_column(table_name, "email"):
        print(f"CANONICAL_COMPAT: skip email lookup for table={table_name}")
        return []

    clean_email = str(email or "").strip().lower()
    if not clean_email:
        return []

    try:
        response = (
            client.table(table_name)
            .select("*")
            .eq("email", clean_email)
            .limit(5)
            .execute()
        )
        return _response_data(response)
    except Exception:
        return []


def _append_provisioning_note(profile_row: Dict[str, Any], note: str) -> str:
    existing = str(profile_row.get("trial_notes") or "").strip()
    prefix = "[PROVISIONING]"
    line = f"{prefix} {note}".strip()
    if not existing:
        return line

    lines = [value for value in existing.splitlines() if value.strip()]
    if lines and lines[-1].strip() == line:
        return existing
    lines.append(line)
    return "\n".join(lines[-8:])


def _canonical_log(message: str) -> None:
    print(message)


def _provisioning_step_summary(steps: List[Dict[str, Any]]) -> str:
    parts: List[str] = []
    for step in steps:
        label = str(step.get("step") or "").strip()
        ok = bool(step.get("ok"))
        detail = str(step.get("detail") or "").strip()
        marker = "OK" if ok else "FAIL"
        if detail:
            parts.append(f"{label}:{marker} ({detail})")
        else:
            parts.append(f"{label}:{marker}")
    return " | ".join(parts)


def _profile_row_for_auth_user(client: Any, user_id: str, email: str) -> dict:
    """Load the current subscription profile from public.user_profiles.

    Stripe webhooks update public.user_profiles, not auth.users metadata.
    Therefore app access must prefer this table after login.
    """
    if client is None:
        return {}

    try:
        if user_id:
            response = (
                client.table("user_profiles")
                .select("*")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            rows = _response_data(response)
            if rows:
                return rows[0] if isinstance(rows[0], dict) else {}
    except Exception:
        return {}

    return {}


def _create_profile_record(
    client: Any,
    user_id: str,
    email: str,
    full_name: str,
    plan: str,
    account_status: str,
    trial_start: datetime,
    trial_end: datetime,
    trial_metadata: Optional[Dict[str, Any]] = None,
) -> list:
    existing = _verified_user_row(client, "user_profiles", user_id)
    if not existing:
        existing = _verified_row_by_email(client, "user_profiles", email)

    existing_row = existing[0] if existing and isinstance(existing[0], dict) else {}

    clean_email = email.strip().lower()
    full_name_value = full_name.strip() or clean_email or user_id

    payload = {
        "user_id": user_id,
        "email": clean_email,
        "full_name": full_name_value,
        "plan": plan,
        "account_status": account_status,
        "trial_start": trial_start.isoformat(),
        "trial_end": trial_end.isoformat(),
    }

    if trial_metadata:
        payload.update(
            {
                "signup_ip": trial_metadata.get("signup_ip"),
                "signup_country": trial_metadata.get("signup_country"),
                "signup_city": trial_metadata.get("signup_city"),
                "city": trial_metadata.get("city"),
                "device_id": trial_metadata.get("device_id"),
                "device_fingerprint": trial_metadata.get("device_fingerprint"),
                "user_agent": trial_metadata.get("user_agent"),
                "browser": trial_metadata.get("browser", "UNKNOWN"),
                "operating_system": trial_metadata.get("operating_system", "UNKNOWN"),
                "trial_started_at": trial_metadata.get("trial_started_at") or trial_start.isoformat(),
                "trial_attempts": trial_metadata.get("trial_attempts", 1),
                "repeat_ips": trial_metadata.get("repeat_ips", 0),
                "repeat_devices": trial_metadata.get("repeat_devices", 0),
                "risk_score": trial_metadata.get("risk_score", 0),
                "fraud_flags": trial_metadata.get("fraud_flags", ""),
                "last_ip_activity": trial_metadata.get("last_ip_activity") or trial_start.isoformat(),
                "first_login_at": trial_metadata.get("first_login_at"),
                "last_login_at": trial_metadata.get("last_login_at"),
                "last_login_ip": trial_metadata.get("last_login_ip"),
                "last_login_country": trial_metadata.get("last_login_country"),
                "last_login_city": trial_metadata.get("last_login_city"),
                "total_logins": trial_metadata.get("total_logins", 0),
                "trial_whitelisted": trial_metadata.get("trial_whitelisted", False),
                "trial_ignored": trial_metadata.get("trial_ignored", False),
                "trial_blocked": trial_metadata.get("trial_blocked", False),
                "trial_notes": trial_metadata.get("trial_notes", ""),
            }
        )

    payload, _ = filter_canonical_payload(
        "user_profiles",
        payload,
        context="_create_profile_record",
        logger=_canonical_log,
    )

    if existing:
        target_user = str(existing_row.get("user_id") or user_id or "").strip()
        if target_user:
            client.table("user_profiles").update(payload).eq("user_id", target_user).execute()
        else:
            client.table("user_profiles").update(payload).eq("email", clean_email).execute()
        return _verified_user_row(client, "user_profiles", user_id) or _verified_row_by_email(client, "user_profiles", clean_email)
    client.table("user_profiles").insert(payload).execute()

    return _verified_user_row(client, "user_profiles", user_id)


def _create_subscription_record(client: Any, user_id: str, plan: str, status: str, email: str = "") -> list:
    existing = _verified_user_row(client, "subscriptions", user_id)

    payload = {
        "user_id": user_id,
        "plan": plan,
        "status": status,
    }
    payload, _ = filter_canonical_payload(
        "subscriptions",
        payload,
        context="_create_subscription_record",
        logger=_canonical_log,
    )

    if existing:
        existing_row = existing[0] if isinstance(existing[0], dict) else {}
        target_user = str(existing_row.get("user_id") or user_id or "").strip()
        if target_user:
            client.table("subscriptions").update(payload).eq("user_id", target_user).execute()
        return _verified_user_row(client, "subscriptions", user_id)

    client.table("subscriptions").insert(payload).execute()

    return _verified_user_row(client, "subscriptions", user_id)


def _create_workspace_record(client: Any, user_id: str, workspace_name: str = "Personal Workspace") -> list:
    existing = _verified_user_row(client, "workspaces", user_id)
    if existing:
        return existing

    payload = {
        "user_id": user_id,
        "workspace_name": workspace_name,
    }
    payload, _ = filter_canonical_payload(
        "workspaces",
        payload,
        context="_create_workspace_record",
        logger=_canonical_log,
    )

    client.table("workspaces").insert(payload).execute()

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

    full_name = str(meta.get("full_name") or meta.get("name") or "JFBP User")
    plan = str(meta.get("plan") or selected_plan or PLAN_MARKET_PULSE)
    account_status = str(meta.get("account_status") or ACCOUNT_TRIAL)
    canonical_trial_start, canonical_trial_end, trial_source = canonical_trial_window(auth_user)
    now = _utc_now()
    if canonical_trial_start is None or canonical_trial_end is None:
        canonical_trial_start = now
        canonical_trial_end = now + timedelta(days=TRIAL_LENGTH_DAYS)
        trial_source = "fallback_now"

    profile_before = _profile_row_for_auth_user(client, user_id, email)
    existing_trial_start = _parse_dt_or_none(profile_before.get("trial_start"))
    existing_trial_end = _parse_dt_or_none(profile_before.get("trial_end"))
    trial_start = existing_trial_start or canonical_trial_start
    trial_end = existing_trial_end or canonical_trial_end
    login_metadata = _login_metadata()
    merged_metadata = _merge_profile_metadata(meta, login_metadata)
    trial_metadata = {
        "signup_ip": merged_metadata.get("signup_ip"),
        "signup_country": merged_metadata.get("signup_country"),
        "signup_city": merged_metadata.get("signup_city"),
        "city": merged_metadata.get("city"),
        "device_id": merged_metadata.get("device_id"),
        "device_fingerprint": merged_metadata.get("device_fingerprint"),
        "user_agent": merged_metadata.get("user_agent"),
        "browser": merged_metadata.get("browser"),
        "operating_system": merged_metadata.get("operating_system"),
        "trial_started_at": profile_before.get("trial_started_at") or meta.get("trial_started_at") or trial_start.isoformat(),
        "trial_attempts": _safe_int(meta.get("trial_attempts"), 1),
        "repeat_ips": _safe_int(meta.get("repeat_ips"), 0),
        "repeat_devices": _safe_int(meta.get("repeat_devices"), 0),
        "risk_score": _safe_int(meta.get("risk_score"), 0),
        "fraud_flags": str(meta.get("fraud_flags") or ""),
        "last_ip_activity": meta.get("last_ip_activity") or trial_start.isoformat(),
        "first_login_at": meta.get("first_login_at"),
        "last_login_at": meta.get("last_login_at"),
        "last_login_ip": meta.get("last_login_ip"),
        "last_login_country": meta.get("last_login_country"),
        "last_login_city": meta.get("last_login_city"),
        "total_logins": _safe_int(meta.get("total_logins"), 0),
        "trial_whitelisted": _parse_bool(meta.get("trial_whitelisted")),
        "trial_ignored": _parse_bool(meta.get("trial_ignored")),
        "trial_blocked": _parse_bool(meta.get("trial_blocked")),
        "trial_notes": str(meta.get("trial_notes") or ""),
    }

    debug.update(
        {
            "plan": plan,
            "account_status": account_status,
            "trial_attempts": trial_metadata.get("trial_attempts", 1),
            "risk_score": trial_metadata.get("risk_score", 0),
            "trial_source": trial_source,
        }
    )

    steps: List[Dict[str, Any]] = []

    def _add_step(step_name: str, ok: bool, detail: str = "") -> None:
        steps.append({"step": step_name, "ok": ok, "detail": detail})

    _add_step("User Created", True, "Authenticated session verified")

    try:
        trial_before_ready = bool(
            str(profile_before.get("trial_start") or "").strip()
            and str(profile_before.get("trial_end") or "").strip()
        )

        profile_rows = _create_profile_record(
            client=client,
            user_id=user_id,
            email=email,
            full_name=full_name,
            plan=plan,
            account_status=account_status,
            trial_start=trial_start,
            trial_end=trial_end,
            trial_metadata=trial_metadata,
        )
        if profile_rows:
            _add_step("Profile Created", True)
            _add_step("Customer Created", True)
        else:
            _add_step("Profile Created", False, "No profile row returned")
            _add_step("Customer Created", False, "No customer/profile row returned")

        profile_row = profile_rows[0] if profile_rows and isinstance(profile_rows[0], dict) else {}
        trial_ready = bool(str(profile_row.get("trial_start") or "").strip() and str(profile_row.get("trial_end") or "").strip())
        trial_created = (not trial_before_ready) and trial_ready
        _add_step("Trial Created", trial_ready, "Missing trial_start/trial_end" if not trial_ready else "")

        subscription_rows = _create_subscription_record(
            client=client,
            user_id=user_id,
            plan=plan,
            status=account_status,
            email=email,
        )
        _add_step("Subscription Created", bool(subscription_rows), "No subscription row returned" if not subscription_rows else "")

        workspace_rows: list = []
        workspace_error = ""
        try:
            workspace_rows = _create_workspace_record(
                client=client,
                user_id=user_id,
                workspace_name=f"{full_name.strip() or 'Personal'} Workspace",
            )
        except Exception as ws_exc:
            workspace_error = str(ws_exc)

        debug.update(
            {
                "user_profiles_rows": len(profile_rows),
                "subscriptions_rows": len(subscription_rows),
                "workspaces_rows": len(workspace_rows),
                "workspace_error": workspace_error,
                "provisioning_steps": steps,
            }
        )

        failed_steps = [step for step in steps if not bool(step.get("ok"))]
        provisioning_ok = not failed_steps

        provisioning_note = _provisioning_step_summary(steps)
        if provisioning_ok:
            _add_step("Provisioning Completed", True)
        else:
            _add_step("Provisioning Completed", False, failed_steps[0].get("step", "Unknown step"))

        profile_row = profile_rows[0] if profile_rows and isinstance(profile_rows[0], dict) else {}
        notification_cache = set(st.session_state.get("saas_founder_notify_users", set()) or set())
        trial_notification_sent = user_id in notification_cache

        if provisioning_ok and trial_created and not trial_notification_sent:
            ok_count = sum(1 for step in steps if bool(step.get("ok")))
            onboarding_progress = f"{ok_count}/{len(steps)}"
            notify_payload = {
                "name": full_name,
                "email": email,
                "plan": PLAN_LABELS.get(plan, plan),
                "trial_start": _dt_text(profile_row.get("trial_start") or trial_start),
                "trial_end": _dt_text(profile_row.get("trial_end") or trial_end),
                "created_at": _dt_text(profile_row.get("created_at") or getattr(auth_user, "created_at", None)),
                "last_login": _dt_text(profile_row.get("last_login_at") or getattr(auth_user, "last_sign_in_at", None)),
                "onboarding_progress": onboarding_progress,
                "provisioning_status": "Provisioning Completed",
            }
            notify_ok, notify_msg = _send_founder_trial_started_email(notify_payload)
            _add_step("Founder Notification Sent", notify_ok, "" if notify_ok else notify_msg)

            if notify_ok:
                notification_cache.add(user_id)
                st.session_state["saas_founder_notify_users"] = notification_cache
                _add_step("Founder Notification Marked", True)

        if profile_rows and isinstance(profile_rows[0], dict):
            profile_row = profile_rows[0]
            note_text = _append_provisioning_note(profile_row, _provisioning_step_summary(steps))
            st.session_state["saas_last_provisioning_note"] = note_text

        st.session_state["saas_onboarding_debug"] = debug

        if not provisioning_ok:
            failed = failed_steps[0] if failed_steps else {"step": "Unknown", "detail": ""}
            return (
                False,
                "Onboarding incomplete. "
                f"Failed at: {failed.get('step')}"
                + (f" ({failed.get('detail')})" if failed.get("detail") else "")
                + ". Check RLS policies and the active Supabase session.",
            )

        message_parts = ["Profile and subscription records are verified."]
        if workspace_error:
            message_parts.append("Workspace sync skipped due to workspace table constraints.")

        return True, " ".join(message_parts)

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

    user_id = _auth_user_id(auth_user)
    email = _auth_user_email(auth_user)

    # Stripe updates public.user_profiles. Auth metadata may still contain the
    # original trial plan, so database values must win after login.
    client = get_supabase_client()
    profile = _profile_row_for_auth_user(client, user_id, email)
    sub_rows = _verified_user_row(client, "subscriptions", user_id) if (client is not None and user_id) else []
    subscription_row = sub_rows[0] if sub_rows and isinstance(sub_rows[0], dict) else {}

    full_name = (
        profile.get("full_name")
        or meta.get("full_name")
        or meta.get("name")
        or "JFBP User"
    )
    role = _authoritative_role_from_auth_user(auth_user).lower() or "user"
    plan = (
        subscription_row.get("plan")
        or profile.get("plan")
        or meta.get("plan")
        or selected_plan
        or st.session_state.get("saas_selected_plan")
        or PLAN_MARKET_PULSE
    )
    plan = str(plan or PLAN_MARKET_PULSE).strip().upper() or PLAN_MARKET_PULSE
    if plan not in {PLAN_MARKET_PULSE, PLAN_PRO, PLAN_ELITE}:
        plan = PLAN_MARKET_PULSE

    raw_trial_start = profile.get("trial_start")
    raw_trial_end = profile.get("trial_end")

    account_status = str(
        profile.get("account_status")
        or meta.get("account_status")
        or ACCOUNT_TRIAL
    ).strip().upper()
    if not account_status:
        account_status = ACCOUNT_TRIAL

    subscription_status = str(
        subscription_row.get("status")
        or account_status
        or ""
    ).strip().upper()
    provisioning_required = not bool(raw_trial_start and raw_trial_end) and subscription_status != ACCOUNT_ACTIVE

    if role == "admin":
        role = "admin"
        plan = PLAN_ELITE
        account_status = ACCOUNT_ACTIVE

    canonical_trial_start, canonical_trial_end, _ = canonical_trial_window(auth_user)
    if role == "admin":
        trial_start = _parse_dt(raw_trial_start, fallback=canonical_trial_start or now)
        trial_end = _parse_dt(
            raw_trial_end,
            fallback=trial_start + timedelta(days=3650),
        )
    else:
        trial_start = _parse_dt(raw_trial_start, fallback=canonical_trial_start or now)
        trial_end = _parse_dt(
            raw_trial_end,
            fallback=canonical_trial_end or (trial_start + timedelta(days=TRIAL_LENGTH_DAYS)),
        )

    return SaaSUser(
        user_id=user_id,
        email=email,
        full_name=str(full_name),
        plan=str(plan),
        account_status=str(account_status),
        trial_start=trial_start,
        trial_end=trial_end,
        created_at=_parse_dt(getattr(auth_user, "created_at", None), fallback=now),
        source="supabase",
        role=role,
        subscription_status=subscription_status,
        provisioning_required=provisioning_required,
    )


def authenticate_user(auth_response: Any) -> tuple[Any, Any, str]:
    user = _auth_response_user(auth_response)
    session = _auth_response_session(auth_response)
    access_token, _ = _get_session_tokens(session)
    _set_auth_debug(
        "authenticate_user",
        {
            "has_user": user is not None,
            "has_session": session is not None,
            "has_access_token": bool(access_token),
            "user_id": _auth_user_id(user) if user is not None else "",
        },
    )
    return user, session, access_token


def _revoke_superseded_browser_sessions(store: Any, user_id: str, browser_fingerprint: str) -> int:
    """Revoke active durable sessions that should be superseded for this browser.

    Invariant target: one active durable session per browser/device.
    """
    uid = str(user_id or "").strip()
    if store is None or not uid:
        return 0

    current_session_id = str(st.session_state.get("saas_app_session_id", "") or "").strip()
    fp = str(browser_fingerprint or "").strip()

    try:
        active_sessions = store.active_sessions_for_user(uid)
    except Exception:
        return 0

    revoked = 0
    for record in active_sessions:
        sid = str(getattr(record, "id", "") or "").strip()
        if not sid:
            continue

        metadata = getattr(record, "client_metadata", {})
        record_fp = ""
        if isinstance(metadata, dict):
            record_fp = str(metadata.get("browser_fingerprint", "") or "").strip()

        should_revoke = bool(fp and record_fp and record_fp == fp)
        if current_session_id and sid == current_session_id:
            should_revoke = True

        if not should_revoke:
            continue

        try:
            revoked += int(store.revoke_session(sid, reason="SESSION_SUPERSEDED"))
        except Exception:
            continue

    return revoked


def _resolve_current_app_session_id(store: Any) -> tuple[str, str]:
    current_session_id = str(st.session_state.get("saas_app_session_id", "") or "").strip()
    if current_session_id:
        return current_session_id, "session_state"

    key = _browser_auth_cache_key()
    if key:
        cached_payload = _auth_session_cache().get(key, {})
        cached_session_id = str(cached_payload.get("app_session_id", "") or "").strip() if isinstance(cached_payload, dict) else ""
        if cached_session_id:
            st.session_state["saas_app_session_id"] = cached_session_id
            return cached_session_id, "auth_cache"

    if store is None:
        return "", "store_unavailable"

    cookie_result = _read_session_cookie_result()
    cookie_value = str(cookie_result.value or "").strip()
    if not cookie_value:
        return "", f"cookie_{cookie_result.state or 'absent'}"

    try:
        raw_handle = _unsign_session_handle(cookie_value)
    except Exception:
        _clear_session_cookie()
        _mark_cookie_readiness_absent()
        return "", "cookie_invalid"

    try:
        lookup = store.get_session_by_handle(raw_handle)
    except Exception:
        return "", "lookup_failed"

    if lookup.record is None:
        status_name = str(getattr(lookup, "status", "missing") or "missing").lower()
        if lookup.status in {
            SessionLookupStatus.MISSING,
            SessionLookupStatus.REVOKED,
            SessionLookupStatus.IDLE_EXPIRED,
            SessionLookupStatus.ABSOLUTE_EXPIRED,
            SessionLookupStatus.MALFORMED,
        }:
            _clear_session_cookie()
            _mark_cookie_readiness_absent()
        return "", f"lookup_{status_name}"

    resolved_session_id = str(getattr(lookup.record, "id", "") or "").strip()
    if resolved_session_id:
        st.session_state["saas_app_session_id"] = resolved_session_id
        return resolved_session_id, "cookie_lookup"

    return "", "lookup_missing_id"


def _revoke_current_app_session(reason: str = "USER_LOGOUT") -> tuple[bool, str]:
    store = _session_store()
    if store is None:
        return False, "session_store_unavailable"

    session_id, source = _resolve_current_app_session_id(store)
    if not session_id:
        _clear_session_cookie()
        _mark_cookie_readiness_absent()
        return False, f"session_unresolved:{source}"

    try:
        revoked_count = int(store.revoke_session(session_id, reason=reason))
    except Exception:
        return False, f"revoke_failed:{source}"

    return revoked_count > 0, source


def initialize_session(user: Any, session: Any, selected_plan: str | None = None) -> Any:
    new_user_id = _auth_user_id(user)
    old_user = st.session_state.get("saas_user")
    old_user_id = str(getattr(old_user, "user_id", "") or "")
    if old_user_id and old_user_id != new_user_id:
        _revoke_current_app_session(reason="IDENTITY_SWITCH")
        _clear_cached_authenticated_session()
        _clear_session_cookie()
        clear_stripe_checkout_state()
        st.session_state["saas_admin_override"] = False

    client = get_supabase_client()
    session_applied = False
    if client is not None:
        session_applied = _apply_auth_session_to_client(client, session)

    session_payload = _session_cache_payload(session)
    st.session_state["saas_auth_session"] = session_payload
    st.session_state["saas_user"] = build_saas_user_from_auth(user, selected_plan=selected_plan)
    st.session_state["saas_logged_in"] = True

    # Phase 9A.3 durable app session integration (primary persistence).
    store = _session_store()
    refresh_material = str(session_payload.get("refresh_token", "") or "").strip()
    user_id = _auth_user_id(user)
    cookie_write_ok = False
    if store is not None and user_id and refresh_material:
        browser_fingerprint = _browser_auth_cache_key()
        _revoke_superseded_browser_sessions(store, user_id, browser_fingerprint)
        remember_me = bool(st.session_state.get("saas_remember_me", False))
        created = store.create_session(
            SessionCreationInput(
                user_id=user_id,
                remember_me=remember_me,
                user_agent=_user_agent(_request_headers()),
                client_metadata={
                    "browser_fingerprint": browser_fingerprint,
                },
                refresh_material=refresh_material,
            )
        )
        st.session_state["saas_app_session_id"] = created.record.id
        cookie_write_ok = _set_session_cookie(created.raw_handle, remember_me=remember_me)

    _cache_authenticated_session(session_payload)

    _clear_cookie_readiness_state()

    _set_auth_debug(
        "initialize_session",
        {
            "old_user_id": old_user_id,
            "new_user_id": new_user_id,
            "session_applied_to_client": session_applied,
        },
    )
    return client


def ensure_user_profile(user: Any, selected_plan: str | None, session: Any, client: Any) -> tuple[bool, str, Dict[str, Any]]:
    onboarding_ok, onboarding_message = ensure_user_workspace_records(
        user,
        selected_plan=selected_plan,
        auth_session=session,
    )
    refreshed_profile = (
        _profile_row_for_auth_user(client, _auth_user_id(user), _auth_user_email(user))
        if client is not None
        else {}
    )
    _set_auth_debug(
        "ensure_user_profile",
        {
            "onboarding_ok": onboarding_ok,
            "onboarding_message": onboarding_message,
            "profile_found": bool(refreshed_profile),
        },
    )
    return onboarding_ok, onboarding_message, refreshed_profile


def capture_login_metadata() -> Dict[str, Any]:
    metadata = _collect_login_metadata()
    _set_auth_debug(
        "capture_login_metadata",
        {
            "last_login_ip": metadata.get("last_login_ip"),
            "last_login_country": metadata.get("last_login_country"),
            "last_login_city": metadata.get("last_login_city"),
            "device_fingerprint": metadata.get("device_fingerprint"),
        },
    )
    return metadata


def persist_login_metadata(client: Any, user: Any, profile_row: Dict[str, Any], login_metadata: Dict[str, Any]) -> tuple[bool, str]:
    user_id = _auth_user_id(user)
    login_ok, login_message, payload, _ = _save_login_metadata(
        client=client,
        user_id=user_id,
        profile_row=profile_row,
        login_metadata=login_metadata,
    )
    _record_metadata_debug(login_ok, login_message, login_metadata)

    if login_ok:
        st.session_state["saas_metadata_debug_message"] = "✓ Metadata write successful"
    else:
        st.session_state["saas_metadata_debug_message"] = f"✗ Metadata write failed:\n{login_message}"

    _set_auth_debug(
        "persist_login_metadata",
        {
            "ok": login_ok,
            "message": login_message,
            "payload_keys": sorted(list(payload.keys())),
            "user_id": user_id,
        },
    )
    return login_ok, login_message


def finalize_login(user: Any, selected_plan: str | None, onboarding_ok: bool, onboarding_message: str) -> None:
    st.session_state["saas_user"] = build_saas_user_from_auth(user, selected_plan=selected_plan)
    st.session_state["saas_auth_last_message"] = onboarding_message
    st.session_state["saas_onboarding_ready"] = onboarding_ok
    _set_auth_debug(
        "finalize_login",
        {
            "onboarding_ok": onboarding_ok,
            "onboarding_message": onboarding_message,
        },
    )


def set_authenticated_session(auth_response: Any, selected_plan: str | None = None) -> bool:
    """Store a real logged-in session and run onboarding.

    v1.3.2 fix: signup responses may contain a user but no session when email
    confirmation is required. In that case we must NOT mark the user as logged
    in and must NOT attempt RLS-protected inserts.
    """
    try:
        _reset_auth_debug()
        user, session, access_token = authenticate_user(auth_response)

        if user is None:
            return False

        if not access_token:
            production_auth_trace(
                "DURABLE_SESSION_CREATE_FAILED",
                "set_authenticated_session",
                user_present=bool(user),
                session_present=bool(session),
                access_token_present=False,
                reason="missing_access_token",
            )
            clear_stripe_checkout_state()
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
            _set_auth_debug(
                "missing_session",
                {
                    "user_id": _auth_user_id(user),
                    "email": _auth_user_email(user),
                },
            )
            return False

        production_auth_trace(
            "DURABLE_SESSION_CREATE_START",
            "set_authenticated_session",
            user_present=bool(user),
            session_present=bool(session),
            access_token_present=bool(access_token),
        )
        client = initialize_session(user, session, selected_plan=selected_plan)
        production_auth_trace(
            "DURABLE_SESSION_CREATE_SUCCESS",
            "set_authenticated_session",
            user_present=bool(user),
            session_present=bool(session),
            client_present=bool(client),
        )
        if not _enforce_identity_binding_contract(
            "post_login",
            login_user=user,
            login_session=session,
            client=client,
        ):
            return False
        onboarding_ok, onboarding_message, refreshed_profile = ensure_user_profile(
            user=user,
            selected_plan=selected_plan,
            session=session,
            client=client,
        )

        if client is not None and refreshed_profile:
            runtime_metadata = capture_login_metadata()
            persist_login_metadata(
                client=client,
                user=user,
                profile_row=refreshed_profile,
                login_metadata=runtime_metadata,
            )
        else:
            profile_error = "Profile row unavailable for metadata update."
            _record_metadata_debug(False, profile_error)
            st.session_state["saas_metadata_debug_message"] = f"✗ Metadata write failed:\n{profile_error}"

        production_auth_trace(
            "SESSION_STATE_WRITE_START",
            "set_authenticated_session",
            user_present=bool(user),
            session_present=bool(session),
        )
        finalize_login(
            user=user,
            selected_plan=selected_plan,
            onboarding_ok=onboarding_ok,
            onboarding_message=onboarding_message,
        )
        st.session_state["saas_rehydrate_blocked"] = False
        production_auth_trace(
            "SESSION_STATE_WRITE_SUCCESS",
            "set_authenticated_session",
            user_present=bool(st.session_state.get("saas_user")),
            session_present=bool(st.session_state.get("saas_auth_session")),
        )
        return True

    except Exception as exc:
        production_auth_trace("DURABLE_SESSION_CREATE_FAILED", "set_authenticated_session", exc=exc)
        st.session_state["saas_auth_last_message"] = f"Session setup failed: {exc}"
        return False


def clear_authenticated_session(*, revoke_current: bool = True, reason: str = "USER_LOGOUT") -> tuple[bool, str]:
    revoke_ok = True
    revoke_detail = "not_attempted"
    if revoke_current:
        revoke_ok, revoke_detail = _revoke_current_app_session(reason=reason)

    _clear_cached_authenticated_session()
    _clear_session_cookie()
    _clear_cookie_readiness_state()
    clear_active_page_cache()
    clear_stripe_checkout_state()
    st.session_state["saas_logged_in"] = False
    st.session_state["saas_user"] = None
    st.session_state["saas_auth_session"] = None
    st.session_state["saas_app_session_id"] = ""
    st.session_state["saas_identity_bound_user_id"] = ""
    st.session_state["saas_admin_override"] = False
    st.session_state["saas_onboarding_ready"] = False
    st.session_state["saas_onboarding_debug"] = {}
    st.session_state["saas_auth_debug"] = {}
    st.session_state["saas_metadata_debug_message"] = ""
    st.session_state["saas_provisioning_repair_attempts"] = {}
    return revoke_ok, revoke_detail


# =========================================================
# AUTH ACTIONS
# =========================================================

def supabase_sign_up(email: str, password: str, full_name: str, plan: str) -> tuple[bool, str]:
    ready, message = supabase_ready()
    if not ready:
        return False, message

    client = get_supabase_client()
    now = _utc_now()
    trial_end = now + timedelta(days=TRIAL_LENGTH_DAYS)
    signup_plan = str(plan or PLAN_MARKET_PULSE).strip().upper()
    if signup_plan not in PLAN_LABELS:
        signup_plan = PLAN_MARKET_PULSE
    clean_email = email.strip().lower()
    st.session_state["saas_trial_warning_message"] = ""

    signup_context = _signup_fingerprint()
    trial_protection = evaluate_trial_protection(clean_email, signup_context)
    if blocked := bool(trial_protection.get("blocked")):
        st.session_state["saas_trial_warning_message"] = ""
        return False, str(trial_protection.get("message") or "The free trial has already been used. Please subscribe or contact support if you believe this is an error.")

    if bool(trial_protection.get("warning")):
        st.session_state["saas_trial_warning_message"] = str(
            trial_protection.get("message") or "It looks like a trial has already been used from this network."
        )

    try:
        signup_options: Dict[str, Any] = {
            "data": {
                "full_name": full_name.strip() or "JFBP User",
                "plan": signup_plan,
                "account_status": ACCOUNT_TRIAL,
                "signup_ip": signup_context.get("signup_ip", "UNKNOWN"),
                "signup_country": signup_context.get("signup_country", "UNKNOWN"),
                "signup_city": signup_context.get("signup_city", "UNKNOWN"),
                "city": signup_context.get("city", "UNKNOWN"),
                "device_id": signup_context.get("device_id", "UNKNOWN"),
                "device_fingerprint": signup_context.get("device_fingerprint", "UNKNOWN"),
                "user_agent": signup_context.get("user_agent", "UNKNOWN"),
                "browser": signup_context.get("browser", "UNKNOWN"),
                "operating_system": signup_context.get("operating_system", "UNKNOWN"),
                "trial_started_at": signup_context.get("trial_started_at", now.isoformat()),
                "trial_attempts": trial_protection.get("trial_attempts", 1),
                "repeat_ips": trial_protection.get("repeat_ips", 0),
                "repeat_devices": trial_protection.get("repeat_devices", 0),
                "risk_score": trial_protection.get("risk_score", 0),
                "fraud_flags": trial_protection.get("fraud_flags", ""),
                "last_ip_activity": trial_protection.get("last_ip_activity", now.isoformat()),
                "first_login_at": None,
                "last_login_at": None,
                "last_login_ip": None,
                "last_login_country": None,
                "last_login_city": None,
                "total_logins": 0,
                "trial_whitelisted": False,
                "trial_ignored": False,
                "trial_blocked": blocked,
                "trial_notes": "",
            }
        }
        email_redirect_to = _signup_email_redirect_to()
        if email_redirect_to:
            signup_options["redirect_to"] = email_redirect_to
            signup_options["email_redirect_to"] = email_redirect_to

        redirect_meta = st.session_state.get("_phase10b_signup_redirect_meta", {})
        _log_phase10b_redirect_diagnostic(
            "supabase_sign_up_pre_call",
            {
                "selected_source": str(redirect_meta.get("selected_source", "FALLBACK") or "FALLBACK"),
                "email_redirect_to_classification": _classify_redirect_value(email_redirect_to),
                "redirect_to_classification": _classify_redirect_value(str(signup_options.get("redirect_to", "") or "")),
                "commit_hash": _runtime_commit_hash(),
                "app_hostname": _runtime_app_hostname(),
            },
        )

        response = client.auth.sign_up(
            {
                "email": clean_email,
                "password": password,
                "options": signup_options,
            }
        )

        # If Supabase returns a real authenticated session, finish onboarding now.
        if set_authenticated_session(response, selected_plan=signup_plan):
            return True, "Account created. 30-day trial and workspace are ready."

        # With email verification enabled, signup can succeed without an active
        # session. This should be treated as success and keeps enumeration-safe
        # behavior because the message is generic.
        return True, "Account created. Check your email to verify your account."

    except Exception as exc:
        classification, user_message, sanitized_error = _signup_error_response(exc)
        _log_signup_failure_diagnostic(classification, sanitized_error)
        return False, user_message


def supabase_login(email: str, password: str) -> tuple[bool, str]:
    production_auth_trace("LOGIN_BRANCH_ENTERED", "supabase_login")
    ready, message = supabase_ready()
    if not ready:
        production_auth_trace(
            "SUPABASE_LOGIN_REJECTED",
            "supabase_login",
            reason="supabase_not_ready",
        )
        return False, message

    client = get_supabase_client()
    clean_email = str(email or "").strip().lower()
    password_value = password if isinstance(password, str) else str(password or "")

    # Explicit password-login attempts must not inherit previously restored identity.
    st.session_state["saas_rehydrate_blocked"] = True
    production_auth_trace("PRE_LOGIN_SESSION_CLEAR_START", "supabase_login")
    try:
        clear_authenticated_session(revoke_current=True, reason="LOGIN_ATTEMPT_RESET")
        production_auth_trace("PRE_LOGIN_SESSION_CLEAR_SUCCESS", "supabase_login")
    except Exception as exc:
        production_auth_trace("PRE_LOGIN_SESSION_CLEAR_FAILED", "supabase_login", exc=exc)
        raise
    try:
        if client is not None:
            client.auth.sign_out()
    except Exception:
        pass

    try:
        production_auth_trace("SUPABASE_LOGIN_CALL_START", "supabase_login")
        response = client.auth.sign_in_with_password(
            {
                "email": clean_email,
                "password": password_value,
            }
        )

        diag_user = _auth_response_user(response)
        diag_session = _auth_response_session(response)
        diag_access, diag_refresh = _get_session_tokens(diag_session)
        production_auth_trace(
            "AUTH_TOKENS_PRESENT",
            "supabase_login",
            user_present=bool(diag_user),
            session_present=bool(diag_session),
            access_token_present=bool(diag_access),
            refresh_token_present=bool(diag_refresh),
        )
        if set_authenticated_session(response):
            production_auth_trace("SUPABASE_LOGIN_SUCCESS", "supabase_login")
            onboarding_message = st.session_state.get("saas_auth_last_message", "")
            if st.session_state.get("saas_onboarding_ready", False):
                return True, "Login successful. " + onboarding_message
            return True, "Login successful. " + onboarding_message

        production_auth_trace(
            "SUPABASE_LOGIN_REJECTED",
            "supabase_login",
            reason="set_authenticated_session_returned_false",
        )
        clear_authenticated_session(revoke_current=False, reason="LOGIN_FAILED")
        st.session_state["saas_rehydrate_blocked"] = True
        return False, "Login failed. No authenticated user session returned."

    except Exception as exc:
        production_auth_trace("SUPABASE_LOGIN_EXCEPTION", "supabase_login", exc=exc)
        production_auth_trace("SUPABASE_LOGIN_REJECTED", "supabase_login", exc=exc)
        clear_authenticated_session(revoke_current=False, reason="LOGIN_FAILED")
        st.session_state["saas_rehydrate_blocked"] = True
        return False, f"Login failed: {exc}"


def supabase_logout() -> tuple[bool, str]:
    revoke_ok, revoke_detail = clear_authenticated_session(revoke_current=True, reason="USER_LOGOUT")

    client = get_supabase_client()
    try:
        if client is not None:
            client.auth.sign_out()
    except Exception:
        pass

    if revoke_ok:
        return True, "Logged out."

    diagnostic = f"Logged out locally. Durable session revocation could not be confirmed ({revoke_detail})."
    st.session_state["saas_auth_last_message"] = diagnostic
    return False, diagnostic


def supabase_logout_all() -> tuple[bool, str]:
    user = get_current_user()
    user_id = str(getattr(user, "user_id", "") or "").strip() if user is not None else ""

    if user_id:
        store = _session_store()
        if store is not None:
            try:
                store.revoke_all_sessions_for_user(user_id, reason="USER_LOGOUT_ALL")
            except Exception:
                pass

    clear_authenticated_session(revoke_current=False)
    return True, "Logged out from all sessions."


def supabase_reset_password(email: str) -> tuple[bool, str, Dict[str, Any]]:
    ready, message = supabase_ready()
    if not ready:
        return False, message, {"status_code": None, "error_code": "", "body": "", "headers": {}}

    email_value = email.strip().lower()

    url = str(st.secrets.get("SUPABASE_URL", "") or "").strip().rstrip("/")
    key = str(st.secrets.get("SUPABASE_ANON_KEY", "") or "").strip()

    if not url or not key:
        return False, "Password reset failed: Supabase credentials unavailable.", {
            "status_code": None,
            "error_code": "",
            "body": "",
            "headers": {},
        }

    endpoint = f"{url}/auth/v1/recover"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "email": email_value,
    }
    query = {
        "redirect_to": _password_reset_redirect_to(),
    }

    try:
        response = requests.post(endpoint, headers=headers, params=query, json=payload, timeout=30)

        meta: Dict[str, Any] = {
            "status_code": int(response.status_code),
            "error_code": "",
            "body": response.text,
            "headers": dict(response.headers),
            "request_url": getattr(getattr(response, "request", None), "url", ""),
        }

        parsed = {}
        try:
            parsed = response.json() if response.text else {}
        except Exception:
            parsed = {}

        if isinstance(parsed, dict):
            meta["error_code"] = str(parsed.get("error_code", "") or "").strip().lower()

        raw_message = ""
        if isinstance(parsed, dict):
            raw_message = str(
                parsed.get("msg")
                or parsed.get("error_description")
                or parsed.get("message")
                or parsed.get("error")
                or ""
            ).strip()
        if not raw_message:
            raw_message = str(response.text or "").strip()

        if response.status_code < 400:
            return True, "Password reset email sent.", meta

        error_message = ""
        if isinstance(parsed, dict):
            error_message = raw_message
        if not error_message:
            error_message = str(response.text or "Unknown Supabase error").strip()

        return False, f"Password reset failed: {error_message}", meta
    except Exception as exc:
        return False, f"Password reset failed: {exc}", {
            "status_code": None,
            "error_code": "",
            "body": "",
            "headers": {},
        }


# =========================================================
# ACCESS CONTROL
# =========================================================

def get_current_user() -> SaaSUser | None:
    user = st.session_state.get("saas_user")
    if isinstance(user, SaaSUser):
        production_auth_trace(
            "AUTHENTICATED_BRANCH_ENTERED",
            "get_current_user",
            user_present=True,
            session_present=bool(st.session_state.get("saas_auth_session")),
        )
        return user
    return None


def trial_days_remaining(user: SaaSUser) -> int:
    remaining = user.trial_end - _utc_now()
    return max(0, remaining.days)


def resolve_access_state(user: SaaSUser) -> str:
    if is_admin_user(user):
        return "active"

    today = _utc_now()
    subscription_status = str(getattr(user, "subscription_status", "") or user.account_status or "").strip().lower()

    if subscription_status == "active":
        return "active"

    if bool(getattr(user, "provisioning_required", False)):
        return "provisioning_required"

    trial_end = getattr(user, "trial_end", None)
    if isinstance(trial_end, datetime):
        if today <= trial_end:
            return "trial"
        return "expired"

    return "provisioning_required"


def _auto_repair_provisioning(user: SaaSUser, trigger: str = "") -> tuple[bool, str]:
    """Attempt one authenticated onboarding repair for a locked trial user."""
    user_id = str(getattr(user, "user_id", "") or "").strip()
    if not user_id:
        return False, "Provisioning recovery failed: missing user_id."

    attempts = dict(st.session_state.get("saas_provisioning_repair_attempts", {}) or {})
    attempt_count = int(attempts.get(user_id, 0) or 0)
    if attempt_count >= 1:
        return False, "Provisioning is still incomplete. Use 'Verify my SaaS onboarding rows' in SaaS Core for detailed diagnostics."

    attempts[user_id] = attempt_count + 1
    st.session_state["saas_provisioning_repair_attempts"] = attempts

    client = get_supabase_client()
    if client is None:
        return False, "Provisioning recovery failed: Supabase client unavailable."

    session_payload = st.session_state.get("saas_auth_session")
    if not _apply_auth_session_to_client(client, session_payload):
        return False, "Provisioning recovery failed: authenticated session missing. Please log out and log in again."

    auth_user = None
    try:
        auth_user = _auth_response_user(client.auth.get_user())
    except Exception:
        auth_user = None

    if auth_user is None:
        auth_user = SimpleNamespace(
            id=user.user_id,
            email=user.email,
            created_at=user.created_at,
            user_metadata={
                "full_name": user.full_name,
                "plan": user.plan,
                "account_status": user.account_status,
                "role": user.role,
            },
        )

    onboarding_ok, onboarding_message = ensure_user_workspace_records(
        auth_user,
        selected_plan=user.plan,
        auth_session=session_payload,
    )
    st.session_state["saas_onboarding_ready"] = onboarding_ok
    st.session_state["saas_auth_last_message"] = onboarding_message
    st.session_state["saas_user"] = build_saas_user_from_auth(auth_user, selected_plan=user.plan)

    _set_auth_debug(
        "auto_repair_provisioning",
        {
            "user_id": user_id,
            "trigger": trigger,
            "ok": onboarding_ok,
            "message": onboarding_message,
        },
    )

    return onboarding_ok, onboarding_message


def is_account_open(user: SaaSUser) -> bool:
    if is_admin_user(user):
        return True

    if user.account_status in {ACCOUNT_SUSPENDED, ACCOUNT_EXPIRED, ACCOUNT_PAST_DUE}:
        return False

    return resolve_access_state(user) in {"active", "trial"}


def can_access_page(user: SaaSUser, page_name: str) -> bool:
    if is_admin_user(user):
        return True

    if not is_account_open(user):
        return False

    return page_name in PLAN_PAGES.get(user.plan, set())


def require_page_access(page_name: str) -> bool:
    user = get_current_user()

    if user is None:
        render_login_required(page_name)
        return False

    if resolve_access_state(user) == "provisioning_required":
        repaired, _ = _auto_repair_provisioning(user, trigger=f"require_page_access:{page_name}")
        if repaired:
            refreshed_user = get_current_user()
            if refreshed_user is not None:
                user = refreshed_user

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
            .saas-hero {border:1px solid #dbeafe;background:#eff6ff;border-radius:18px;padding:0.82rem 0.9rem;margin:0.50rem auto 0.72rem auto;max-width:760px;}
            .saas-kicker {font-size:var(--jfbp-type-card-label);text-transform:uppercase;letter-spacing:0.055em;color:#475569;font-weight:850;margin-bottom:0.22rem;}
            .saas-title {font-size:clamp(1.22rem,2.35vw,1.62rem);line-height:1.14;font-weight:880;color:#0f172a;margin-bottom:0.30rem;}
            .saas-text {font-size:var(--jfbp-type-body);line-height:1.38;color:#334155;font-weight:700;margin-bottom:0;}
            .saas-auth-form {max-width:580px;margin:0 auto;}
            .saas-auth-shell {max-width:580px;margin:0 auto;}
            .saas-auth-shell div[data-testid="stForm"] {max-width:580px;margin-left:auto;margin-right:auto;}
            .saas-auth-shell div[data-testid="stTextInput"] input {min-height:40px;padding:0.66rem 0.96rem;border-radius:10px;}
            .saas-auth-shell div[data-testid="stFormSubmitButton"] button {width:100%;}
            .stButton>button {min-height:40px;border-radius:11px;font-size:0.92rem;}
            .saas-card-grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,230px),1fr));gap:0.85rem;margin:0.7rem 0 1rem 0;}
            .saas-card {border:1px solid #dbe3ef;border-radius:16px;background:#f8fafc;padding:0.9rem 1rem;min-height:105px;}
            .saas-label {font-size:var(--jfbp-type-card-label);color:#64748b;letter-spacing:0.05em;text-transform:uppercase;font-weight:850;margin-bottom:0.30rem;}
            .saas-value {font-size:var(--jfbp-type-card-value);line-height:1.14;color:#111827;font-weight:880;overflow-wrap:anywhere;}
            .saas-detail {margin-top:0.30rem;color:#475569;font-size:var(--jfbp-type-caption);line-height:1.35;}
            .saas-lock {border:1px solid #fecaca;background:#fef2f2;border-radius:18px;padding:1rem;margin:1rem 0;}
            .saas-upgrade {border:1px solid #fde68a;background:#fffbeb;border-radius:18px;padding:1rem;margin:1rem 0;}
            .saas-ok {border:1px solid #bbf7d0;background:#ecfdf5;border-radius:18px;padding:0.85rem 1rem;margin:0.75rem 0;color:#166534;font-weight:850;}
            .saas-warn {border:1px solid #fde68a;background:#fffbeb;border-radius:18px;padding:0.85rem 1rem;margin:0.75rem 0;color:#92400e;font-weight:850;}
            .saas-auth-shell .stMarkdown,
            .saas-auth-shell .stCaption,
            .saas-auth-shell .stInfo,
            .saas-auth-shell .stWarning,
            .saas-auth-shell .stSuccess,
            .saas-auth-shell .stError {
                overflow-wrap:anywhere;
                word-break:break-word;
            }
            .saas-auth-shell .stRadio [role="radiogroup"] {
                flex-wrap:wrap;
                row-gap:0.35rem;
            }
            @media (max-width: 820px) {
                .saas-auth-form, .saas-auth-shell {max-width:100%;}
                .saas-auth-shell div[data-testid="stForm"] {max-width:100%;}
                .saas-auth-shell div[data-testid="stFormSubmitButton"] button,
                .saas-auth-shell .stButton>button {width:100%;}
                .saas-auth-shell {padding-left:0.15rem; padding-right:0.15rem;}
                .saas-auth-shell .saas-hero {padding-left:0.8rem; padding-right:0.8rem;}
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def card(label: str, value: str, detail: str = "") -> str:
    return (
        '<div class="jfbp-card">'
        f'<div class="jfbp-card-label">{label}</div>'
        f'<div class="jfbp-card-value">{value}</div>'
        f'<div class="jfbp-card-detail">{detail}</div>'
        '</div>'
    )


def get_stripe_price_id(plan: str) -> str:
    """Return Stripe Price ID for a subscription plan from Streamlit Secrets."""
    secret_name = STRIPE_PRICE_SECRET_KEYS.get(plan, "")
    if not secret_name:
        return ""
    return _secret_value(secret_name)


def stripe_runtime_status(plan: str | None = None) -> tuple[bool, str]:
    """Return Stripe runtime readiness with accurate failure diagnostics."""
    if stripe is None:
        base = "Stripe SDK is not installed in this environment."
        if STRIPE_IMPORT_ERROR:
            return False, f"{base} Import error: {STRIPE_IMPORT_ERROR}"
        return False, base

    if not _secret_value("STRIPE_SECRET_KEY"):
        return False, "Missing STRIPE_SECRET_KEY."

    if plan:
        secret_name = STRIPE_PRICE_SECRET_KEYS.get(plan, "PRICE_ID")
        if not get_stripe_price_id(plan):
            return False, f"Missing {secret_name}."

    try:
        # Validate the SDK accepts API key assignment in this runtime.
        stripe.api_key = _secret_value("STRIPE_SECRET_KEY")
    except Exception as exc:
        return False, f"Stripe SDK initialization failed: {exc}"

    return True, "Stripe checkout ready."


def stripe_checkout_config_ready(plan: str) -> tuple[bool, str]:
    return stripe_runtime_status(plan=plan)


def create_stripe_checkout_session(user: SaaSUser, target_plan: str) -> tuple[bool, str]:
    """Create a Stripe Checkout Session for a subscription upgrade.

    This avoids hard-coded Payment Links and guarantees the Pro button uses the
    Pro Price ID, while the Elite button uses the Elite Price ID.
    """
    ready, message = stripe_checkout_config_ready(target_plan)
    if not ready:
        return False, message

    try:
        stripe.api_key = _secret_value("STRIPE_SECRET_KEY")

        app_url = "https://jfbp-quant-desk.streamlit.app"
        success_url = str(
            st.secrets.get(
                "STRIPE_SUCCESS_URL",
                f"{app_url}/?checkout=success&plan={target_plan}",
            )
            or f"{app_url}/?checkout=success&plan={target_plan}"
        ).strip()
        cancel_url = str(
            st.secrets.get(
                "STRIPE_CANCEL_URL",
                f"{app_url}/?checkout=cancelled&plan={target_plan}",
            )
            or f"{app_url}/?checkout=cancelled&plan={target_plan}"
        ).strip()

        metadata = {
            "user_id": user.user_id,
            "email": user.email,
            "target_plan": target_plan,
        }

        session = stripe.checkout.Session.create(
            mode="subscription",
            customer_email=user.email,
            client_reference_id=user.user_id,
            line_items=[{"price": get_stripe_price_id(target_plan), "quantity": 1}],
            metadata=metadata,
            subscription_data={"metadata": metadata},
            success_url=success_url,
            cancel_url=cancel_url,
        )

        checkout_url = str(getattr(session, "url", "") or "").strip()
        if not checkout_url:
            return False, "Stripe did not return a checkout URL."

        return True, checkout_url

    except Exception as exc:
        return False, f"Stripe checkout creation failed: {exc}"


def available_upgrade_targets(user: SaaSUser) -> list[str]:
    current_rank = PLAN_RANK.get(user.plan, 0)
    return [p for p in [PLAN_PRO, PLAN_ELITE] if PLAN_RANK.get(p, 0) > current_rank]


def render_checkout_button(user: SaaSUser, target_plan: str, label: str, key: str) -> None:
    """Create checkout and show a clean Stripe link.

    Checkout URLs are user-specific. If a different account logs in, any old
    checkout URL is removed so Stripe cannot show the wrong customer email.
    """
    session_key = f"stripe_checkout_url_{target_plan}"
    owner_key = f"stripe_checkout_owner_{target_plan}"
    current_owner = f"{user.user_id}:{user.email}"

    if st.session_state.get(owner_key) != current_owner:
        st.session_state.pop(session_key, None)
        st.session_state[owner_key] = current_owner

    if st.button(label, use_container_width=True, key=key):
        st.session_state.pop(session_key, None)
        st.session_state[owner_key] = current_owner

        ok, result = create_stripe_checkout_session(user, target_plan)
        if ok:
            st.session_state[session_key] = result
            st.success("Secure Stripe Checkout is ready.")
        else:
            st.error(result)

    checkout_url = st.session_state.get(session_key, "")
    if checkout_url:
        st.link_button(
            "Continue to secure Stripe Checkout",
            checkout_url,
            use_container_width=True,
        )


def render_login_required(page_name: str) -> None:
    inject_saas_css()
    st.markdown(
        f'<div class="saas-lock"><strong>Login required.</strong><br>Please sign in to access <strong>{page_name}</strong>.</div>',
        unsafe_allow_html=True,
    )


def render_account_locked(user: SaaSUser) -> None:
    inject_saas_css()
    access_state = resolve_access_state(user)
    if access_state == "expired":
        headline = "Trial Expired - Upgrade Required"
    elif access_state == "provisioning_required":
        headline = "Provisioning Required"
    else:
        headline = "Account locked"
    st.markdown(
        f'<div class="saas-lock"><strong>{headline}.</strong><br>Status: <strong>{user.account_status}</strong><br>Please update your subscription to continue.</div>',
        unsafe_allow_html=True,
    )

    if access_state == "provisioning_required":
        st.info("We detected incomplete onboarding records. You can complete provisioning without buying a plan.")
        if st.button("Complete provisioning now", use_container_width=True, key="saas_complete_provisioning_now"):
            repaired, message = _auto_repair_provisioning(user, trigger="render_account_locked")
            if repaired:
                st.success(message)
                st.rerun()
            else:
                st.error(message)


def render_upgrade_required(user: SaaSUser, page_name: str) -> None:
    inject_saas_css()

    st.markdown(
        f"""
        <div class="saas-upgrade">
            <strong>🚀 Upgrade Required</strong><br>
            Your current plan is <strong>{PLAN_LABELS.get(user.plan, user.plan)}</strong>.<br>
            <strong>{page_name}</strong> is not included in your current subscription.
        </div>
        """,
        unsafe_allow_html=True,
    )

    targets = available_upgrade_targets(user)
    if not targets:
        st.warning("Your account already has the highest plan available. Please refresh or contact support if access still looks locked.")
        return

    st.markdown("### Unlock More Tools")

    if targets == [PLAN_ELITE]:
        elite_col, spacer_col = st.columns([0.62, 0.38], gap="large")
        with elite_col:
            st.markdown("#### Quant Desk Elite")
            st.caption(f"{PLAN_PRICES[PLAN_ELITE]} · {PLAN_TRADING_MODE[PLAN_ELITE]}")
            st.markdown(ELITE_FEATURE_MARKDOWN)
            render_checkout_button(user, PLAN_ELITE, "👑 Upgrade to Elite", "stripe_upgrade_elite_only")
        return

    pro_col, elite_col = st.columns(2, gap="large")

    with pro_col:
        st.markdown("#### Quant Desk Pro")
        st.caption(f"{PLAN_PRICES[PLAN_PRO]} · {PLAN_TRADING_MODE[PLAN_PRO]}")
        st.markdown(
            """
            ✓ Everything in Market Pulse  
            ✓ Portfolio tools + Private Portfolio  
            ✓ Position Command Center + Journal  
            ✓ Database + Trade Command Center  
            ✓ Options Center  
            """
        )
        render_checkout_button(user, PLAN_PRO, "🚀 Upgrade to Pro", "stripe_upgrade_pro")

    with elite_col:
        st.markdown("#### Quant Desk Elite")
        st.caption(f"{PLAN_PRICES[PLAN_ELITE]} · {PLAN_TRADING_MODE[PLAN_ELITE]}")
        st.markdown(ELITE_FEATURE_MARKDOWN)
        render_checkout_button(user, PLAN_ELITE, "👑 Upgrade to Elite", "stripe_upgrade_elite")


def render_auth_status() -> None:
    ready, _ = supabase_ready()
    if ready:
        return

    message = "Sign-in service is temporarily unavailable. Please refresh or contact support."
    st.markdown(
        f'<div class="saas-warn"><strong>Authentication unavailable.</strong><br>{message}</div>',
        unsafe_allow_html=True,
    )


def render_auth_panel() -> None:
    left, center, right = st.columns([0.75, 1.2, 0.75], gap="large")
    with center:
        _bridge_fragment_auth_callback_to_query()

        st.markdown('<div class="saas-auth-shell">', unsafe_allow_html=True)
        st.subheader("🔐 Secure Access")
        st.caption("Sign in to JFBP Quant Desk to access your workspace and tools.")
        production_auth_trace("SECURE_ACCESS_RENDERED", "render_auth_panel")
        render_auth_status()

        callback_client = get_supabase_client()
        callback_consumed, callback_ok, callback_message = _establish_non_recovery_session_from_query(
            callback_client
        )
        if callback_consumed:
            if callback_ok:
                st.success(callback_message)
                st.rerun()
            else:
                st.error(callback_message)

        trial_warning_message = str(st.session_state.get("saas_trial_warning_message", "") or "")
        if trial_warning_message:
            st.warning(trial_warning_message)

        recovery_mode_active = bool(st.session_state.get("saas_recovery_session_active", False))
        mode = st.radio("Choose access action", ["Login", "Create Account", "Reset Password"], horizontal=True)
        if _is_recovery_callback() or recovery_mode_active:
            mode = "Reset Password"

        st.markdown('<div class="saas-auth-form">', unsafe_allow_html=True)
        if mode == "Login":
            production_auth_trace("LOGIN_FORM_RENDERED", "render_auth_panel")
            with st.form("saas_login_form"):
                email = st.text_input("Email", value="")
                password = st.text_input("Password", type="password")
                remember_me = st.checkbox("Remember Me", value=False)
                submitted = st.form_submit_button("Login", use_container_width=True)

            if submitted:
                _new_auth_attempt_id()
                production_auth_trace("LOGIN_FORM_SUBMITTED", "render_auth_panel")
                production_auth_trace("LOGIN_BRANCH_ENTERED", "render_auth_panel")
                st.session_state["saas_remember_me"] = bool(remember_me)
                ok, message = supabase_login(email=email, password=password)
                if ok:
                    st.success(message)
                    production_auth_trace("RERUN_REQUESTED", "render_auth_panel", reason="login_success")
                    st.rerun()
                else:
                    st.error(message)

        elif mode == "Create Account":
            signup_processing = bool(st.session_state.get("saas_signup_processing", False))
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
                st.caption("Already have an account? Use Login above to return to the sign-in form.")
                st.info(
                    "📧 **One More Step**\n\n"
                    "After creating your account, we'll send a verification email to activate your access.\n\n"
                    "Please check your **Inbox** first. If you don't receive it within a few minutes, check your **Junk/Spam** folder and mark the email as **Not Spam** to ensure future JFBP Quant Desk emails arrive correctly.\n\n"
                    "Click the verification link before attempting to log in."
                )

                submitted = st.form_submit_button(
                    "Create Account & Start Trial",
                    use_container_width=True,
                    disabled=signup_processing,
                )

            if submitted and not signup_processing:
                st.session_state["saas_signup_processing"] = True
                try:
                    valid, validation_message = _validate_signup_inputs(
                        email=email,
                        full_name=full_name,
                        password=password,
                        password_confirm=password_confirm,
                        plan=plan,
                    )
                    if not valid:
                        st.error(validation_message)
                    else:
                        ok, message = supabase_sign_up(email=email, password=password, full_name=full_name, plan=plan)
                        if ok:
                            st.success(
                                "✅ **Almost Done!**\n\n"
                                "Your account has been created successfully.\n\n"
                                "We've sent a verification email to your email address.\n\n"
                                "Please:\n\n"
                                "• Check your Inbox\n"
                                "• Check your Junk/Spam folder\n"
                                "• Click the verification link\n"
                                "• Use Login above after verification\n\n"
                                "If you don't receive the email after **5–10 minutes**, check your **Junk/Spam** folder and mark it as **Not Spam** if necessary.\n\n"
                                "If it's still missing, use **Reset Password** or contact **[support@jfbpquantdesk.com](mailto:support@jfbpquantdesk.com)**."
                            )
                            if st.session_state.get("saas_logged_in", False):
                                st.rerun()
                        else:
                            st.error(message)
                finally:
                    st.session_state["saas_signup_processing"] = False

        else:
            if _is_recovery_callback() or recovery_mode_active:
                st.info("Recovery link detected. Set a new password to complete account recovery.")
                recovery_client = get_supabase_client()
                recovery_ready = False
                recovery_message = ""

                if _is_recovery_callback():
                    recovery_error_code, recovery_error_message = _recovery_error_summary()
                    if recovery_error_code:
                        st.session_state["saas_recovery_session_active"] = False
                        _clear_recovery_query_params()
                        st.error(recovery_error_message)
                        st.info("Use Reset Password once to request a fresh link.")
                        st.markdown('</div>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        return

                    recovery_ready, recovery_message = _establish_recovery_session_from_query(recovery_client)
                    if recovery_ready:
                        st.session_state["saas_recovery_session_active"] = True
                    else:
                        st.session_state["saas_recovery_session_active"] = False
                    _clear_recovery_query_params()
                else:
                    recovery_ready = _has_active_recovery_session(recovery_client)
                    recovery_message = (
                        "Recovery session established."
                        if recovery_ready
                        else "Recovery session is not active."
                    )

                if recovery_ready:
                    with st.form("saas_complete_password_recovery_form"):
                        new_password = st.text_input("New Password", type="password")
                        confirm_password = st.text_input("Confirm New Password", type="password")
                        update_submitted = st.form_submit_button(
                            "Update Password",
                            use_container_width=True,
                        )

                    if update_submitted:
                        valid, validation_message = _validate_password_recovery_inputs(
                            new_password,
                            confirm_password,
                        )
                        if not valid:
                            st.error(validation_message)
                        else:
                            updated, update_message = _complete_password_recovery(
                                recovery_client,
                                new_password,
                            )
                            if updated:
                                st.session_state["saas_recovery_session_active"] = False
                                _clear_recovery_query_params()
                                st.success(update_message)
                                st.info("Password recovery complete. Return to Login and sign in with your new password.")
                            else:
                                st.error(update_message)
                else:
                    st.session_state["saas_recovery_session_active"] = False
                    st.error(f"Recovery session unavailable: {recovery_message}")

            cooldown_remaining = _reset_password_cooldown_remaining()
            if cooldown_remaining > 0:
                st.warning(
                    f"{RESET_PASSWORD_RATE_LIMIT_MESSAGE} ({_format_mmss(cooldown_remaining)})"
                )

            with st.form("saas_reset_form"):
                email = st.text_input("Email", value="")
                submitted = st.form_submit_button(
                    "Send Password Reset Email",
                    use_container_width=True,
                    disabled=cooldown_remaining > 0,
                )

            if submitted:
                if not email or "@" not in email:
                    st.error("Enter a valid email.")
                else:
                    ok, message, meta = supabase_reset_password(email=email)
                    if ok:
                        _reset_password_backoff_reset()
                        st.success(message)
                    else:
                        rate_limit_kind = _supabase_reset_rate_limit_kind(meta)
                        if rate_limit_kind in {"request", "email"}:
                            next_level, cooldown_seconds = _reset_password_backoff_seconds_for_next_429()
                            _set_reset_password_cooldown(next_level, cooldown_seconds)
                            st.warning(f"{RESET_PASSWORD_RATE_LIMIT_MESSAGE} ({_format_mmss(cooldown_seconds)})")
                            st.rerun()
                        else:
                            st.error(message)

            if cooldown_remaining > 0:
                time.sleep(1)
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


def render_user_status(user: SaaSUser) -> None:
    days_left = trial_days_remaining(user)
    access_state = resolve_access_state(user)
    if is_admin_user(user):
        status_detail = "Lifetime admin access"
    elif access_state == "trial":
        status_detail = f"Trial: {days_left} days remaining"
    elif access_state == "expired":
        status_detail = "Trial expired - upgrade required"
    elif access_state == "provisioning_required":
        status_detail = "Provisioning required"
    else:
        status_detail = f"Trial: {days_left} days remaining"

    role_label = "Admin / Founder" if is_admin_user(user) else "User"
    cards = [
        card("User", user.email, user.full_name),
        card("Role", role_label, "Full platform access" if is_admin_user(user) else "Plan-based access"),
        card("Plan", PLAN_LABELS.get(user.plan, user.plan), PLAN_PRICES.get(user.plan, "")),
        card("Account Status", user.account_status, status_detail),
        card("Trading Mode", PLAN_TRADING_MODE.get(user.plan, "N/A"), "Controlled by subscription plan"),
    ]
    st.markdown('<div class="jfbp-grid-card-wrap">' + "".join(cards) + "</div>", unsafe_allow_html=True)


def render_permissions_matrix(user: SaaSUser) -> None:
    st.subheader("🧭 Page Permission Matrix")
    all_pages = sorted(set().union(*PLAN_PAGES.values()))
    rows: List[Dict[str, str]] = []
    for page in all_pages:
        rows.append(
            {
                "Page": page,
                "Page Access": "Allowed" if can_access_page(user, page) else "Blocked",
                "Current Plan": PLAN_LABELS.get(user.plan, user.plan),
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_saas_core_dashboard() -> None:
    init_saas_state()
    inject_responsive_css()
    inject_card_css()
    inject_saas_css()

    st.markdown(
        """
        <div class="jfbp-hero">
            <div class="jfbp-hero-kicker">JFBP Quant Desk · Secure Access</div>
            <div class="jfbp-hero-title">Secure Login & Workspace Access</div>
            <div class="jfbp-hero-text">Sign in, create your trial account, or recover access to your JFBP workspace and plan-enabled tools.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    user = get_current_user()
    if user is None:
        render_auth_panel()
        return

    metadata_debug_message = str(st.session_state.get("saas_metadata_debug_message", "") or "").strip()
    if metadata_debug_message:
        st.text(metadata_debug_message)
        st.session_state["saas_metadata_debug_message"] = ""

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
        metadata_write = st.session_state.get("saas_onboarding_debug", {}).get("metadata_write", {})
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
                "metadata_write_ok": bool(metadata_write.get("ok", False)),
                "metadata_write_message": str(metadata_write.get("message", "")),
                "metadata_payload": metadata_write.get("payload", {}),
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
