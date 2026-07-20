from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from pages import SaaS_Core as saas


def _jwt_with_claims(claims: dict) -> str:
    header = {"alg": "none", "typ": "JWT"}
    h = base64.urlsafe_b64encode(json.dumps(header).encode("utf-8")).decode("utf-8").rstrip("=")
    p = base64.urlsafe_b64encode(json.dumps(claims).encode("utf-8")).decode("utf-8").rstrip("=")
    return f"{h}.{p}.sig"


class _FakeAuth:
    def __init__(self, user_id: str, email: str):
        self._user = SimpleNamespace(id=user_id, email=email, user_metadata={})
        self.sign_out_called = False

    def get_user(self, *_args, **_kwargs):
        return SimpleNamespace(user=self._user, session=None)

    def sign_out(self):
        self.sign_out_called = True


class _FakeClient:
    def __init__(self, user_id: str, email: str):
        self.auth = _FakeAuth(user_id, email)


class _FakeStore:
    def __init__(self, session_owner: str = ""):
        self.session_owner = session_owner

    def _select_single_by_id(self, _sid):
        if not self.session_owner:
            return None
        return {"user_id": self.session_owner}


def _install_default_identity_env(monkeypatch, *, auth_user_id: str, auth_email: str, durable_owner: str = ""):
    client = _FakeClient(auth_user_id, auth_email)
    store = _FakeStore(durable_owner)

    monkeypatch.setattr(saas, "get_supabase_client", lambda: client)
    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "_verified_user_row", lambda *_a, **_k: [{"user_id": auth_user_id}])
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {"user_id": auth_user_id})

    failures = []

    def _fake_clear_authenticated_session(*, revoke_current=True, reason=""):
        failures.append({"revoke_current": revoke_current, "reason": reason})
        saas.st.session_state["saas_logged_in"] = False
        saas.st.session_state["saas_user"] = None
        saas.st.session_state["saas_auth_session"] = None
        saas.st.session_state["saas_app_session_id"] = ""
        saas.st.session_state["saas_identity_bound_user_id"] = ""
        saas.st.session_state["saas_admin_override"] = False
        return True, "ok"

    monkeypatch.setattr(saas, "clear_authenticated_session", _fake_clear_authenticated_session)
    return client, failures


def test_login_user_b_cannot_bind_to_user_a_durable_session(monkeypatch):
    saas.st.session_state.clear()
    _install_default_identity_env(
        monkeypatch,
        auth_user_id="user-b",
        auth_email="user-b@example.com",
        durable_owner="user-a",
    )

    token = _jwt_with_claims({"sub": "user-b", "email": "user-b@example.com"})
    ok = saas._enforce_identity_binding_contract(
        "post_login",
        login_user=SimpleNamespace(id="user-b", email="user-b@example.com", user_metadata={}),
        login_session={"access_token": token},
        expected_durable_user_id="user-a",
    )
    assert ok is False
    assert saas.st.session_state.get("saas_auth_last_message") == "Your session could not be verified. Please sign in again."


def test_stale_admin_cookie_owner_is_rejected_for_ordinary_login(monkeypatch):
    saas.st.session_state.clear()
    _install_default_identity_env(
        monkeypatch,
        auth_user_id="captain51",
        auth_email="captain51@example.com",
        durable_owner="founder-admin",
    )

    token = _jwt_with_claims({"sub": "captain51", "email": "captain51@example.com"})
    ok = saas._enforce_identity_binding_contract(
        "post_login",
        login_user=SimpleNamespace(id="captain51", email="captain51@example.com", user_metadata={}),
        login_session={"access_token": token},
        expected_durable_user_id="founder-admin",
    )
    assert ok is False


def test_successful_login_binding_takes_precedence_and_clears_admin_override(monkeypatch):
    saas.st.session_state.clear()
    saas.st.session_state["saas_identity_bound_user_id"] = "founder-admin"
    saas.st.session_state["saas_admin_override"] = True

    _install_default_identity_env(
        monkeypatch,
        auth_user_id="captain51",
        auth_email="captain51@example.com",
        durable_owner="captain51",
    )

    token = _jwt_with_claims({"sub": "captain51", "email": "captain51@example.com"})
    saas.st.session_state["saas_user"] = saas.SaaSUser(
        user_id="captain51",
        email="captain51@example.com",
        full_name="captain51",
        plan=saas.PLAN_ELITE,
        account_status=saas.ACCOUNT_ACTIVE,
        trial_start=datetime.now(timezone.utc),
        trial_end=datetime.now(timezone.utc) + timedelta(days=30),
        created_at=datetime.now(timezone.utc),
        role="user",
    )

    ok = saas._enforce_identity_binding_contract(
        "post_login",
        login_user=SimpleNamespace(id="captain51", email="captain51@example.com", user_metadata={}),
        login_session={"access_token": token},
        expected_durable_user_id="captain51",
    )
    assert ok is True
    assert saas.st.session_state.get("saas_admin_override") is False
    assert saas.st.session_state.get("saas_identity_bound_user_id") == "captain51"


def test_session_id_rotates_when_identity_switches(monkeypatch):
    saas.st.session_state.clear()

    class _RotateStore:
        def __init__(self):
            self.counter = 0

        def active_sessions_for_user(self, _uid):
            return []

        def create_session(self, data):
            self.counter += 1
            sid = f"sid-{self.counter}"
            return SimpleNamespace(
                raw_handle=f"h-{self.counter}",
                record=SimpleNamespace(id=sid, user_id=data.user_id),
            )

    store = _RotateStore()
    client = _FakeClient("user-a", "user-a@example.com")
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client)
    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "_set_session_cookie", lambda *_a, **_k: True)
    monkeypatch.setattr(saas, "_cache_authenticated_session", lambda *_a, **_k: None)
    monkeypatch.setattr(saas, "_browser_auth_cache_key", lambda: "fp")
    monkeypatch.setattr(saas, "_user_agent", lambda _h: "ua")
    monkeypatch.setattr(saas, "_request_headers", lambda: {})
    monkeypatch.setattr(saas, "_revoke_current_app_session", lambda reason="": (True, reason))
    monkeypatch.setattr(saas, "_verified_user_row", lambda *_a, **_k: [])
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {})

    user_a = SimpleNamespace(id="user-a", email="user-a@example.com", user_metadata={}, created_at=datetime.now(timezone.utc).isoformat())
    user_b = SimpleNamespace(id="user-b", email="user-b@example.com", user_metadata={}, created_at=datetime.now(timezone.utc).isoformat())
    session_a = SimpleNamespace(access_token="a", refresh_token="ra", expires_at=0)
    session_b = SimpleNamespace(access_token="b", refresh_token="rb", expires_at=0)

    saas.st.session_state["saas_user"] = saas.SaaSUser(
        user_id="user-a",
        email="user-a@example.com",
        full_name="A",
        plan=saas.PLAN_MARKET_PULSE,
        account_status=saas.ACCOUNT_TRIAL,
        trial_start=datetime.now(timezone.utc),
        trial_end=datetime.now(timezone.utc) + timedelta(days=1),
        created_at=datetime.now(timezone.utc),
    )

    saas.initialize_session(user_a, session_a)
    first_sid = saas.st.session_state.get("saas_app_session_id")
    saas.initialize_session(user_b, session_b)
    second_sid = saas.st.session_state.get("saas_app_session_id")

    assert first_sid != second_sid


def test_durable_owner_must_equal_authenticated_user(monkeypatch):
    saas.st.session_state.clear()
    _install_default_identity_env(
        monkeypatch,
        auth_user_id="user-b",
        auth_email="user-b@example.com",
        durable_owner="user-a",
    )
    token = _jwt_with_claims({"sub": "user-b", "email": "user-b@example.com"})
    assert not saas._enforce_identity_binding_contract(
        "rehydrate_durable",
        login_user=SimpleNamespace(id="user-b", email="user-b@example.com", user_metadata={}),
        login_session={"access_token": token},
        expected_durable_user_id="user-a",
    )


def test_profile_lookup_does_not_fallback_to_email():
    class _NoFallbackTable:
        def __init__(self):
            self.calls = []

        def select(self, *_a):
            return self

        def eq(self, key, value):
            self.calls.append((key, value))
            return self

        def limit(self, _n):
            return self

        def execute(self):
            # Would return data only for email path, not user_id path.
            if any(key == "email" for key, _ in self.calls):
                return SimpleNamespace(data=[{"user_id": "email-row"}])
            return SimpleNamespace(data=[])

    class _NoFallbackClient:
        def __init__(self):
            self.table_obj = _NoFallbackTable()

        def table(self, _name):
            return self.table_obj

    client = _NoFallbackClient()
    row = saas._profile_row_for_auth_user(client, "", "captain51@example.com")
    assert row == {}
    assert all(key != "email" for key, _ in client.table_obj.calls)


def test_profile_owner_mismatch_fails_closed(monkeypatch):
    saas.st.session_state.clear()
    _install_default_identity_env(monkeypatch, auth_user_id="u1", auth_email="u1@example.com", durable_owner="u1")
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {"user_id": "u2"})
    token = _jwt_with_claims({"sub": "u1", "email": "u1@example.com"})
    assert not saas._enforce_identity_binding_contract("post_login", login_user=SimpleNamespace(id="u1", email="u1@example.com"), login_session={"access_token": token})


def test_admin_state_cleared_on_identity_switch(monkeypatch):
    saas.st.session_state.clear()
    saas.st.session_state["saas_admin_override"] = True
    saas.st.session_state["saas_identity_bound_user_id"] = "admin-u"

    _install_default_identity_env(monkeypatch, auth_user_id="user-u", auth_email="user@example.com", durable_owner="user-u")
    saas.st.session_state["saas_user"] = saas.SaaSUser(
        user_id="user-u",
        email="user@example.com",
        full_name="U",
        plan=saas.PLAN_MARKET_PULSE,
        account_status=saas.ACCOUNT_TRIAL,
        trial_start=datetime.now(timezone.utc),
        trial_end=datetime.now(timezone.utc) + timedelta(days=3),
        created_at=datetime.now(timezone.utc),
        role="user",
    )

    token = _jwt_with_claims({"sub": "user-u", "email": "user@example.com"})
    assert saas._enforce_identity_binding_contract("post_login", login_user=SimpleNamespace(id="user-u", email="user@example.com"), login_session={"access_token": token})
    assert saas.st.session_state.get("saas_admin_override") is False


def test_logout_clears_auth_state_and_signs_out(monkeypatch):
    saas.st.session_state.clear()
    client = _FakeClient("logout-u", "logout@example.com")
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client)
    monkeypatch.setattr(saas, "_revoke_current_app_session", lambda reason="": (True, reason))

    saas.st.session_state["saas_logged_in"] = True
    saas.st.session_state["saas_user"] = saas.SaaSUser(
        user_id="logout-u",
        email="logout@example.com",
        full_name="Logout",
        plan=saas.PLAN_MARKET_PULSE,
        account_status=saas.ACCOUNT_TRIAL,
        trial_start=datetime.now(timezone.utc),
        trial_end=datetime.now(timezone.utc) + timedelta(days=1),
        created_at=datetime.now(timezone.utc),
    )
    saas.st.session_state["saas_auth_session"] = {"access_token": "a", "refresh_token": "r"}
    saas.st.session_state["saas_app_session_id"] = "sid-1"
    saas.st.session_state["saas_identity_bound_user_id"] = "logout-u"
    saas.st.session_state["saas_admin_override"] = True

    ok, _msg = saas.supabase_logout()
    assert ok is True
    assert client.auth.sign_out_called is True
    assert saas.st.session_state.get("saas_logged_in") is False
    assert saas.st.session_state.get("saas_user") is None
    assert saas.st.session_state.get("saas_auth_session") is None
    assert saas.st.session_state.get("saas_app_session_id") == ""
    assert saas.st.session_state.get("saas_identity_bound_user_id") == ""
    assert saas.st.session_state.get("saas_admin_override") is False


def test_confirmation_flow_cannot_inherit_stale_admin_identity(monkeypatch):
    saas.st.session_state.clear()

    # Login response says ordinary user, but get_user() incorrectly returns admin.
    client = _FakeClient("admin-u", "admin@example.com")
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client)
    monkeypatch.setattr(saas, "_session_store", lambda: _FakeStore("admin-u"))
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {"user_id": "admin-u"})
    monkeypatch.setattr(saas, "_verified_user_row", lambda *_a, **_k: [{"user_id": "admin-u"}])

    failures = []

    def _fake_clear_authenticated_session(*, revoke_current=True, reason=""):
        failures.append(reason)
        saas.st.session_state["saas_logged_in"] = False
        saas.st.session_state["saas_user"] = None
        saas.st.session_state["saas_auth_session"] = None
        saas.st.session_state["saas_app_session_id"] = ""
        saas.st.session_state["saas_identity_bound_user_id"] = ""
        return True, "ok"

    monkeypatch.setattr(saas, "clear_authenticated_session", _fake_clear_authenticated_session)

    token = _jwt_with_claims({"sub": "ordinary-u", "email": "ordinary@example.com"})
    ok = saas._enforce_identity_binding_contract(
        "callback_login",
        login_user=SimpleNamespace(id="ordinary-u", email="ordinary@example.com", user_metadata={}),
        login_session={"access_token": token},
        expected_durable_user_id="ordinary-u",
    )
    assert ok is False
    assert failures and failures[-1] == "IDENTITY_MISMATCH"


def test_cookie_name_is_environment_scoped(monkeypatch):
    monkeypatch.setattr(saas, "build_runtime_config_from_secrets", lambda: {"APP_ENV": "production"})
    prod_name = saas._session_cookie_name()
    monkeypatch.setattr(saas, "build_runtime_config_from_secrets", lambda: {"APP_ENV": "development"})
    dev_name = saas._session_cookie_name()
    assert prod_name != dev_name
    assert prod_name.endswith("_prod")
    assert dev_name.endswith("_dev")


def test_regression_captain51_identity_remains_captain51(monkeypatch):
    saas.st.session_state.clear()
    _install_default_identity_env(
        monkeypatch,
        auth_user_id="captain51",
        auth_email="captain51@example.com",
        durable_owner="captain51",
    )

    saas.st.session_state["saas_user"] = saas.SaaSUser(
        user_id="captain51",
        email="captain51@example.com",
        full_name="Captain 51",
        plan=saas.PLAN_ELITE,
        account_status=saas.ACCOUNT_ACTIVE,
        trial_start=datetime.now(timezone.utc),
        trial_end=datetime.now(timezone.utc) + timedelta(days=30),
        created_at=datetime.now(timezone.utc),
        role="user",
    )

    token = _jwt_with_claims({"sub": "captain51", "email": "captain51@example.com"})
    ok = saas._enforce_identity_binding_contract(
        "post_login",
        login_user=SimpleNamespace(id="captain51", email="captain51@example.com", user_metadata={}),
        login_session={"access_token": token},
        expected_durable_user_id="captain51",
    )
    assert ok is True
    assert saas.st.session_state["saas_user"].user_id == "captain51"
    assert saas.st.session_state["saas_user"].role != "admin"
