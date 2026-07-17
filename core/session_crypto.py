from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass
from typing import Optional, Tuple

from cryptography.fernet import Fernet, InvalidToken


class SessionCryptoError(RuntimeError):
    """Raised when session refresh-material encryption/decryption fails."""


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


def _fernet_key_from_secret(raw_secret: str) -> bytes:
    secret = str(raw_secret or "").strip()
    if not secret:
        raise SessionCryptoError("SESSION_ENCRYPTION_KEY is required")

    # Accept canonical Fernet keys directly.
    try:
        decoded = base64.urlsafe_b64decode(secret.encode("utf-8"))
        if len(decoded) == 32:
            return secret.encode("utf-8")
    except Exception:
        pass

    # Deterministic derivation for non-Fernet inputs keeps runtime strict while
    # still allowing operators to provide sufficiently random key material.
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


@dataclass(frozen=True)
class CiphertextEnvelope:
    version: str
    key_version: str
    ciphertext: str


class SessionCrypto:
    """Versioned authenticated encryption for refresh material."""

    CIPHERTEXT_VERSION = "v1"

    def __init__(
        self,
        *,
        current_key_version: Optional[str] = None,
        current_key: Optional[str] = None,
    ) -> None:
        self._current_key_version = (
            str(current_key_version or _secret_value("SESSION_ENCRYPTION_KEY_VERSION", "v1")).strip() or "v1"
        )

        raw_current = current_key if current_key is not None else _secret_value("SESSION_ENCRYPTION_KEY", "")
        self._current_fernet = Fernet(_fernet_key_from_secret(raw_current))

    @property
    def current_key_version(self) -> str:
        return self._current_key_version

    def encrypt(self, plaintext: str) -> str:
        value = str(plaintext or "")
        if not value:
            raise SessionCryptoError("refresh material cannot be empty")

        token = self._current_fernet.encrypt(value.encode("utf-8")).decode("utf-8")
        return f"{self.CIPHERTEXT_VERSION}:{self._current_key_version}:{token}"

    def decrypt(self, envelope_text: str) -> str:
        envelope = self._parse_envelope(envelope_text)
        fernet = self._fernet_for_version(envelope.key_version)

        try:
            plaintext = fernet.decrypt(envelope.ciphertext.encode("utf-8"))
            return plaintext.decode("utf-8")
        except InvalidToken as exc:
            raise SessionCryptoError("failed to decrypt refresh material") from exc
        except Exception as exc:
            raise SessionCryptoError("invalid encrypted refresh material") from exc

    def _parse_envelope(self, envelope_text: str) -> CiphertextEnvelope:
        raw = str(envelope_text or "").strip()
        if not raw:
            raise SessionCryptoError("encrypted refresh material is missing")

        parts = raw.split(":", 2)
        if len(parts) != 3:
            raise SessionCryptoError("encrypted refresh material format is invalid")

        version, key_version, ciphertext = (parts[0].strip(), parts[1].strip(), parts[2].strip())
        if version != self.CIPHERTEXT_VERSION:
            raise SessionCryptoError("unsupported encrypted refresh material version")
        if not key_version:
            raise SessionCryptoError("encrypted refresh material key version is missing")
        if not ciphertext:
            raise SessionCryptoError("encrypted refresh material ciphertext is missing")

        return CiphertextEnvelope(version=version, key_version=key_version, ciphertext=ciphertext)

    def _fernet_for_version(self, key_version: str) -> Fernet:
        if key_version == self._current_key_version:
            return self._current_fernet

        env_name = f"SESSION_ENCRYPTION_KEY_{key_version.upper()}"
        versioned_secret = _secret_value(env_name, "")
        if not versioned_secret:
            raise SessionCryptoError("missing encryption key for ciphertext key version")

        return Fernet(_fernet_key_from_secret(versioned_secret))


def split_ciphertext_envelope(envelope_text: str) -> Tuple[str, str]:
    parts = str(envelope_text or "").split(":", 2)
    if len(parts) != 3:
        raise SessionCryptoError("encrypted refresh material format is invalid")
    return parts[1], parts[2]
