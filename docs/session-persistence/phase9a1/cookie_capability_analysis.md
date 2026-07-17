# Phase 9A.1 Cookie Capability Analysis

Status: Analysis only. No dependency or code changes.

## Current Repository State
No Streamlit cookie helper library is currently installed in the environment:
- streamlit_cookies_manager: not installed
- extra_streamlit_components: not installed
- streamlit_js_eval: not installed
- streamlit_javascript: not installed

No cookie helper usage was found in repository Python sources.

## Required Cookie Role in Target Architecture
- Cookie stores only an opaque session handle (not raw Supabase refresh token).
- Durable auth state remains server-side in session store.

## Capability Requirements
- Secure flag support in production
- SameSite support (Lax recommended)
- Domain/path controls
- Expiration controls (`Max-Age`/`Expires`)
- Reliable read/write in Streamlit rerun model
- Safe behavior in localhost and production domains

## HttpOnly Feasibility in Pure Streamlit
- Pure Streamlit app code generally does not expose low-level response header control required for authoritative HttpOnly cookie setting.
- Many Streamlit cookie components are browser-side JavaScript bridges and therefore not HttpOnly.

Conclusion: In pure Streamlit without a reverse proxy edge function, HttpOnly may not be technically achievable.

## Cookie Implementation Options

### Option A: Streamlit cookie component (non-HttpOnly) + opaque handle
Pros:
- Minimal app architecture change
- Works with Streamlit Cloud deployment model

Cons:
- Cookie is script-readable; XSS hardening becomes critical

### Option B: External edge/proxy sets HttpOnly cookie
Pros:
- Strongest cookie security posture

Cons:
- Additional infrastructure and operational complexity
- Outside smallest-change scope

## Key Management and Rotation
- Add dedicated app secret for session handle signing/HMAC.
- Add optional encryption key if payload confidentiality is needed.
- Rotation policy:
  - active key id + previous key support window
  - re-sign on successful auth activity

## Domain Behavior

### Production
- Domain: Streamlit app host
- `Secure=true`
- `SameSite=Lax`
- `Path=/`

### Localhost
- `Secure=false` for local http dev only
- same handle format and validation logic

## Recommendation for Phase 9A.2
- Use a Streamlit-compatible cookie mechanism storing only opaque session handle.
- Do not store refresh token in cookie.
- Use server-side durable session table as source of truth for refresh material.
