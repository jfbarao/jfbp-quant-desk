# Phase 9A.2 Refresh Material Storage Decision

Status: Implemented decision for durable session foundation.

## Verified Supabase Auth API (installed)
Environment verification used configured Python environment and inspected installed source for:
- `SyncGoTrueClient.set_session(access_token, refresh_token)`
- `SyncGoTrueClient.refresh_session(refresh_token: Optional[str] = None)`

Observed behavior in installed source:
- `set_session` requires both arguments and refreshes when access token is expired.
- `refresh_session` requires an explicit refresh token if no in-memory session exists.
- After process restart, in-memory session is unavailable.

## Decision
Refresh material is required for reliable post-restart restoration. Therefore this phase stores refresh material server-side in encrypted form.

## Minimal Material Stored
- `refresh_material_encrypted`
- `refresh_material_key_version`

Not stored:
- raw session handle
- raw refresh token
- access token in durable app session table

## Security Controls Applied
- Encryption helper: [core/session_crypto.py](core/session_crypto.py)
- Secret name: `SESSION_ENCRYPTION_KEY`
- Key version tag: `SESSION_ENCRYPTION_KEY_VERSION`
- Versioned envelope format: `v1:<key_version>:<ciphertext>`
- No token logging in service/repository paths

## Why Access Token Was Not Stored
Access tokens are short-lived and are not sufficient as the only restart restoration artifact. Persisting only encrypted refresh material keeps stored auth material minimal while supporting restoration and rotation.
