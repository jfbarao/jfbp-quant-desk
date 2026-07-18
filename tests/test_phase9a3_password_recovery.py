from __future__ import annotations

from types import SimpleNamespace

import pytest

from pages import SaaS_Core as saas


class _FakeRecoveryAuth:
    def __init__(self):
        self.update_user_calls = 0
        self.last_password = ""
        self.verify_otp_calls = []
        self._session = {"access_token": "recovery-access", "refresh_token": "recovery-refresh"}
        self.exchange_code_calls = []
        self.set_session_calls = []

    def update_user(self, payload=None, password=None):
        self.update_user_calls += 1
        if isinstance(payload, dict):
            self.last_password = str(payload.get("password", "") or "")
        elif isinstance(password, str):
            self.last_password = password

    def verify_otp(self, payload):
        self.verify_otp_calls.append(payload)

    def exchange_code_for_session(self, code):
        self.exchange_code_calls.append(code)

    def set_session(self, access_token=None, refresh_token=None, *args):
        if args:
            access_token = args[0] if len(args) > 0 else access_token
            refresh_token = args[1] if len(args) > 1 else refresh_token
        self.set_session_calls.append(
            {"access_token": access_token, "refresh_token": refresh_token}
        )
        self._session = {"access_token": access_token, "refresh_token": refresh_token}

    def get_session(self):
        return self._session


class _FakeRecoveryClient:
    def __init__(self):
        self.auth = _FakeRecoveryAuth()


def test_validate_password_recovery_inputs_rejects_mismatch():
    ok, message = saas._validate_password_recovery_inputs("password-123", "password-456")
    assert ok is False
    assert "do not match" in message.lower()


def test_complete_password_recovery_calls_sdk_once(monkeypatch):
    client = _FakeRecoveryClient()

    def _should_not_run(*_args, **_kwargs):
        raise AssertionError("unexpected signup or onboarding call")

    monkeypatch.setattr(saas, "supabase_sign_up", _should_not_run)
    monkeypatch.setattr(saas, "ensure_user_workspace_records", _should_not_run)
    monkeypatch.setattr(saas, "initialize_session", _should_not_run)
    monkeypatch.setattr(saas, "_set_session_cookie", _should_not_run)
    monkeypatch.setattr(saas, "_session_store", _should_not_run)

    ok, message = saas._complete_password_recovery(client, "new-password-123")

    assert ok is True
    assert "updated successfully" in message.lower()
    assert client.auth.update_user_calls == 1
    assert client.auth.last_password == "new-password-123"


def test_establish_recovery_session_requires_recovery_link(monkeypatch):
    client = SimpleNamespace(auth=SimpleNamespace())

    monkeypatch.setattr(saas, "_recovery_flow_type", lambda: "")

    ok, message = saas._establish_recovery_session_from_query(client)

    assert ok is False
    assert "not detected" in message.lower()


def test_complete_password_recovery_without_client_fails():
    ok, message = saas._complete_password_recovery(None, "new-password-123")
    assert ok is False
    assert "unavailable" in message.lower()


def test_establish_recovery_session_uses_token_hash(monkeypatch):
    client = _FakeRecoveryClient()

    monkeypatch.setattr(saas, "_is_recovery_callback", lambda: True)
    monkeypatch.setattr(
        saas,
        "_query_param_value",
        lambda name: {"token_hash": "hash-123", "type": "recovery"}.get(name, ""),
    )

    ok, message = saas._establish_recovery_session_from_query(client)

    assert ok is True
    assert "established" in message.lower()
    assert client.auth.verify_otp_calls == [{"type": "recovery", "token_hash": "hash-123"}]


def test_establish_recovery_session_uses_token_with_email(monkeypatch):
    client = _FakeRecoveryClient()

    monkeypatch.setattr(saas, "_is_recovery_callback", lambda: True)
    monkeypatch.setattr(
        saas,
        "_query_param_value",
        lambda name: {
            "token": "token-123",
            "email": "user@example.com",
            "type": "recovery",
        }.get(name, ""),
    )

    ok, message = saas._establish_recovery_session_from_query(client)

    assert ok is True
    assert "established" in message.lower()
    assert client.auth.verify_otp_calls == [
        {"type": "recovery", "token": "token-123", "email": "user@example.com"}
    ]


def test_establish_recovery_session_uses_code_first(monkeypatch):
    client = _FakeRecoveryClient()

    monkeypatch.setattr(saas, "_is_recovery_callback", lambda: True)
    monkeypatch.setattr(
        saas,
        "_query_param_value",
        lambda name: {
            "type": "recovery",
            "code": "code-123",
            "token_hash": "hash-ignored",
            "token": "token-ignored",
            "email": "ignored@example.com",
        }.get(name, ""),
    )

    ok, message = saas._establish_recovery_session_from_query(client)

    assert ok is True
    assert "established" in message.lower()
    assert client.auth.exchange_code_calls == ["code-123"]
    assert client.auth.verify_otp_calls == []


def test_establish_recovery_session_uses_access_refresh_pair(monkeypatch):
    client = _FakeRecoveryClient()

    monkeypatch.setattr(saas, "_is_recovery_callback", lambda: True)
    monkeypatch.setattr(
        saas,
        "_query_param_value",
        lambda name: {
            "type": "recovery",
            "access_token": "access-123",
            "refresh_token": "refresh-123",
        }.get(name, ""),
    )

    ok, message = saas._establish_recovery_session_from_query(client)

    assert ok is True
    assert "established" in message.lower()
    assert client.auth.set_session_calls == [
        {"access_token": "access-123", "refresh_token": "refresh-123"}
    ]


def test_missing_type_recovery_is_rejected(monkeypatch):
    monkeypatch.setattr(saas, "_query_param_value", lambda name: {"token_hash": "hash-123"}.get(name, ""))

    assert saas._is_recovery_callback() is False


def test_plain_token_without_email_is_rejected(monkeypatch):
    client = _FakeRecoveryClient()

    monkeypatch.setattr(saas, "_is_recovery_callback", lambda: True)
    monkeypatch.setattr(
        saas,
        "_query_param_value",
        lambda name: {"type": "recovery", "token": "token-123"}.get(name, ""),
    )

    ok, message = saas._establish_recovery_session_from_query(client)

    assert ok is False
    assert "requires the email address" in message.lower()
    assert client.auth.verify_otp_calls == []
    assert client.auth.update_user_calls == 0


def test_token_with_more_than_one_identity_field_is_rejected(monkeypatch):
    client = _FakeRecoveryClient()

    monkeypatch.setattr(saas, "_is_recovery_callback", lambda: True)
    monkeypatch.setattr(
        saas,
        "_query_param_value",
        lambda name: {
            "type": "recovery",
            "token": "token-123",
            "email": "user@example.com",
            "phone": "+15555550123",
        }.get(name, ""),
    )

    ok, message = saas._establish_recovery_session_from_query(client)

    assert ok is False
    assert "exactly one identity field" in message.lower()
    assert client.auth.verify_otp_calls == []


def test_incomplete_access_refresh_pair_is_rejected(monkeypatch):
    client = _FakeRecoveryClient()

    monkeypatch.setattr(saas, "_is_recovery_callback", lambda: True)
    monkeypatch.setattr(
        saas,
        "_query_param_value",
        lambda name: {"type": "recovery", "access_token": "access-123"}.get(name, ""),
    )

    ok, message = saas._establish_recovery_session_from_query(client)

    assert ok is False
    assert "both access and refresh tokens" in message.lower()
    assert client.auth.set_session_calls == []


def test_url_fragment_data_is_not_supported_callback(monkeypatch):
    monkeypatch.setattr(saas, "_query_param_value", lambda _name: "")

    assert saas._is_recovery_callback() is False


def test_password_mismatch_does_not_call_update_user():
    client = _FakeRecoveryClient()

    ok, _message = saas._validate_password_recovery_inputs("password-123", "password-456")

    assert ok is False
    assert client.auth.update_user_calls == 0


def test_clear_recovery_query_params_removes_sensitive_keys(monkeypatch):
    fake_params = {
        "type": "recovery",
        "token_hash": "hash-123",
        "token": "token-123",
        "email": "user@example.com",
        "code": "code-123",
        "access_token": "access-123",
        "refresh_token": "refresh-123",
        "other": "keep-me",
    }
    monkeypatch.setattr(saas.st, "query_params", fake_params, raising=False)

    saas._clear_recovery_query_params()

    assert fake_params == {"other": "keep-me"}
