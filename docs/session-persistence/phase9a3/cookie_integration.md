# Phase 9A.3 Cookie Integration

## Selected Library
- extra-streamlit-components (`stx.CookieManager`)

## Why Selected
- Latest release is recent relative to alternatives used in Phase 9A.1 analysis.
- Supports production-compatible cookie options via universal-cookie options.
- Works in Streamlit Cloud and localhost execution models.
- Smallest practical dependency that fits existing Streamlit architecture.

## Signed Opaque Cookie Design
- Cookie name: `opaque_session_handle`
- Cookie payload: signed opaque handle only
- Signature: HMAC-SHA256 (server key)
- Cookie flags:
  - `Secure=true` in production
  - `SameSite=Lax`
  - `Path=/`
- Browser cookie never includes access token, refresh token, user profile, or session object.

## Failure Handling
- Malformed/tampered cookie -> clear cookie, fail closed to Secure Access.
- Missing/expired/revoked durable row -> clear cookie, fail closed to Secure Access.
