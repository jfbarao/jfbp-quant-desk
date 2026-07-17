# Phase 9A.1 Decision Summary

Status: Approved design recommendation candidate. No implementation in this phase.

## Recommended Architecture
- Supabase Auth remains identity source of truth.
- Add durable application session store in Supabase (`app_auth_sessions`, spec-level in this phase).
- Use opaque cookie session handle in browser.
- Use `st.session_state` only as active runtime cache.
- Do not use in-memory cache as primary persistence.

## Recommended Session Duration
- Sliding idle expiration: 12 hours
- Absolute maximum expiration: 30 days

## Fixed vs Sliding Expiration
- Recommended: Sliding + absolute cap

## Concurrent Session Policy
- Max active sessions per user: 5
- On overflow: revoke oldest active sessions

## Refresh Token Storage Requirement
- Required for robust post-restart restoration.
- Store server-side only, never in raw client cookie.
- Encrypt at rest (application-level encryption) if persisted.

## Cookie Library Recommendation
- Introduce one Streamlit-compatible cookie library in Phase 9A.2.
- Cookie payload should contain opaque handle only.
- In pure Streamlit, HttpOnly may not be feasible; compensate with opaque handle design + server-side checks.

## Root Cause Recap (from audit)
- Current persistence depends on process-local cache keyed by request fingerprint.
- This is not durable across Streamlit Cloud restarts/redeploys/multi-instance routing.

## Unresolved Risks or Blockers
1. Final cookie library selection and exact flag support behavior.
2. HttpOnly limitation in pure Streamlit (without external edge/proxy).
3. Final decision on refresh-material encryption approach and key rotation process.
4. Supabase client auth-state isolation strategy with cached client object.
5. Operational job strategy for expired session cleanup.

## Phase 9A.2 Readiness
- Ready to begin implementation planning and controlled coding after design review approval.
- Preconditions:
  - approve cookie library choice
  - approve session policy defaults
  - approve secret/key management approach
