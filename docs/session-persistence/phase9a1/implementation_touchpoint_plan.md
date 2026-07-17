# Phase 9A.1 Implementation Touchpoint Plan

Status: Planning only. No code/migration changes in this phase.

## Existing Functions Likely to Change

### app.py
- `enforce_app_login()`
  - Ensure startup path calls robust rehydration from durable store.
- Sidebar logout branch (current call to `supabase_logout()`)
  - Ensure cookie + durable session revocation semantics are enforced.

### pages/SaaS_Core.py
- `init_saas_state()`
  - Replace primary dependence on in-memory cache with durable-cookie rehydration.
- `_cache_authenticated_session(...)`
  - Demote/remove as primary persistence path.
- `_rehydrate_authenticated_session()`
  - Resolve cookie handle, validate durable row, restore Supabase session.
- `initialize_session(...)`
  - Create durable app session row and issue cookie handle.
- `set_authenticated_session(...)`
  - Integrate rotation/creation policy and robust error paths.
- `supabase_logout()`
  - Revoke current durable session and clear cookie.
- `clear_authenticated_session()`
  - Keep runtime cleanup; ensure no accidental durable-session deletion except via explicit revocation path.
- `supabase_reset_password(...)` and password update flow call sites
  - Trigger logout-all revocation policy on password-security events.

## New Functions Likely to Be Added (proposed names)
- `_session_handle_generate()`
- `_session_handle_hash(handle)`
- `_session_cookie_set(handle, ttl, remember_me)`
- `_session_cookie_get()`
- `_session_cookie_clear()`
- `_app_session_create(user_id, refresh_material, metadata)`
- `_app_session_resolve(handle)`
- `_app_session_touch(session_id)`
- `_app_session_revoke(session_id, reason)`
- `_app_session_revoke_all(user_id, reason)`
- `_app_session_cleanup_expired()`
- `_rehydrate_from_durable_session()`
- `_restore_supabase_session_from_refresh(...)`
- `_session_should_rotate(...)`
- `_session_rotate(...)`

## Proposed Helper Module
- `core/session_persistence.py` (proposed)
  - Cookie operations abstraction
  - Handle generation/hashing helpers
  - Session store CRUD wrappers
  - TTL/rotation/revocation policy helpers

## Proposed Future Migration Artifact (not created in this phase)
- A future migration file to introduce `app_auth_sessions` (name/number TBD by migration framework in repo).

## Proposed Future Dependency Changes (not applied now)
- Add one Streamlit-compatible cookie helper library.
- No dependency selected/installed in Phase 9A.1.

## Proposed Future Environment/Secret Names (not added now)
- `SESSION_HANDLE_SIGNING_KEY`
- `SESSION_REFRESH_ENCRYPTION_KEY`
- `SESSION_KEY_ID`
- `SESSION_IDLE_TIMEOUT_SECONDS`
- `SESSION_ABSOLUTE_TIMEOUT_SECONDS`
- `SESSION_MAX_CONCURRENT`
- Optional:
  - `SESSION_REMEMBER_ME_IDLE_TIMEOUT_SECONDS`
  - `SESSION_REMEMBER_ME_ABSOLUTE_TIMEOUT_SECONDS`

## Non-goals for Phase 9A.2 Implementation
- No changes to Stripe, Supabase billing, schema beyond session table.
- No production key material exposure in logs/docs.

## Touchpoint Risk Notes
- Avoid shared mutable global auth context from cached Supabase client.
- Ensure revocation checks happen before rehydration finalization.
- Keep failure mode fail-closed to Secure Access.
