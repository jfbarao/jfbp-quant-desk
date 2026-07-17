# Phase 9A.2 Decision Summary

## Table Name
- `public.app_sessions`

## Migration File
- [supabase/migrations/20260717_140000_create_app_sessions.sql](supabase/migrations/20260717_140000_create_app_sessions.sql)

## Refresh Material Storage
- Stored: yes
- Why: verified installed Supabase auth behavior requires refresh token capability for reliable post-restart session restoration when no in-memory session exists.

## Encryption Approach
- Module: [core/session_crypto.py](core/session_crypto.py)
- Algorithm: Fernet authenticated encryption (cryptography package already present in requirements)
- Secret: `SESSION_ENCRYPTION_KEY`
- Version tag: `SESSION_ENCRYPTION_KEY_VERSION`
- Envelope format: `v1:<key_version>:<ciphertext>`

## Concurrent Session Enforcement
- Max active sessions: 5
- Enforcement path: `public.app_sessions_create(...)` function
- Concurrency behavior: transaction-level per-user advisory lock + deterministic oldest active session revocation

## Cleanup / Retention Behavior
- Opportunistic cleanup only (no cron in this phase)
- Function: `public.app_sessions_cleanup(...)`
- Current retention default: 7 days for revoked/expired rows

## Remaining Risks
- Security-definer function privileges and search path must be validated in staging DB prior to production migration run.
- Key rotation orchestration is not automated yet.
- Runtime app still uses existing auth wiring until Phase 9A.3 integration.

## Phase 9A.3 Readiness
- Ready for integration phase, contingent on staging migration validation and final review of DB grants/function permissions.
