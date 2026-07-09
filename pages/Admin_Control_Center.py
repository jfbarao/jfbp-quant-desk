# =========================================================
# 🚢 JFBP QUANT DESK — Admin Control Center v1.0
# Customer Management Console
# ---------------------------------------------------------
# Purpose:
# - Internal admin dashboard for SaaS users, plans, trials, and status.
# - Uses Supabase Auth users as source of truth, then enriches from
#   public.user_profiles and public.subscriptions.
# - Optional writes for plan/status updates.
#
# Recommended Streamlit Secrets:
# SUPABASE_URL = "https://..."
# SUPABASE_SERVICE_ROLE_KEY = "..."   # preferred for admin console
# SUPABASE_ANON_KEY = "..."           # fallback read client
# ADMIN_EMAILS = "jfbarao@icloud.com"
# =========================================================

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import os
import requests

import pandas as pd
import streamlit as st

try:
    from supabase import create_client
except Exception:  # pragma: no cover
    create_client = None

try:
    from core.responsive import inject_responsive_css
except Exception:  # pragma: no cover
    def inject_responsive_css() -> None:
        return None

try:
    from core.ui_cards import inject_card_css
except Exception:  # pragma: no cover
    def inject_card_css() -> None:
        return None

try:
    from pages.SaaS_Core import (
        ACCOUNT_ACTIVE,
        ACCOUNT_CANCELLED,
        ACCOUNT_EXPIRED,
        ACCOUNT_PAST_DUE,
        ACCOUNT_SUSPENDED,
        ACCOUNT_TRIAL,
        PLAN_ELITE,
        PLAN_LABELS,
        PLAN_MARKET_PULSE,
        PLAN_PRICES,
        PLAN_PRO,
        TRIAL_LENGTH_DAYS,
        auth_user_created_at,
        canonical_trial_window,
        get_current_user,
        is_admin_email,
        is_admin_user,
        trial_dates_consistent,
    )
except Exception:  # pragma: no cover
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
    TRIAL_LENGTH_DAYS = 30

    def get_current_user():
        return None

    def auth_user_created_at(auth_user: Any) -> Optional[datetime]:
        value = auth_user.get("created_at") if isinstance(auth_user, dict) else getattr(auth_user, "created_at", None)
        return _parse_dt(value)

    def canonical_trial_window(auth_user: Any) -> Tuple[Optional[datetime], Optional[datetime], str]:
        auth_created = auth_user_created_at(auth_user)
        if auth_created is None:
            return None, None, "missing_auth_created_at"
        return auth_created, auth_created + timedelta(days=TRIAL_LENGTH_DAYS), "auth.users.created_at"

    def trial_dates_consistent(auth_created_at_value: Any, trial_start_value: Any, trial_end_value: Any) -> bool:
        auth_created = _parse_dt(auth_created_at_value)
        trial_start = _parse_dt(trial_start_value)
        trial_end = _parse_dt(trial_end_value)
        if auth_created is None or trial_start is None or trial_end is None:
            return False
        expected_end = auth_created + timedelta(days=TRIAL_LENGTH_DAYS)
        return trial_start.date() == auth_created.date() and trial_end.date() == expected_end.date()

    def is_admin_email(email: str) -> bool:
        raw = str(st.secrets.get("ADMIN_EMAILS", "") or "")
        emails = {e.strip().lower() for e in raw.replace(";", ",").split(",") if e.strip()}
        emails.add("jfbarao@icloud.com")
        return str(email or "").strip().lower() in emails

    def is_admin_user(user: Any) -> bool:
        return bool(user and is_admin_email(getattr(user, "email", "")))


PLAN_OPTIONS = [PLAN_MARKET_PULSE, PLAN_PRO, PLAN_ELITE]
STATUS_OPTIONS = [
    ACCOUNT_TRIAL,
    ACCOUNT_ACTIVE,
    ACCOUNT_PAST_DUE,
    ACCOUNT_CANCELLED,
    ACCOUNT_EXPIRED,
    ACCOUNT_SUSPENDED,
]

PLAN_BADGES = {
    PLAN_MARKET_PULSE: "⚪ Market Pulse",
    PLAN_PRO: "🔵 Pro",
    PLAN_ELITE: "🟣 Elite",
}

STATUS_BADGES = {
    ACCOUNT_TRIAL: "🟢 Trial",
    ACCOUNT_ACTIVE: "✅ Active",
    ACCOUNT_PAST_DUE: "🟡 Past Due",
    ACCOUNT_CANCELLED: "🟠 Cancelled",
    ACCOUNT_EXPIRED: "🔴 Expired",
    ACCOUNT_SUSPENDED: "⛔ Suspended",
}

RISK_LOW = "LOW"
RISK_MEDIUM = "MEDIUM"
RISK_HIGH = "HIGH"

AUDIT_LOG_FALLBACK_PATH = Path(__file__).resolve().parents[1] / "data" / "admin_audit_log.csv"
AUDIT_LOG_TABLES = ["admin_audit_log", "admin_audit_logs"]
LOGIN_HISTORY_TABLES = ["login_history", "user_login_history", "auth_login_history"]

DISPOSABLE_EMAIL_DOMAINS = {
    "10minutemail.com",
    "guerrillamail.com",
    "mailinator.com",
    "tempmail.com",
    "temp-mail.org",
    "yopmail.com",
}


# =========================================================
# BASIC HELPERS
# =========================================================

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def _fmt_date(value: Any) -> str:
    dt = _parse_dt(value)
    if not dt:
        return "—"
    return dt.strftime("%Y-%m-%d")


def _fmt_datetime(value: Any) -> str:
    dt = _parse_dt(value)
    if not dt:
        return "—"
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _days_until(value: Any) -> str:
    dt = _parse_dt(value)
    if not dt:
        return "—"
    days = (dt - _utc_now()).days
    if days < 0:
        return f"Expired {abs(days)}d ago"
    if days == 0:
        return "Ends today"
    return f"{days}d left"


def _clean_email(value: Any) -> str:
    return str(value or "").strip().lower()


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _risk_level(score: int) -> str:
    if score >= 70:
        return RISK_HIGH
    if score >= 30:
        return RISK_MEDIUM
    return RISK_LOW


def _risk_badge(score: int, blocked: bool = False, whitelisted: bool = False) -> str:
    if whitelisted:
        return "🟢 Low Risk"
    if blocked or score >= 70:
        return "🔴 High Risk"
    if score >= 30:
        return "🟡 Medium Risk"
    return "🟢 Low Risk"


def _risk_tone(risk_key: str) -> str:
    if risk_key == RISK_HIGH:
        return "risk"
    if risk_key == RISK_MEDIUM:
        return "warning"
    return "good"


def _directory_status_badge(status: str) -> str:
    status_key = str(status or "").strip()
    mapping = {
        "Registered": "🟡 Provisioning Required",
        "Provisioning Required": "🟡 Provisioning Required",
        "Trial": "🟢 Trial",
        "Trial Ending Soon": "🟠 Trial Ending Soon",
        "Trial Expired": "🔴 Trial Expired",
        "Active": "🟢 Active",
    }
    return mapping.get(status_key, status_key or "🟡 Provisioning Required")


def _needs_attention(admin_status: str) -> bool:
    return str(admin_status or "").strip() in {"Registered", "Provisioning Required", "Trial Ending Soon", "Trial Expired"}


def _short_device_id(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text == "UNKNOWN":
        return "—"
    if len(text) <= 14:
        return text
    return f"{text[:8]}...{text[-4:]}"


def _email_domain(email: Any) -> str:
    text = _clean_email(email)
    parts = text.split("@")
    return parts[-1] if len(parts) == 2 else ""


def _is_disposable_email(email: Any) -> bool:
    return _email_domain(email) in DISPOSABLE_EMAIL_DOMAINS


def _browser_from_user_agent(user_agent: Any) -> str:
    text = str(user_agent or "").lower()
    if not text:
        return "—"
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
    if not text:
        return "—"
    if "windows" in text:
        return "Windows"
    if "mac os" in text or "macintosh" in text:
        return "macOS"
    if "iphone" in text or "ipad" in text or "ios" in text:
        return "iOS"
    if "android" in text:
        return "Android"
    if "linux" in text:
        return "Linux"
    return "Other"


def _dedupe_dict_rows(rows: List[Dict[str, Any]], key_name: str) -> List[Dict[str, Any]]:
    seen: set[str] = set()
    out: List[Dict[str, Any]] = []
    for row in rows:
        key = str(row.get(key_name) or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _response_data(response: Any) -> List[Dict[str, Any]]:
    data = getattr(response, "data", None)
    if data is None:
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return [data] if isinstance(data, dict) else []


def _normalize_customer_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(profile or {})
    defaults = {
        "signup_ip": "",
        "last_login_ip": "",
        "signup_country": "",
        "last_login_country": "",
        "city": "",
        "last_login_city": "",
        "browser": "",
        "operating_system": "",
        "device_id": "",
        "device_fingerprint": "",
        "user_agent": "",
        "trial_notes": "",
        "total_logins": 0,
    }
    for key, value in defaults.items():
        if key not in normalized or normalized.get(key) in {None, ""}:
            normalized[key] = value
    return normalized


def _dedupe_flags(flags: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for flag in flags:
        if flag in seen:
            continue
        seen.add(flag)
        out.append(flag)
    return out


def _dt_series(df: pd.DataFrame, raw_col: str, display_col: str) -> pd.Series:
    source_col = raw_col if raw_col in df.columns else display_col
    return df[source_col].apply(_parse_dt)


# =========================================================
# SUPABASE REST ADMIN CLIENT
# =========================================================
#
# Why REST instead of create_client here:
# Some Supabase projects now expose service-role keys as sb_secret_...
# and older supabase-py / gotrue versions may reject that key format while
# direct PostgREST calls work correctly. This admin page only needs table
# reads/writes, so REST is simpler and more reliable for the control center.

def _secret_value(name: str, default: str = "") -> str:
    value = ""
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""

    if value is None or str(value).strip() == "":
        value = os.environ.get(name, default)

    return str(value or default).strip()


def _admin_debug_enabled() -> bool:
    raw = _secret_value("ADMIN_CONTROL_DEBUG", "") or _secret_value("ADMIN_DEBUG", "")
    if raw:
        return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(st.session_state.get("admin_control_debug", False))


def _admin_debug_log(message: str) -> None:
    if _admin_debug_enabled():
        print(f"[Admin-Control][Debug] {message}")


def _admin_rest_config() -> Tuple[str, str, str]:
    url = _secret_value("SUPABASE_URL")
    service_key = _secret_value("SUPABASE_SERVICE_ROLE_KEY")
    anon_key = _secret_value("SUPABASE_ANON_KEY")
    key = service_key or anon_key
    key_type = "service_role" if service_key else "anon"
    return url.rstrip("/"), key, key_type


def _admin_rest_headers() -> Dict[str, str]:
    _, key, _ = _admin_rest_config()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _supabase_error_body(exc: Exception) -> str:
    if isinstance(exc, requests.HTTPError) and getattr(exc, "response", None) is not None:
        response = exc.response
        try:
            parsed = response.json()
            return json.dumps(parsed, default=str)
        except Exception:
            return str(response.text or "")
    return str(exc)


def _log_supabase_write_debug(
    table_name: str,
    payload: Dict[str, Any],
    error_body: str = "",
    table_columns: Optional[List[str]] = None,
) -> None:
    ordered_keys = sorted(payload.keys())
    ordered_values = {key: payload.get(key) for key in ordered_keys}
    known_columns = sorted([str(col).strip() for col in (table_columns or []) if str(col).strip()])
    unexpected_payload_keys = [key for key in ordered_keys if known_columns and key not in known_columns]
    missing_columns_from_payload = [col for col in known_columns if col not in ordered_keys]

    lines = [
        "[Admin-Control][Supabase-Write-Debug]",
        f"target table: {table_name}",
        f"payload keys: {ordered_keys}",
        f"payload values: {json.dumps(ordered_values, default=str)}",
    ]
    if known_columns:
        lines.append(f"table columns: {known_columns}")
        lines.append(f"payload keys not in table columns: {unexpected_payload_keys}")
        lines.append(f"table columns missing in payload: {missing_columns_from_payload}")
    if error_body:
        lines.append(f"Supabase error body: {error_body}")

    debug_message = "\n".join(lines)
    print(debug_message)

    history = st.session_state.setdefault("admin_supabase_write_debug", [])
    history.append(
        {
            "ts": _utc_now().isoformat(),
            "table": table_name,
            "payload_keys": ordered_keys,
            "payload_values": ordered_values,
            "table_columns": known_columns,
            "payload_not_in_columns": unexpected_payload_keys,
            "columns_missing_in_payload": missing_columns_from_payload,
            "error_body": error_body,
        }
    )
    st.session_state["admin_supabase_write_debug"] = history[-25:]


def _load_table_columns(table_name: str, schema_name: str = "public") -> List[str]:
    url, key, _ = _admin_rest_config()
    if not url or not key:
        return []

    endpoint = f"{url}/rest/v1/information_schema.columns"
    params = {
        "select": "column_name,ordinal_position",
        "table_schema": f"eq.{schema_name}",
        "table_name": f"eq.{table_name}",
        "order": "ordinal_position.asc",
    }

    try:
        response = requests.get(
            endpoint,
            headers=_admin_rest_headers(),
            params=params,
            timeout=20,
        )
        response.raise_for_status()
        rows = response.json() if response.content else []
        if isinstance(rows, list):
            columns = [str(row.get("column_name") or "").strip() for row in rows if isinstance(row, dict)]
            columns = [col for col in columns if col]
            if columns:
                return columns
    except Exception:
        pass

    try:
        sample_rows = _rest_select(table_name, extra_params={"limit": 1})
        if sample_rows:
            return sorted(list(sample_rows[0].keys()))
    except Exception:
        pass

    return []


def admin_supabase_ready() -> Tuple[bool, str]:
    url, key, key_type = _admin_rest_config()

    if not url:
        return False, "Missing SUPABASE_URL in Streamlit Secrets."
    if not key:
        return False, "Missing SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY in Streamlit Secrets."
    if not url.startswith("https://") or ".supabase." not in url:
        return False, "SUPABASE_URL does not look like a valid Supabase project URL."

    if key_type == "anon":
        return True, "Connected with anon key. If rows are missing, add SUPABASE_SERVICE_ROLE_KEY for the admin console."

    return True, "Connected with service role key."


def _rest_select(
    table_name: str,
    order_expr: str = "created_at.desc",
    extra_params: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    url, key, _ = _admin_rest_config()
    if not url or not key:
        return []

    endpoint = f"{url}/rest/v1/{table_name}"
    params = {"select": "*", "order": order_expr}
    if extra_params:
        params.update(extra_params)

    response = requests.get(
        endpoint,
        headers=_admin_rest_headers(),
        params=params,
        timeout=20,
    )
    response.raise_for_status()

    data = response.json()
    return data if isinstance(data, list) else []


def _rest_insert(table_name: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    url, key, _ = _admin_rest_config()
    if not url or not key:
        return []

    endpoint = f"{url}/rest/v1/{table_name}"
    response = requests.post(
        endpoint,
        headers=_admin_rest_headers(),
        json=payload,
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


def _rest_patch_by_user_id(table_name: str, user_id: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    url, key, _ = _admin_rest_config()
    if not url or not key:
        return []

    endpoint = f"{url}/rest/v1/{table_name}"
    response = requests.patch(
        endpoint,
        headers=_admin_rest_headers(),
        params={"user_id": f"eq.{user_id}"},
        json=payload,
        timeout=20,
    )
    response.raise_for_status()

    data = response.json()
    return data if isinstance(data, list) else []


def _rest_select_first_available(
    table_names: List[str],
    order_expr: str = "created_at.desc",
    extra_params: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    for table_name in table_names:
        try:
            return _rest_select(table_name, order_expr=order_expr, extra_params=extra_params)
        except Exception:
            continue
    return []


def _auth_recovery_email(email: str) -> Tuple[bool, str]:
    url, key, _ = _admin_rest_config()
    if not url or not key:
        return False, "Supabase auth recovery is unavailable."

    endpoint = f"{url}/auth/v1/recover"
    response = requests.post(
        endpoint,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json={"email": _clean_email(email)},
        timeout=20,
    )

    if response.ok:
        return True, "Password reset email sent."
    return False, f"Password reset failed: {response.text}"


def _current_admin_email() -> str:
    user = get_current_user()
    return str(getattr(user, "email", "admin@jfbp.local") or "admin@jfbp.local")


def _append_local_audit_log(payload: Dict[str, Any]) -> None:
    AUDIT_LOG_FALLBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    row_df = pd.DataFrame([payload])
    if AUDIT_LOG_FALLBACK_PATH.exists():
        row_df.to_csv(AUDIT_LOG_FALLBACK_PATH, mode="a", header=False, index=False)
    else:
        row_df.to_csv(AUDIT_LOG_FALLBACK_PATH, index=False)


def _append_admin_audit_log(
    customer_row: Dict[str, Any],
    action: str,
    old_value: Any,
    new_value: Any,
    reason: str = "",
) -> None:
    customer_row = customer_row or {}
    payload = {
        "timestamp": _utc_now().isoformat(),
        "admin_user": _current_admin_email(),
        "customer_user_id": str(customer_row.get("User ID") or ""),
        "customer_email": str(customer_row.get("Email") or ""),
        "customer_name": str(customer_row.get("Name") or ""),
        "action": action,
        "old_value": json.dumps(old_value, default=str),
        "new_value": json.dumps(new_value, default=str),
        "reason": reason,
    }

    for table_name in AUDIT_LOG_TABLES:
        try:
            _rest_insert(table_name, payload)
            return
        except Exception:
            continue

    _append_local_audit_log(payload)

# =========================================================
# DATA LOADERS
# =========================================================

@st.cache_data(ttl=60)
def load_profiles() -> List[Dict[str, Any]]:
    return _rest_select("user_profiles", order_expr="created_at.desc")


@st.cache_data(ttl=60)
def load_subscriptions() -> List[Dict[str, Any]]:
    try:
        return _rest_select("subscriptions", order_expr="created_at.desc")
    except Exception:
        return []


@st.cache_data(ttl=60)
def load_auth_users() -> List[Dict[str, Any]]:
    url, key, key_type = _admin_rest_config()
    if not url or not key:
        return []
    if key_type != "service_role":
        return []

    endpoint = f"{url}/auth/v1/admin/users"
    users: List[Dict[str, Any]] = []
    page = 1
    per_page = 200

    while page <= 50:
        response = requests.get(
            endpoint,
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            params={"page": page, "per_page": per_page},
            timeout=20,
        )
        response.raise_for_status()

        payload = response.json() if response.content else {}
        if isinstance(payload, dict):
            page_rows = payload.get("users") or payload.get("data") or []
        elif isinstance(payload, list):
            page_rows = payload
        else:
            page_rows = []

        page_rows = [row for row in page_rows if isinstance(row, dict)]
        if not page_rows:
            break

        users.extend(page_rows)

        if len(page_rows) < per_page:
            break
        page += 1

    return _dedupe_dict_rows(users, "id")


@st.cache_data(ttl=60)
def load_audit_log_rows() -> List[Dict[str, Any]]:
    rows = _rest_select_first_available(AUDIT_LOG_TABLES, order_expr="timestamp.desc")
    if rows:
        return rows

    if AUDIT_LOG_FALLBACK_PATH.exists():
        try:
            df = pd.read_csv(AUDIT_LOG_FALLBACK_PATH)
            return df.fillna("").to_dict("records")
        except Exception:
            return []
    return []


@st.cache_data(ttl=60)
def load_login_history_rows() -> List[Dict[str, Any]]:
    return _rest_select_first_available(LOGIN_HISTORY_TABLES, order_expr="created_at.desc")


def _clear_read_caches() -> None:
    load_auth_users.clear()
    load_profiles.clear()
    load_subscriptions.clear()
    load_audit_log_rows.clear()
    load_login_history_rows.clear()


def _login_event_timestamp(row: Dict[str, Any]) -> Optional[datetime]:
    return (
        _parse_dt(row.get("created_at"))
        or _parse_dt(row.get("timestamp"))
        or _parse_dt(row.get("logged_in_at"))
        or _parse_dt(row.get("attempted_at"))
    )


def _login_event_success(row: Dict[str, Any]) -> Optional[bool]:
    if "success" in row:
        value = row.get("success")
        if isinstance(value, bool):
            return value
        text = str(value or "").strip().lower()
        if text in {"true", "1", "yes", "y", "success", "succeeded"}:
            return True
        if text in {"false", "0", "no", "n", "failed", "failure"}:
            return False
    text = str(row.get("status") or row.get("result") or row.get("event_type") or "").strip().lower()
    if text in {"success", "succeeded", "login_success"}:
        return True
    if text in {"failed", "failure", "login_failed"}:
        return False
    return None


def _synthetic_login_row_from_profile(profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    last_login_at = profile.get("last_sign_in_at") or profile.get("last_login_at") or profile.get("created_at")
    has_metadata = any(
        str(profile.get(key) or "").strip()
        for key in ["last_login_ip", "signup_ip", "browser", "operating_system", "device_id", "signup_country", "last_login_country", "city", "last_login_city", "user_agent"]
    )
    if not last_login_at and not has_metadata:
        return None
    return {
        "user_id": str(profile.get("user_id") or "").strip(),
        "created_at": last_login_at or _utc_now().isoformat(),
        "ip_address": profile.get("last_login_ip") or profile.get("signup_ip"),
        "country": profile.get("last_login_country") or profile.get("signup_country"),
        "city": profile.get("last_login_city") or profile.get("city"),
        "browser": profile.get("browser") or _browser_from_user_agent(profile.get("user_agent")),
        "device": profile.get("device_id"),
        "operating_system": profile.get("operating_system") or _os_from_user_agent(profile.get("user_agent")),
        "success": True,
    }


# Build per-user login history with profile-based synthetic fallback when tables are absent.
# Login history index with fallback rows so operational views stay populated without history tables.
def _build_login_history_index(
    profiles: List[Dict[str, Any]],
    login_history_rows: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    by_user: Dict[str, List[Dict[str, Any]]] = {}

    for row in login_history_rows:
        user_id = str(row.get("user_id") or row.get("customer_user_id") or "").strip()
        if not user_id:
            continue
        by_user.setdefault(user_id, []).append(row)

    for profile in profiles:
        user_id = str(profile.get("user_id") or "").strip()
        if not user_id or user_id in by_user:
            continue

        synthetic_row = _synthetic_login_row_from_profile(profile)
        if synthetic_row is not None:
            by_user[user_id] = [synthetic_row]

    for user_id, rows in by_user.items():
        rows.sort(key=lambda row: _login_event_timestamp(row) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        by_user[user_id] = rows
    return by_user


def _build_audit_index(audit_rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    by_user: Dict[str, List[Dict[str, Any]]] = {}
    for row in audit_rows:
        user_id = str(row.get("customer_user_id") or row.get("user_id") or "").strip()
        if not user_id:
            continue
        by_user.setdefault(user_id, []).append(row)

    for user_id, rows in by_user.items():
        rows.sort(key=lambda row: _parse_dt(row.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        by_user[user_id] = rows
    return by_user


def _score_trial_risk(trial_attempts: int) -> Tuple[int, List[str], List[str]]:
    score = 0
    reasons: List[str] = []
    flags: List[str] = []
    if trial_attempts > 1:
        score += min(30, 10 * trial_attempts)
        reasons.append(f"{trial_attempts} trial attempts")
        flags.append("🧪")
    return score, reasons, flags


def _score_ip_risk(same_ip_accounts: int) -> Tuple[int, List[str], List[str]]:
    score = 0
    reasons: List[str] = []
    flags: List[str] = []
    if same_ip_accounts > 1:
        score += min(20, 8 * same_ip_accounts)
        reasons.append(f"{same_ip_accounts} accounts from same IP")
        flags.append("🌐")
    return score, reasons, flags


def _score_device_risk(same_device_accounts: int) -> Tuple[int, List[str], List[str]]:
    score = 0
    reasons: List[str] = []
    flags: List[str] = []
    if same_device_accounts > 1:
        score += min(25, 10 * same_device_accounts)
        reasons.append(f"{same_device_accounts} emails on same device")
        flags.append("💻")
    return score, reasons, flags


def _score_login_risk(failed_logins: int, password_resets: int) -> Tuple[int, List[str], List[str]]:
    score = 0
    reasons: List[str] = []
    flags: List[str] = []
    if failed_logins >= 5:
        score += 15
        reasons.append(f"{failed_logins} failed login attempts")
        flags.append("🔐")
    if password_resets >= 3:
        score += 10
        reasons.append(f"{password_resets} password reset actions")
        flags.append("♻️")
    return score, reasons, flags


def _build_risk_summary(score: int, blocked: bool, ignored: bool, whitelisted: bool, reasons: List[str], flags: List[str]) -> Dict[str, Any]:
    if blocked:
        score = max(score, 90)
        reasons.append("Account blocked for future trials")
    if ignored:
        reasons.append("Flag ignored by admin")
    if whitelisted:
        score = 0
        reasons = ["Whitelisted by admin override"]

    score = min(100, score)
    risk_key = _risk_level(score)
    explanation = " • ".join(reasons) if reasons else "No major risk indicators detected."
    deduped_flags = _dedupe_flags(flags)
    fraud_summary = " ".join(deduped_flags).strip()
    return {
        "risk_score": score,
        "risk_key": risk_key,
        "risk_badge": _risk_badge(score, blocked=blocked, whitelisted=whitelisted),
        "risk_explanation": explanation,
        "fraud_flags": fraud_summary or ("⚠️" if score >= 50 else ""),
    }


# Risk engine: computes deterministic fraud/risk score and diagnostics for a profile.
def _risk_intelligence(
    profile: Dict[str, Any],
    all_profiles: List[Dict[str, Any]],
    login_rows: List[Dict[str, Any]],
    audit_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    email = _clean_email(profile.get("email"))
    signup_ip = str(profile.get("signup_ip") or "").strip()
    device_id = str(profile.get("device_id") or "").strip()
    signup_country = str(profile.get("signup_country") or "UNKNOWN").upper()
    trial_attempts = _safe_int(profile.get("trial_attempts"), 0)
    whitelisted = _parse_bool(profile.get("trial_whitelisted"))
    blocked = _parse_bool(profile.get("trial_blocked"))
    ignored = _parse_bool(profile.get("trial_ignored"))

    same_ip_accounts = len({
        _clean_email(row.get("email"))
        for row in all_profiles
        if signup_ip and str(row.get("signup_ip") or "").strip() == signup_ip and _clean_email(row.get("email"))
    })
    same_device_accounts = len({
        _clean_email(row.get("email"))
        for row in all_profiles
        if device_id and str(row.get("device_id") or "").strip() == device_id and _clean_email(row.get("email"))
    })

    countries = {signup_country} if signup_country and signup_country != "UNKNOWN" else set()
    devices = {device_id} if device_id and device_id != "UNKNOWN" else set()
    failed_logins = 0
    successful_logins = 0
    last_login_row = login_rows[0] if login_rows else {}

    for row in login_rows:
        row_country = str(row.get("country") or row.get("signup_country") or "").upper().strip()
        row_device = str(row.get("device") or row.get("device_id") or "").strip()
        if row_country:
            countries.add(row_country)
        if row_device:
            devices.add(row_device)
        success = _login_event_success(row)
        if success is True:
            successful_logins += 1
        elif success is False:
            failed_logins += 1

    password_resets = sum(
        1 for row in audit_rows
        if str(row.get("action") or "").strip().lower() == "reset password"
    )

    vpn_or_proxy = _parse_bool(profile.get("vpn_or_proxy") or profile.get("proxy_detected"))
    score = 0
    reasons: List[str] = []
    fraud_flags: List[str] = []

    trial_score, trial_reasons, trial_flags = _score_trial_risk(trial_attempts)
    ip_score, ip_reasons, ip_flags = _score_ip_risk(same_ip_accounts)
    device_score, device_reasons, device_flags = _score_device_risk(same_device_accounts)
    score += trial_score + ip_score + device_score
    reasons.extend(trial_reasons + ip_reasons + device_reasons)
    fraud_flags.extend(trial_flags + ip_flags + device_flags)

    if len(countries) > 1:
        score += 15
        reasons.append("Country changes detected")
    if len(devices) > 1:
        score += 15
        reasons.append("Device changes detected")
    if _is_disposable_email(email):
        score += 30
        reasons.append("Disposable email domain")
        fraud_flags.append("📨")
    if vpn_or_proxy:
        score += 20
        reasons.append("VPN / proxy signal")
        fraud_flags.append("🛡️")
    login_score, login_reasons, login_flags = _score_login_risk(failed_logins, password_resets)
    score += login_score
    reasons.extend(login_reasons)
    fraud_flags.extend(login_flags)

    summary = _build_risk_summary(score, blocked, ignored, whitelisted, reasons, fraud_flags)

    return {
        "risk_score": summary["risk_score"],
        "risk_key": summary["risk_key"],
        "risk_badge": summary["risk_badge"],
        "risk_explanation": summary["risk_explanation"],
        "same_ip_accounts": same_ip_accounts,
        "same_device_accounts": same_device_accounts,
        "country_changes": max(0, len(countries) - 1),
        "device_changes": max(0, len(devices) - 1),
        "failed_logins": failed_logins,
        "successful_logins": successful_logins,
        "password_resets": password_resets,
        "fraud_flags": summary["fraud_flags"],
        "last_login_row": last_login_row,
    }


def _build_customer_record(
    profile: Dict[str, Any],
    sub: Dict[str, Any],
    login_rows: List[Dict[str, Any]],
    audit_user_rows: List[Dict[str, Any]],
    all_profiles: List[Dict[str, Any]],
    auth_user: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    auth_user = auth_user or {}
    profile = profile or {}
    sub = sub or {}

    has_profile = bool(profile)
    has_subscription = bool(sub)

    user_id = str(auth_user.get("id") or profile.get("user_id") or sub.get("user_id") or "")
    email = _clean_email(auth_user.get("email") or profile.get("email") or sub.get("email"))

    raw_plan = str(profile.get("plan") or sub.get("plan") or "").strip().upper()
    plan = raw_plan or "—"
    if not has_profile and not has_subscription:
        plan = "—"

    status = str(profile.get("account_status") or sub.get("status") or "").upper().strip()
    if not status:
        status = "REGISTERED" if not has_profile and not has_subscription else ACCOUNT_TRIAL

    role = str(profile.get("role") or "admin" if is_admin_email(email) else "user").lower()
    app_meta = auth_user.get("app_metadata") if isinstance(auth_user.get("app_metadata"), dict) else {}
    user_meta = auth_user.get("user_metadata") if isinstance(auth_user.get("user_metadata"), dict) else {}

    display_name = str(
        profile.get("full_name")
        or profile.get("display_name")
        or user_meta.get("full_name")
        or user_meta.get("name")
        or user_meta.get("display_name")
        or user_meta.get("preferred_username")
        or app_meta.get("display_name")
        or ""
    ).strip()
    if not display_name:
        display_name = email or user_id or "Unknown User"

    profile_trial_start = profile.get("trial_start") or profile.get("trial_started_at")
    profile_trial_end = profile.get("trial_end")

    sub_trial_start = sub.get("trial_start") or sub.get("trial_starts_at")
    sub_trial_end = sub.get("trial_end")

    trial_start = profile_trial_start
    trial_end = profile_trial_end

    trial_end_source_table = "user_profiles" if profile_trial_end else "none"
    trial_end_source_field = ""
    if profile_trial_end:
        for field_name in ["trial_end"]:
            if profile.get(field_name):
                trial_end_source_field = field_name
                break
    renewal = (
        sub.get("current_period_end")
        or sub.get("renewal_date")
        or sub.get("period_end")
        or profile.get("renewal_date")
    )
    trial_attempts = _safe_int(profile.get("trial_attempts"), 0)
    whitelisted = _parse_bool(profile.get("trial_whitelisted"))
    ignored = _parse_bool(profile.get("trial_ignored"))
    blocked = _parse_bool(profile.get("trial_blocked"))
    risk = _risk_intelligence(profile, all_profiles, login_rows, audit_user_rows)
    last_login_row = risk.get("last_login_row") or {}
    browser = (
        str(last_login_row.get("browser") or "").strip()
        or str(profile.get("browser") or profile.get("last_login_browser") or "").strip()
        or _browser_from_user_agent(profile.get("user_agent"))
    )
    operating_system = (
        str(last_login_row.get("operating_system") or "").strip()
        or str(profile.get("operating_system") or "").strip()
        or _os_from_user_agent(profile.get("user_agent"))
    )
    first_login = (
        min(
            (_login_event_timestamp(row) for row in login_rows if _login_event_timestamp(row) is not None),
            default=None,
        )
        or _parse_dt(profile.get("first_login_at"))
    )
    last_login = (
        _login_event_timestamp(last_login_row)
        or _parse_dt(profile.get("last_sign_in_at"))
        or _parse_dt(profile.get("last_login_at"))
    )
    login_count = _safe_int(profile.get("total_logins") or profile.get("login_count"), risk.get("successful_logins", 0))
    current_country = str(
        last_login_row.get("country")
        or profile.get("last_login_country")
        or profile.get("signup_country")
        or ""
    ).upper()
    if current_country in {"UNKNOWN", "—"}:
        current_country = ""
    current_city = str(last_login_row.get("city") or profile.get("city") or profile.get("last_login_city") or "").strip()
    last_login_ip = str(last_login_row.get("ip_address") or profile.get("last_login_ip") or "").strip()
    signup_ip = str(profile.get("signup_ip") or "").strip()
    device_fingerprint = str(profile.get("device_fingerprint") or profile.get("device_id") or "").strip()

    auth_created_raw = auth_user.get("created_at")
    created_raw = auth_created_raw or profile.get("created_at") or sub.get("created_at")
    auth_last_sign_in_raw = auth_user.get("last_sign_in_at") or profile.get("last_sign_in_at") or profile.get("last_login_at")

    email_confirmed = bool(auth_user.get("email_confirmed_at") or auth_user.get("confirmed_at") or auth_user.get("confirmed_at"))

    provider = "—"
    provider = str(app_meta.get("provider") or user_meta.get("provider") or "").strip()
    if not provider:
        identities = auth_user.get("identities")
        if isinstance(identities, list):
            for identity in identities:
                if not isinstance(identity, dict):
                    continue
                provider = str(identity.get("provider") or identity.get("identity_data", {}).get("provider") or "").strip()
                if provider:
                    break
    provider = provider or "email"

    status_badge = STATUS_BADGES.get(status, status.title() if status else "Registered")

    now = _utc_now()
    trial_end_dt = _parse_dt(trial_end)
    trial_days_left = (trial_end_dt.date() - now.date()).days if trial_end_dt else None

    subscription_status = str(sub.get("status") or "").strip().upper()
    if subscription_status == ACCOUNT_ACTIVE or status == ACCOUNT_ACTIVE:
        admin_status = "Active"
    elif trial_end_dt and now <= trial_end_dt:
        admin_status = "Trial Ending Soon" if trial_days_left is not None and trial_days_left <= 5 else "Trial"
    elif trial_end_dt and now > trial_end_dt:
        admin_status = "Trial Expired"
    else:
        admin_status = "Provisioning Required"

    integrity_warning = ""
    if auth_user and not has_profile and not has_subscription:
        integrity_warning = "⚠️ Auth user exists but customer record is missing"
    elif auth_user and not has_profile:
        integrity_warning = "⚠️ Auth user exists but customer record is missing"
    elif auth_user and not has_subscription:
        integrity_warning = "⚠️ Auth user exists but subscription record is missing"

    account_created = bool(_parse_dt(created_raw))
    email_verified = email_confirmed
    first_login_started = bool(_parse_dt(auth_last_sign_in_raw) or _parse_dt(profile.get("last_login_at")) or _parse_dt(profile.get("first_login_at")))
    profile_created = has_profile
    subscription_created = has_subscription
    trial_started = bool(_parse_dt(trial_start))

    onboarding_done = sum([
        account_created,
        email_verified,
        trial_started,
        first_login_started,
        profile_created,
        subscription_created,
    ])
    if auth_user and not has_profile and not has_subscription:
        onboarding_done = max(onboarding_done, 3)
    onboarding_total = 6
    onboarding_progress = f"{onboarding_done}/{onboarding_total}"
    onboarding_summary = (
        f"Account {'✔' if account_created else '✖'} · "
        f"Email {'✔' if email_verified else '✖'} · "
        f"Trial {'✔' if trial_started else '✖'} · "
        f"Login {'✔' if first_login_started else '✖'} · "
        f"Profile {'✔' if profile_created else '✖'} · "
        f"Subscription {'✔' if subscription_created else '✖'}"
    )

    trial_notes_text = str(profile.get("trial_notes") or "")
    provisioning_trace = ""
    for line in reversed(trial_notes_text.splitlines()):
        clean_line = str(line or "").strip()
        if clean_line.startswith("[PROVISIONING]"):
            provisioning_trace = clean_line
            break

    admin_status_badge = _directory_status_badge(admin_status)
    trial_countdown = ""
    if trial_end_dt is not None and admin_status in {"Trial", "Trial Ending Soon"} and trial_days_left is not None:
        trial_countdown = f"Trial: {max(0, trial_days_left)} days remaining"
    elif admin_status == "Trial Expired":
        trial_countdown = "Trial expired"

    auth_created_dt = auth_user_created_at(auth_user)
    canonical_trial_start, canonical_trial_end, canonical_trial_source = canonical_trial_window(auth_user)
    trial_dates_ok = trial_dates_consistent(auth_created_dt, trial_start, trial_end)
    trial_consistency_warning = ""
    if auth_created_dt is not None and (trial_start or trial_end) and not trial_dates_ok:
        trial_consistency_warning = "⚠ Trial dates inconsistent"

    if trial_consistency_warning:
        integrity_warning = f"{integrity_warning} · {trial_consistency_warning}".strip(" ·")

    ray_target = "ray" in str(display_name or "").lower() or "ray" in str(email or "").lower()
    if ray_target and _admin_debug_enabled():
        print(f"Ray auth_created_at: {auth_created_raw or '—'}")
        print(f"Ray profile trial_start: {profile_trial_start or '—'}")
        print(f"Ray profile trial_end: {profile_trial_end or '—'}")
        print(f"Ray subscription trial_start: {sub_trial_start or '—'}")
        print(f"Ray subscription trial_end: {sub_trial_end or '—'}")
        print(f"Final displayed trial_end: {trial_end or '—'}")
        print(f"Final displayed countdown: {trial_countdown or '—'}")
        print(f"Ray trial_end source: table={trial_end_source_table}, field={trial_end_source_field or '—'}")

    return {
        "User ID": user_id,
        "UID": user_id,
        "Name": display_name,
        "Email": email,
        "Plan": PLAN_BADGES.get(plan, plan) if plan != "—" else "—",
        "Plan Key": plan,
        "Status": status_badge,
        "Status Key": status,
        "Admin Status": admin_status,
        "Directory Status": admin_status_badge,
        "Trial Countdown": trial_countdown,
        "Trial Start": _fmt_date(trial_start),
        "Trial Start Raw": trial_start,
        "Trial End": _fmt_date(trial_end),
        "Trial End Raw": trial_end,
        "Trial End Source Table": trial_end_source_table,
        "Trial End Source Field": trial_end_source_field,
        "Trial Dates Consistent": trial_dates_ok,
        "Trial Consistency Warning": trial_consistency_warning,
        "Canonical Trial Source": canonical_trial_source,
        "Canonical Trial Start": canonical_trial_start.isoformat() if canonical_trial_start else "",
        "Canonical Trial End": canonical_trial_end.isoformat() if canonical_trial_end else "",
        "Trial Ends": _fmt_date(trial_end),
        "Trial Ends Raw": trial_end,
        "Trial": _days_until(trial_end),
        "Renewal Date": _fmt_date(renewal),
        "Role": "Admin" if role == "admin" or is_admin_email(email) else "User",
        "Stripe Customer ID": str(sub.get("stripe_customer_id") or profile.get("stripe_customer_id") or "—"),
        "Stripe Customer": str(sub.get("stripe_customer_id") or profile.get("stripe_customer_id") or "—"),
        "Stripe Subscription": str(sub.get("stripe_subscription_id") or profile.get("stripe_subscription_id") or "—"),
        "Created At": _fmt_datetime(created_raw),
        "Created": _fmt_date(created_raw),
        "Created Raw": created_raw,
        "Auth Created Raw": auth_created_raw,
        "Last Sign In": _fmt_datetime(auth_last_sign_in_raw),
        "Email Confirmed": "Yes" if email_confirmed else "No",
        "Provider": provider,
        "Last Login": _fmt_datetime(last_login),
        "Last Login Raw": last_login.isoformat() if isinstance(last_login, datetime) else "",
        "Signup IP": signup_ip,
        "Last Login IP": last_login_ip,
        "Country": current_country,
        "City": current_city,
        "Device ID": _short_device_id(device_fingerprint) if device_fingerprint else "",
        "Device Fingerprint": device_fingerprint,
        "Device ID Raw": device_fingerprint,
        "Browser": browser or "",
        "Operating System": operating_system or "",
        "First Login": _fmt_datetime(first_login),
        "Total Logins": login_count,
        "Risk": risk["risk_badge"],
        "Risk Key": risk["risk_key"],
        "Risk Score": risk["risk_score"],
        "Risk Explanation": risk["risk_explanation"],
        "Trial Attempts": trial_attempts,
        "Last IP Activity": _fmt_date(profile.get("last_ip_activity")),
        "Whitelisted": whitelisted,
        "Ignored": ignored,
        "Trial Blocked": blocked,
        "Trial Notes": str(profile.get("trial_notes") or ""),
        "Provisioning Trace": provisioning_trace,
        "Fraud Flags": risk["fraud_flags"],
        "Same IP Accounts": risk["same_ip_accounts"],
        "Same Device Accounts": risk["same_device_accounts"],
        "Country Changes": risk["country_changes"],
        "Device Changes": risk["device_changes"],
        "Failed Logins": risk["failed_logins"],
        "Password Resets": risk["password_resets"],
        "Has Profile": has_profile,
        "Has Subscription": has_subscription,
        "Integrity Warning": integrity_warning,
        "Needs Attention": _needs_attention(admin_status),
        "Onboarding Progress": onboarding_progress,
        "Onboarding Summary": onboarding_summary,
        "Onboarding Account Created": account_created,
        "Onboarding Email Verified": email_verified,
        "Onboarding Trial Started": trial_started,
        "Onboarding First Login": first_login_started,
        "Onboarding Profile Created": profile_created,
        "Onboarding Subscription Created": subscription_created,
        "Actions": "⋮",
    }


# Build canonical customer rows with separate raw and display fields.
def merge_customer_rows(
    auth_users: List[Dict[str, Any]],
    profiles: List[Dict[str, Any]],
    subscriptions: List[Dict[str, Any]],
    login_history_rows: List[Dict[str, Any]],
    audit_rows: List[Dict[str, Any]],
) -> pd.DataFrame:
    sub_by_user_id = {str(row.get("user_id", "")): row for row in subscriptions if row.get("user_id")}
    sub_by_email = {_clean_email(row.get("email")): row for row in subscriptions if _clean_email(row.get("email"))}
    profile_by_user_id = {str(row.get("user_id", "")): row for row in profiles if row.get("user_id")}
    profile_by_email = {_clean_email(row.get("email")): row for row in profiles if _clean_email(row.get("email"))}

    login_by_user = _build_login_history_index(profiles, login_history_rows)
    audit_by_user = _build_audit_index(audit_rows)

    rows: List[Dict[str, Any]] = []
    normalized_profiles = [_normalize_customer_profile(profile) for profile in profiles]

    seen_auth_keys: set[Tuple[str, str]] = set()
    for auth_user in auth_users:
        try:
            user_id = str(auth_user.get("id") or "").strip()
            email = _clean_email(auth_user.get("email"))
            if not user_id and not email:
                continue

            profile = profile_by_user_id.get(user_id) or profile_by_email.get(email) or {}
            sub = sub_by_user_id.get(user_id) or sub_by_email.get(email) or {}
            login_rows = login_by_user.get(user_id, [])
            audit_user_rows = audit_by_user.get(user_id, [])

            _admin_debug_log(
                "auth_user_id={uid} customer_row_found={customer} profile_row_found={profile_found} "
                "subscription_row_found={sub_found}".format(
                    uid=user_id or "(missing)",
                    customer="Yes" if (profile or sub) else "No",
                    profile_found="Yes" if bool(profile) else "No",
                    sub_found="Yes" if bool(sub) else "No",
                )
            )

            rows.append(
                _build_customer_record(
                    profile=profile,
                    sub=sub,
                    login_rows=login_rows,
                    audit_user_rows=audit_user_rows,
                    all_profiles=normalized_profiles,
                    auth_user=auth_user,
                )
            )
            seen_auth_keys.add((user_id, email))
        except Exception as exc:
            auth_id = str((auth_user or {}).get("id") or "").strip() or "(missing)"
            _admin_debug_log(f"merge_error auth_user_id={auth_id}: {exc}")
            continue

    for profile in normalized_profiles:
        try:
            user_id = str(profile.get("user_id", "") or "").strip()
            email = _clean_email(profile.get("email"))
            if (user_id, email) in seen_auth_keys:
                continue

            sub = sub_by_user_id.get(user_id) or sub_by_email.get(email) or {}
            login_rows = login_by_user.get(user_id, [])
            audit_user_rows = audit_by_user.get(user_id, [])
            auth_stub = {
                "id": user_id,
                "email": email,
                "created_at": profile.get("created_at"),
                "last_sign_in_at": profile.get("last_sign_in_at") or profile.get("last_login_at"),
            }
            rows.append(
                _build_customer_record(
                    profile=profile,
                    sub=sub,
                    login_rows=login_rows,
                    audit_user_rows=audit_user_rows,
                    all_profiles=normalized_profiles,
                    auth_user=auth_stub,
                )
            )
        except Exception as exc:
            profile_user = str((profile or {}).get("user_id") or "").strip() or "(missing)"
            _admin_debug_log(f"merge_profile_only_error user_id={profile_user}: {exc}")
            continue

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(
            columns=[
                "User ID",
                "UID",
                "Name",
                "Email",
                "Created At",
                "Last Sign In",
                "Email Confirmed",
                "Provider",
                "Plan",
                "Plan Key",
                "Status",
                "Status Key",
                "Admin Status",
                "Trial Start",
                "Trial Start Raw",
                "Trial End",
                "Trial End Raw",
                "Trial Ends",
                "Trial Ends Raw",
                "Trial",
                "Renewal Date",
                "Role",
                "Stripe Customer ID",
                "Stripe Customer",
                "Stripe Subscription",
                "Created",
                "Created Raw",
                "Last Login",
                "Last Login Raw",
                "Signup IP",
                "Last Login IP",
                "Country",
                "City",
                "Device ID",
                "Device Fingerprint",
                "Device ID Raw",
                "Browser",
                "Operating System",
                "First Login",
                "Total Logins",
                "Risk",
                "Risk Key",
                "Risk Score",
                "Risk Explanation",
                "Trial Attempts",
                "Last IP Activity",
                "Whitelisted",
                "Ignored",
                "Trial Blocked",
                "Trial Notes",
                "Fraud Flags",
                "Same IP Accounts",
                "Same Device Accounts",
                "Country Changes",
                "Device Changes",
                "Failed Logins",
                "Password Resets",
                "Has Profile",
                "Has Subscription",
                "Integrity Warning",
            ]
        )
    return df


# =========================================================
# WRITE ACTIONS
# =========================================================

def update_customer_plan_status(user_id: str, plan: str, status: str) -> Tuple[bool, str]:
    if not user_id:
        return False, "Missing user_id for selected customer."

    try:
        _rest_patch_by_user_id(
            "user_profiles",
            user_id,
            {
                "plan": plan,
                "account_status": status,
            },
        )

        try:
            _rest_patch_by_user_id(
                "subscriptions",
                user_id,
                {
                    "plan": plan,
                    "status": status,
                },
            )
        except Exception:
            # Some accounts may not have a subscription row yet.
            pass

        _clear_read_caches()
        return True, "Customer plan/status updated."
    except Exception as exc:
        return False, f"Update failed: {exc}"


def update_customer_trial_controls(user_id: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
    if not user_id:
        return False, "Missing user_id for selected customer."

    try:
        _rest_patch_by_user_id("user_profiles", user_id, payload)
        _clear_read_caches()
        return True, "Trial protection settings updated."
    except Exception as exc:
        return False, f"Trial protection update failed: {exc}"


def update_customer_profile_fields(user_id: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
    if not user_id:
        return False, "Missing user_id for selected customer."
    try:
        _rest_patch_by_user_id("user_profiles", user_id, payload)
        _clear_read_caches()
        return True, "Customer profile updated."
    except Exception as exc:
        return False, f"Profile update failed: {exc}"


def _rest_first_row(table_name: str, user_id: str = "", email: str = "") -> Dict[str, Any]:
    clean_user = str(user_id or "").strip()
    clean_email = _clean_email(email)

    if clean_user:
        try:
            rows = _rest_select(
                table_name,
                order_expr="created_at.desc",
                extra_params={"user_id": f"eq.{clean_user}", "limit": 1},
            )
            if rows:
                return rows[0]
        except Exception:
            pass

    if clean_email:
        try:
            rows = _rest_select(
                table_name,
                order_expr="created_at.desc",
                extra_params={"email": f"eq.{clean_email}", "limit": 1},
            )
            if rows:
                return rows[0]
        except Exception:
            pass

    return {}


def apply_repair_provisioning(customer_row: Dict[str, Any], reason: str = "") -> Tuple[bool, str]:
    customer_row = customer_row or {}
    user_id = str(customer_row.get("User ID") or customer_row.get("UID") or "").strip()
    email = _clean_email(customer_row.get("Email"))
    full_name = str(customer_row.get("Name") or email or "Unknown User").strip()

    if not user_id or not email:
        return False, "Missing user_id or email for provisioning repair."

    now = _utc_now()
    plan_key = str(customer_row.get("Plan Key") or PLAN_MARKET_PULSE).strip().upper()
    if plan_key not in PLAN_OPTIONS:
        plan_key = PLAN_MARKET_PULSE

    status_key = str(customer_row.get("Status Key") or "").strip().upper()
    if status_key not in STATUS_OPTIONS:
        status_key = ACCOUNT_TRIAL
    if status_key in {"REGISTERED", ""}:
        status_key = ACCOUNT_TRIAL

    auth_created_dt = _parse_dt(customer_row.get("Auth Created Raw") or customer_row.get("Created Raw") or customer_row.get("Created"))

    trial_start_existing = _parse_dt(customer_row.get("Trial Start Raw") or customer_row.get("Trial Start"))
    trial_end_existing = _parse_dt(customer_row.get("Trial End Raw") or customer_row.get("Trial End") or customer_row.get("Trial Ends Raw") or customer_row.get("Trial Ends"))

    # Repair Provisioning only fills missing trial metadata; it must not reset or extend an existing trial.
    if trial_start_existing is None and trial_end_existing is None and auth_created_dt is not None:
        trial_start_dt = auth_created_dt
        trial_end_dt = auth_created_dt + timedelta(days=TRIAL_LENGTH_DAYS)
    else:
        trial_start_dt = trial_start_existing or auth_created_dt or now
        trial_end_dt = trial_end_existing or ((auth_created_dt or trial_start_dt) + timedelta(days=TRIAL_LENGTH_DAYS))

    old_value = {
        "plan": customer_row.get("Plan Key"),
        "status": customer_row.get("Status Key"),
        "trial_start": customer_row.get("Trial Start") or customer_row.get("Trial Start Raw"),
        "trial_end": customer_row.get("Trial End") or customer_row.get("Trial End Raw"),
    }

    step_log: List[str] = []
    if trial_start_existing is None or trial_end_existing is None:
        step_log.append("Trial metadata repaired")

    try:
        existing_profile = _rest_first_row("user_profiles", user_id=user_id, email=email)
        profile_payload = {
            "user_id": user_id,
            "email": email,
            "full_name": full_name,
            "plan": plan_key,
            "account_status": status_key,
            "trial_start": trial_start_dt.isoformat(),
            "trial_end": trial_end_dt.isoformat(),
            "trial_started_at": str(existing_profile.get("trial_started_at") or trial_start_dt.isoformat()),
            "trial_attempts": _safe_int(existing_profile.get("trial_attempts") or 1, 1),
        }

        profile_columns = _load_table_columns("user_profiles")
        if profile_columns:
            unexpected_keys = [key for key in profile_payload.keys() if key not in profile_columns]
            if unexpected_keys:
                step_log.append(f"Filtered unexpected profile keys: {unexpected_keys}")
                profile_payload = {key: value for key, value in profile_payload.items() if key in profile_columns}

            missing_payload_keys = [column for column in profile_columns if column in {"user_id", "email", "full_name", "plan", "account_status", "trial_start", "trial_end"} and column not in profile_payload]
            if missing_payload_keys:
                step_log.append(f"Missing expected profile columns in payload: {missing_payload_keys}")

        _log_supabase_write_debug("user_profiles", profile_payload, table_columns=profile_columns)

        if existing_profile:
            try:
                _rest_patch_by_user_id("user_profiles", user_id, profile_payload)
            except Exception as exc:
                _log_supabase_write_debug(
                    "user_profiles",
                    profile_payload,
                    _supabase_error_body(exc),
                    table_columns=profile_columns,
                )
                raise
            step_log.append("Profile Created (upsert)")
        else:
            try:
                _rest_insert("user_profiles", profile_payload)
            except Exception as exc:
                _log_supabase_write_debug(
                    "user_profiles",
                    profile_payload,
                    _supabase_error_body(exc),
                    table_columns=profile_columns,
                )
                raise
            step_log.append("Profile Created")

        step_log.append("Customer Created")

        existing_subscription = _rest_first_row("subscriptions", user_id=user_id, email=email)
        subscription_payload = {
            "user_id": user_id,
            "plan": plan_key,
            "status": status_key,
        }

        if existing_subscription:
            _rest_patch_by_user_id("subscriptions", user_id, subscription_payload)
            step_log.append("Subscription Created (upsert)")
        else:
            _rest_insert("subscriptions", subscription_payload)
            step_log.append("Subscription Created")

        step_log.append("Trial Created")
        step_log.append("Provisioning Completed")

        _append_admin_audit_log(
            customer_row,
            "Repair Provisioning",
            old_value,
            {
                "plan": plan_key,
                "status": status_key,
                "trial_start": trial_start_dt.isoformat(),
                "trial_end": trial_end_dt.isoformat(),
                "steps": step_log,
            },
            reason or "Admin provisioning repair",
        )

        _clear_read_caches()
        return True, "Provisioning repair completed."
    except Exception as exc:
        failed_step = step_log[-1] if step_log else "User Created"
        _append_admin_audit_log(
            customer_row,
            "Repair Provisioning Failed",
            old_value,
            {
                "failed_step": failed_step,
                "error": str(exc),
                "steps": step_log,
            },
            reason or "Admin provisioning repair failed",
        )
        _clear_read_caches()
        return False, f"Provisioning repair failed at {failed_step}: {exc}"


def apply_subscription_action(customer_row: Dict[str, Any], action: str, target_plan: str, reason: str = "") -> Tuple[bool, str]:
    customer_row = customer_row or {}
    user_id = str(customer_row.get("User ID") or "")
    old_value = {"plan": customer_row.get("Plan Key"), "status": customer_row.get("Status Key")}

    new_status = str(customer_row.get("Status Key") or ACCOUNT_TRIAL)
    if action == "Activate":
        new_status = ACCOUNT_ACTIVE
    elif action == "Suspend":
        new_status = ACCOUNT_SUSPENDED
    elif action == "Cancel":
        new_status = ACCOUNT_CANCELLED

    ok, message = update_customer_plan_status(user_id, target_plan, new_status)
    if ok:
        _append_admin_audit_log(customer_row, action, old_value, {"plan": target_plan, "status": new_status}, reason)
    return ok, message


def apply_trial_action(customer_row: Dict[str, Any], action: str, days: int, reason: str = "") -> Tuple[bool, str]:
    customer_row = customer_row or {}
    user_id = str(customer_row.get("User ID") or "")
    now = _utc_now()
    trial_end_dt = _parse_dt(customer_row.get("Trial Ends Raw") or customer_row.get("Trial Ends")) or now
    auth_user = {
        "created_at": customer_row.get("Auth Created Raw") or customer_row.get("Created Raw") or customer_row.get("Created"),
    }
    canonical_trial_start, canonical_trial_end, _ = canonical_trial_window(auth_user)
    payload: Dict[str, Any] = {}
    old_value = {
        "trial_end": customer_row.get("Trial Ends"),
        "trial_attempts": customer_row.get("Trial Attempts"),
    }

    if action == "Extend Trial":
        payload["trial_end"] = (trial_end_dt + timedelta(days=max(days, 1))).isoformat()
    elif action == "End Trial":
        payload["trial_end"] = now.isoformat()
        payload["account_status"] = ACCOUNT_EXPIRED
    elif action == "Reset Trial":
        reset_trial_start = canonical_trial_start or now
        reset_trial_end = canonical_trial_end or (reset_trial_start + timedelta(days=TRIAL_LENGTH_DAYS))
        payload["trial_start"] = reset_trial_start.isoformat()
        payload["trial_end"] = reset_trial_end.isoformat()
        payload["trial_started_at"] = reset_trial_start.isoformat()
        payload["trial_attempts"] = 1
        payload["risk_score"] = 0

    ok, message = update_customer_profile_fields(user_id, payload)
    if ok:
        _append_admin_audit_log(customer_row, action, old_value, payload, reason)
    return ok, message


def apply_repair_trial(customer_row: Dict[str, Any], reason: str = "") -> Tuple[bool, str]:
    customer_row = customer_row or {}
    user_id = str(customer_row.get("User ID") or "").strip()
    if not user_id:
        return False, "Missing user_id for selected customer."

    trial_start_raw = customer_row.get("Trial Start Raw") or customer_row.get("Trial Start")
    trial_end_raw = customer_row.get("Trial End Raw") or customer_row.get("Trial End") or customer_row.get("Trial Ends Raw") or customer_row.get("Trial Ends")
    if _parse_dt(trial_start_raw) is not None and _parse_dt(trial_end_raw) is not None:
        return False, "Repair Trial is only available when trial_start or trial_end is missing."

    now = _utc_now()
    auth_user = {
        "created_at": customer_row.get("Auth Created Raw") or customer_row.get("Created Raw") or customer_row.get("Created"),
    }
    canonical_trial_start, canonical_trial_end, source = canonical_trial_window(auth_user)
    resolved_trial_start = canonical_trial_start or now
    resolved_trial_end = canonical_trial_end or (resolved_trial_start + timedelta(days=TRIAL_LENGTH_DAYS))
    payload = {
        "trial_start": resolved_trial_start.isoformat(),
        "trial_end": resolved_trial_end.isoformat(),
        "trial_started_at": resolved_trial_start.isoformat(),
        "account_status": ACCOUNT_TRIAL,
        "plan": PLAN_MARKET_PULSE,
    }

    ok, message = update_customer_profile_fields(user_id, payload)
    if not ok:
        return False, message

    try:
        update_customer_plan_status(user_id, PLAN_MARKET_PULSE, ACCOUNT_TRIAL)
    except Exception:
        pass

    _append_admin_audit_log(
        customer_row,
        "Repair Trial",
        {
            "trial_start": trial_start_raw,
            "trial_end": trial_end_raw,
            "status": customer_row.get("Status Key"),
        },
        {**payload, "source": source},
        reason or "Repair Trial from admin action",
    )
    return True, "Trial repaired from canonical auth signup timestamp."


def apply_rebuild_trial_dates(customer_row: Dict[str, Any], reason: str = "") -> Tuple[bool, str]:
    customer_row = customer_row or {}
    user_id = str(customer_row.get("User ID") or customer_row.get("UID") or "").strip()
    email = _clean_email(customer_row.get("Email"))
    if not user_id:
        return False, "Missing user_id for selected customer."

    auth_user = {
        "created_at": customer_row.get("Auth Created Raw") or customer_row.get("Created Raw") or customer_row.get("Created"),
    }
    canonical_trial_start, canonical_trial_end, source = canonical_trial_window(auth_user)
    if canonical_trial_start is None or canonical_trial_end is None:
        return False, "Cannot rebuild trial dates because auth.users.created_at is unavailable."

    existing_profile = _rest_first_row("user_profiles", user_id=user_id, email=email)
    payload = {
        "trial_start": canonical_trial_start.isoformat(),
        "trial_end": canonical_trial_end.isoformat(),
        "trial_started_at": str(existing_profile.get("trial_started_at") or canonical_trial_start.isoformat()),
    }

    ok, message = update_customer_profile_fields(user_id, payload)
    if not ok:
        return False, message

    _append_admin_audit_log(
        customer_row,
        "Rebuild Trial Dates",
        {
            "trial_start": customer_row.get("Trial Start Raw") or customer_row.get("Trial Start"),
            "trial_end": customer_row.get("Trial End Raw") or customer_row.get("Trial End"),
        },
        {
            "trial_start": payload["trial_start"],
            "trial_end": payload["trial_end"],
            "source": source,
        },
        reason or "Rebuild trial dates from canonical auth signup timestamp",
    )
    return True, "Trial dates rebuilt from auth signup timestamp."


def apply_account_action(customer_row: Dict[str, Any], action: str, reason: str = "") -> Tuple[bool, str]:
    customer_row = customer_row or {}
    user_id = str(customer_row.get("User ID") or "")
    email = str(customer_row.get("Email") or "")
    old_value = {"status": customer_row.get("Status Key")}

    if action == "Reset Password":
        ok, message = _auth_recovery_email(email)
        if ok:
            _append_admin_audit_log(customer_row, action, old_value, {"email": email}, reason)
        return ok, message

    if action == "Lock Account":
        ok, message = update_customer_profile_fields(user_id, {"account_status": ACCOUNT_SUSPENDED})
        if ok:
            _append_admin_audit_log(customer_row, action, old_value, {"account_status": ACCOUNT_SUSPENDED}, reason)
        return ok, message

    if action == "Unlock Account":
        target_status = ACCOUNT_ACTIVE if customer_row.get("Plan Key") in {PLAN_PRO, PLAN_ELITE} else ACCOUNT_TRIAL
        ok, message = update_customer_profile_fields(user_id, {"account_status": target_status})
        if ok:
            _append_admin_audit_log(customer_row, action, old_value, {"account_status": target_status}, reason)
        return ok, message

    if action == "Force Logout":
        return False, "Force Logout requires auth session revocation wiring and is not available in this admin-only UI build."

    return False, "Unsupported account action."


# =========================================================
# UI
# =========================================================

def inject_admin_css() -> None:
    st.markdown(
        """
        <style>
            .admin-hero {
                border:1px solid #dbeafe;
                background:#eff6ff;
                border-radius:18px;
                padding:1.05rem 1.15rem;
                margin:0.3rem 0 1rem 0;
            }
            .admin-kicker {
                color:#475569;
                font-size:0.74rem;
                text-transform:uppercase;
                letter-spacing:0.07em;
                font-weight:850;
                margin-bottom:0.22rem;
            }
            .admin-title {
                color:#0f172a;
                font-size:1.62rem;
                line-height:1.12;
                font-weight:900;
                margin-bottom:0.32rem;
            }
            .admin-text {
                color:#334155;
                font-size:0.95rem;
                line-height:1.42;
                font-weight:650;
            }
            .admin-card-grid {
                display:grid;
                grid-template-columns:repeat(auto-fit,minmax(165px,1fr));
                gap:0.78rem;
                margin:0.8rem 0 1rem 0;
            }
            .admin-card {
                border:1px solid #e2e8f0;
                background:#f8fafc;
                border-radius:16px;
                padding:0.82rem 0.92rem;
            }
            .admin-card-label {
                color:#64748b;
                font-size:0.70rem;
                text-transform:uppercase;
                letter-spacing:0.06em;
                font-weight:850;
                margin-bottom:0.22rem;
            }
            .admin-card-value {
                color:#111827;
                font-size:1.32rem;
                font-weight:900;
                line-height:1.12;
            }
            .admin-card-detail {
                color:#475569;
                font-size:0.78rem;
                margin-top:0.18rem;
            }
            .admin-lock {
                border:1px solid #fecaca;
                background:#fef2f2;
                border-radius:18px;
                padding:1rem;
                color:#7f1d1d;
                font-weight:800;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: Any, detail: str = "") -> str:
    return (
        '<div class="admin-card">'
        f'<div class="admin-card-label">{label}</div>'
        f'<div class="admin-card-value">{value}</div>'
        f'<div class="admin-card-detail">{detail}</div>'
        '</div>'
    )


def render_hero() -> None:
    st.markdown(
        """
        <div class="admin-hero">
            <div class="admin-kicker">JFBP Quant Desk · Internal Command</div>
            <div class="admin-title">Admin Control Center</div>
            <div class="admin-text">Customer management console for plans, trials, account status, and subscription visibility.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_admin_gate() -> bool:
    user = get_current_user()
    if is_admin_user(user):
        return True

    st.markdown(
        """
        <div class="admin-lock">
            Admin access required. Please sign in with an authorized founder/admin account.
        </div>
        """,
        unsafe_allow_html=True,
    )
    return False


def render_overview_cards(df: pd.DataFrame) -> None:
    registered = int((df.get("Admin Status", pd.Series(dtype=str)) == "Provisioning Required").sum()) if not df.empty else 0
    trial = int((df.get("Admin Status", pd.Series(dtype=str)).isin(["Trial", "Trial Ending Soon"])).sum()) if not df.empty else 0
    active = int((df.get("Admin Status", pd.Series(dtype=str)) == "Active").sum()) if not df.empty else 0
    needs_attention = int(df.get("Needs Attention", pd.Series(dtype=bool)).sum()) if not df.empty else 0

    cards = [
        metric_card("Provisioning Required", registered, "Auth users with incomplete setup"),
        metric_card("Trial", trial, "Open trial accounts"),
        metric_card("Active", active, "Active customers"),
        metric_card("Need Attention", needs_attention, "Missing profile/subscription or expired"),
    ]
    st.markdown('<div class="admin-card-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)

    f1, f2, f3, f4 = st.columns(4, gap="small")
    with f1:
        if st.button("Show Provisioning", width="stretch", key="admin_filter_registered"):
            st.session_state["admin_directory_status_filter"] = "Provisioning Required"
            st.rerun()
    with f2:
        if st.button("Show Trial", width="stretch", key="admin_filter_trial"):
            st.session_state["admin_directory_status_filter"] = "Trial"
            st.rerun()
    with f3:
        if st.button("Show Active", width="stretch", key="admin_filter_active"):
            st.session_state["admin_directory_status_filter"] = "Active"
            st.rerun()
    with f4:
        if st.button("Need Attention", width="stretch", key="admin_filter_attention"):
            st.session_state["admin_directory_status_filter"] = "__NEEDS_ATTENTION__"
            st.rerun()


def _revenue_for_plan(plan_key: str) -> int:
    if plan_key == PLAN_MARKET_PULSE:
        return 39
    if plan_key == PLAN_PRO:
        return 99
    if plan_key == PLAN_ELITE:
        return 199
    return 0


# Dashboard metrics are computed from raw datetime fields to avoid display-format drift.
def _dashboard_metrics(df: pd.DataFrame, audit_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if df.empty:
        return {
            "todays_signups": 0,
            "trials_this_week": 0,
            "paid_conversions": 0,
            "expired_trials": 0,
            "repeat_trial_attempts": 0,
            "suspended_accounts": 0,
            "conversion_pct": 0.0,
            "avg_trial_age": 0.0,
            "avg_time_to_upgrade": 0.0,
            "mrr": 0,
            "arr": 0,
            "arpu": 0.0,
        }

    now = _utc_now()
    created_dts = _dt_series(df, "Created Raw", "Created")
    trial_end_dts = _dt_series(df, "Trial Ends Raw", "Trial Ends")
    signup_today = int(sum(dt is not None and dt.date() == now.date() for dt in created_dts))
    trials_this_week = int(sum(
        df.iloc[idx].get("Status Key") == ACCOUNT_TRIAL and dt is not None and (now - dt) <= timedelta(days=7)
        for idx, dt in enumerate(created_dts)
    ))
    paid_conversions = int(sum(df["Status Key"] == ACCOUNT_ACTIVE))
    expired_trials = int(sum(
        ((df.iloc[idx].get("Status Key") == ACCOUNT_TRIAL) or (df.iloc[idx].get("Status Key") == ACCOUNT_EXPIRED))
        and dt is not None and dt < now
        for idx, dt in enumerate(trial_end_dts)
    ))
    repeat_trial_attempts = int(sum(df["Trial Attempts"] > 1))
    suspended_accounts = int(sum(df["Status Key"] == ACCOUNT_SUSPENDED))
    conversion_pct = (paid_conversions / len(df) * 100.0) if len(df) else 0.0

    trial_ages = [
        max(0, (now - dt).days)
        for dt in created_dts
        if dt is not None
    ]
    avg_trial_age = float(sum(trial_ages) / len(trial_ages)) if trial_ages else 0.0

    upgrade_actions: Dict[str, datetime] = {}
    for row in audit_rows:
        action = str(row.get("action") or "").strip().lower()
        if action not in {"upgrade plan", "activate", "manual activation"}:
            continue
        user_id = str(row.get("customer_user_id") or "").strip()
        action_dt = _parse_dt(row.get("timestamp"))
        if user_id and action_dt is not None:
            upgrade_actions[user_id] = min(action_dt, upgrade_actions.get(user_id, action_dt))

    upgrade_days: List[int] = []
    for _, row in df.iterrows():
        created_dt = _parse_dt(row.get("Created Raw") or row.get("Created"))
        upgrade_dt = upgrade_actions.get(str(row.get("User ID") or ""))
        if created_dt is not None and upgrade_dt is not None and upgrade_dt >= created_dt:
            upgrade_days.append((upgrade_dt - created_dt).days)
    avg_time_to_upgrade = float(sum(upgrade_days) / len(upgrade_days)) if upgrade_days else 0.0

    mrr = 0
    for _, row in df.iterrows():
        if row.get("Status Key") in {ACCOUNT_ACTIVE, ACCOUNT_TRIAL}:
            mrr += _revenue_for_plan(str(row.get("Plan Key") or ""))
    arr = mrr * 12
    arpu = (mrr / paid_conversions) if paid_conversions else 0.0

    return {
        "todays_signups": signup_today,
        "trials_this_week": trials_this_week,
        "paid_conversions": paid_conversions,
        "expired_trials": expired_trials,
        "repeat_trial_attempts": repeat_trial_attempts,
        "suspended_accounts": suspended_accounts,
        "conversion_pct": conversion_pct,
        "avg_trial_age": avg_trial_age,
        "avg_time_to_upgrade": avg_time_to_upgrade,
        "mrr": mrr,
        "arr": arr,
        "arpu": arpu,
    }


def render_dashboard_analytics(df: pd.DataFrame, audit_rows: List[Dict[str, Any]]) -> None:
    stats = _dashboard_metrics(df, audit_rows)

    top_cards = [
        metric_card("Today's Signups", stats["todays_signups"], "New accounts today"),
        metric_card("Trials This Week", stats["trials_this_week"], "New trial cohort"),
        metric_card("Paid Conversions", stats["paid_conversions"], "Active paid accounts"),
        metric_card("Expired Trials", stats["expired_trials"], "Trial access expired"),
        metric_card("Repeat Trial Attempts", stats["repeat_trial_attempts"], "2+ attempts observed"),
        metric_card("Suspended Accounts", stats["suspended_accounts"], "Restricted access"),
    ]
    second_cards = [
        metric_card("Conversion %", f"{stats['conversion_pct']:.1f}%", "Paid conversions / customers"),
        metric_card("Average Trial Age", f"{stats['avg_trial_age']:.1f}d", "Mean customer age"),
        metric_card("Average Time to Upgrade", f"{stats['avg_time_to_upgrade']:.1f}d", "From signup to logged upgrade"),
        metric_card("Monthly Revenue", f"${stats['mrr']:,}", "Estimated MRR"),
        metric_card("Annual Revenue", f"${stats['arr']:,}", "Estimated ARR"),
        metric_card("Average Revenue Per User", f"${stats['arpu']:.2f}", "MRR / paid customers"),
    ]
    st.markdown('<div class="admin-card-grid">' + "".join(top_cards) + "</div>", unsafe_allow_html=True)
    st.markdown('<div class="admin-card-grid">' + "".join(second_cards) + "</div>", unsafe_allow_html=True)


def filter_customer_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    def _has_col(name: str) -> bool:
        return name in df.columns

    c1, c2, c3, c4, c5 = st.columns([0.24, 0.14, 0.14, 0.14, 0.14], gap="medium")
    with c1:
        query = st.text_input("Search customers", placeholder="Name, email, plan, status…")
    with c2:
        plan_filter = st.selectbox("Plan", ["All"] + PLAN_OPTIONS, format_func=lambda p: "All" if p == "All" else PLAN_LABELS.get(p, p))
    with c3:
        admin_status_values = [
            "Provisioning Required",
            "Trial",
            "Trial Ending Soon",
            "Trial Expired",
            "Active",
        ]
        desired_status = st.session_state.get("admin_directory_status_filter", "All")
        preset = "All"
        if desired_status in admin_status_values:
            preset = desired_status
        status_filter = st.selectbox(
            "Status",
            ["All"] + admin_status_values,
            index=(["All"] + admin_status_values).index(preset),
            key="admin_directory_status_filter_select",
        )
    with c4:
        risk_filter = st.selectbox("Risk", ["All", "High Risk", "Medium Risk", "Low Risk"])
    with c5:
        countries = sorted({str(value or "UNKNOWN") for value in df.get("Country", pd.Series(dtype=str)).tolist()})
        country_filter = st.selectbox("Country", ["All"] + countries)

    c6, c7, c8, c9, c10 = st.columns([0.16, 0.16, 0.16, 0.16, 0.16], gap="medium")
    with c6:
        roles = sorted({str(value or "User") for value in df.get("Role", pd.Series(dtype=str)).tolist()})
        role_filter = st.selectbox("Role", ["All"] + roles)
    with c7:
        multiple_trials_only = st.checkbox("Multiple Trials", value=False)
    with c8:
        device_filter = st.text_input("Device", placeholder="Device fingerprint")
    with c9:
        signup_from = st.date_input("Signup From", value=None, format="YYYY-MM-DD")
    with c10:
        trial_end_before = st.date_input("Trial End Before", value=None, format="YYYY-MM-DD")

    out = df.copy()
    if query:
        q = query.strip().lower()
        mask = out.apply(lambda row: q in " ".join(str(v).lower() for v in row.values), axis=1)
        out = out[mask]
    if plan_filter != "All" and _has_col("Plan Key"):
        out = out[out["Plan Key"] == plan_filter]
    sticky_status_filter = st.session_state.get("admin_directory_status_filter")
    if sticky_status_filter == "__NEEDS_ATTENTION__" and _has_col("Needs Attention"):
        out = out[out["Needs Attention"] == True]
    elif status_filter != "All" and _has_col("Admin Status"):
        st.session_state["admin_directory_status_filter"] = status_filter
        out = out[out["Admin Status"] == status_filter]
    else:
        st.session_state["admin_directory_status_filter"] = "All"
    if risk_filter != "All" and _has_col("Risk Key"):
        risk_key = risk_filter.split()[0].upper()
        out = out[out["Risk Key"] == risk_key]
    if country_filter != "All" and _has_col("Country"):
        out = out[out["Country"] == country_filter]
    if role_filter != "All" and _has_col("Role"):
        out = out[out["Role"] == role_filter]
    if multiple_trials_only and _has_col("Trial Attempts"):
        out = out[out["Trial Attempts"] > 1]
    if device_filter and _has_col("Device Fingerprint"):
        needle = device_filter.strip().lower()
        out = out[out["Device Fingerprint"].astype(str).str.lower().str.contains(needle, na=False)]
    if signup_from and _has_col("Created"):
        out = out[out[("Created Raw" if "Created Raw" in out.columns else "Created")].apply(lambda value: (_parse_dt(value) or datetime.min.replace(tzinfo=timezone.utc)).date() >= signup_from)]
    if trial_end_before and _has_col("Trial Ends"):
        out = out[out[("Trial Ends Raw" if "Trial Ends Raw" in out.columns else "Trial Ends")].apply(lambda value: (_parse_dt(value) or datetime.max.replace(tzinfo=timezone.utc)).date() <= trial_end_before)]
    return out


def render_customer_table(df: pd.DataFrame) -> None:
    st.markdown(
        """
        <div class="admin-tip" style="margin-bottom:0.8rem;">
            <strong>How to use Customer Directory</strong><br>
            Use this table to search customers, review plan/status, monitor trial risk, and inspect login metadata.<br><br>
            Search: enter name, email, plan, or status.<br>
            Plan / Status / Risk / Country: narrow the table.<br>
            Multiple Trials: show accounts with repeat trial attempts.<br>
            Device: search by device fingerprint, IP, browser, or operating system.<br>
            Signup From / Trial End Before: optional date filters.<br>
            Clear date filters if the table shows no results.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.subheader("👥 Customer Directory")
    filtered = filter_customer_df(df)

    if filtered.empty:
        st.info("No customers match the current filters. Clear filters or widen the date range.")

    display_cols = [
        "Name",
        "Email",
        "Plan",
        "Directory Status",
        "Trial Countdown",
        "Trial End",
        "Created",
        "Last Login",
        "Onboarding Progress",
        "Actions",
    ]

    optional_metadata_cols = ["Fraud Flags", "Risk", "Risk Score"]

    for col in optional_metadata_cols:
        if col not in filtered.columns:
            continue
        values = filtered[col].astype(str).str.strip()
        non_empty = values[(values != "") & (values != "—") & (values != "UNKNOWN")]
        if not non_empty.empty:
            display_cols.append(col)

    safe_display_cols = [col for col in display_cols if col in filtered.columns]
    st.dataframe(
        filtered[safe_display_cols] if (not filtered.empty and safe_display_cols) else filtered,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(f"Showing {len(filtered)} of {len(df)} customers.")
    _quick_customer_action(filtered if not filtered.empty else df)


def _selected_customer_row(df: pd.DataFrame) -> Optional[pd.Series]:
    if df.empty:
        return None
    labels = [f"{row['Name']} · {row['Email']}" for _, row in df.iterrows()]
    default_label = str(st.session_state.get("admin_selected_customer_label") or "")
    default_index = labels.index(default_label) if default_label in labels else 0
    selected_label = st.selectbox("Select customer", labels, index=default_index)
    st.session_state["admin_selected_customer_label"] = selected_label
    return df.iloc[labels.index(selected_label)]


def _quick_customer_action(df: pd.DataFrame) -> None:
    if df.empty:
        return

    labels = [f"{row['Name']} · {row['Email']}" for _, row in df.iterrows()]
    default_label = str(st.session_state.get("admin_selected_customer_label") or "")
    default_index = labels.index(default_label) if default_label in labels else 0

    st.markdown("### Row Actions")
    a1, a2, a3, a4 = st.columns([0.42, 0.22, 0.16, 0.2], gap="small")
    with a1:
        selected_label = st.selectbox("Customer", labels, index=default_index, key="admin_quick_action_customer")

    selected_row_preview = df.iloc[labels.index(selected_label)]
    trial_start_missing = _parse_dt(selected_row_preview.get("Trial Start Raw") or selected_row_preview.get("Trial Start")) is None
    trial_end_missing = _parse_dt(selected_row_preview.get("Trial End Raw") or selected_row_preview.get("Trial End") or selected_row_preview.get("Trial Ends Raw") or selected_row_preview.get("Trial Ends")) is None
    trial_dates_inconsistent = not bool(selected_row_preview.get("Trial Dates Consistent", True)) and bool(selected_row_preview.get("Trial Consistency Warning"))

    action_options = [
        "Open Customer",
        "Repair Provisioning",
        "Start Trial",
        "Extend Trial",
        "Upgrade",
        "Reset Password",
        "Suspend",
        "Delete",
    ]
    if trial_start_missing or trial_end_missing:
        action_options.insert(2, "Repair Trial")
    if trial_dates_inconsistent:
        action_options.insert(2 if not (trial_start_missing or trial_end_missing) else 3, "Rebuild Trial Dates")

    with a2:
        action = st.selectbox(
            "⋮",
            action_options,
            key="admin_quick_action_action",
        )
    with a3:
        days = st.number_input("Days", min_value=1, max_value=90, value=7, key="admin_quick_action_days")
    with a4:
        run_action = st.button("Run", width="stretch", key="admin_quick_action_run")

    with st.expander(f"Onboarding Progress Details · {selected_row_preview.get('Onboarding Progress', '0/6')}", expanded=False):
        stages = [
            ("Authentication Account", bool(selected_row_preview.get("Onboarding Account Created"))),
            ("Email Verified", bool(selected_row_preview.get("Onboarding Email Verified"))),
            ("First Login", bool(selected_row_preview.get("Onboarding First Login"))),
            ("Customer Profile", bool(selected_row_preview.get("Onboarding Profile Created"))),
            ("Trial Created", bool(selected_row_preview.get("Onboarding Trial Started"))),
            ("Subscription Initialized", bool(selected_row_preview.get("Onboarding Subscription Created"))),
        ]
        for label, ok in stages:
            st.markdown(f"{'✔' if ok else '✖'} {label}")

        provisioning_trace = str(selected_row_preview.get("Provisioning Trace") or "").strip()
        if provisioning_trace:
            st.caption(f"Last Provisioning Trace: {provisioning_trace}")
        trial_warning = str(selected_row_preview.get("Trial Consistency Warning") or "").strip()
        if trial_warning:
            st.warning(trial_warning)

    if not run_action:
        return

    selected_row = df.iloc[labels.index(selected_label)]
    st.session_state["admin_selected_customer_label"] = selected_label

    if action == "Open Customer":
        st.success("Customer selected in Operational Command Panel.")
        return

    if action == "Repair Provisioning":
        ok, message = apply_repair_provisioning(selected_row.to_dict(), "Repair Provisioning from Customer Directory quick action")
        if ok:
            st.success(message)
            st.rerun()
        st.error(message)
        return

    if action == "Repair Trial":
        ok, message = apply_repair_trial(selected_row.to_dict(), "Repair Trial from Customer Directory quick action")
        if ok:
            st.success(message)
            st.rerun()
        st.error(message)
        return

    if action == "Rebuild Trial Dates":
        ok, message = apply_rebuild_trial_dates(selected_row.to_dict(), "Rebuild Trial Dates from Customer Directory quick action")
        if ok:
            st.success(message)
            st.rerun()
        st.error(message)
        return

    if action == "Start Trial":
        ok, message = apply_trial_action(selected_row.to_dict(), "Reset Trial", int(days), "Started from Customer Directory quick action")
        if ok:
            st.success(message)
            st.rerun()
        st.error(message)
        return

    if action == "Extend Trial":
        ok, message = apply_trial_action(selected_row.to_dict(), "Extend Trial", int(days), "Extended from Customer Directory quick action")
        if ok:
            st.success(message)
            st.rerun()
        st.error(message)
        return

    if action == "Upgrade":
        ok, message = apply_subscription_action(selected_row.to_dict(), "Upgrade Plan", PLAN_PRO, "Upgrade from Customer Directory quick action")
        if ok:
            st.success(message)
            st.rerun()
        st.error(message)
        return

    if action == "Reset Password":
        ok, message = apply_account_action(selected_row.to_dict(), "Reset Password", "Password reset from Customer Directory quick action")
        if ok:
            st.success(message)
            st.rerun()
        st.error(message)
        return

    if action == "Suspend":
        ok, message = apply_account_action(selected_row.to_dict(), "Lock Account", "Suspended from Customer Directory quick action")
        if ok:
            st.success(message)
            st.rerun()
        st.error(message)
        return

    if action == "Delete":
        st.error("Delete action is intentionally disabled in this UI build. Use backend admin tooling for hard deletes.")


def _display_login_history(selected: pd.Series, login_history_rows: List[Dict[str, Any]]) -> None:
    user_id = str(selected.get("User ID") or "")
    rows = [row for row in login_history_rows if str(row.get("user_id") or row.get("customer_user_id") or "") == user_id]
    if not rows and str(selected.get("Last Login") or "") != "—":
        rows = [{
            "created_at": selected.get("Last Login"),
            "ip_address": selected.get("Last Login IP"),
            "country": selected.get("Country"),
            "city": selected.get("City"),
            "browser": selected.get("Browser"),
            "device": selected.get("Device Fingerprint"),
            "success": True,
        }]

    if not rows:
        st.info("No login history recorded for this customer yet.")
        return

    history_df = pd.DataFrame(
        [
            {
                "Date": _fmt_datetime(_login_event_timestamp(row) or row.get("created_at")),
                "IP": str(row.get("ip_address") or row.get("ip") or "—"),
                "Country": str(row.get("country") or "—"),
                "Browser": str(row.get("browser") or _browser_from_user_agent(row.get("user_agent")) or "—"),
                "Device": _short_device_id(row.get("device") or row.get("device_id") or "—"),
                "Success / Failed": "Success" if _login_event_success(row) is not False else "Failed",
                "Approximate Location": f"{str(row.get('city') or '—')}, {str(row.get('country') or '—')}",
            }
            for row in rows
        ]
    )
    st.dataframe(history_df, use_container_width=True, hide_index=True)


def _display_customer_audit_log(selected: pd.Series, audit_rows: List[Dict[str, Any]]) -> None:
    user_id = str(selected.get("User ID") or "")
    rows = [row for row in audit_rows if str(row.get("customer_user_id") or row.get("user_id") or "") == user_id]
    if not rows:
        st.info("No audit actions recorded for this customer yet.")
        return

    audit_df = pd.DataFrame(
        [
            {
                "Timestamp": _fmt_datetime(row.get("timestamp")),
                "Admin User": str(row.get("admin_user") or "—"),
                "Action": str(row.get("action") or "—"),
                "Old Value": str(row.get("old_value") or "—"),
                "New Value": str(row.get("new_value") or "—"),
                "Reason": str(row.get("reason") or ""),
            }
            for row in rows
        ]
    )
    st.dataframe(audit_df, use_container_width=True, hide_index=True)


def _save_internal_notes(selected: pd.Series, notes_value: str) -> Tuple[bool, str]:
    ok, message = update_customer_trial_controls(str(selected.get("User ID") or ""), {"trial_notes": notes_value})
    if ok:
        _append_admin_audit_log(selected.to_dict(), "Save Notes", {"trial_notes": selected.get("Trial Notes")}, {"trial_notes": notes_value}, "Internal admin notes updated")
    return ok, message


def render_customer_actions(df: pd.DataFrame, login_history_rows: List[Dict[str, Any]], audit_rows: List[Dict[str, Any]]) -> None:
    st.subheader("Operational Command Panel")

    selected = _selected_customer_row(df)
    if selected is None:
        st.info("No customer rows found yet.")
        return

    overview_a, overview_b, overview_c, overview_d = st.columns(4, gap="medium")
    with overview_a:
        st.metric("Risk Score", f"{int(selected.get('Risk Score') or 0)}/100", help=str(selected.get("Risk Explanation") or "No major risk indicators detected."))
    with overview_b:
        st.metric("Trial Attempts", int(selected.get("Trial Attempts") or 0), help="Repeated trial attempts increase risk.")
    with overview_c:
        st.metric("Total Logins", int(selected.get("Total Logins") or 0), help="Successful login count if available.")
    with overview_d:
        st.metric("Fraud Flags", str(selected.get("Fraud Flags") or "—"), help=str(selected.get("Risk Explanation") or ""))

    customer_tabs = st.tabs(["Overview", "Operations", "Login History", "Audit Log", "Notes", "Details"])

    with customer_tabs[0]:
        detail_cols = [
            "Name", "Email", "Plan", "Directory Status", "Trial End", "Created", "Last Login",
            "Onboarding Progress", "Onboarding Summary", "Risk", "Risk Score", "Risk Explanation",
            "First Login", "Total Logins", "Fraud Flags", "Provisioning Trace",
        ]

        for optional_col in ["Signup IP", "Last Login IP", "Country", "City", "Device Fingerprint", "Browser", "Operating System", "Trial Attempts", "Last IP Activity"]:
            value = str(selected.get(optional_col, "") or "").strip()
            if value and value not in {"—", "UNKNOWN"}:
                detail_cols.append(optional_col)

        detail_df = pd.DataFrame([{col: selected.get(col, "—") for col in detail_cols}])
        st.dataframe(detail_df, use_container_width=True, hide_index=True)

        st.markdown("#### Onboarding Stages")
        stages = [
            ("Authentication Account", bool(selected.get("Onboarding Account Created"))),
            ("Email Verified", bool(selected.get("Onboarding Email Verified"))),
            ("First Login", bool(selected.get("Onboarding First Login"))),
            ("Customer Profile", bool(selected.get("Onboarding Profile Created"))),
            ("Trial Created", bool(selected.get("Onboarding Trial Started"))),
            ("Subscription Initialized", bool(selected.get("Onboarding Subscription Created"))),
        ]
        for label, is_ok in stages:
            st.markdown(f"{'✔' if is_ok else '❌'} {label}")

    with customer_tabs[1]:
        op_tabs = st.tabs(["Subscription", "Trial", "Account"])

        with op_tabs[0]:
            with st.form("admin_subscription_action_form"):
                action = st.selectbox("Subscription Action", ["Upgrade Plan", "Downgrade Plan", "Activate", "Suspend", "Cancel"])
                target_plan = st.selectbox(
                    "Target Plan",
                    PLAN_OPTIONS,
                    index=PLAN_OPTIONS.index(selected["Plan Key"]) if selected["Plan Key"] in PLAN_OPTIONS else 0,
                    format_func=lambda p: PLAN_LABELS.get(p, p),
                )
                reason = st.text_input("Reason (optional)")
                confirm = st.checkbox("I confirm this subscription change")
                submitted = st.form_submit_button("Apply Subscription Action", use_container_width=True, disabled=not confirm)

            if submitted:
                ok, message = apply_subscription_action(selected.to_dict(), action, target_plan, reason)
                if ok:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

        with op_tabs[1]:
            with st.form("admin_trial_action_form"):
                action = st.selectbox("Trial Action", ["Extend Trial", "End Trial", "Reset Trial"])
                days = st.number_input("Extension Days", min_value=1, max_value=90, value=7)
                reason = st.text_input("Reason (optional)")
                confirm = st.checkbox("I confirm this trial action")
                submitted = st.form_submit_button("Apply Trial Action", use_container_width=True, disabled=not confirm)

            if submitted:
                ok, message = apply_trial_action(selected.to_dict(), action, int(days), reason)
                if ok:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

        with op_tabs[2]:
            with st.form("admin_account_action_form"):
                action = st.selectbox("Account Action", ["Reset Password", "Force Logout", "Lock Account", "Unlock Account"])
                reason = st.text_input("Reason (optional)")
                confirm = st.checkbox("I confirm this account action")
                submitted = st.form_submit_button("Apply Account Action", use_container_width=True, disabled=not confirm)

            if submitted:
                ok, message = apply_account_action(selected.to_dict(), action, reason)
                if ok:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

    with customer_tabs[2]:
        _display_login_history(selected, login_history_rows)

    with customer_tabs[3]:
        _display_customer_audit_log(selected, audit_rows)

    with customer_tabs[4]:
        notes_value = st.text_area("Internal Notes", value=str(selected.get("Trial Notes") or ""), height=160)
        if st.button("Save Internal Notes", use_container_width=True):
            ok, message = _save_internal_notes(selected, notes_value)
            if ok:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    with customer_tabs[5]:
        with st.expander("Developer Details", expanded=False):
            dev_cols = [
                "UID",
                "Provider",
                "Email Confirmed",
                "Created At",
                "Last Sign In",
                "Stripe Customer ID",
                "Stripe Subscription",
                "Integrity Warning",
                "Provisioning Trace",
                "Has Profile",
                "Has Subscription",
            ]
            dev_df = pd.DataFrame([{col: selected.get(col, "—") for col in dev_cols}])
            st.dataframe(dev_df, use_container_width=True, hide_index=True)


# Export helpers serialize current admin views without mutating source data.
def _build_excel_bytes(sheets: Dict[str, pd.DataFrame]) -> Optional[bytes]:
    for engine in ["xlsxwriter", "openpyxl"]:
        try:
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine=engine) as writer:
                for sheet_name, frame in sheets.items():
                    frame.to_excel(writer, sheet_name=sheet_name[:31], index=False)
            return buffer.getvalue()
        except Exception:
            continue
    return None


def _customer_summary_text(df: pd.DataFrame) -> str:
    lines = ["JFBP Quant Desk Customer Summary", ""]
    for _, row in df.iterrows():
        lines.append(
            f"- {row.get('Name', row.get('Email', 'Unknown User'))} | {row.get('Email', '—')} | {row.get('Plan', '—')} | "
            f"{row.get('Status', '—')} | {row.get('Risk', '—')} | Attempts {row.get('Trial Attempts', 0)}"
        )
    return "\n".join(lines)


def render_export_panel(df: pd.DataFrame, audit_rows: List[Dict[str, Any]], login_history_rows: List[Dict[str, Any]]) -> None:
    st.subheader("Exports")
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    excel_bytes = _build_excel_bytes(
        {
            "customers": df,
            "audit_log": pd.DataFrame(audit_rows),
            "login_history": pd.DataFrame(login_history_rows),
        }
    )
    summary_bytes = _customer_summary_text(df).encode("utf-8")

    st.download_button("Export CSV", data=csv_bytes, file_name="admin_customer_export.csv", mime="text/csv", use_container_width=True)
    if excel_bytes:
        st.download_button(
            "Export Excel",
            data=excel_bytes,
            file_name="admin_customer_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    else:
        st.info("Excel export requires xlsxwriter or openpyxl in this environment.")
    st.download_button("Export Customer Summary", data=summary_bytes, file_name="customer_summary.txt", mime="text/plain", use_container_width=True)


def render_global_audit_log(audit_rows: List[Dict[str, Any]]) -> None:
    st.subheader("Admin Audit Log")
    if not audit_rows:
        st.info("No admin audit rows recorded yet.")
        return
    audit_df = pd.DataFrame(
        [
            {
                "Timestamp": _fmt_datetime(row.get("timestamp")),
                "Admin User": str(row.get("admin_user") or "—"),
                "Customer": str(row.get("customer_email") or row.get("customer_name") or "—"),
                "Action": str(row.get("action") or "—"),
                "Old Value": str(row.get("old_value") or "—"),
                "New Value": str(row.get("new_value") or "—"),
                "Reason": str(row.get("reason") or ""),
            }
            for row in sorted(
                audit_rows,
                key=lambda row: _parse_dt(row.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )
        ]
    )
    st.dataframe(audit_df, use_container_width=True, hide_index=True)


def render_admin_control_center() -> None:
    inject_responsive_css()
    inject_card_css()
    inject_admin_css()
    render_hero()

    if not render_admin_gate():
        return

    ready, message = admin_supabase_ready()
    if not ready:
        st.error(message)
        return

    if "anon key" in message.lower():
        st.warning(message)
    else:
        st.success(message)

    try:
        auth_users = load_auth_users()
        profiles = load_profiles()
        subscriptions = load_subscriptions()
        audit_rows = load_audit_log_rows()
        login_history_rows = load_login_history_rows()
        df = merge_customer_rows(auth_users, profiles, subscriptions, login_history_rows, audit_rows)
    except Exception as exc:
        st.error(f"Could not load admin customer data: {exc}")
        st.caption("Check SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, table names, and RLS/API permissions.")
        return

    if not auth_users:
        st.warning("Auth user directory is empty or unavailable. Add SUPABASE_SERVICE_ROLE_KEY so Auth users are visible in Customer Directory.")

    render_overview_cards(df)

    tabs = st.tabs(["Customers", "Operations", "Audit Log", "Exports", "Raw Data", "Setup Notes"])

    with tabs[0]:
        render_dashboard_analytics(df, audit_rows)
        render_customer_table(df)

    with tabs[1]:
        render_customer_actions(df, login_history_rows, audit_rows)

    with tabs[2]:
        render_global_audit_log(audit_rows)

    with tabs[3]:
        render_export_panel(df, audit_rows, login_history_rows)

    with tabs[4]:
        st.subheader("Raw Customer Rows")
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption("Secret keys and tokens are never displayed here.")

    with tabs[5]:
        st.markdown(
            """
            ### Recommended Supabase Tables

            This page expects:

            - `user_profiles`: `user_id`, `email`, `full_name`, `plan`, `account_status`, `trial_start`, `trial_end`, `role`, `created_at`
            - Trial protection fields on `user_profiles`: `signup_ip`, `signup_country`, `device_id`, `user_agent`, `trial_started_at`, `trial_attempts`, `risk_score`, `last_ip_activity`, `trial_whitelisted`, `trial_ignored`, `trial_blocked`, `trial_notes`
            - Optional metadata fields on `user_profiles`: `last_login_ip`, `last_login_country`, `last_login_city`, `browser`, `operating_system`, `first_login_at`, `last_login_at`, `total_logins`
            - `subscriptions`: `user_id`, `plan`, `status`, `stripe_customer_id`, `stripe_subscription_id`, `current_period_end`, `created_at`
            - Optional audit tables: `admin_audit_log` or `admin_audit_logs`
            - Optional login history tables: `login_history`, `user_login_history`, or `auth_login_history`

            Metadata notes:

            - Browser and operating system are derived from the stored user agent with simple server-side parsing.
            - `device_id` uses a server-side fallback fingerprint when no stable client fingerprint is available in Streamlit.
            - Country remains `UNKNOWN` unless your hosting headers or an external IP geolocation provider supply location metadata.

            ### Recommended Secret

            Add `SUPABASE_SERVICE_ROLE_KEY` to Streamlit Secrets for this admin-only page so the console can read all customer rows despite RLS.

            Keep this page available only to founder/admin emails.
            """
        )


def run_page() -> None:
    render_admin_control_center()


def page() -> None:
    run_page()


if __name__ == "__main__":
    run_page()
