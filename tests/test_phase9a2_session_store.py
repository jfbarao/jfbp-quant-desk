from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from core.session_crypto import SessionCrypto, SessionCryptoError
from core.session_store import (
    SessionCreationInput,
    SessionLookupStatus,
    SessionPolicy,
    SessionStore,
    SessionStoreError,
)


class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload
        self.content = b"" if payload is None else b"x"

    def json(self):
        return self._payload


class _FakeRequests:
    def __init__(self):
        self.rows = []
        self.id_counter = 0

    def post(self, url, headers=None, json=None, timeout=None):
        if url.endswith("/rpc/app_sessions_create"):
            self.id_counter += 1
            row_id = f"s{self.id_counter}"
            row = {
                "id": row_id,
                "session_handle_hash": json["p_session_handle_hash"],
                "user_id": json["p_user_id"],
                "created_at": json["p_created_at"],
                "last_seen_at": json["p_created_at"],
                "idle_expires_at": json["p_idle_expires_at"],
                "absolute_expires_at": json["p_absolute_expires_at"],
                "revoked_at": None,
                "revocation_reason": "",
                "remember_me": bool(json.get("p_remember_me", False)),
                "user_agent": json.get("p_user_agent") or "",
                "client_metadata": json.get("p_client_metadata") or {},
                "rotation_parent_id": json.get("p_rotation_parent_id"),
                "replaced_by_session_id": None,
                "refresh_material_encrypted": json.get("p_refresh_material_encrypted"),
                "refresh_material_key_version": json.get("p_refresh_material_key_version"),
            }

            # Deterministic oldest-session eviction policy for > 5 sessions.
            now = datetime.fromisoformat(json["p_created_at"].replace("Z", "+00:00"))
            active = [
                r for r in self.rows
                if r["user_id"] == json["p_user_id"]
                and r["revoked_at"] is None
                and datetime.fromisoformat(r["idle_expires_at"].replace("Z", "+00:00")) > now
                and datetime.fromisoformat(r["absolute_expires_at"].replace("Z", "+00:00")) > now
            ]
            max_sessions = int(json.get("p_max_active_sessions", 5))
            overflow = len(active) - (max_sessions - 1)
            if overflow > 0:
                for old in sorted(active, key=lambda x: x["created_at"])[:overflow]:
                    old["revoked_at"] = json["p_created_at"]
                    old["revocation_reason"] = "MAX_CONCURRENT_LIMIT"

            self.rows.append(row)
            return _FakeResponse(payload=[dict(row)])

        if url.endswith("/rpc/app_sessions_cleanup"):
            return _FakeResponse(payload=0)

        return _FakeResponse(status_code=500, payload={"message": "unsupported post"})

    def get(self, url, headers=None, params=None, timeout=None):
        params = params or {}
        if not url.endswith("/rest/v1/app_sessions"):
            return _FakeResponse(status_code=500, payload={"message": "unsupported get"})

        selected = list(self.rows)
        if "session_handle_hash" in params:
            _, value = str(params["session_handle_hash"]).split(".", 1)
            selected = [r for r in selected if r["session_handle_hash"] == value]
        if "id" in params:
            _, value = str(params["id"]).split(".", 1)
            selected = [r for r in selected if r["id"] == value]
        if "user_id" in params:
            _, value = str(params["user_id"]).split(".", 1)
            selected = [r for r in selected if r["user_id"] == value]
        if params.get("revoked_at") == "is.null":
            selected = [r for r in selected if r["revoked_at"] is None]
        if "idle_expires_at" in params and str(params["idle_expires_at"]).startswith("gt."):
            cutoff = datetime.fromisoformat(str(params["idle_expires_at"])[3:].replace("Z", "+00:00"))
            selected = [r for r in selected if datetime.fromisoformat(r["idle_expires_at"].replace("Z", "+00:00")) > cutoff]
        if "absolute_expires_at" in params and str(params["absolute_expires_at"]).startswith("gt."):
            cutoff = datetime.fromisoformat(str(params["absolute_expires_at"])[3:].replace("Z", "+00:00"))
            selected = [r for r in selected if datetime.fromisoformat(r["absolute_expires_at"].replace("Z", "+00:00")) > cutoff]
        if str(params.get("order", "")).startswith("created_at"):
            selected = sorted(selected, key=lambda x: x["created_at"])
        if params.get("limit"):
            selected = selected[: int(params["limit"])]

        return _FakeResponse(payload=[dict(x) for x in selected])

    def patch(self, url, headers=None, params=None, json=None, timeout=None):
        params = params or {}
        if not url.endswith("/rest/v1/app_sessions"):
            return _FakeResponse(status_code=500, payload={"message": "unsupported patch"})

        touched = []
        for row in self.rows:
            if "id" in params:
                _, value = str(params["id"]).split(".", 1)
                if row["id"] != value:
                    continue
            if "user_id" in params:
                _, value = str(params["user_id"]).split(".", 1)
                if row["user_id"] != value:
                    continue
            if params.get("revoked_at") == "is.null" and row["revoked_at"] is not None:
                continue

            for key, value in (json or {}).items():
                row[key] = value
            touched.append({"id": row["id"]})

        return _FakeResponse(payload=touched)


@pytest.fixture
def fake_requests(monkeypatch):
    fake = _FakeRequests()
    import core.session_store as session_store

    monkeypatch.setattr(session_store, "requests", fake)
    return fake


@pytest.fixture
def crypto_env(monkeypatch):
    monkeypatch.setenv(
        "SESSION_ENCRYPTION_KEY",
        "hU8sNndT0QCeQ2U8Vl8mUdQqRmk_NsX6V4NlIdv1Q2k=",
    )
    monkeypatch.setenv("SESSION_ENCRYPTION_KEY_VERSION", "v1")


def _build_store() -> SessionStore:
    return SessionStore(
        supabase_url="https://unit-test.supabase.co",
        service_role_key="service-role-unit-test-key",
        policy=SessionPolicy(
            idle_timeout_seconds=24 * 60 * 60,
            absolute_timeout_seconds=24 * 60 * 60,
            remember_me_absolute_timeout_seconds=30 * 24 * 60 * 60,
            max_active_sessions=5,
            last_seen_throttle_seconds=300,
        ),
    )


def test_handle_generation_is_opaque(crypto_env):
    store = _build_store()
    handle = store.generate_session_handle()
    assert isinstance(handle, str)
    assert len(handle) >= 64


def test_handle_hash_is_deterministic(crypto_env):
    store = _build_store()
    h1 = store.hash_session_handle("abc")
    h2 = store.hash_session_handle("abc")
    assert h1 == h2


def test_create_and_retrieve_valid_session(fake_requests, crypto_env):
    store = _build_store()
    created = store.create_session(
        SessionCreationInput(
            user_id="00000000-0000-0000-0000-000000000001",
            remember_me=False,
            user_agent="ua-test",
            client_metadata={"ip_hash": "x"},
            refresh_material="refresh-123",
        )
    )

    assert created.raw_handle
    assert created.record.session_handle_hash
    assert all(r.get("session_handle_hash") != created.raw_handle for r in fake_requests.rows)

    lookup = store.get_session_by_handle(created.raw_handle)
    assert lookup.status == SessionLookupStatus.VALID
    assert lookup.record is not None
    assert lookup.record.user_id == "00000000-0000-0000-0000-000000000001"


def test_missing_and_malformed_handle(fake_requests, crypto_env):
    store = _build_store()

    malformed = store.get_session_by_handle("")
    assert malformed.status == SessionLookupStatus.MALFORMED

    missing = store.get_session_by_handle("not-found")
    assert missing.status == SessionLookupStatus.MISSING


def test_revoked_idle_and_absolute_expiration_states(fake_requests, crypto_env):
    store = _build_store()
    base = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)
    created = store.create_session(
        SessionCreationInput(
            user_id="00000000-0000-0000-0000-000000000002",
            created_at=base,
            refresh_material="refresh-abc",
        )
    )

    sid = created.record.id
    store.revoke_session(sid, reason="USER_LOGOUT", now=base + timedelta(minutes=1))
    lookup = store.get_session_by_handle(created.raw_handle, now=base + timedelta(minutes=2))
    assert lookup.status == SessionLookupStatus.REVOKED

    idle_created = store.create_session(
        SessionCreationInput(
            user_id="00000000-0000-0000-0000-000000000003",
            created_at=base,
            refresh_material="refresh-idle",
        )
    )
    idle_lookup = store.get_session_by_handle(idle_created.raw_handle, now=base + timedelta(days=2))
    assert idle_lookup.status == SessionLookupStatus.ABSOLUTE_EXPIRED

    # Force idle-only expiration by manually extending absolute expiry.
    row = next(r for r in fake_requests.rows if r["id"] == idle_created.record.id)
    row["absolute_expires_at"] = (base + timedelta(days=10)).isoformat()
    row["idle_expires_at"] = (base + timedelta(hours=1)).isoformat()
    idle_only_lookup = store.get_session_by_handle(idle_created.raw_handle, now=base + timedelta(days=1))
    assert idle_only_lookup.status == SessionLookupStatus.IDLE_EXPIRED


def test_last_seen_throttling(fake_requests, crypto_env):
    store = _build_store()
    base = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)
    created = store.create_session(
        SessionCreationInput(
            user_id="00000000-0000-0000-0000-000000000004",
            created_at=base,
            refresh_material="refresh-throttle",
        )
    )

    assert store.touch_last_seen(created.record.id, now=base + timedelta(seconds=10)) is False
    assert store.touch_last_seen(created.record.id, now=base + timedelta(minutes=10)) is True


def test_revoke_all_current_and_cross_user_isolation(fake_requests, crypto_env):
    store = _build_store()
    a = store.create_session(
        SessionCreationInput(user_id="00000000-0000-0000-0000-000000000005", refresh_material="r1")
    )
    b = store.create_session(
        SessionCreationInput(user_id="00000000-0000-0000-0000-000000000005", refresh_material="r2")
    )
    c = store.create_session(
        SessionCreationInput(user_id="00000000-0000-0000-0000-000000000006", refresh_material="r3")
    )

    revoked = store.revoke_all_sessions_for_user("00000000-0000-0000-0000-000000000005")
    assert revoked == 2

    la = store.get_session_by_handle(a.raw_handle)
    lb = store.get_session_by_handle(b.raw_handle)
    lc = store.get_session_by_handle(c.raw_handle)

    assert la.status == SessionLookupStatus.REVOKED
    assert lb.status == SessionLookupStatus.REVOKED
    assert lc.status == SessionLookupStatus.VALID


def test_max_five_session_enforcement_and_oldest_eviction(fake_requests, crypto_env):
    store = _build_store()
    uid = "00000000-0000-0000-0000-000000000007"
    base = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)

    created = []
    for i in range(6):
        created.append(
            store.create_session(
                SessionCreationInput(
                    user_id=uid,
                    created_at=base + timedelta(minutes=i),
                    refresh_material=f"refresh-{i}",
                )
            )
        )

    active = store.active_sessions_for_user(uid, now=base + timedelta(hours=1))
    assert len(active) == 5

    first_lookup = store.get_session_by_handle(created[0].raw_handle, now=base + timedelta(hours=1))
    assert first_lookup.status == SessionLookupStatus.REVOKED


def test_rotate_session_handle(fake_requests, crypto_env):
    store = _build_store()
    original = store.create_session(
        SessionCreationInput(
            user_id="00000000-0000-0000-0000-000000000008",
            refresh_material="refresh-rotate",
        )
    )

    rotated = store.rotate_session_handle(original.record.id)

    old_lookup = store.get_session_by_handle(original.raw_handle)
    new_lookup = store.get_session_by_handle(rotated.raw_handle)

    assert old_lookup.status == SessionLookupStatus.REVOKED
    assert new_lookup.status == SessionLookupStatus.VALID
    assert rotated.record.rotation_parent_id == original.record.id


def test_no_secret_leakage_in_repr(fake_requests, crypto_env):
    store = _build_store()
    created = store.create_session(
        SessionCreationInput(
            user_id="00000000-0000-0000-0000-000000000009",
            refresh_material="highly-sensitive-refresh-token",
        )
    )
    text = repr(created)
    assert "highly-sensitive-refresh-token" not in text


def test_refresh_material_round_trip_and_wrong_key_failure(crypto_env):
    crypto = SessionCrypto()
    encrypted = crypto.encrypt("refresh-token-xyz")
    assert crypto.decrypt(encrypted) == "refresh-token-xyz"

    with pytest.raises(SessionCryptoError):
        wrong = SessionCrypto(current_key="another-secret-not-same")
        wrong.decrypt(encrypted)


def test_missing_encryption_key_failure(monkeypatch):
    monkeypatch.delenv("SESSION_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("SESSION_ENCRYPTION_KEY_VERSION", raising=False)
    with pytest.raises(SessionCryptoError):
        SessionCrypto(current_key="")


def test_session_store_requires_service_role_and_url(monkeypatch, crypto_env):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    import core.session_store as session_store
    monkeypatch.setattr(session_store, "_secret_value", lambda _name, _default="": "")

    with pytest.raises(SessionStoreError):
        SessionStore(supabase_url="", service_role_key="x")
    with pytest.raises(SessionStoreError):
        SessionStore(supabase_url="https://unit-test.supabase.co", service_role_key="")


def test_get_refresh_material_for_handle(fake_requests, crypto_env):
    store = _build_store()
    created = store.create_session(
        SessionCreationInput(
            user_id="00000000-0000-0000-0000-000000000010",
            refresh_material="refresh-value",
        )
    )
    value = store.get_refresh_material_for_handle(created.raw_handle)
    assert value == "refresh-value"


def test_refresh_material_never_persisted_in_plaintext(fake_requests, crypto_env):
    store = _build_store()
    store.create_session(
        SessionCreationInput(
            user_id="00000000-0000-0000-0000-000000000011",
            refresh_material="plain-refresh-secret",
        )
    )
    dumped = json.dumps(fake_requests.rows)
    assert "plain-refresh-secret" not in dumped
