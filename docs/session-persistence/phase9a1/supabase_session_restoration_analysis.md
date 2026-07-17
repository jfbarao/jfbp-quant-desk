# Phase 9A.1 Supabase Session Restoration Analysis

Status: Analysis only. No implementation changes.

## Installed Library Confirmation
- supabase: 2.15.3
- streamlit: 1.50.0

## Confirmed Auth Methods and Signatures
- `sign_in_with_password(credentials) -> AuthResponse`
- `sign_up(credentials) -> AuthResponse`
- `sign_out(options={'scope': 'global'}) -> None`
- `set_session(access_token, refresh_token) -> AuthResponse`
- `refresh_session(refresh_token: Optional[str] = None) -> AuthResponse`
- `get_session() -> Optional[Session]`
- `get_user(jwt: Optional[str] = None) -> Optional[UserResponse]`

## Confirmed vs Assumed Behavior

### Confirmed
- The client supports setting a session from `access_token + refresh_token`.
- The client supports explicit refresh via `refresh_session(...)`.
- Login response provides session material used by app code.

### Not Confirmed in Current Architecture
- Durable persistence of auth session across Streamlit process restarts.
- Automatic cross-instance restoration without app-managed durable store.

## Minimum Auth Material Needed After Streamlit Restart

### Requirement
To restore authenticated context after process restart, the app needs material sufficient to recover or recreate valid session state.

### Practical Minimum
- A valid refresh token (or equivalent secure server-side reference to one)
- User/session linkage metadata (user id, session id, expiry metadata) for revocation and policy checks

### Why Access Token Alone Is Insufficient
- Access tokens are short-lived and cannot reliably survive longer inactivity or restart windows.
- Long-term restoration requires refresh capability.

## Restoration Strategy Implications

### If no refresh token is retained anywhere durable
- Session restoration after restart is not reliable.
- User must re-authenticate.

### If refresh token is retained securely server-side
- App can restore session by calling `set_session` and/or `refresh_session`.
- Durable restoration can survive app restarts and multi-instance routing.

## Security Implications for Refresh Material
- Refresh token should not be stored in plaintext client-side cookie.
- Preferred: store opaque session handle in cookie; keep refresh token server-side only.
- If refresh token is persisted server-side, it should be encrypted at rest (application-layer envelope encryption) and revocable.

## Current Gap in Repository
- No durable server-side app session table exists.
- Existing in-memory cache is not restart-safe.
- Therefore current design cannot guarantee restoration after Streamlit Cloud restart/redeploy.

## Analysis Conclusion
Supabase Python client capabilities are sufficient to support robust restoration, but only if the app persists refresh-capable session material durably and securely outside process memory.
