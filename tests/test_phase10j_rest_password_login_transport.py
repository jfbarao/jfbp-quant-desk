from __future__ import annotations

import json
from types import SimpleNamespace

import httpx

from pages import SaaS_Core as saas


class _FakeHttpResponse:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload
        self.headers = {"content-type": "application/json"}
        if isinstance(payload, (dict, list)):
            self.content = json.dumps(payload).encode("utf-8")
        elif isinstance(payload, bytes):
            self.content = payload
        else:
            self.content = b""

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _FakeClient:
    class _Auth:
        def __init__(self):
            self.sign_out_calls = 0

        def sign_out(self):
            self.sign_out_calls += 1

    def __init__(self):
        self.auth = self._Auth()


def _install_secret_values(monkeypatch):
    values = {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_ANON_KEY": "anon_test_key",
    }
    monkeypatch.setattr(saas, "_secret_value", lambda name, default="": values.get(name, default))


def _capture_traces(monkeypatch):
    traces = []

    def _trace(stage, source_function, *, exc=None, **metadata):
        traces.append(
            {
                "stage": stage,
                "source": source_function,
                "exc": "" if exc is None else f"{exc.__class__.__name__}:{exc}",
                "metadata": metadata,
            }
        )

    monkeypatch.setattr(saas, "production_auth_trace", _trace)
    return traces


def _make_success_payload(user_id: str = "u-1", email: str = "u1@example.com"):
    return {
        "access_token": "access-token-123",
        "refresh_token": "refresh-token-456",
        "expires_in": 3600,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": email,
            "user_metadata": {"full_name": "U1"},
            "app_metadata": {"role": "user"},
            "created_at": "2026-07-20T00:00:00+00:00",
        },
    }


def test_rest_password_login_success(monkeypatch):
    _install_secret_values(monkeypatch)
    traces = _capture_traces(monkeypatch)
    saas.st.session_state.clear()
    saas.st.session_state["saas_script_execution_id"] = "exec-1"

    def _post(*args, **kwargs):
        return _FakeHttpResponse(200, _make_success_payload())

    monkeypatch.setattr(saas.httpx, "post", _post)

    auth_response = saas._supabase_rest_password_login(
        email="u1@example.com",
        password="pw",
        thread_ident=11,
        script_run_context_id="ctx-1",
        script_execution_id="exec-1",
    )

    assert getattr(auth_response, "user", None) is not None
    assert getattr(auth_response.user, "id", "") == "u-1"
    assert getattr(auth_response.user, "email", "") == "u1@example.com"
    assert getattr(auth_response, "session", None) is not None
    assert getattr(auth_response.session, "access_token", "") == "access-token-123"
    assert getattr(auth_response.session, "refresh_token", "") == "refresh-token-456"
    assert any(t["stage"] == "SUPABASE_REST_LOGIN_HTTPX_ARGS_EVALUATION_START" for t in traces)
    assert any(t["stage"] == "SUPABASE_REST_LOGIN_HTTPX_POST_ENTER" for t in traces)
    assert any(t["stage"] == "SUPABASE_REST_LOGIN_HTTPX_POST_RETURNED" for t in traces)
    assert any(t["stage"] == "SUPABASE_REST_LOGIN_RESPONSE_BODY_READ_AFTER" for t in traces)
    assert any(t["stage"] == "SUPABASE_REST_LOGIN_JSON_PARSE_AFTER" for t in traces)
    assert any(t["stage"] == "SUPABASE_REST_LOGIN_CALL_RETURNED" for t in traces)
    assert any(t["stage"] == "SUPABASE_REST_LOGIN_FINALLY" for t in traces)
    trace = next(t for t in traces if t["stage"] == "SUPABASE_REST_LOGIN_HTTPX_ARGS_EVALUATION_START")
    assert trace["metadata"]["request_method"] == "POST"
    assert trace["metadata"]["request_url_host"] == "example.supabase.co"
    assert trace["metadata"]["request_project_ref"] == "example"
    assert trace["metadata"]["request_header_count"] == 3
    assert trace["metadata"]["timeout_read_s"] == 10.0
    assert trace["metadata"]["email_present"] is True
    assert trace["metadata"]["password_present"] is True
    assert trace["metadata"]["script_execution_id"] == "exec-1"


def test_rest_password_login_invalid_credentials(monkeypatch):
    _install_secret_values(monkeypatch)
    traces = _capture_traces(monkeypatch)
    saas.st.session_state.clear()
    saas.st.session_state["saas_script_execution_id"] = "exec-2"

    def _post(*args, **kwargs):
        return _FakeHttpResponse(400, {"message": "Invalid login credentials", "error_code": "invalid_credentials"})

    monkeypatch.setattr(saas.httpx, "post", _post)

    try:
        saas._supabase_rest_password_login(
            email="u1@example.com",
            password="bad",
            thread_ident=22,
            script_run_context_id="ctx-2",
            script_execution_id="exec-2",
        )
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "Invalid login credentials" in str(exc)

    assert any(t["stage"] == "SUPABASE_REST_LOGIN_HTTP_ERROR" for t in traces)
    assert any(t["stage"] == "SUPABASE_REST_LOGIN_HTTP_ERROR_BEFORE_RAISE" for t in traces)
    assert any(t["stage"] == "SUPABASE_REST_LOGIN_FINALLY" for t in traces)


def test_rest_password_login_timeout(monkeypatch):
    _install_secret_values(monkeypatch)
    traces = _capture_traces(monkeypatch)
    saas.st.session_state.clear()
    saas.st.session_state["saas_script_execution_id"] = "exec-3"

    def _post(*args, **kwargs):
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr(saas.httpx, "post", _post)

    try:
        saas._supabase_rest_password_login(
            email="u1@example.com",
            password="pw",
            thread_ident=33,
            script_run_context_id="ctx-3",
            script_execution_id="exec-3",
        )
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "timed out" in str(exc).lower()

    assert any(t["stage"] == "SUPABASE_REST_LOGIN_EXCEPTION" for t in traces)
    assert any(t["stage"] == "SUPABASE_REST_LOGIN_FINALLY" for t in traces)


def test_rest_password_login_malformed_successful_response(monkeypatch):
    _install_secret_values(monkeypatch)
    traces = _capture_traces(monkeypatch)
    saas.st.session_state.clear()
    saas.st.session_state["saas_script_execution_id"] = "exec-4"

    def _post(*args, **kwargs):
        return _FakeHttpResponse(
            200,
            {
                "access_token": "",
                "refresh_token": "",
                "user": {"id": ""},
            },
        )

    monkeypatch.setattr(saas.httpx, "post", _post)

    try:
        saas._supabase_rest_password_login(
            email="u1@example.com",
            password="pw",
            thread_ident=44,
            script_run_context_id="ctx-4",
            script_execution_id="exec-4",
        )
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "Malformed Supabase Auth response" in str(exc)

    assert any(t["stage"] == "SUPABASE_REST_LOGIN_EXCEPTION" for t in traces)
    assert any(t["stage"] == "SUPABASE_REST_LOGIN_FINALLY" for t in traces)
    assert any(t["stage"] == "SUPABASE_REST_LOGIN_EXCEPTION" for t in traces)


def test_rest_password_login_no_sensitive_leakage_in_diagnostics(monkeypatch):
    _install_secret_values(monkeypatch)
    traces = _capture_traces(monkeypatch)
    saas.st.session_state.clear()
    saas.st.session_state["saas_script_execution_id"] = "exec-5"

    secret_password = "PW_LEAK_CHECK_789"
    secret_access = "ACCESS_LEAK_CHECK_ABC"
    secret_refresh = "REFRESH_LEAK_CHECK_DEF"

    def _post(*args, **kwargs):
        payload = _make_success_payload()
        payload["access_token"] = secret_access
        payload["refresh_token"] = secret_refresh
        return _FakeHttpResponse(200, payload)

    monkeypatch.setattr(saas.httpx, "post", _post)

    saas._supabase_rest_password_login(
        email="u1@example.com",
        password=secret_password,
        thread_ident=55,
        script_run_context_id="ctx-5",
        script_execution_id="exec-5",
    )

    rendered = json.dumps(traces)
    assert secret_password not in rendered
    assert secret_access not in rendered
    assert secret_refresh not in rendered
    assert "Bearer " not in rendered


def test_supabase_login_downstream_contract_unchanged(monkeypatch):
    saas.st.session_state.clear()
    saas.st.session_state["saas_script_execution_id"] = "exec-login-contract"
    _install_secret_values(monkeypatch)
    _capture_traces(monkeypatch)

    fake_client = _FakeClient()
    monkeypatch.setattr(saas, "supabase_ready", lambda: (True, "ready"))
    monkeypatch.setattr(saas, "get_supabase_client", lambda: fake_client)

    def _clear(*, revoke_current=True, reason=""):
        saas.st.session_state["saas_logged_in"] = False
        saas.st.session_state["saas_user"] = None
        saas.st.session_state["saas_auth_session"] = None
        return True, "ok"

    monkeypatch.setattr(saas, "clear_authenticated_session", _clear)

    expected = _make_success_payload(user_id="captain51-id", email="captain51@example.com")

    def _mock_rest_login(
        *,
        email: str,
        password: str,
        thread_ident: int,
        script_run_context_id: str,
        script_execution_id: str,
    ):
        assert email == "captain51@example.com"
        assert password == "correct"
        assert script_execution_id
        user = SimpleNamespace(**expected["user"])
        session = SimpleNamespace(
            access_token=expected["access_token"],
            refresh_token=expected["refresh_token"],
            expires_in=expected["expires_in"],
            expires_at=1,
            token_type=expected["token_type"],
            user=user,
        )
        return SimpleNamespace(user=user, session=session)

    monkeypatch.setattr(saas, "_supabase_rest_password_login", _mock_rest_login)

    seen = {"validated": False}

    def _set_session(auth_response):
        user, session, access = saas.authenticate_user(auth_response)
        assert getattr(user, "id", "") == "captain51-id"
        assert getattr(user, "email", "") == "captain51@example.com"
        assert getattr(session, "refresh_token", "") == "refresh-token-456"
        assert access == "access-token-123"
        seen["validated"] = True
        saas.st.session_state["saas_auth_last_message"] = "ok"
        saas.st.session_state["saas_onboarding_ready"] = True
        return True

    monkeypatch.setattr(saas, "set_authenticated_session", _set_session)

    ok, msg = saas.supabase_login("captain51@example.com", "correct")
    assert ok is True
    assert "Login successful." in msg
    assert seen["validated"] is True
