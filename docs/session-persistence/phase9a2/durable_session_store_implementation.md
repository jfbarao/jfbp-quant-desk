# Phase 9A.2 Durable Session Store Implementation

Status: Foundation implemented. No UI/login wiring in this phase.

## New Modules
- [core/session_store.py](core/session_store.py)
- [core/session_crypto.py](core/session_crypto.py)

## Session Store Capabilities Implemented
- Opaque handle generation (`token_urlsafe`) without persistence of raw handle.
- One-way handle hashing (`sha256`) for lookups and storage.
- Durable session creation via RPC function `app_sessions_create`.
- Status classification on lookup:
  - valid
  - missing
  - revoked
  - idle_expired
  - absolute_expired
  - malformed
- `last_seen_at` update throttling (default 300 seconds).
- Revoke current session by id.
- Revoke all sessions for user.
- Active session listing/count by user.
- Maximum active-session policy enforcement with deterministic oldest-session revocation.
- Safe session handle rotation with parent/replacement linkage.
- Opportunistic cleanup calls through `app_sessions_cleanup`.

## Policy Defaults Implemented
- Idle timeout: 24h
- Absolute timeout: 24h
- Remember Me absolute timeout: 30d
- Max active sessions: 5
- Last-seen throttle: 5 minutes

## Security Controls Implemented
- Raw session handle is never persisted.
- Raw refresh material is encrypted before persistence.
- Encrypted refresh material is only decrypted on explicit service call.
- Store operations use service-role scoped REST headers per instance call.
- No global cached authenticated user session object introduced.

## Intentionally Not Implemented in Phase 9A.2
- Cookie issuance/validation integration.
- Startup rehydration wiring.
- Login/logout UI changes.
- Stripe/subscription/entitlement changes.
- Removal of existing in-memory auth cache.
