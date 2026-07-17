# Phase 9A.1 Current Auth Lifecycle Audit

Status: Design-time audit only. No code changes.

## Audited Sources
- app.py
- pages/SaaS_Core.py
- core/environment_validation.py (boundary gating context)

## High-Level Runtime Flow
1. App startup calls environment boundary validation.
2. If boundary passes, app enforces login before protected pages.
3. SaaS auth panel handles Login/Create Account/Reset Password.
4. Successful login stores session/user in Streamlit session state.
5. Rehydration attempts to restore auth from an in-memory cache keyed by request fingerprint.

## Detailed Lifecycle Trace

### A. Boundary Gate (pre-auth)
- app.py `app()` calls `validate_runtime_environment()`.
- On failure, app stops before auth UI is usable.

### B. Login Gate
- app.py `enforce_app_login()` calls `init_saas_state()` then checks `get_current_user()`.
- If no user: render front door and stop.

### C. State Initialization
- pages/SaaS_Core.py `init_saas_state()` initializes:
  - `saas_logged_in`
  - `saas_user`
  - `saas_auth_session`
  - onboarding/debug fields
- If not logged in, calls `_rehydrate_authenticated_session()`.

### D. Login Action
- `supabase_login(email, password)` calls `client.auth.sign_in_with_password(...)`.
- `set_authenticated_session(auth_response)` drives post-login setup:
  - `authenticate_user()` extracts user/session/token presence.
  - `initialize_session()` writes `saas_auth_session`, `saas_user`, `saas_logged_in`.
  - `_cache_authenticated_session(session_payload)` caches payload in memory.
  - onboarding/profile/subscription/workspace checks run.

### E. Rehydration Action
- `_rehydrate_authenticated_session()`:
  - If already logged in with valid user object, returns true.
  - Builds `_browser_auth_cache_key()` from request headers/IP/UA.
  - Reads payload from `_auth_session_cache()`.
  - Applies payload using `_apply_auth_session_to_client(client, session_payload)`.
  - Reads current auth user from Supabase and rebuilds `saas_user`.

### F. Logout/Cleanup
- `supabase_logout()` calls `client.auth.sign_out()` then `clear_authenticated_session()`.
- `clear_authenticated_session()` clears:
  - cached auth payload
  - active page cache
  - checkout cache
  - session-state auth/user flags and debug state

## Current Persistence Mechanisms (Observed)

### Confirmed
- Primary active cache: `st.session_state`
- Secondary persistence: `_auth_session_cache()` (`@st.cache_resource`) in-memory dictionary

### Not Present
- No secure cookie-backed session handle persistence
- No browser localStorage/sessionStorage token persistence
- No URL query token persistence
- No durable server-side session table for app sessions

## Current Failure Mode Relevant to Production Reload
- Rehydration depends on in-memory cache and a fingerprint key derived from request metadata.
- On Streamlit Cloud restart/redeploy/process migration/multi-instance routing, in-memory cache can be unavailable.
- Header/IP-derived key can vary, breaking lookup.
- Result: authenticated user returns to Secure Access after refresh.

## Confirmed Supabase Python Auth API Surface (installed `supabase==2.15.3`)
- `sign_in_with_password(credentials) -> AuthResponse`
- `sign_up(credentials) -> AuthResponse`
- `sign_out(options={'scope': 'global'})`
- `set_session(access_token, refresh_token) -> AuthResponse`
- `refresh_session(refresh_token: Optional[str] = None) -> AuthResponse`
- `get_session() -> Optional[Session]`
- `get_user(jwt: Optional[str] = None) -> Optional[UserResponse]`
- `update_user(attributes, options={}) -> UserResponse`

## Audit Conclusion
Current auth lifecycle is logically correct for single-process continuity but not production-grade durable for browser refresh under cloud runtime churn. Durable server-side session persistence with cookie session handle is required to meet production session persistence goals.
