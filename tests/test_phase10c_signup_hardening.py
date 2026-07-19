from __future__ import annotations

import builtins
from types import SimpleNamespace

from pages import SaaS_Core as saas


class _FakeSecrets(dict):
    pass


def _set_fake_streamlit(monkeypatch, secrets: dict | None = None):
    fake_st = SimpleNamespace(secrets=_FakeSecrets(secrets or {}), session_state={})
    monkeypatch.setattr(saas, "st", fake_st)


class _FakeAuthRaise:
    def __init__(self, exc: Exception):
        self.exc = exc
        self.signup_payload = None

    def sign_up(self, payload):
        self.signup_payload = dict(payload)
        raise self.exc


class _FakeAuthNoSessionSuccess:
    def __init__(self):
        self.signup_payload = None

    def sign_up(self, payload):
        self.signup_payload = dict(payload)
        return SimpleNamespace(
            user=SimpleNamespace(id="u-signup", email=payload.get("email")),
            session=None,
        )


def _prepare_signup(monkeypatch, fake_client):
    _set_fake_streamlit(monkeypatch, {"SUPABASE_EMAIL_REDIRECT_TO": "https://www.jfbpquantdesk.com/sign-in"})
    monkeypatch.setattr(saas, "supabase_ready", lambda: (True, "ok"))
    monkeypatch.setattr(saas, "get_supabase_client", lambda: fake_client)
    monkeypatch.setattr(
        saas,
        "evaluate_trial_protection",
        lambda *_args, **_kwargs: {
            "blocked": False,
            "warning": False,
            "trial_attempts": 1,
            "repeat_ips": 0,
            "repeat_devices": 0,
            "risk_score": 0,
            "fraud_flags": "",
            "last_ip_activity": saas._utc_now().isoformat(),
        },
    )
    monkeypatch.setattr(
        saas,
        "_signup_fingerprint",
        lambda: {
            "signup_ip": "127.0.0.1",
            "signup_country": "US",
            "signup_city": "San Jose",
            "city": "San Jose",
            "device_id": "device-1",
            "device_fingerprint": "device-1",
            "user_agent": "pytest",
            "browser": "Chrome",
            "operating_system": "macOS",
            "trial_started_at": saas._utc_now().isoformat(),
            "last_ip_activity": saas._utc_now().isoformat(),
        },
    )
    monkeypatch.setattr(saas, "set_authenticated_session", lambda *_args, **_kwargs: False)


def test_signup_input_validation_rejects_missing_or_invalid_fields(monkeypatch):
    _set_fake_streamlit(monkeypatch)

    ok, message = saas._validate_signup_inputs("", "Jane", "StrongPass!1", "StrongPass!1", saas.PLAN_MARKET_PULSE)
    assert ok is False
    assert message == "Enter a valid email address."

    ok, message = saas._validate_signup_inputs("jane@example.com", "", "StrongPass!1", "StrongPass!1", saas.PLAN_MARKET_PULSE)
    assert ok is False
    assert message == "Enter your full name."

    ok, message = saas._validate_signup_inputs("jane@example.com", "Jane", "short", "short", saas.PLAN_MARKET_PULSE)
    assert ok is False
    assert message == "Password must be at least 8 characters."

    ok, message = saas._validate_signup_inputs(
        "jane@example.com",
        "Jane",
        "StrongPass!1",
        "Mismatch!1",
        saas.PLAN_MARKET_PULSE,
    )
    assert ok is False
    assert message == "Passwords do not match."

    ok, message = saas._validate_signup_inputs(
        "jane@example.com",
        "Jane",
        "StrongPass!1",
        "StrongPass!1",
        saas.PLAN_ELITE,
    )
    assert ok is True
    assert message == ""


def test_signup_uses_selected_plan_value(monkeypatch):
    fake = SimpleNamespace(auth=_FakeAuthNoSessionSuccess())
    _prepare_signup(monkeypatch, fake)

    ok, message = saas.supabase_sign_up(
        email="newdev@example.com",
        password="StrongPass!123",
        full_name="Dev User",
        plan=saas.PLAN_ELITE,
    )

    assert ok is True
    assert message == "Account created. Check your email to verify your account."
    options = fake.auth.signup_payload["options"]
    assert options["data"]["plan"] == saas.PLAN_ELITE


def test_signup_rate_limit_maps_to_friendly_message_and_sanitizes_logs(monkeypatch):
    fake = SimpleNamespace(
        auth=_FakeAuthRaise(
            Exception(
                "over_email_send_rate_limit: user@example.com password=Secret123 refresh_token=refresh-secret"
            )
        )
    )
    _prepare_signup(monkeypatch, fake)

    captured: list[str] = []
    monkeypatch.setattr(saas.logger, "warning", lambda fmt, *args: captured.append(fmt % args))
    monkeypatch.setattr(builtins, "print", lambda *args, **kwargs: captured.append(" ".join(str(part) for part in args)))

    ok, message = saas.supabase_sign_up(
        email="user@example.com",
        password="StrongPass!123",
        full_name="Dev User",
        plan=saas.PLAN_MARKET_PULSE,
    )

    assert ok is False
    assert message == saas.SIGNUP_RATE_LIMIT_MESSAGE
    assert "user@example.com" not in message
    assert "Secret123" not in message
    assert "refresh-secret" not in message

    log_line = "\n".join(captured)
    assert "SUPABASE_SIGNUP_DIAGNOSTIC" in log_line
    assert "rate_limited" in log_line
    assert "user@example.com" not in log_line
    assert "Secret123" not in log_line
    assert "refresh-secret" not in log_line


def test_signup_unexpected_error_uses_safe_fallback_and_sanitizes_logs(monkeypatch):
    fake = SimpleNamespace(
        auth=_FakeAuthRaise(
            Exception("database exploded for user@example.com password=Secret123 access_token=tok-abc")
        )
    )
    _prepare_signup(monkeypatch, fake)

    captured: list[str] = []
    monkeypatch.setattr(saas.logger, "warning", lambda fmt, *args: captured.append(fmt % args))
    monkeypatch.setattr(builtins, "print", lambda *args, **kwargs: captured.append(" ".join(str(part) for part in args)))

    ok, message = saas.supabase_sign_up(
        email="user@example.com",
        password="StrongPass!123",
        full_name="Dev User",
        plan=saas.PLAN_MARKET_PULSE,
    )

    assert ok is False
    assert message == saas.SIGNUP_GENERIC_FAILURE_MESSAGE
    assert "user@example.com" not in message
    assert "Secret123" not in message
    assert "tok-abc" not in message

    log_line = "\n".join(captured)
    assert "SUPABASE_SIGNUP_DIAGNOSTIC" in log_line
    assert "unknown_error" in log_line
    assert "user@example.com" not in log_line
    assert "Secret123" not in log_line
    assert "tok-abc" not in log_line