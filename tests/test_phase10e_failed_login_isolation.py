from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from pages import SaaS_Core as saas


class _FakeAuth:
    def __init__(self, *, user_id: str = "", email: str = "", fail: bool = True):
        self._user_id = user_id
        self._email = email
        self._fail = fail
        self.sign_out_calls = 0

    def sign_in_with_password(self, _payload):
        if self._fail:
            raise RuntimeError("Invalid login credentials")
        user = SimpleNamespace(id=self._user_id, email=self._email, user_metadata={})
        session = SimpleNamespace(access_token="access-token", refresh_token="refresh-token", expires_at=0)
        return SimpleNamespace(user=user, session=session)

    def sign_out(self):
        self.sign_out_calls += 1


class _FakeClient:
    def __init__(self, *, user_id: str = "", email: str = "", fail: bool = True):
        self.auth = _FakeAuth(user_id=user_id, email=email, fail=fail)


def _seed_admin_identity() -> saas.SaaSUser:
    return saas.SaaSUser(
        user_id="founder-admin",
        email="founder@example.com",
        full_name="Founder",
        plan=saas.PLAN_ELITE,
        account_status=saas.ACCOUNT_ACTIVE,
        trial_start=datetime.now(timezone.utc),
        trial_end=datetime.now(timezone.utc) + timedelta(days=365),
        created_at=datetime.now(timezone.utc),
        role="admin",
    )


def _install_clear_stub(monkeypatch):
    calls = []

    def _clear(*, revoke_current=True, reason=""):
        calls.append({"revoke_current": revoke_current, "reason": reason})
        saas.st.session_state["saas_logged_in"] = False
        saas.st.session_state["saas_user"] = None
        saas.st.session_state["saas_auth_session"] = None
        saas.st.session_state["saas_app_session_id"] = ""
        saas.st.session_state["saas_identity_bound_user_id"] = ""
        saas.st.session_state["saas_admin_override"] = False
        return True, "ok"

    monkeypatch.setattr(saas, "clear_authenticated_session", _clear)
    return calls


def _install_ready_and_client(monkeypatch, client):
    monkeypatch.setattr(saas, "supabase_ready", lambda: (True, "ready"))
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client)

    def _mock_rest_login(*, email: str, password: str, thread_ident: int, script_run_context_id: str):
        if client.auth._fail:
            raise RuntimeError("Invalid login credentials")
        user = SimpleNamespace(id=client.auth._user_id, email=client.auth._email, user_metadata={})
        session = SimpleNamespace(access_token="access-token", refresh_token="refresh-token", expires_at=0, user=user)
        return SimpleNamespace(user=user, session=session)

    monkeypatch.setattr(saas, "_supabase_rest_password_login", _mock_rest_login)


def test_existing_admin_session_failed_ordinary_login_results_logged_out(monkeypatch):
    saas.st.session_state.clear()
    saas.st.session_state["saas_logged_in"] = True
    saas.st.session_state["saas_user"] = _seed_admin_identity()
    saas.st.session_state["saas_admin_override"] = True

    calls = _install_clear_stub(monkeypatch)
    _install_ready_and_client(monkeypatch, _FakeClient(fail=True))

    ok, message = saas.supabase_login("captain51@example.com", "wrong")

    assert ok is False
    assert "Invalid login credentials" in message
    assert saas.st.session_state.get("saas_logged_in") is False
    assert saas.st.session_state.get("saas_user") is None
    assert calls[0]["reason"] == "LOGIN_ATTEMPT_RESET"


def test_existing_admin_cookie_failed_login_never_restores_admin(monkeypatch):
    saas.st.session_state.clear()
    saas.st.session_state["saas_logged_in"] = True
    saas.st.session_state["saas_user"] = _seed_admin_identity()

    _install_clear_stub(monkeypatch)
    _install_ready_and_client(monkeypatch, _FakeClient(fail=True))
    saas.supabase_login("captain51@example.com", "wrong")

    read_cookie_called = {"value": False}

    def _read_cookie_result():
        read_cookie_called["value"] = True
        return saas.CookieReadResult(saas.COOKIE_READINESS_PRESENT, "cookie")

    monkeypatch.setattr(saas, "_read_session_cookie_result", _read_cookie_result)
    assert saas._rehydrate_authenticated_session() is False
    assert read_cookie_called["value"] is False
    assert saas.st.session_state.get("saas_user") is None


def test_existing_durable_admin_session_failed_login_never_restores(monkeypatch):
    saas.st.session_state.clear()
    saas.st.session_state["saas_logged_in"] = True
    saas.st.session_state["saas_user"] = _seed_admin_identity()

    _install_clear_stub(monkeypatch)
    _install_ready_and_client(monkeypatch, _FakeClient(fail=True))
    saas.supabase_login("captain51@example.com", "wrong")

    store_called = {"value": False}

    def _store():
        store_called["value"] = True
        return None

    monkeypatch.setattr(saas, "_session_store", _store)
    assert saas._rehydrate_authenticated_session() is False
    assert store_called["value"] is False


def test_failed_login_clears_saas_user(monkeypatch):
    saas.st.session_state.clear()
    saas.st.session_state["saas_user"] = _seed_admin_identity()
    saas.st.session_state["saas_logged_in"] = True

    _install_clear_stub(monkeypatch)
    _install_ready_and_client(monkeypatch, _FakeClient(fail=True))

    saas.supabase_login("captain51@example.com", "wrong")
    assert saas.st.session_state.get("saas_user") is None


def test_failed_login_clears_admin_role_state(monkeypatch):
    saas.st.session_state.clear()
    saas.st.session_state["saas_user"] = _seed_admin_identity()
    saas.st.session_state["saas_logged_in"] = True
    saas.st.session_state["saas_admin_override"] = True

    _install_clear_stub(monkeypatch)
    _install_ready_and_client(monkeypatch, _FakeClient(fail=True))

    saas.supabase_login("captain51@example.com", "wrong")
    assert saas.st.session_state.get("saas_admin_override") is False


def test_failed_login_suppresses_rehydration_for_same_rerun(monkeypatch):
    saas.st.session_state.clear()
    saas.st.session_state["saas_user"] = _seed_admin_identity()
    saas.st.session_state["saas_logged_in"] = True

    _install_clear_stub(monkeypatch)
    _install_ready_and_client(monkeypatch, _FakeClient(fail=True))

    saas.supabase_login("captain51@example.com", "wrong")
    assert saas.st.session_state.get("saas_rehydrate_blocked") is True
    assert saas._rehydrate_authenticated_session() is False


def test_successful_login_renders_only_returned_supabase_identity(monkeypatch):
    saas.st.session_state.clear()
    saas.st.session_state["saas_logged_in"] = True
    saas.st.session_state["saas_user"] = _seed_admin_identity()

    _install_clear_stub(monkeypatch)
    _install_ready_and_client(
        monkeypatch,
        _FakeClient(user_id="captain51-user-id", email="captain51@example.com", fail=False),
    )

    def _set_session(auth_response):
        user = auth_response.user
        saas.st.session_state["saas_logged_in"] = True
        saas.st.session_state["saas_user"] = saas.SaaSUser(
            user_id=user.id,
            email=user.email,
            full_name="captain51",
            plan=saas.PLAN_ELITE,
            account_status=saas.ACCOUNT_ACTIVE,
            trial_start=datetime.now(timezone.utc),
            trial_end=datetime.now(timezone.utc) + timedelta(days=30),
            created_at=datetime.now(timezone.utc),
            role="user",
        )
        saas.st.session_state["saas_rehydrate_blocked"] = False
        saas.st.session_state["saas_auth_last_message"] = "ok"
        saas.st.session_state["saas_onboarding_ready"] = True
        return True

    monkeypatch.setattr(saas, "set_authenticated_session", _set_session)

    ok, _message = saas.supabase_login("captain51@example.com", "correct")
    assert ok is True
    user = saas.st.session_state.get("saas_user")
    assert isinstance(user, saas.SaaSUser)
    assert user.user_id == "captain51-user-id"
    assert user.email == "captain51@example.com"
    assert user.role != "admin"


def test_two_consecutive_failed_logins_cannot_restore_previous_identity(monkeypatch):
    saas.st.session_state.clear()
    saas.st.session_state["saas_logged_in"] = True
    saas.st.session_state["saas_user"] = _seed_admin_identity()

    _install_clear_stub(monkeypatch)
    _install_ready_and_client(monkeypatch, _FakeClient(fail=True))

    ok1, _ = saas.supabase_login("captain51@example.com", "wrong1")
    ok2, _ = saas.supabase_login("captain51@example.com", "wrong2")

    assert ok1 is False
    assert ok2 is False
    assert saas.st.session_state.get("saas_user") is None
    assert saas._rehydrate_authenticated_session() is False


def test_failed_founder_then_failed_captain51_remains_logged_out(monkeypatch):
    saas.st.session_state.clear()
    saas.st.session_state["saas_logged_in"] = True
    saas.st.session_state["saas_user"] = _seed_admin_identity()

    _install_clear_stub(monkeypatch)
    _install_ready_and_client(monkeypatch, _FakeClient(fail=True))

    founder_ok, _ = saas.supabase_login("founder@example.com", "wrong")
    captain_ok, _ = saas.supabase_login("captain51@example.com", "wrong")

    assert founder_ok is False
    assert captain_ok is False
    assert saas.st.session_state.get("saas_logged_in") is False
    assert saas.st.session_state.get("saas_user") is None


def test_production_regression_sequence_cannot_restore_founder_identity(monkeypatch):
    saas.st.session_state.clear()
    saas.st.session_state["saas_logged_in"] = True
    saas.st.session_state["saas_user"] = _seed_admin_identity()
    saas.st.session_state["saas_admin_override"] = True

    _install_clear_stub(monkeypatch)
    _install_ready_and_client(monkeypatch, _FakeClient(fail=True))

    # Sequence observed in production: fail captain51, fail founder, fail captain51.
    assert saas.supabase_login("captain51@example.com", "wrong")[0] is False
    assert saas.supabase_login("founder@example.com", "wrong")[0] is False
    assert saas.supabase_login("captain51@example.com", "wrong")[0] is False

    assert saas.st.session_state.get("saas_logged_in") is False
    assert saas.st.session_state.get("saas_user") is None
    assert saas.st.session_state.get("saas_admin_override") is False
    assert saas._rehydrate_authenticated_session() is False


def test_failed_login_then_valid_login_succeeds(monkeypatch):
    saas.st.session_state.clear()
    saas.st.session_state["saas_logged_in"] = True
    saas.st.session_state["saas_user"] = _seed_admin_identity()

    _install_clear_stub(monkeypatch)
    client = _FakeClient(user_id="captain51-user-id", email="captain51@example.com", fail=True)
    _install_ready_and_client(monkeypatch, client)

    def _set_session(auth_response):
        user = auth_response.user
        saas.st.session_state["saas_logged_in"] = True
        saas.st.session_state["saas_user"] = saas.SaaSUser(
            user_id=user.id,
            email=user.email,
            full_name="captain51",
            plan=saas.PLAN_ELITE,
            account_status=saas.ACCOUNT_ACTIVE,
            trial_start=datetime.now(timezone.utc),
            trial_end=datetime.now(timezone.utc) + timedelta(days=30),
            created_at=datetime.now(timezone.utc),
            role="user",
        )
        saas.st.session_state["saas_rehydrate_blocked"] = False
        saas.st.session_state["saas_auth_last_message"] = "ok"
        saas.st.session_state["saas_onboarding_ready"] = True
        return True

    monkeypatch.setattr(saas, "set_authenticated_session", _set_session)

    bad_ok, _ = saas.supabase_login("captain51@example.com", "bad")
    assert bad_ok is False
    assert saas.st.session_state.get("saas_rehydrate_blocked") is True

    client.auth._fail = False
    good_ok, _ = saas.supabase_login("captain51@example.com", "good")
    assert good_ok is True
    assert saas.st.session_state.get("saas_logged_in") is True
    assert saas.st.session_state.get("saas_rehydrate_blocked") is False


def test_failed_login_browser_refresh_keeps_login_usable(monkeypatch):
    saas.st.session_state.clear()
    saas.st.session_state["saas_user"] = _seed_admin_identity()
    saas.st.session_state["saas_logged_in"] = True

    _install_clear_stub(monkeypatch)
    client = _FakeClient(user_id="captain51-user-id", email="captain51@example.com", fail=True)
    _install_ready_and_client(monkeypatch, client)

    monkeypatch.setattr(saas, "_read_session_cookie_result", lambda: saas.CookieReadResult(saas.COOKIE_READINESS_PRESENT, "cookie"))

    bad_ok, _ = saas.supabase_login("captain51@example.com", "bad")
    assert bad_ok is False
    assert saas._rehydrate_authenticated_session() is False

    def _set_session(auth_response):
        user = auth_response.user
        saas.st.session_state["saas_logged_in"] = True
        saas.st.session_state["saas_user"] = saas.SaaSUser(
            user_id=user.id,
            email=user.email,
            full_name="captain51",
            plan=saas.PLAN_ELITE,
            account_status=saas.ACCOUNT_ACTIVE,
            trial_start=datetime.now(timezone.utc),
            trial_end=datetime.now(timezone.utc) + timedelta(days=30),
            created_at=datetime.now(timezone.utc),
            role="user",
        )
        saas.st.session_state["saas_rehydrate_blocked"] = False
        saas.st.session_state["saas_auth_last_message"] = "ok"
        saas.st.session_state["saas_onboarding_ready"] = True
        return True

    monkeypatch.setattr(saas, "set_authenticated_session", _set_session)
    client.auth._fail = False
    good_ok, _ = saas.supabase_login("captain51@example.com", "good")
    assert good_ok is True


def test_logout_followed_by_login_works(monkeypatch):
    saas.st.session_state.clear()
    saas.st.session_state["saas_logged_in"] = True
    saas.st.session_state["saas_user"] = _seed_admin_identity()

    _install_clear_stub(monkeypatch)
    client = _FakeClient(user_id="captain51-user-id", email="captain51@example.com", fail=False)
    _install_ready_and_client(monkeypatch, client)

    def _set_session(auth_response):
        user = auth_response.user
        saas.st.session_state["saas_logged_in"] = True
        saas.st.session_state["saas_user"] = saas.SaaSUser(
            user_id=user.id,
            email=user.email,
            full_name="captain51",
            plan=saas.PLAN_ELITE,
            account_status=saas.ACCOUNT_ACTIVE,
            trial_start=datetime.now(timezone.utc),
            trial_end=datetime.now(timezone.utc) + timedelta(days=30),
            created_at=datetime.now(timezone.utc),
            role="user",
        )
        saas.st.session_state["saas_rehydrate_blocked"] = False
        saas.st.session_state["saas_auth_last_message"] = "ok"
        saas.st.session_state["saas_onboarding_ready"] = True
        return True

    monkeypatch.setattr(saas, "set_authenticated_session", _set_session)

    out_ok, _ = saas.supabase_logout()
    assert out_ok is True
    in_ok, _ = saas.supabase_login("captain51@example.com", "good")
    assert in_ok is True
    assert saas.st.session_state.get("saas_logged_in") is True


def test_rehydrate_block_scoped_to_current_session_state(monkeypatch):
    # Session A: failed login blocks rehydrate.
    saas.st.session_state.clear()
    saas.st.session_state["saas_user"] = _seed_admin_identity()
    saas.st.session_state["saas_logged_in"] = True
    _install_clear_stub(monkeypatch)
    _install_ready_and_client(monkeypatch, _FakeClient(fail=True))
    saas.supabase_login("captain51@example.com", "bad")
    assert saas.st.session_state.get("saas_rehydrate_blocked") is True

    # Session B simulation: fresh session_state starts unblocked.
    saas.st.session_state.clear()
    saas.init_saas_state()
    assert saas.st.session_state.get("saas_rehydrate_blocked") is False
