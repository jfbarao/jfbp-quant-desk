# Phase 9A.3 Authentication Rehydration

## Startup Flow
1. `init_saas_state()` invokes `_rehydrate_authenticated_session()` when user is not already authenticated.
2. Rehydration reads signed opaque cookie.
3. Signature is validated server-side.
4. Session store resolves durable app session by handle hash.
5. Session status validated (valid/revoked/expired/missing/malformed).
6. Refresh material is read server-side and used to call Supabase `refresh_session()`.
7. On success, `st.session_state` is rebuilt (`saas_logged_in`, `saas_auth_session`, `saas_user`).
8. Legacy in-memory cache remains secondary fallback.

## Login Flow Integration
- Existing successful auth path now also:
  - creates durable app session row,
  - stores encrypted refresh material server-side,
  - issues signed opaque session cookie,
  - preserves existing onboarding and metadata behavior.

## Logout Flow Integration
- Current-session logout revokes current durable app session id and clears cookie.
- `supabase_logout_all()` revokes all user sessions in store and clears local state.
