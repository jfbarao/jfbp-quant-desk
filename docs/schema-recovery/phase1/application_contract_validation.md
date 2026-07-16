# Application Contract Validation (Phase 1)

## Scope
- Validated application read/write contracts for `user_profiles`, `subscriptions`, and `workspaces`.
- Sources:
  - `pages/SaaS_Core.py`
  - `pages/Admin_Control_Center.py`
  - `runtime_state/schema_recovery_phase0_20260715_203519/application_table_contracts.json`

## Cross-Validation Checks

### 1) Every application read has a corresponding field
Result: PASS

- `user_profiles` reads are covered in the canonical catalog:
  - identity/entitlement: `user_id`, `email`, `full_name`, `plan`, `account_status`, `role`, `status`, `subscription_status`
  - trial lifecycle: `trial_start`, `trial_end`, `trial_notification_sent`, `trial_notification_sent_at`, `trial_started_at`
  - telemetry/fraud: `signup_ip`, `signup_country`, `signup_city`, `city`, `device_id`, `device_fingerprint`, `user_agent`, `browser`, `operating_system`, `risk_score`, `fraud_flags`, `last_ip_activity`, `first_login_at`, `last_login_at`, `last_login_ip`, `last_login_country`, `last_login_city`, `total_logins`, `trial_whitelisted`, `trial_ignored`, `trial_blocked`, `trial_notes`, `last_sign_in_at`
  - billing metadata: `stripe_customer_id`, `stripe_subscription_id`

- `subscriptions` reads are covered:
  - `user_id`, `email`, `plan`, `status`, `stripe_customer_id`, `stripe_subscription_id`, `current_period_end`, `trial_start`, `trial_end`, `created_at`

- `workspaces` reads are covered:
  - `user_id` (existence check), and implicit row materialization with `id`, `workspace_name`, `created_at`

### 2) Every application write has a corresponding field
Result: PASS

- `user_profiles` write payloads in onboarding/login/admin repair are covered.
- `subscriptions` write payloads (`user_id`, `plan`, `status`; optional email-based update path) are covered.
- `workspaces` write payload (`user_id`, `workspace_name`) is covered.

### 3) Every production-visible field is represented
Result: PASS

All Source A fields from `openapi_tables_extract.json` are represented in the canonical catalog.

### 4) Duplicate names are resolved
Result: PASS WITH NORMALIZATION NOTES

- Status naming:
  - `user_profiles.account_status` is canonical account state.
  - `subscriptions.status` is canonical subscription state.
  - `user_profiles.status` and `user_profiles.subscription_status` are optional profile-level fallbacks (Tier 2).

### 5) Conflicting data types are identified
Result: PARTIAL (DOCUMENTED)

- Source A has authoritative SQL types for Tier 1 fields only.
- Tier 2 fields lack authoritative DB type metadata in available sources.
- Tier 2 types are recorded as `unknown` or `unknown (x-like)` with Medium/High confidence based on runtime usage patterns.

### 6) Conflicting defaults are identified
Result: PARTIAL (DOCUMENTED)

- Source A defaults known:
  - `id` -> `gen_random_uuid()`
  - `created_at` -> `now()`
- Tier 2 defaults are app-level fallbacks only (for example `trial_attempts=1`, `risk_score=0`, `trial_whitelisted=false`), not proven DB defaults.

### 7) Conflicting nullability assumptions are identified
Result: PARTIAL (DOCUMENTED)

- Source A required list indicates non-null only for `id` and `created_at` in Swagger-visible contract.
- Application behavior assumes practical presence of additional columns and values (especially `user_id`, `email`, `trial_start`, `trial_end`).
- Nullability for Tier 2 remains unresolved without direct DB metadata channel.

## Validation Summary
- Contract coverage achieved for all known read/write paths.
- No orphaned read/write fields detected in current app code.
- Remaining blockers are metadata completeness (types/defaults/nullability/constraints for Tier 2 and advanced objects).
