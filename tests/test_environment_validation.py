from __future__ import annotations

import base64
import json

import pytest

from core.environment_validation import (
    DEVELOPMENT_REF,
    PRODUCTION_REF,
    EnvironmentValidationError,
    validate_runtime_config,
)


def _jwt_with_ref(ref: str) -> str:
    # Tests only assert boundary behavior; signature is not validated by parser.
    payload = json.dumps({"ref": ref}, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload).decode("utf-8").rstrip("=")
    return f"x.{payload_b64}.y"


def _base_config(env: str, ref: str) -> dict[str, str]:
    mode = "test" if env == "development" else "live"
    stripe_key = "sk_test_example" if mode == "test" else "sk_live_example"
    cfg = {
        "APP_ENV": env,
        "SUPABASE_URL": f"https://{ref}.supabase.co",
        "SUPABASE_ANON_KEY": _jwt_with_ref(ref),
        "SUPABASE_SERVICE_ROLE_KEY": _jwt_with_ref(ref),
        "SUPABASE_EMAIL_REDIRECT_TO": "http://localhost:8501" if env == "development" else "https://jfbpquantdesk.com",
        "SESSION_ENCRYPTION_KEY": "A" * 48,
        "SESSION_COOKIE_SIGNING_KEY": "B" * 48,
        "STRIPE_MODE": mode,
        "STRIPE_SECRET_KEY": stripe_key,
        "STRIPE_SUCCESS_URL": "http://localhost:8501/?checkout=success" if env == "development" else "https://jfbpquantdesk.com/?checkout=success",
        "STRIPE_CANCEL_URL": "http://localhost:8501/?checkout=cancelled" if env == "development" else "https://jfbpquantdesk.com/?checkout=cancelled",
        "STRIPE_BILLING_PORTAL_URL": "" if env == "development" else "https://billing.stripe.com/p/login/example",
    }
    return cfg


def test_valid_development_config_passes():
    result = validate_runtime_config(_base_config("development", DEVELOPMENT_REF))
    assert result.environment == "development"
    assert result.supabase_ref == DEVELOPMENT_REF
    assert result.stripe_mode == "test"


def test_valid_production_config_passes():
    result = validate_runtime_config(_base_config("production", PRODUCTION_REF))
    assert result.environment == "production"
    assert result.supabase_ref == PRODUCTION_REF
    assert result.stripe_mode == "live"


@pytest.mark.parametrize(
    ("mutator", "message_snippet"),
    [
        (lambda c: c.__setitem__("APP_ENV", ""), "Invalid APP_ENV"),
        (lambda c: c.__setitem__("APP_ENV", "invalid"), "Invalid APP_ENV"),
        (lambda c: c.__setitem__("SUPABASE_URL", ""), "SUPABASE_URL is missing or invalid"),
        (lambda c: c.__setitem__("SUPABASE_ANON_KEY", ""), "SUPABASE_ANON_KEY and SUPABASE_SERVICE_ROLE_KEY are required"),
        (lambda c: c.__setitem__("SUPABASE_SERVICE_ROLE_KEY", ""), "SUPABASE_ANON_KEY and SUPABASE_SERVICE_ROLE_KEY are required"),
        (lambda c: c.__setitem__("SESSION_ENCRYPTION_KEY", ""), "SESSION_ENCRYPTION_KEY is required"),
        (lambda c: c.__setitem__("SESSION_COOKIE_SIGNING_KEY", ""), "SESSION_COOKIE_SIGNING_KEY is required"),
        (lambda c: c.__setitem__("SESSION_ENCRYPTION_KEY", "short"), "SESSION_ENCRYPTION_KEY is too short"),
        (lambda c: c.__setitem__("SESSION_COOKIE_SIGNING_KEY", "short"), "SESSION_COOKIE_SIGNING_KEY is too short"),
        (lambda c: c.__setitem__("SUPABASE_EMAIL_REDIRECT_TO", ""), "SUPABASE_EMAIL_REDIRECT_TO is required"),
        (lambda c: c.__setitem__("STRIPE_MODE", "test"), "Production requires Stripe live mode"),
        (lambda c: c.__setitem__("STRIPE_SECRET_KEY", "sk_test_wrong"), "STRIPE_SECRET_KEY does not match STRIPE_MODE=live"),
        (lambda c: c.__setitem__("SUPABASE_URL", f"https://{DEVELOPMENT_REF}.supabase.co"), "Supabase project reference does not match declared APP_ENV"),
        (lambda c: c.__setitem__("SUPABASE_ANON_KEY", _jwt_with_ref(DEVELOPMENT_REF)), "SUPABASE_ANON_KEY project reference does not match SUPABASE_URL"),
        (lambda c: c.__setitem__("STRIPE_BILLING_PORTAL_URL", ""), "STRIPE_BILLING_PORTAL_URL is required in production"),
        (lambda c: c.__setitem__("STRIPE_BILLING_PORTAL_URL", "not-a-url"), "STRIPE_BILLING_PORTAL_URL is invalid"),
    ],
)
def test_production_fail_closed_cases(mutator, message_snippet):
    cfg = _base_config("production", PRODUCTION_REF)
    mutator(cfg)
    with pytest.raises(EnvironmentValidationError) as exc:
        validate_runtime_config(cfg)
    assert message_snippet in str(exc.value)


@pytest.mark.parametrize(
    ("mutator", "message_snippet"),
    [
        (lambda c: c.__setitem__("SUPABASE_URL", f"https://{PRODUCTION_REF}.supabase.co"), "Supabase project reference does not match declared APP_ENV"),
        (lambda c: c.__setitem__("STRIPE_MODE", "live"), "Development requires Stripe test mode"),
        (lambda c: c.__setitem__("SUPABASE_EMAIL_REDIRECT_TO", "https://jfbpquantdesk.com"), "Development cannot use production redirect host"),
        (lambda c: c.__setitem__("STRIPE_BILLING_PORTAL_URL", "https://billing.stripe.com/p/login/example"), "Development must not configure STRIPE_BILLING_PORTAL_URL"),
    ],
)
def test_development_fail_closed_cases(mutator, message_snippet):
    cfg = _base_config("development", DEVELOPMENT_REF)
    mutator(cfg)
    with pytest.raises(EnvironmentValidationError) as exc:
        validate_runtime_config(cfg)
    assert message_snippet in str(exc.value)


def test_error_messages_do_not_echo_secret_values():
    cfg = _base_config("production", PRODUCTION_REF)
    secret_literal = "ultra-secret-cookie-signing-key-material"
    cfg["SESSION_COOKIE_SIGNING_KEY"] = ""
    cfg["SUPABASE_SERVICE_ROLE_KEY"] = secret_literal

    with pytest.raises(EnvironmentValidationError) as exc:
        validate_runtime_config(cfg)

    text = str(exc.value)
    assert "SESSION_COOKIE_SIGNING_KEY" in text
    assert secret_literal not in text
