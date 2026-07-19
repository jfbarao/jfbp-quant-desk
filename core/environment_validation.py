from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlparse

import requests
import streamlit as st


DEVELOPMENT_REF = "qkqexvlprzjqjtsarqbz"
PRODUCTION_REF = "zqzujesufquifrtqnanb"

ENV_ALIASES = {
    "dev": "development",
    "development": "development",
    "local": "development",
    "prod": "production",
    "production": "production",
    "live": "production",
}


class EnvironmentValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class EnvironmentValidationResult:
    environment: str
    supabase_ref: str
    redirect_host: str
    stripe_mode: str


def _secret_value(name: str, default: str = "") -> str:
    value = ""
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""

    if value is None or str(value).strip() == "":
        value = os.environ.get(name, default)

    return str(value or default).strip()


def _normalize_env(raw: str) -> str:
    key = str(raw or "").strip().lower()
    if not key:
        return ""
    return ENV_ALIASES.get(key, "")


def _host_from_url(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    return str(parsed.hostname or "").strip().lower()


def _supabase_ref_from_url(url: str) -> str:
    host = _host_from_url(url)
    if not host:
        return ""
    return host.split(".", 1)[0]


def _decode_jwt_payload(token: str) -> Dict[str, Any]:
    parts = str(token or "").split(".")
    if len(parts) < 2:
        return {}
    payload_part = parts[1]
    padding = "=" * (-len(payload_part) % 4)
    try:
        raw = base64.urlsafe_b64decode(payload_part + padding)
        decoded = json.loads(raw.decode("utf-8"))
        return decoded if isinstance(decoded, dict) else {}
    except Exception:
        return {}


def _project_ref_from_key(key: str) -> str:
    payload = _decode_jwt_payload(key)
    return str(payload.get("ref") or "").strip()


def _is_local_host(host: str) -> bool:
    host = str(host or "").strip().lower()
    return host in {"localhost", "127.0.0.1", "0.0.0.0"}


def _is_production_host(host: str) -> bool:
    host = str(host or "").strip().lower()
    return host.endswith("jfbpquantdesk.com") or host.endswith("streamlit.app")


def _probe_service_role(url: str, service_role_key: str, http_get: Callable[..., Any]) -> bool:
    endpoint = f"{url.rstrip('/')}/auth/v1/admin/users"
    response = http_get(
        endpoint,
        headers={
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
        },
        params={"page": 1, "per_page": 1},
        timeout=10,
    )
    return int(getattr(response, "status_code", 500) or 500) < 400


def validate_runtime_config(
    config: Dict[str, str],
    *,
    http_get: Optional[Callable[..., Any]] = None,
) -> EnvironmentValidationResult:
    env = _normalize_env(config.get("APP_ENV", ""))
    if not env:
        raise EnvironmentValidationError("Invalid APP_ENV. Use 'development' or 'production'.")

    supabase_url = str(config.get("SUPABASE_URL", "")).strip()
    supabase_ref = _supabase_ref_from_url(supabase_url)
    if not supabase_ref:
        raise EnvironmentValidationError("SUPABASE_URL is missing or invalid.")

    anon_key = str(config.get("SUPABASE_ANON_KEY", "")).strip()
    service_role_key = str(config.get("SUPABASE_SERVICE_ROLE_KEY", "")).strip()
    if not anon_key or not service_role_key:
        raise EnvironmentValidationError("SUPABASE_ANON_KEY and SUPABASE_SERVICE_ROLE_KEY are required.")

    expected_ref = DEVELOPMENT_REF if env == "development" else PRODUCTION_REF
    wrong_ref = PRODUCTION_REF if env == "development" else DEVELOPMENT_REF

    if supabase_ref != expected_ref:
        raise EnvironmentValidationError("Supabase project reference does not match declared APP_ENV.")
    if supabase_ref == wrong_ref:
        raise EnvironmentValidationError("Supabase project reference is not allowed in this APP_ENV.")

    anon_ref = _project_ref_from_key(anon_key)
    if anon_ref and anon_ref != supabase_ref:
        raise EnvironmentValidationError("SUPABASE_ANON_KEY project reference does not match SUPABASE_URL.")

    service_ref = _project_ref_from_key(service_role_key)
    if service_ref and service_ref != supabase_ref:
        raise EnvironmentValidationError("SUPABASE_SERVICE_ROLE_KEY project reference does not match SUPABASE_URL.")

    probe_get = http_get or requests.get
    if not service_ref and service_role_key.startswith("sb_secret_"):
        if not _probe_service_role(supabase_url, service_role_key, probe_get):
            raise EnvironmentValidationError("SUPABASE_SERVICE_ROLE_KEY is invalid for the configured project.")

    signup_redirect = str(config.get("SUPABASE_EMAIL_REDIRECT_TO", "")).strip()
    redirect_host = _host_from_url(signup_redirect)
    if not redirect_host:
        raise EnvironmentValidationError("SUPABASE_EMAIL_REDIRECT_TO is required.")

    stripe_mode = str(config.get("STRIPE_MODE", "")).strip().lower()
    if stripe_mode not in {"test", "live"}:
        raise EnvironmentValidationError("STRIPE_MODE must be 'test' or 'live'.")

    if env == "development" and stripe_mode != "test":
        raise EnvironmentValidationError("Development requires Stripe test mode.")
    if env == "production" and stripe_mode != "live":
        raise EnvironmentValidationError("Production requires Stripe live mode.")

    session_encryption_key = str(config.get("SESSION_ENCRYPTION_KEY", "")).strip()
    cookie_signing_key = str(config.get("SESSION_COOKIE_SIGNING_KEY", "")).strip()
    if not session_encryption_key:
        raise EnvironmentValidationError("SESSION_ENCRYPTION_KEY is required.")
    if not cookie_signing_key:
        raise EnvironmentValidationError("SESSION_COOKIE_SIGNING_KEY is required.")
    if len(session_encryption_key) < 32:
        raise EnvironmentValidationError("SESSION_ENCRYPTION_KEY is too short (min 32 characters).")
    if len(cookie_signing_key) < 32:
        raise EnvironmentValidationError("SESSION_COOKIE_SIGNING_KEY is too short (min 32 characters).")

    billing_portal_url = str(config.get("STRIPE_BILLING_PORTAL_URL", "")).strip()
    if env == "production" and not billing_portal_url:
        raise EnvironmentValidationError("STRIPE_BILLING_PORTAL_URL is required in production.")
    if env == "development" and billing_portal_url:
        raise EnvironmentValidationError("Development must not configure STRIPE_BILLING_PORTAL_URL.")
    if billing_portal_url:
        billing_portal_host = _host_from_url(billing_portal_url)
        if not billing_portal_host:
            raise EnvironmentValidationError("STRIPE_BILLING_PORTAL_URL is invalid.")

    stripe_secret_key = str(config.get("STRIPE_SECRET_KEY", "")).strip()
    if stripe_secret_key:
        if stripe_mode == "test" and not stripe_secret_key.startswith("sk_test_"):
            raise EnvironmentValidationError("STRIPE_SECRET_KEY does not match STRIPE_MODE=test.")
        if stripe_mode == "live" and not stripe_secret_key.startswith("sk_live_"):
            raise EnvironmentValidationError("STRIPE_SECRET_KEY does not match STRIPE_MODE=live.")

    if env == "development":
        if _is_production_host(redirect_host):
            raise EnvironmentValidationError("Development cannot use production redirect host.")
        if not _is_local_host(redirect_host):
            raise EnvironmentValidationError("Development redirect host must be localhost.")
    else:
        if _is_local_host(redirect_host):
            raise EnvironmentValidationError("Production cannot use localhost redirect host.")

    for key in ("STRIPE_SUCCESS_URL", "STRIPE_CANCEL_URL"):
        value = str(config.get(key, "")).strip()
        if not value:
            continue
        host = _host_from_url(value)
        if not host:
            continue
        if env == "development" and _is_production_host(host):
            raise EnvironmentValidationError(f"Development cannot use production host in {key}.")
        if env == "production" and _is_local_host(host):
            raise EnvironmentValidationError(f"Production cannot use localhost in {key}.")

    return EnvironmentValidationResult(
        environment=env,
        supabase_ref=supabase_ref,
        redirect_host=redirect_host,
        stripe_mode=stripe_mode,
    )


def build_runtime_config_from_secrets() -> Dict[str, str]:
    return {
        "APP_ENV": _secret_value("APP_ENV", ""),
        "SUPABASE_URL": _secret_value("SUPABASE_URL", ""),
        "SUPABASE_ANON_KEY": _secret_value("SUPABASE_ANON_KEY", ""),
        "SUPABASE_SERVICE_ROLE_KEY": _secret_value("SUPABASE_SERVICE_ROLE_KEY", ""),
        "SUPABASE_EMAIL_REDIRECT_TO": _secret_value("SUPABASE_EMAIL_REDIRECT_TO", ""),
        "SESSION_ENCRYPTION_KEY": _secret_value("SESSION_ENCRYPTION_KEY", ""),
        "SESSION_COOKIE_SIGNING_KEY": _secret_value("SESSION_COOKIE_SIGNING_KEY", ""),
        "STRIPE_MODE": _secret_value("STRIPE_MODE", ""),
        "STRIPE_SECRET_KEY": _secret_value("STRIPE_SECRET_KEY", ""),
        "STRIPE_BILLING_PORTAL_URL": _secret_value("STRIPE_BILLING_PORTAL_URL", ""),
        "STRIPE_SUCCESS_URL": _secret_value("STRIPE_SUCCESS_URL", ""),
        "STRIPE_CANCEL_URL": _secret_value("STRIPE_CANCEL_URL", ""),
    }


@st.cache_data(show_spinner=False, ttl=120)
def validate_runtime_environment_cached(config: Dict[str, str]) -> EnvironmentValidationResult:
    return validate_runtime_config(config)


def validate_runtime_environment() -> EnvironmentValidationResult:
    config = build_runtime_config_from_secrets()
    return validate_runtime_environment_cached(config)


def default_signup_redirect_for_env(environment: str) -> str:
    if _normalize_env(environment) == "production":
        return "https://jfbpquantdesk.com"
    return "http://localhost:8501"


def default_password_reset_redirect_for_env(environment: str) -> str:
    if _normalize_env(environment) == "production":
        return "https://jfbpquantdesk.com/reset-password"
    return "http://localhost:8501"
