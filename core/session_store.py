from __future__ import annotations

import hashlib
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import requests

from core.session_crypto import SessionCrypto, SessionCryptoError


DEFAULT_IDLE_TIMEOUT_SECONDS = 24 * 60 * 60
DEFAULT_ABSOLUTE_TIMEOUT_SECONDS = 24 * 60 * 60
DEFAULT_REMEMBER_ME_ABSOLUTE_TIMEOUT_SECONDS = 30 * 24 * 60 * 60
DEFAULT_MAX_ACTIVE_SESSIONS = 5
LAST_SEEN_THROTTLE_SECONDS = 300


class SessionLookupStatus(str, Enum):
    VALID = "valid"
    MISSING = "missing"
    REVOKED = "revoked"
    IDLE_EXPIRED = "idle_expired"
    ABSOLUTE_EXPIRED = "absolute_expired"
    MALFORMED = "malformed"


class SessionStoreError(RuntimeError):
    """Raised when session-store operations fail."""


@dataclass(frozen=True)
class SessionPolicy:
    idle_timeout_seconds: int = DEFAULT_IDLE_TIMEOUT_SECONDS
    absolute_timeout_seconds: int = DEFAULT_ABSOLUTE_TIMEOUT_SECONDS
    remember_me_absolute_timeout_seconds: int = DEFAULT_REMEMBER_ME_ABSOLUTE_TIMEOUT_SECONDS
    max_active_sessions: int = DEFAULT_MAX_ACTIVE_SESSIONS
    last_seen_throttle_seconds: int = LAST_SEEN_THROTTLE_SECONDS


@dataclass(frozen=True)
class SessionRecord:
    id: str
    user_id: str
    session_handle_hash: str
    created_at: datetime
    last_seen_at: datetime
    idle_expires_at: datetime
    absolute_expires_at: datetime
    revoked_at: Optional[datetime]
    revocation_reason: str
    remember_me: bool
    user_agent: str
    client_metadata: Dict[str, Any]
    rotation_parent_id: Optional[str]
    replaced_by_session_id: Optional[str]


@dataclass(frozen=True)
class SessionLookupResult:
    status: SessionLookupStatus
    record: Optional[SessionRecord] = None


@dataclass(frozen=True)
class CreatedSession:
    raw_handle: str
    record: SessionRecord


@dataclass(frozen=True)
class SessionCreationInput:
    user_id: str
    remember_me: bool = False
    user_agent: str = ""
    client_metadata: Optional[Dict[str, Any]] = None
    refresh_material: str = ""
    created_at: Optional[datetime] = None
    rotation_parent_id: Optional[str] = None


class SessionStore:
    """Durable server-side session store using Supabase PostgREST + RPC."""

    def __init__(
        self,
        *,
        supabase_url: Optional[str] = None,
        service_role_key: Optional[str] = None,
        policy: Optional[SessionPolicy] = None,
        session_crypto: Optional[SessionCrypto] = None,
        timeout_seconds: int = 20,
    ) -> None:
        self._supabase_url = str(supabase_url or _secret_value("SUPABASE_URL", "")).rstrip("/")
        self._service_role_key = str(service_role_key or _secret_value("SUPABASE_SERVICE_ROLE_KEY", "")).strip()
        self._policy = policy or SessionPolicy()
        self._timeout_seconds = int(timeout_seconds)

        if not self._supabase_url or not self._service_role_key:
            raise SessionStoreError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for SessionStore")

        self._session_crypto = session_crypto or SessionCrypto()

    @property
    def policy(self) -> SessionPolicy:
        return self._policy

    def generate_session_handle(self) -> str:
        return secrets.token_urlsafe(48)

    def hash_session_handle(self, raw_handle: str) -> str:
        text = str(raw_handle or "").strip()
        if not text:
            raise SessionStoreError("session handle is required")
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def create_session(self, data: SessionCreationInput) -> CreatedSession:
        user_id = str(data.user_id or "").strip()
        if not user_id:
            raise SessionStoreError("user_id is required")

        created_at = _aware_utc(data.created_at) if data.created_at else _utc_now()
        idle_expires_at = created_at + timedelta(seconds=self._policy.idle_timeout_seconds)
        absolute_seconds = (
            self._policy.remember_me_absolute_timeout_seconds
            if bool(data.remember_me)
            else self._policy.absolute_timeout_seconds
        )
        absolute_expires_at = created_at + timedelta(seconds=absolute_seconds)

        raw_handle = self.generate_session_handle()
        handle_hash = self.hash_session_handle(raw_handle)

        refresh_ciphertext = None
        refresh_key_version = None
        refresh_material = str(data.refresh_material or "").strip()
        if refresh_material:
            refresh_ciphertext = self._session_crypto.encrypt(refresh_material)
            refresh_key_version = self._session_crypto.current_key_version

        payload = {
            "p_user_id": user_id,
            "p_session_handle_hash": handle_hash,
            "p_created_at": _to_iso(created_at),
            "p_idle_expires_at": _to_iso(idle_expires_at),
            "p_absolute_expires_at": _to_iso(absolute_expires_at),
            "p_remember_me": bool(data.remember_me),
            "p_user_agent": str(data.user_agent or "")[:512] or None,
            "p_client_metadata": data.client_metadata or {},
            "p_rotation_parent_id": str(data.rotation_parent_id or "") or None,
            "p_refresh_material_encrypted": refresh_ciphertext,
            "p_refresh_material_key_version": refresh_key_version,
            "p_max_active_sessions": int(self._policy.max_active_sessions),
        }

        row = self._rpc("app_sessions_create", payload)
        record = _record_from_row(row)

        # Opportunistic retention cleanup per approved policy.
        self.cleanup_expired(now=created_at)

        return CreatedSession(raw_handle=raw_handle, record=record)

    def get_session_by_handle(self, raw_handle: str, *, now: Optional[datetime] = None) -> SessionLookupResult:
        text = str(raw_handle or "").strip()
        if not text:
            return SessionLookupResult(status=SessionLookupStatus.MALFORMED)

        handle_hash = self.hash_session_handle(text)
        row = self._select_single_by_hash(handle_hash)
        if row is None:
            return SessionLookupResult(status=SessionLookupStatus.MISSING)

        record = _record_from_row(row)
        status = self._classify_record(record, now=now)
        if status != SessionLookupStatus.VALID:
            return SessionLookupResult(status=status, record=record)

        self.touch_last_seen(record.id, now=now)
        return SessionLookupResult(status=SessionLookupStatus.VALID, record=record)

    def get_refresh_material_for_handle(self, raw_handle: str, *, now: Optional[datetime] = None) -> Optional[str]:
        lookup = self.get_session_by_handle(raw_handle, now=now)
        if lookup.status != SessionLookupStatus.VALID or lookup.record is None:
            return None

        row = self._select_single_by_hash(lookup.record.session_handle_hash)
        if row is None:
            return None

        ciphertext = str(row.get("refresh_material_encrypted") or "").strip()
        if not ciphertext:
            return None

        try:
            return self._session_crypto.decrypt(ciphertext)
        except SessionCryptoError as exc:
            raise SessionStoreError("stored refresh material could not be decrypted") from exc

    def touch_last_seen(self, session_id: str, *, now: Optional[datetime] = None) -> bool:
        sid = str(session_id or "").strip()
        if not sid:
            raise SessionStoreError("session_id is required")

        row = self._select_single_by_id(sid)
        if row is None:
            return False

        record = _record_from_row(row)
        now_value = _aware_utc(now) if now else _utc_now()
        if (now_value - record.last_seen_at).total_seconds() < self._policy.last_seen_throttle_seconds:
            return False

        endpoint = f"{self._supabase_url}/rest/v1/app_sessions"
        response = requests.patch(
            endpoint,
            headers=self._headers(prefer_representation=False),
            params={"id": f"eq.{sid}"},
            json={"last_seen_at": _to_iso(now_value)},
            timeout=self._timeout_seconds,
        )
        self._raise_for_status(response, "touch_last_seen failed")
        return True

    def revoke_session(self, session_id: str, *, reason: str = "USER_LOGOUT", now: Optional[datetime] = None) -> int:
        sid = str(session_id or "").strip()
        if not sid:
            raise SessionStoreError("session_id is required")

        now_value = _aware_utc(now) if now else _utc_now()
        return self._revoke_where(
            {"id": f"eq.{sid}", "revoked_at": "is.null"},
            reason=reason,
            now=now_value,
        )

    def revoke_all_sessions_for_user(
        self,
        user_id: str,
        *,
        reason: str = "SECURITY_EVENT",
        now: Optional[datetime] = None,
    ) -> int:
        uid = str(user_id or "").strip()
        if not uid:
            raise SessionStoreError("user_id is required")

        now_value = _aware_utc(now) if now else _utc_now()
        return self._revoke_where(
            {"user_id": f"eq.{uid}", "revoked_at": "is.null"},
            reason=reason,
            now=now_value,
        )

    def active_sessions_for_user(self, user_id: str, *, now: Optional[datetime] = None) -> List[SessionRecord]:
        uid = str(user_id or "").strip()
        if not uid:
            raise SessionStoreError("user_id is required")

        now_value = _aware_utc(now) if now else _utc_now()
        endpoint = f"{self._supabase_url}/rest/v1/app_sessions"
        params = {
            "select": "*",
            "user_id": f"eq.{uid}",
            "revoked_at": "is.null",
            "order": "created_at.asc",
            "idle_expires_at": f"gt.{_to_iso(now_value)}",
            "absolute_expires_at": f"gt.{_to_iso(now_value)}",
        }
        response = requests.get(endpoint, headers=self._headers(), params=params, timeout=self._timeout_seconds)
        self._raise_for_status(response, "active_sessions_for_user failed")
        rows = response.json() if response.content else []
        return [_record_from_row(row) for row in (rows or []) if isinstance(row, dict)]

    def count_active_sessions_for_user(self, user_id: str, *, now: Optional[datetime] = None) -> int:
        return len(self.active_sessions_for_user(user_id, now=now))

    def enforce_max_active_sessions(self, user_id: str, *, now: Optional[datetime] = None) -> int:
        uid = str(user_id or "").strip()
        if not uid:
            raise SessionStoreError("user_id is required")

        active = self.active_sessions_for_user(uid, now=now)
        overflow = len(active) - int(self._policy.max_active_sessions)
        if overflow <= 0:
            return 0

        revoked = 0
        for record in active[:overflow]:
            revoked += self.revoke_session(record.id, reason="MAX_CONCURRENT_LIMIT", now=now)
        return revoked

    def rotate_session_handle(self, session_id: str, *, now: Optional[datetime] = None) -> CreatedSession:
        sid = str(session_id or "").strip()
        if not sid:
            raise SessionStoreError("session_id is required")

        row = self._select_single_by_id(sid)
        if row is None:
            raise SessionStoreError("session not found")

        current = _record_from_row(row)
        status = self._classify_record(current, now=now)
        if status != SessionLookupStatus.VALID:
            raise SessionStoreError("cannot rotate a non-valid session")

        created = self.create_session(
            SessionCreationInput(
                user_id=current.user_id,
                remember_me=current.remember_me,
                user_agent=current.user_agent,
                client_metadata=current.client_metadata,
                refresh_material=self.get_refresh_material_by_session_id(sid) or "",
                created_at=now,
                rotation_parent_id=current.id,
            )
        )

        endpoint = f"{self._supabase_url}/rest/v1/app_sessions"
        response = requests.patch(
            endpoint,
            headers=self._headers(prefer_representation=False),
            params={"id": f"eq.{sid}"},
            json={
                "revoked_at": _to_iso(_aware_utc(now) if now else _utc_now()),
                "revocation_reason": "ROTATED",
                "replaced_by_session_id": created.record.id,
            },
            timeout=self._timeout_seconds,
        )
        self._raise_for_status(response, "rotate_session_handle failed")

        return created

    def get_refresh_material_by_session_id(self, session_id: str) -> Optional[str]:
        sid = str(session_id or "").strip()
        if not sid:
            raise SessionStoreError("session_id is required")

        row = self._select_single_by_id(sid)
        if row is None:
            return None

        ciphertext = str(row.get("refresh_material_encrypted") or "").strip()
        if not ciphertext:
            return None

        try:
            return self._session_crypto.decrypt(ciphertext)
        except SessionCryptoError as exc:
            raise SessionStoreError("stored refresh material could not be decrypted") from exc

    def cleanup_expired(self, *, now: Optional[datetime] = None, retention_days: int = 7) -> int:
        payload = {
            "p_now": _to_iso(_aware_utc(now) if now else _utc_now()),
            "p_retention": f"{int(retention_days)} days",
        }
        result = self._rpc("app_sessions_cleanup", payload)
        if isinstance(result, int):
            return result
        if isinstance(result, dict):
            # Some PostgREST versions return {"app_sessions_cleanup": N}
            for value in result.values():
                if isinstance(value, int):
                    return value
        return 0

    def _classify_record(self, record: SessionRecord, *, now: Optional[datetime] = None) -> SessionLookupStatus:
        now_value = _aware_utc(now) if now else _utc_now()

        if record.revoked_at is not None:
            return SessionLookupStatus.REVOKED
        if record.absolute_expires_at <= now_value:
            return SessionLookupStatus.ABSOLUTE_EXPIRED
        if record.idle_expires_at <= now_value:
            return SessionLookupStatus.IDLE_EXPIRED
        return SessionLookupStatus.VALID

    def _revoke_where(self, where_params: Dict[str, str], *, reason: str, now: datetime) -> int:
        endpoint = f"{self._supabase_url}/rest/v1/app_sessions"
        params = dict(where_params)
        params["select"] = "id"

        response = requests.patch(
            endpoint,
            headers=self._headers(prefer_representation=True),
            params=params,
            json={
                "revoked_at": _to_iso(now),
                "revocation_reason": str(reason or "REVOKED")[:128],
            },
            timeout=self._timeout_seconds,
        )
        self._raise_for_status(response, "revoke operation failed")
        rows = response.json() if response.content else []
        return len(rows or [])

    def _select_single_by_hash(self, handle_hash: str) -> Optional[Dict[str, Any]]:
        endpoint = f"{self._supabase_url}/rest/v1/app_sessions"
        response = requests.get(
            endpoint,
            headers=self._headers(),
            params={
                "select": "*",
                "session_handle_hash": f"eq.{handle_hash}",
                "limit": "1",
            },
            timeout=self._timeout_seconds,
        )
        self._raise_for_status(response, "session lookup failed")
        rows = response.json() if response.content else []
        if not rows:
            return None
        return rows[0]

    def _select_single_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        endpoint = f"{self._supabase_url}/rest/v1/app_sessions"
        response = requests.get(
            endpoint,
            headers=self._headers(),
            params={"select": "*", "id": f"eq.{session_id}", "limit": "1"},
            timeout=self._timeout_seconds,
        )
        self._raise_for_status(response, "session id lookup failed")
        rows = response.json() if response.content else []
        if not rows:
            return None
        return rows[0]

    def _rpc(self, function_name: str, payload: Dict[str, Any]) -> Any:
        endpoint = f"{self._supabase_url}/rest/v1/rpc/{function_name}"
        response = requests.post(
            endpoint,
            headers=self._headers(prefer_representation=True),
            json=payload,
            timeout=self._timeout_seconds,
        )
        self._raise_for_status(response, f"rpc {function_name} failed")

        if not response.content:
            return None

        data = response.json()
        if isinstance(data, list):
            return data[0] if data else None
        return data

    def _headers(self, *, prefer_representation: bool = True) -> Dict[str, str]:
        headers = {
            "apikey": self._service_role_key,
            "Authorization": f"Bearer {self._service_role_key}",
            "Content-Type": "application/json",
        }
        if prefer_representation:
            headers["Prefer"] = "return=representation"
        return headers

    def _raise_for_status(self, response: requests.Response, message: str) -> None:
        if int(response.status_code) < 400:
            return

        body = ""
        try:
            parsed = response.json()
            body = parsed.get("message") or parsed.get("hint") or parsed.get("code") or ""
        except Exception:
            body = ""

        if body:
            raise SessionStoreError(f"{message}: {body}")
        raise SessionStoreError(message)


def _secret_value(name: str, default: str = "") -> str:
    value = ""

    try:
        import streamlit as st  # type: ignore

        try:
            value = st.secrets.get(name, "")
        except Exception:
            value = ""
    except Exception:
        value = ""

    if value is None or str(value).strip() == "":
        value = os.environ.get(name, default)

    return str(value or default).strip()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _to_iso(value: datetime) -> str:
    return _aware_utc(value).isoformat()


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return _aware_utc(value)
    text = str(value or "").strip()
    if not text:
        return _utc_now()
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return _aware_utc(parsed)


def _record_from_row(row: Dict[str, Any]) -> SessionRecord:
    return SessionRecord(
        id=str(row.get("id") or ""),
        user_id=str(row.get("user_id") or ""),
        session_handle_hash=str(row.get("session_handle_hash") or ""),
        created_at=_parse_dt(row.get("created_at")),
        last_seen_at=_parse_dt(row.get("last_seen_at")),
        idle_expires_at=_parse_dt(row.get("idle_expires_at")),
        absolute_expires_at=_parse_dt(row.get("absolute_expires_at")),
        revoked_at=_parse_dt(row.get("revoked_at")) if row.get("revoked_at") else None,
        revocation_reason=str(row.get("revocation_reason") or ""),
        remember_me=bool(row.get("remember_me", False)),
        user_agent=str(row.get("user_agent") or ""),
        client_metadata=row.get("client_metadata") if isinstance(row.get("client_metadata"), dict) else {},
        rotation_parent_id=str(row.get("rotation_parent_id") or "") or None,
        replaced_by_session_id=str(row.get("replaced_by_session_id") or "") or None,
    )


def sanitize_session_store_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    return str(value)
