from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from pages import SaaS_Core as saas


_TOKEN_USER_MAP = {}
_REVOKED_TOKENS = set()
_TOKEN_COUNTER = 0


def _next_refresh_token(user_id: str) -> str:
    global _TOKEN_COUNTER
    _TOKEN_COUNTER += 1
    token = f"refresh-{user_id}-{_TOKEN_COUNTER}"
    _TOKEN_USER_MAP[token] = user_id
    return token


class _FakeCookieManager:
    def __init__(self):
        self.store = {}
        self.last_set = None

    def get(self, key):
        return self.store.get(key)

    def set(
        self,
        cookie: str,
        val,
        key: str = "set",
        path: str = "/",
        expires_at=None,
        max_age=None,
        domain=None,
        secure=None,
        same_site="strict",
    ):
        self.store[cookie] = val
        self.last_set = {
            "cookie": cookie,
            "key": key,
            "path": path,
            "expires_at": expires_at,
            "max_age": max_age,
            "domain": domain,
            "secure": secure,
            "same_site": same_site,
        }

    def delete(self, key):
        self.store.pop(key, None)


class _SequencedCookieManager(_FakeCookieManager):
    def __init__(self, sequence=None):
        super().__init__()
        self.sequence = list(sequence or [])
        self.get_calls = 0

    def get(self, key):
        self.get_calls += 1
        if self.sequence:
            return self.sequence.pop(0)
        return super().get(key)


class _FakeAuthResponse:
    def __init__(self, user=None, session=None):
        self.user = user
        self.session = session


class _FakeAuthClient:
    def __init__(self, user_id: str, refresh_token: str = "refresh-good"):
        if refresh_token == "refresh-good":
            refresh_token = _next_refresh_token(user_id)
        _TOKEN_USER_MAP[refresh_token] = user_id
        self._user = SimpleNamespace(id=user_id, email=f"{user_id}@example.com", user_metadata={})
        self._session = SimpleNamespace(
            access_token="access-good",
            refresh_token=refresh_token,
            expires_at=int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        )
        self._revoked = False

    def sign_in_with_password(self, _payload):
        return _FakeAuthResponse(user=self._user, session=self._session)

    def refresh_session(self, refresh_token=None):
        token = refresh_token or self._session.refresh_token
        if self._revoked or token in {"bad", "revoked", ""} or token in _REVOKED_TOKENS:
            raise RuntimeError("refresh failed")

        restored_user_id = _TOKEN_USER_MAP.get(token)
        if not restored_user_id:
            raise RuntimeError("refresh failed")

        self._user = SimpleNamespace(
            id=restored_user_id,
            email=f"{restored_user_id}@example.com",
            user_metadata={},
        )

        new_refresh = _next_refresh_token(restored_user_id)
        self._session = SimpleNamespace(
            access_token="access-refreshed",
            refresh_token=new_refresh,
            expires_at=int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        )
        return _FakeAuthResponse(user=self._user, session=self._session)

    def get_user(self, *_args, **_kwargs):
        return _FakeAuthResponse(user=self._user, session=self._session)

    def get_session(self):
        return self._session

    def set_session(self, *_args, **_kwargs):
        return _FakeAuthResponse(user=self._user, session=self._session)

    def sign_out(self, *_args, **_kwargs):
        _REVOKED_TOKENS.add(self._session.refresh_token)
        self._revoked = True


class _FakeSupabaseClient:
    def __init__(self, user_id="u1", refresh_token: str = "refresh-good"):
        self.auth = _FakeAuthClient(user_id=user_id, refresh_token=refresh_token)


class _FakeSessionStore:
    def __init__(self):
        self.rows = {}
        self.refresh = {}
        self.user_sessions = {}
        self.counter = 0
        self.revoke_calls = []

    def create_session(self, data):
        self.counter += 1
        sid = f"s{self.counter}"
        handle = f"h{self.counter}"
        now = datetime.now(timezone.utc)
        absolute_hours = 24 * (30 if data.remember_me else 1)
        row = SimpleNamespace(
            id=sid,
            user_id=data.user_id,
            session_handle_hash="hash",
            created_at=now,
            last_seen_at=now,
            idle_expires_at=now + timedelta(hours=24),
            absolute_expires_at=now + timedelta(hours=absolute_hours),
            revoked_at=None,
            revocation_reason="",
            remember_me=bool(data.remember_me),
            user_agent=data.user_agent,
            client_metadata=data.client_metadata or {},
            rotation_parent_id=None,
            replaced_by_session_id=None,
        )
        self.rows[handle] = row
        self.refresh[handle] = data.refresh_material
        self.user_sessions.setdefault(data.user_id, []).append((handle, row))
        return SimpleNamespace(raw_handle=handle, record=row)

    def get_session_by_handle(self, handle, now=None):
        row = self.rows.get(handle)
        if not row:
            return SimpleNamespace(status=saas.SessionLookupStatus.MISSING, record=None)
        now = now or datetime.now(timezone.utc)
        if row.revoked_at is not None:
            return SimpleNamespace(status=saas.SessionLookupStatus.REVOKED, record=row)
        if row.absolute_expires_at <= now:
            return SimpleNamespace(status=saas.SessionLookupStatus.ABSOLUTE_EXPIRED, record=row)
        if row.idle_expires_at <= now:
            return SimpleNamespace(status=saas.SessionLookupStatus.IDLE_EXPIRED, record=row)
        return SimpleNamespace(status=saas.SessionLookupStatus.VALID, record=row)

    def get_refresh_material_for_handle(self, handle, now=None):
        lookup = self.get_session_by_handle(handle, now=now)
        if lookup.status != saas.SessionLookupStatus.VALID:
            return None
        return self.refresh.get(handle)

    def revoke_session(self, session_id, reason="USER_LOGOUT", now=None):
        for _handle, row in self.rows.items():
            if row.id == session_id and row.revoked_at is None:
                row.revoked_at = now or datetime.now(timezone.utc)
                row.revocation_reason = reason
                self.revoke_calls.append({"session_id": session_id, "reason": reason})
                return 1
        return 0

    def revoke_all_sessions_for_user(self, user_id, reason="USER_LOGOUT_ALL", now=None):
        count = 0
        for handle, row in self.user_sessions.get(user_id, []):
            if row.revoked_at is None:
                row.revoked_at = now or datetime.now(timezone.utc)
                row.revocation_reason = reason
                count += 1
        return count

    def active_sessions_for_user(self, user_id, now=None):
        current = now or datetime.now(timezone.utc)
        active = []
        for _handle, row in self.user_sessions.get(user_id, []):
            if row.revoked_at is not None:
                continue
            if row.idle_expires_at <= current:
                continue
            if row.absolute_expires_at <= current:
                continue
            active.append(row)
        return active


@pytest.fixture(autouse=True)
def reset_state(monkeypatch):
    _TOKEN_USER_MAP.clear()
    _REVOKED_TOKENS.clear()
    saas.st.session_state.clear()
    manager = _FakeCookieManager()
    monkeypatch.setattr(saas, "_cookie_manager", lambda: manager)
    monkeypatch.setattr(saas, "_session_signing_key", lambda: b"unit-test-signing-key")
    monkeypatch.setattr(saas, "_is_production_runtime", lambda: False)
    monkeypatch.setattr(saas, "_request_headers", lambda: {"user-agent": "pytest"})
    monkeypatch.setattr(saas, "_browser_auth_cache_key", lambda: "browser-key")
    monkeypatch.setattr(saas, "_cache_authenticated_session", lambda _s: None)
    monkeypatch.setattr(saas.st, "rerun", lambda: None)
    monkeypatch.setattr(
        saas,
        "build_saas_user_from_auth",
        lambda auth_user, selected_plan=None: saas.SaaSUser(
            user_id=str(getattr(auth_user, "id", "u")),
            email=str(getattr(auth_user, "email", "u@example.com")),
            full_name="Test User",
            plan=selected_plan or saas.PLAN_MARKET_PULSE,
            account_status=saas.ACCOUNT_TRIAL,
            trial_start=datetime.now(timezone.utc),
            trial_end=datetime.now(timezone.utc) + timedelta(days=30),
            created_at=datetime.now(timezone.utc),
            source="supabase",
            role="user",
            subscription_status=saas.ACCOUNT_TRIAL,
            provisioning_required=False,
        ),
    )


def test_cookie_signed_and_tamper_detected():
    signed = saas._sign_session_handle("opaque-handle")
    assert saas._unsign_session_handle(signed) == "opaque-handle"

    tampered = signed[:-1] + ("A" if signed[-1] != "A" else "B")
    with pytest.raises(Exception):
        saas._unsign_session_handle(tampered)


def test_cookie_manager_set_uses_supported_argument_contract(monkeypatch):
    manager = _FakeCookieManager()
    monkeypatch.setattr(saas, "_cookie_manager", lambda: manager)
    monkeypatch.setattr(saas, "_is_production_runtime", lambda: False)

    ok = saas._set_session_cookie("opaque-handle", remember_me=False)

    assert ok is True
    assert manager.last_set is not None
    assert manager.last_set["cookie"] == saas.SESSION_COOKIE_NAME
    assert manager.last_set["path"] == "/"
    assert manager.last_set["secure"] is False
    assert manager.last_set["same_site"] == "lax"


def test_cookie_readiness_retries_once_then_accepts_present_cookie(monkeypatch):
    store = _FakeSessionStore()
    client = _FakeSupabaseClient(user_id="u-ready")
    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client)
    monkeypatch.setattr(saas, "ensure_user_workspace_records", lambda *_a, **_k: (True, "ok"))
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {})
    monkeypatch.setattr(saas, "_save_login_metadata", lambda *_a, **_k: (True, "ok", {}, None))

    saas.initialize_session(client.auth._user, client.auth._session)
    cookie_value = saas._read_session_cookie()

    manager = _SequencedCookieManager(sequence=["", cookie_value])
    monkeypatch.setattr(saas, "_cookie_manager", lambda: manager)

    saas.st.session_state.clear()
    saas.st.session_state["saas_logged_in"] = False
    saas.st.session_state["saas_user"] = None
    saas.st.session_state["saas_selected_plan"] = saas.PLAN_MARKET_PULSE

    first_result = saas._rehydrate_authenticated_session()
    assert first_result is None
    assert saas.st.session_state.get(saas.COOKIE_READINESS_STATE_KEY) == saas.COOKIE_READINESS_NOT_READY
    assert saas.st.session_state.get(saas.COOKIE_READINESS_ATTEMPTS_KEY) == 1

    second_result = saas._rehydrate_authenticated_session()
    assert second_result is True
    assert saas.st.session_state.get(saas.COOKIE_READINESS_STATE_KEY) == saas.COOKIE_READINESS_PRESENT
    assert saas.st.session_state.get(saas.COOKIE_READINESS_ATTEMPTS_KEY) == 0
    assert saas.st.session_state.get("saas_logged_in") is True
    assert store.counter == 1


def test_cookie_readiness_bounded_when_cookie_absent(monkeypatch):
    store = _FakeSessionStore()
    manager = _SequencedCookieManager(sequence=["", "", ""])
    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "_cookie_manager", lambda: manager)

    cleared = []
    reruns = []
    monkeypatch.setattr(saas, "_clear_session_cookie", lambda: cleared.append(True))
    monkeypatch.setattr(saas.st, "rerun", lambda: reruns.append(True))

    saas.st.session_state["saas_logged_in"] = False
    saas.st.session_state["saas_user"] = None

    first_result = saas._rehydrate_authenticated_session()
    second_result = saas._rehydrate_authenticated_session()
    third_result = saas._rehydrate_authenticated_session()

    assert first_result is None
    assert second_result is False
    assert third_result is False
    assert len(reruns) == 1
    assert not cleared
    assert saas.st.session_state.get(saas.COOKIE_READINESS_STATE_KEY) == saas.COOKIE_READINESS_ABSENT
    assert saas.st.session_state.get(saas.COOKIE_READINESS_ATTEMPTS_KEY) == 0


def test_cookie_not_ready_rerun_suppressed_during_login_in_progress(monkeypatch):
    store = _FakeSessionStore()
    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(
        saas,
        "_read_session_cookie_result",
        lambda: saas.CookieReadResult(saas.COOKIE_READINESS_NOT_READY, ""),
    )

    reruns = []
    monkeypatch.setattr(saas.st, "rerun", lambda: reruns.append(True))

    saas.st.session_state["saas_logged_in"] = False
    saas.st.session_state["saas_user"] = None
    saas.st.session_state["saas_login_in_progress"] = True

    result = saas._rehydrate_authenticated_session()

    assert result is False
    assert not reruns


def test_login_attempt_reset_defers_cookie_readiness_clear(monkeypatch):
    saas.st.session_state[saas.COOKIE_READINESS_STATE_KEY] = saas.COOKIE_READINESS_PRESENT
    saas.st.session_state["saas_login_in_progress"] = True

    saas.clear_authenticated_session(revoke_current=False, reason="LOGIN_ATTEMPT_RESET")

    assert saas.st.session_state.get(saas.COOKIE_READINESS_STATE_KEY) == saas.COOKIE_READINESS_PRESENT


def test_present_cookie_still_verifies_signature(monkeypatch):
    store = _FakeSessionStore()
    client = _FakeSupabaseClient(user_id="u-signature")
    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client)
    monkeypatch.setattr(saas, "ensure_user_workspace_records", lambda *_a, **_k: (True, "ok"))
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {})
    monkeypatch.setattr(saas, "_save_login_metadata", lambda *_a, **_k: (True, "ok", {}, None))

    saas.initialize_session(client.auth._user, client.auth._session)
    signed_cookie = saas._read_session_cookie()
    handle = saas._unsign_session_handle(signed_cookie)

    saas.st.session_state.clear()
    saas.st.session_state["saas_logged_in"] = False
    saas.st.session_state["saas_user"] = None
    monkeypatch.setattr(saas, "_read_session_cookie_result", lambda: saas.CookieReadResult(saas.COOKIE_READINESS_PRESENT, signed_cookie))

    assert saas._rehydrate_authenticated_session() is True
    assert saas.st.session_state.get("saas_app_session_id")
    assert handle in store.rows


def test_login_creates_durable_session_and_cookie(monkeypatch):
    store = _FakeSessionStore()
    client = _FakeSupabaseClient(user_id="u-login")

    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client)
    monkeypatch.setattr(saas, "ensure_user_workspace_records", lambda *_a, **_k: (True, "ok"))
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {})
    monkeypatch.setattr(saas, "_save_login_metadata", lambda *_a, **_k: (True, "ok", {}, None))

    saas.st.session_state["saas_remember_me"] = True
    saas.initialize_session(client.auth._user, client.auth._session)

    assert saas.st.session_state.get("saas_logged_in") is True
    assert saas.st.session_state.get("saas_app_session_id")


def test_rehydrate_from_cookie_with_fresh_client(monkeypatch):
    store = _FakeSessionStore()
    client1 = _FakeSupabaseClient(user_id="u-rehydrate")
    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client1)
    monkeypatch.setattr(saas, "ensure_user_workspace_records", lambda *_a, **_k: (True, "ok"))
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {})
    monkeypatch.setattr(saas, "_save_login_metadata", lambda *_a, **_k: (True, "ok", {}, None))

    saas.initialize_session(client1.auth._user, client1.auth._session)
    initial_session_count = store.counter

    saas.st.session_state.clear()
    saas.st.session_state["saas_logged_in"] = False
    saas.st.session_state["saas_user"] = None
    saas.st.session_state["saas_selected_plan"] = saas.PLAN_MARKET_PULSE
    cookie_value = saas._read_session_cookie()

    # Simulate browser restart/fresh client instance.
    client2 = _FakeSupabaseClient(user_id="u-rehydrate")
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client2)
    monkeypatch.setattr(saas, "_read_session_cookie_result", lambda: saas.CookieReadResult(saas.COOKIE_READINESS_PRESENT, cookie_value))

    assert saas._rehydrate_authenticated_session() is True
    assert saas.st.session_state.get("saas_logged_in") is True
    assert store.counter == initial_session_count
    assert saas.st.session_state.get(saas.COOKIE_READINESS_STATE_KEY) == saas.COOKIE_READINESS_PRESENT
    assert saas.st.session_state.get(saas.COOKIE_READINESS_ATTEMPTS_KEY) == 0


def test_login_again_supersedes_same_browser_active_session(monkeypatch):
    store = _FakeSessionStore()
    client = _FakeSupabaseClient(user_id="u-supersede")

    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client)
    monkeypatch.setattr(saas, "ensure_user_workspace_records", lambda *_a, **_k: (True, "ok"))
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {})
    monkeypatch.setattr(saas, "_save_login_metadata", lambda *_a, **_k: (True, "ok", {}, None))

    saas.initialize_session(client.auth._user, client.auth._session)
    first_app_session_id = str(saas.st.session_state.get("saas_app_session_id") or "")

    # Simulate explicit login again for the same browser/device.
    saas.initialize_session(client.auth._user, client.auth._session)
    second_app_session_id = str(saas.st.session_state.get("saas_app_session_id") or "")

    assert first_app_session_id
    assert second_app_session_id
    assert first_app_session_id != second_app_session_id

    rows = [row for _handle, row in store.user_sessions.get("u-supersede", [])]
    active = [row for row in rows if row.revoked_at is None]
    revoked = [row for row in rows if row.revoked_at is not None]

    assert len(rows) == 2
    assert len(active) == 1
    assert len(revoked) == 1
    assert revoked[0].revocation_reason == "SESSION_SUPERSEDED"


def test_logout_then_login_again_keeps_exactly_one_active(monkeypatch):
    store = _FakeSessionStore()
    client = _FakeSupabaseClient(user_id="u-logout-login")

    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client)
    monkeypatch.setattr(saas, "ensure_user_workspace_records", lambda *_a, **_k: (True, "ok"))
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {})
    monkeypatch.setattr(saas, "_save_login_metadata", lambda *_a, **_k: (True, "ok", {}, None))

    saas.initialize_session(client.auth._user, client.auth._session)
    rows = [row for _handle, row in store.user_sessions.get("u-logout-login", [])]
    assert len([row for row in rows if row.revoked_at is None]) == 1

    ok, _message = saas.supabase_logout()
    assert ok is True
    rows = [row for _handle, row in store.user_sessions.get("u-logout-login", [])]
    assert len([row for row in rows if row.revoked_at is None]) == 0
    assert len([row for row in rows if row.revocation_reason == "USER_LOGOUT"]) == 1

    saas.initialize_session(client.auth._user, client.auth._session)
    rows = [row for _handle, row in store.user_sessions.get("u-logout-login", [])]
    assert len(rows) == 2
    assert len([row for row in rows if row.revoked_at is None]) == 1


def test_malformed_cookie_clears_safely(monkeypatch):
    store = _FakeSessionStore()
    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "_read_session_cookie_result", lambda: saas.CookieReadResult(saas.COOKIE_READINESS_PRESENT, "malformed"))

    assert saas._rehydrate_authenticated_session() is False


def test_invalid_signed_cookie_remains_rejected(monkeypatch):
    store = _FakeSessionStore()
    client = _FakeSupabaseClient(user_id="u-invalid")
    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client)
    monkeypatch.setattr(saas, "ensure_user_workspace_records", lambda *_a, **_k: (True, "ok"))
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {})
    monkeypatch.setattr(saas, "_save_login_metadata", lambda *_a, **_k: (True, "ok", {}, None))

    saas.initialize_session(client.auth._user, client.auth._session)
    signed_cookie = saas._read_session_cookie()
    tampered_cookie = signed_cookie[:-1] + ("A" if signed_cookie[-1] != "A" else "B")

    cleared = []
    monkeypatch.setattr(saas, "_read_session_cookie_result", lambda: saas.CookieReadResult(saas.COOKIE_READINESS_PRESENT, tampered_cookie))
    monkeypatch.setattr(saas, "_clear_session_cookie", lambda: cleared.append(True))

    saas.st.session_state["saas_logged_in"] = False
    saas.st.session_state["saas_user"] = None

    assert saas._rehydrate_authenticated_session() is False
    assert cleared
    assert saas.st.session_state.get(saas.COOKIE_READINESS_STATE_KEY) == saas.COOKIE_READINESS_ABSENT


def test_invalid_signature_clears_cookie_safely(monkeypatch):
    store = _FakeSessionStore()
    client = _FakeSupabaseClient(user_id="u-sig")
    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client)
    monkeypatch.setattr(saas, "ensure_user_workspace_records", lambda *_a, **_k: (True, "ok"))
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {})
    monkeypatch.setattr(saas, "_save_login_metadata", lambda *_a, **_k: (True, "ok", {}, None))

    saas.initialize_session(client.auth._user, client.auth._session)
    signed_cookie = saas._read_session_cookie()
    tampered_cookie = signed_cookie[:-1] + ("A" if signed_cookie[-1] != "A" else "B")

    saas.st.session_state["saas_logged_in"] = False
    saas.st.session_state["saas_user"] = None
    monkeypatch.setattr(saas, "_read_session_cookie_result", lambda: saas.CookieReadResult(saas.COOKIE_READINESS_PRESENT, tampered_cookie))

    assert saas._rehydrate_authenticated_session() is False
    assert saas._cookie_manager().get(saas.SESSION_COOKIE_NAME) is None


def test_missing_durable_session_clears_cookie_safely(monkeypatch):
    store = _FakeSessionStore()
    client = _FakeSupabaseClient(user_id="u-missing")
    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client)
    monkeypatch.setattr(saas, "ensure_user_workspace_records", lambda *_a, **_k: (True, "ok"))
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {})
    monkeypatch.setattr(saas, "_save_login_metadata", lambda *_a, **_k: (True, "ok", {}, None))

    saas.initialize_session(client.auth._user, client.auth._session)
    cookie_value = saas._read_session_cookie()
    handle = saas._unsign_session_handle(cookie_value)

    store.rows.pop(handle, None)
    store.refresh.pop(handle, None)
    saas.st.session_state["saas_logged_in"] = False
    saas.st.session_state["saas_user"] = None
    monkeypatch.setattr(saas, "_read_session_cookie_result", lambda: saas.CookieReadResult(saas.COOKIE_READINESS_PRESENT, cookie_value))

    assert saas._rehydrate_authenticated_session() is False
    assert saas._cookie_manager().get(saas.SESSION_COOKIE_NAME) is None


def test_revoked_and_expired_rows_clear_safely(monkeypatch):
    store = _FakeSessionStore()
    client = _FakeSupabaseClient(user_id="u-exp")
    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client)
    monkeypatch.setattr(saas, "ensure_user_workspace_records", lambda *_a, **_k: (True, "ok"))
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {})
    monkeypatch.setattr(saas, "_save_login_metadata", lambda *_a, **_k: (True, "ok", {}, None))

    saas.initialize_session(client.auth._user, client.auth._session)
    cookie_value = saas._read_session_cookie()
    handle = saas._unsign_session_handle(cookie_value)

    row = store.rows[handle]
    row.revoked_at = datetime.now(timezone.utc)
    saas.st.session_state["saas_logged_in"] = False
    saas.st.session_state["saas_user"] = None
    assert saas._rehydrate_authenticated_session() is False

    row.revoked_at = None
    row.absolute_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    saas.st.session_state["saas_logged_in"] = False
    saas.st.session_state["saas_user"] = None
    assert saas._rehydrate_authenticated_session() is False


def test_logout_revokes_current_session_and_clears_cookie(monkeypatch):
    store = _FakeSessionStore()
    client = _FakeSupabaseClient(user_id="u-logout")
    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client)
    monkeypatch.setattr(saas, "ensure_user_workspace_records", lambda *_a, **_k: (True, "ok"))
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {})
    monkeypatch.setattr(saas, "_save_login_metadata", lambda *_a, **_k: (True, "ok", {}, None))

    saas.initialize_session(client.auth._user, client.auth._session)
    sid = saas.st.session_state.get("saas_app_session_id")
    assert sid

    ok, _ = saas.supabase_logout()
    assert ok is True
    assert saas.st.session_state.get(saas.COOKIE_READINESS_STATE_KEY) is None
    assert saas.st.session_state.get(saas.COOKIE_READINESS_ATTEMPTS_KEY) is None

    revoked_count = 0
    for row in store.rows.values():
        if row.id == sid and row.revoked_at is not None:
            revoked_count += 1
    assert revoked_count == 1
    assert store.revoke_calls[-1]["reason"] == "USER_LOGOUT"


def test_logout_resolves_current_session_from_cookie_when_state_id_missing(monkeypatch):
    store = _FakeSessionStore()
    client = _FakeSupabaseClient(user_id="u-cookie-logout")
    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client)
    monkeypatch.setattr(saas, "ensure_user_workspace_records", lambda *_a, **_k: (True, "ok"))
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {})
    monkeypatch.setattr(saas, "_save_login_metadata", lambda *_a, **_k: (True, "ok", {}, None))

    saas.initialize_session(client.auth._user, client.auth._session)
    sid = str(saas.st.session_state.get("saas_app_session_id") or "")
    assert sid

    # Simulate authenticated fallback state with cookie still present but no tracked durable id.
    saas.st.session_state["saas_app_session_id"] = ""

    ok, message = saas.supabase_logout()

    assert ok is True
    assert message == "Logged out."
    revoked = [row for row in store.rows.values() if row.id == sid and row.revoked_at is not None]
    assert len(revoked) == 1
    assert revoked[0].revocation_reason == "USER_LOGOUT"


def test_refresh_after_logout_does_not_restore_or_create_session(monkeypatch):
    store = _FakeSessionStore()
    client = _FakeSupabaseClient(user_id="u-refresh-after-logout")
    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client)
    monkeypatch.setattr(saas, "ensure_user_workspace_records", lambda *_a, **_k: (True, "ok"))
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {})
    monkeypatch.setattr(saas, "_save_login_metadata", lambda *_a, **_k: (True, "ok", {}, None))

    saas.initialize_session(client.auth._user, client.auth._session)
    session_count_before_logout = store.counter

    ok, _message = saas.supabase_logout()
    assert ok is True

    saas.st.session_state["saas_logged_in"] = False
    saas.st.session_state["saas_user"] = None
    first_result = saas._rehydrate_authenticated_session()
    if first_result is None:
        assert saas._rehydrate_authenticated_session() is False
    else:
        assert first_result is False
    assert store.counter == session_count_before_logout
    assert len(store.active_sessions_for_user("u-refresh-after-logout")) == 0


def test_browser_restart_after_logout_cannot_rehydrate_revoked_session(monkeypatch):
    store = _FakeSessionStore()
    client1 = _FakeSupabaseClient(user_id="u-restart-after-logout")
    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client1)
    monkeypatch.setattr(saas, "ensure_user_workspace_records", lambda *_a, **_k: (True, "ok"))
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {})
    monkeypatch.setattr(saas, "_save_login_metadata", lambda *_a, **_k: (True, "ok", {}, None))

    saas.initialize_session(client1.auth._user, client1.auth._session)
    session_count_before_logout = store.counter

    ok, _message = saas.supabase_logout()
    assert ok is True

    saas.st.session_state.clear()
    saas.st.session_state["saas_logged_in"] = False
    saas.st.session_state["saas_user"] = None
    saas.st.session_state["saas_selected_plan"] = saas.PLAN_MARKET_PULSE

    client2 = _FakeSupabaseClient(user_id="u-restart-after-logout")
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client2)

    first_result = saas._rehydrate_authenticated_session()
    if first_result is None:
        assert saas._rehydrate_authenticated_session() is False
    else:
        assert first_result is False
    assert store.counter == session_count_before_logout
    assert len(store.active_sessions_for_user("u-restart-after-logout")) == 0


def test_auth_cache_stores_and_resolves_session_id_for_logout(monkeypatch):
    store = _FakeSessionStore()
    client1 = _FakeSupabaseClient(user_id="u-cache-logout")
    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client1)
    monkeypatch.setattr(saas, "ensure_user_workspace_records", lambda *_a, **_k: (True, "ok"))
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {})
    monkeypatch.setattr(saas, "_save_login_metadata", lambda *_a, **_k: (True, "ok", {}, None))

    saas.initialize_session(client1.auth._user, client1.auth._session)
    sid = str(saas.st.session_state.get("saas_app_session_id") or "")
    assert sid

    cache_key = saas._browser_auth_cache_key()
    saas._auth_session_cache()[cache_key] = {
        "access_token": "cached-access",
        "refresh_token": "cached-refresh",
        "expires_at": None,
        "app_session_id": sid,
    }

    saas.st.session_state["saas_app_session_id"] = ""
    monkeypatch.setattr(saas, "_read_session_cookie_result", lambda: saas.CookieReadResult(saas.COOKIE_READINESS_ABSENT, ""))

    resolved_sid, source = saas._resolve_current_app_session_id(store)
    assert resolved_sid == sid
    assert source == "auth_cache"

    ok, _message = saas.supabase_logout()
    assert ok is True
    revoked = [row for row in store.rows.values() if row.id == sid and row.revoked_at is not None]
    assert len(revoked) == 1
    assert revoked[0].revocation_reason == "USER_LOGOUT"


def test_logout_does_not_revoke_other_browser_session(monkeypatch):
    store = _FakeSessionStore()
    client = _FakeSupabaseClient(user_id="u-browser-isolation")
    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client)
    monkeypatch.setattr(saas, "ensure_user_workspace_records", lambda *_a, **_k: (True, "ok"))
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {})
    monkeypatch.setattr(saas, "_save_login_metadata", lambda *_a, **_k: (True, "ok", {}, None))

    saas.initialize_session(client.auth._user, client.auth._session)
    current_sid = str(saas.st.session_state.get("saas_app_session_id") or "")

    other = store.create_session(
        saas.SessionCreationInput(
            user_id="u-browser-isolation",
            remember_me=False,
            user_agent="ua-test",
            client_metadata={"browser_fingerprint": "other-browser"},
            refresh_material="refresh-other",
        )
    )

    ok, _message = saas.supabase_logout()
    assert ok is True

    current_rows = [row for row in store.rows.values() if row.id == current_sid]
    other_rows = [row for row in store.rows.values() if row.id == other.record.id]
    assert current_rows and current_rows[0].revoked_at is not None
    assert other_rows and other_rows[0].revoked_at is None


def test_logout_all_revokes_all_user_sessions(monkeypatch):
    store = _FakeSessionStore()
    client = _FakeSupabaseClient(user_id="u-all")
    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client)
    monkeypatch.setattr(saas, "ensure_user_workspace_records", lambda *_a, **_k: (True, "ok"))
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {})
    monkeypatch.setattr(saas, "_save_login_metadata", lambda *_a, **_k: (True, "ok", {}, None))

    saas.initialize_session(client.auth._user, client.auth._session)
    saas.initialize_session(client.auth._user, client.auth._session)

    ok, _ = saas.supabase_logout_all()
    assert ok is True

    active = [row for row in store.rows.values() if row.user_id == "u-all" and row.revoked_at is None]
    assert not active


def test_remember_me_and_standard_duration_policy(monkeypatch):
    store = _FakeSessionStore()
    client = _FakeSupabaseClient(user_id="u-policy")
    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client)
    monkeypatch.setattr(saas, "ensure_user_workspace_records", lambda *_a, **_k: (True, "ok"))
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {})
    monkeypatch.setattr(saas, "_save_login_metadata", lambda *_a, **_k: (True, "ok", {}, None))

    saas.st.session_state["saas_remember_me"] = False
    saas.initialize_session(client.auth._user, client.auth._session)
    standard_row = list(store.rows.values())[-1]

    saas.st.session_state["saas_remember_me"] = True
    saas.initialize_session(client.auth._user, client.auth._session)
    remember_row = list(store.rows.values())[-1]

    standard_duration = standard_row.absolute_expires_at - standard_row.created_at
    remember_duration = remember_row.absolute_expires_at - remember_row.created_at

    assert standard_duration <= timedelta(days=1, minutes=1)
    assert remember_duration >= timedelta(days=29)


def test_successful_login_resets_readiness_state(monkeypatch):
    store = _FakeSessionStore()
    client = _FakeSupabaseClient(user_id="u-login-reset")
    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client)
    monkeypatch.setattr(saas, "ensure_user_workspace_records", lambda *_a, **_k: (True, "ok"))
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {})
    monkeypatch.setattr(saas, "_save_login_metadata", lambda *_a, **_k: (True, "ok", {}, None))

    saas.st.session_state[saas.COOKIE_READINESS_STATE_KEY] = saas.COOKIE_READINESS_NOT_READY
    saas.st.session_state[saas.COOKIE_READINESS_ATTEMPTS_KEY] = 1

    assert saas.set_authenticated_session(_FakeAuthResponse(user=client.auth._user, session=client.auth._session)) is True
    assert saas.st.session_state.get(saas.COOKIE_READINESS_STATE_KEY) is None
    assert saas.st.session_state.get(saas.COOKIE_READINESS_ATTEMPTS_KEY) is None


def test_no_token_leakage_in_cookie_value(monkeypatch):
    store = _FakeSessionStore()
    client = _FakeSupabaseClient(user_id="u-leak", refresh_token="sensitive-refresh")
    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: client)
    monkeypatch.setattr(saas, "ensure_user_workspace_records", lambda *_a, **_k: (True, "ok"))
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {})
    monkeypatch.setattr(saas, "_save_login_metadata", lambda *_a, **_k: (True, "ok", {}, None))

    saas.initialize_session(client.auth._user, client.auth._session)
    cookie_value = saas._read_session_cookie()

    assert "sensitive-refresh" not in cookie_value
    assert "access-" not in cookie_value


def test_cross_user_isolation(monkeypatch):
    store = _FakeSessionStore()
    user1 = _FakeSupabaseClient(user_id="user-1")
    monkeypatch.setattr(saas, "_session_store", lambda: store)
    monkeypatch.setattr(saas, "get_supabase_client", lambda: user1)
    monkeypatch.setattr(saas, "ensure_user_workspace_records", lambda *_a, **_k: (True, "ok"))
    monkeypatch.setattr(saas, "_profile_row_for_auth_user", lambda *_a, **_k: {})
    monkeypatch.setattr(saas, "_save_login_metadata", lambda *_a, **_k: (True, "ok", {}, None))

    saas.initialize_session(user1.auth._user, user1.auth._session)
    cookie_user1 = saas._read_session_cookie()

    # Different user client should not authenticate as user1 when forced mismatched store refresh.
    user2 = _FakeSupabaseClient(user_id="user-2")
    monkeypatch.setattr(saas, "get_supabase_client", lambda: user2)
    monkeypatch.setattr(saas, "_read_session_cookie_result", lambda: saas.CookieReadResult(saas.COOKIE_READINESS_PRESENT, cookie_user1))
    saas.st.session_state["saas_logged_in"] = False
    saas.st.session_state["saas_user"] = None

    assert saas._rehydrate_authenticated_session() is True
    assert saas.get_current_user() is not None
    assert saas.get_current_user().user_id == "user-1"
