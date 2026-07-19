# Phase 9C Deployment and Rollback Runbook

Date: 2026-07-18
Scope: Authentication and durable-session production deployment sequence
Repository: /Users/josepereira/rs_clean
Approved baseline commit: 13063e44e13e423ad608882a04b8e5d0bc2cbe2c

## 1. Pre-Deployment Checklist

1. Confirm deployment source commit is approved by release owner.
2. Snapshot production database according to Supabase operational policy.
3. Verify production secrets/config contract from `production_configuration_contract.md`.
4. Verify `SUPABASE_EMAIL_REDIRECT_TO` points to production HTTPS app host.
5. Verify password recovery redirect destination is correct for production UX.
6. Verify Stripe is configured for live mode and live keys.
7. Verify `STRIPE_BILLING_PORTAL_URL` is configured for production.
8. Verify migration status for `supabase/migrations/20260717_140000_create_app_sessions.sql`.
9. Assign rollback owner and go/no-go decision owner.
10. Confirm production domain, TLS certificate, and HTTPS reachability.

## 2. Deployment Order

1. Apply database migration for `public.app_sessions` and RPC functions.
2. Apply production secrets/environment variables.
3. Deploy application artifact.
4. Perform startup health check and validate environment gate passed.
5. Execute controlled authentication smoke test.
6. Validate durable-session lifecycle behavior.
7. Validate password recovery callback flow.
8. Validate logout current-session revocation behavior.
9. Validate Stripe Manage Plan portal and checkout boundary behavior.

Rationale:
- Durable session creation depends on migration and service-role REST/RPC.
- Startup environment validation now fails closed when boundary keys are missing/mismatched.

## 3. Production Smoke Test (Authorized Operator Only)

Use an already-approved production account only. Do not create new production test users during this phase.

1. Login (or approved signup + confirmation callback path).
2. Confirm canonical provisioning record integrity (no duplicates).
3. Verify exactly one active durable session for current browser.
4. Refresh browser and confirm authenticated restore.
5. Restart browser and confirm authenticated restore.
6. Logout and verify durable session is revoked with `USER_LOGOUT`.
7. Refresh after logout and verify no auth restoration.
8. Login again and confirm exact-one-active-session invariant.
9. Execute password recovery flow and verify old password fails/new password succeeds.
10. Click Manage Plan and verify expected Stripe production portal behavior.

## 4. Rollback Strategy

### Application rollback

1. Roll back app deployment to prior stable artifact.
2. Keep production secrets aligned with rolled-back artifact requirements.
3. If required, temporarily disable login UI while reconciling key or schema mismatch.

### Schema rollback

- Preferred approach: forward-fix.
- Avoid destructive rollback of `public.app_sessions` in a live environment.
- If migration rollback is mandatory, require explicit DBA sign-off and data-preservation plan.

### Session/key incident handling

- If `SESSION_COOKIE_SIGNING_KEY` changes unexpectedly:
  - Existing cookies become invalid.
  - Users will be required to re-authenticate.
- If `SESSION_ENCRYPTION_KEY` cannot decrypt stored refresh material:
  - Recovery via retained versioned keys if configured.
  - Otherwise force fresh login and consider temporary login pause for controlled recovery.

### Data preservation requirements

- Preserve auth users and canonical profile/workspace/subscription records.
- Preserve session history rows unless approved retention policy cleanup applies.

## 5. Halt Conditions

Stop rollout immediately if any of the following occurs:

1. Startup boundary validation fails.
2. App starts with missing critical production keys.
3. Durable session rows are not created or not revoked on logout.
4. Multiple unexpected active sessions are created for one browser.
5. Recovery callback fails repeatedly with valid inputs.
6. Stripe live/test boundary mismatch is detected.
7. Canonical provisioning duplication appears.

## 6. Go/No-Go Criteria

Go when all are true:

1. Startup environment validation passes.
2. Migration applied successfully and contracts verified.
3. Smoke test lifecycle passes end-to-end.
4. Logout revocation and post-logout non-restore are confirmed.
5. Password recovery flow confirmed.
6. Stripe portal behavior confirmed under production configuration.
7. No secret leakage in UI/log diagnostics.

No-Go when any criterion fails.

## 7. Operational Signals to Watch

1. Authentication failure rate spikes.
2. SessionStore REST/RPC failure spikes.
3. Repeated callback replay consumption attempts.
4. Logout revocation failure diagnostics.
5. Unexpected active-session counts per user/browser.
6. Provisioning duplicate detection.
7. Stripe portal/checkout failures.
