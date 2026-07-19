# Sanitized Runtime Evidence (Phase 9B Final)

## Boundary
- app_env_runtime_command: development
- supabase_ref: qkqexvlprzjqjtsarqbz
- stripe_mode: test
- streamlit_url: http://localhost:8501
- production_supabase_touched: false
- production_stripe_touched: false

## Authorized identity
- email_hash: 226df0acbdf4
- user_id_prefix: 34037a2d

## Logout root cause
- fallback authenticated restore could leave saas_app_session_id unavailable
- logout revocation previously depended only on saas_app_session_id from Streamlit state
- local auth cleared while durable row could remain active

## Logout remediation
- resolve durable session id from session state, auth cache, or signed cookie lookup
- revoke durable row before clearing cookie/state
- persist app_session_id into auth cache after durable session creation
- repopulate app_session_id during fallback restore when possible

## Final live timeline highlights
- baseline before final retest: total_rows=7, active_rows=0, revoked_rows=7
- final-sequence login-created row: fd49f72b
- final-sequence logout revoked row: fd49f72b with USER_LOGOUT
- post-logout counts: total_rows=8, active_rows=0, revoked_rows=8
- restart after logout: Secure Access confirmed, active_rows=0
- login-again row: 3a344a6f active, later revoked with USER_LOGOUT
- recovery flow produced final active row: a83572cf
- final state: total_rows=11, active_rows=1, revoked_rows=10

## Final active session state
- active session_id_prefix: a83572cf
- active session_handle_hash_prefix: 9350e5782409
- active created_at: 2026-07-19T01:52:25.483179+00:00
- browser_fingerprint_prefix: afb4929eec55

## Recent session chronology tail
- c8a3acee revoked_at=2026-07-19T01:44:09.786136+00:00 reason=PHASE9B6_FINAL_BASELINE_RESET
- fd49f72b revoked_at=2026-07-19T01:45:16.199673+00:00 reason=USER_LOGOUT
- 3a344a6f revoked_at=2026-07-19T01:49:49.521704+00:00 reason=USER_LOGOUT
- e5961cc5 revoked_at=2026-07-19T01:51:37.667858+00:00 reason=USER_LOGOUT
- a83572cf active

## Provisioning and trial invariants
- profile_count: 1
- workspace_count: 1
- subscription_count: 1
- duplicate_provisioning_detected: false
- trial_start: 2026-07-18T23:47:36.258703+00:00
- trial_end: 2026-08-17T23:47:36.258703+00:00

## Manage Plan
- user confirmation: portal opened
- runtime stripe_mode remained test

## Automated verification
- py_compile: PASS
- pytest: 87 passed, 1 warning
- warning: gotrue deprecation warning from supabase package.

## Data handling
- No raw passwords, cookies, JWTs, token values, or full session handles recorded.
- All identities and session handles are sanitized prefixes only.
