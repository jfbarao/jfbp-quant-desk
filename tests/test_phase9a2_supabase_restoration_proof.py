from __future__ import annotations

import os
import secrets
import tomllib
from pathlib import Path

import pytest
import requests
from supabase import create_client

from core.session_crypto import SessionCrypto, SessionCryptoError


def _secret_value(name: str, default: str = "") -> str:
    value = str(os.environ.get(name, "") or "").strip()
    if value:
        return value

    secrets_file = Path(".streamlit/secrets.toml")
    if secrets_file.exists():
        data = tomllib.loads(secrets_file.read_text(encoding="utf-8"))
        return str(data.get(name, default) or default).strip()

    return str(default or "").strip()


def _admin_headers(service_key: str) -> dict[str, str]:
    return {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }


def _create_temp_user(url: str, service_key: str, email: str, password: str) -> str:
    endpoint = f"{url.rstrip('/')}/auth/v1/admin/users"
    payload = {
        "email": email,
        "password": password,
        "email_confirm": True,
        "user_metadata": {"phase": "9A2-restoration-proof"},
    }
    response = requests.post(endpoint, headers=_admin_headers(service_key), json=payload, timeout=20)
    response.raise_for_status()
    data = response.json() or {}
    user_id = str(data.get("id") or "").strip()
    assert user_id, "Temp user creation did not return id"
    return user_id


def _delete_temp_user(url: str, service_key: str, user_id: str) -> None:
    if not user_id:
        return

    endpoint = f"{url.rstrip('/')}/auth/v1/admin/users/{user_id}"
    response = requests.delete(endpoint, headers=_admin_headers(service_key), timeout=20)
    response.raise_for_status()


@pytest.mark.live
def test_supabase_refresh_only_restoration_proof():
    """Live proof that refresh-material-only restoration works with installed client."""
    supabase_url = _secret_value("SUPABASE_URL", "")
    anon_key = _secret_value("SUPABASE_ANON_KEY", "")
    service_key = _secret_value("SUPABASE_SERVICE_ROLE_KEY", "")

    assert supabase_url, "SUPABASE_URL is required"
    assert anon_key, "SUPABASE_ANON_KEY is required"
    assert service_key, "SUPABASE_SERVICE_ROLE_KEY is required"

    temp_email = f"phase9a2-proof-{secrets.token_hex(8)}@example.com"
    temp_password = f"Proof-{secrets.token_urlsafe(18)}-Aa1!"

    temp_user_id = ""

    try:
        temp_user_id = _create_temp_user(supabase_url, service_key, temp_email, temp_password)

        # 1-2) brand-new client and normal authentication
        client1 = create_client(supabase_url, anon_key)
        auth_response = client1.auth.sign_in_with_password(
            {
                "email": temp_email,
                "password": temp_password,
            }
        )
        assert auth_response is not None
        assert auth_response.session is not None

        # 3) capture only minimum material (refresh token) and encrypt it for server-side storage simulation
        initial_refresh_material = str(getattr(auth_response.session, "refresh_token", "") or "").strip()
        assert initial_refresh_material, "refresh material missing from authenticated session"

        session_crypto = SessionCrypto(current_key="phase9a2-proof-encryption-key-material")
        encrypted_refresh_material = session_crypto.encrypt(initial_refresh_material)

        # 4) destroy first client instance + plain refresh material reference
        del auth_response
        del client1
        initial_refresh_material = ""

        # 5-6) brand-new client, restore using only stored refresh material
        client2 = create_client(supabase_url, anon_key)
        restored_refresh_material = session_crypto.decrypt(encrypted_refresh_material)
        restored_response = client2.auth.refresh_session(restored_refresh_material)
        assert restored_response is not None
        assert restored_response.session is not None

        # 7) verify required auth operations
        got_user = client2.auth.get_user()
        assert getattr(got_user, "user", None) is not None
        assert str(getattr(got_user.user, "id", "") or "") == temp_user_id

        got_session = client2.auth.get_session()
        assert got_session is not None

        refreshed_again = client2.auth.refresh_session()
        assert refreshed_again is not None
        assert refreshed_again.session is not None

        active_session = client2.auth.get_session()
        access_token = str(getattr(active_session, "access_token", "") or "").strip()
        assert access_token

        auth_request = requests.get(
            f"{supabase_url.rstrip('/')}/auth/v1/user",
            headers={
                "apikey": anon_key,
                "Authorization": f"Bearer {access_token}",
            },
            timeout=20,
        )
        auth_request.raise_for_status()
        auth_data = auth_request.json() or {}
        assert str(auth_data.get("id") or "") == temp_user_id

        active_refresh_material = str(getattr(active_session, "refresh_token", "") or "").strip()
        assert active_refresh_material

        # 8a) corrupted refresh material must fail
        corrupted_refresh = active_refresh_material[:-3] + "bad"
        client_corrupt = create_client(supabase_url, anon_key)
        with pytest.raises(Exception):
            client_corrupt.auth.refresh_session(corrupted_refresh)

        # 8b) revoked refresh material must fail
        client2.auth.sign_out({"scope": "global"})
        client_revoked = create_client(supabase_url, anon_key)
        with pytest.raises(Exception):
            client_revoked.auth.refresh_session(active_refresh_material)

        # 8c) wrong encryption key must fail decryption
        wrong_key_crypto = SessionCrypto(current_key="phase9a2-proof-wrong-key")
        with pytest.raises(SessionCryptoError):
            wrong_key_crypto.decrypt(encrypted_refresh_material)

    finally:
        _delete_temp_user(supabase_url, service_key, temp_user_id)
