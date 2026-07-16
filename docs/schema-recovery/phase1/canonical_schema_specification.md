# Canonical Schema Specification (Phase 1, No SQL)

## Objective
Definitive schema specification for `user_profiles`, `subscriptions`, and `workspaces`, reconciling Source A (production-visible), Source B (application contracts), and Source C (historical repository artifacts).

## Evidence Priority
1. Source A (highest):
- `runtime_state/prod_schema_export_zqzujesufquifrtqnanb_20260716_031915/openapi_tables_extract.json`
- `runtime_state/prod_schema_export_zqzujesufquifrtqnanb_20260716_031915/production_tables_ddl_export.sql`

2. Source B:
- `runtime_state/schema_recovery_phase0_20260715_203519/application_table_contracts.json`
- `pages/SaaS_Core.py`
- `pages/Admin_Control_Center.py`

3. Source C (supporting only):
- `runtime_state/schema_recovery_dev_qkqexvlprzjqjtsarqbz_20260716_030658/base_schema_draft.sql`
- `runtime_state/schema_recovery_20260715_user_profiles/user_profiles_schema_summary.json`
- `runtime_state/schema_recovery_phase0_20260715_203519/repository_schema_inventory.json`

## Classification Rules
- Tier 1: Verified Production (present in Source A)
- Tier 2: Verified Application Contract (not in Source A, but required/used by app code)
- Tier 3: Historical (only Source C)
- Tier 4: Unverified (cannot be proven)

## Table: user_profiles

### Tier 1 (Verified Production)
- `id` | type `uuid` | nullable `false` | default `gen_random_uuid()` | confidence High | runtime Yes | admin Yes | onboarding Yes
  - reads: `pages/SaaS_Core.py:_profile_row_for_auth_user`, `pages/Admin_Control_Center.py:load_profiles`
  - writes: db default
  - evidence: Source A openapi + DDL
- `created_at` | type `timestamp with time zone` | nullable `false` | default `now()` | confidence High | runtime No | admin Yes | onboarding No
  - reads: admin ordering + onboarding notifications
  - writes: db default
  - evidence: Source A openapi + DDL
- `email` | type `text` | nullable `true` | default null | confidence High | runtime Yes | admin Yes | onboarding Yes
  - reads: profile/subscription fallback lookups
  - writes: onboarding + admin repair
  - evidence: Source A + Source B
- `full_name` | type `text` | nullable `true` | default null | confidence High | runtime Yes | admin Yes | onboarding Yes
  - reads: session identity/admin directory
  - writes: onboarding + admin repair
  - evidence: Source A + Source B
- `plan` | type `text` | nullable `true` | default null | confidence High | runtime Yes | admin Yes | onboarding Yes
  - reads: access control/admin reporting
  - writes: onboarding + admin plan actions
  - evidence: Source A + Source B
- `account_status` | type `text` | nullable `true` | default null | confidence High | runtime Yes | admin Yes | onboarding Yes
  - reads: account open/closed state
  - writes: onboarding + admin account actions
  - evidence: Source A + Source B
- `trial_start` | type `timestamp with time zone` | nullable `true` | default null | confidence High | runtime Yes | admin Yes | onboarding Yes
  - reads: provisioning-required logic
  - writes: onboarding + trial repair
  - evidence: Source A + Source B
- `trial_end` | type `timestamp with time zone` | nullable `true` | default null | confidence High | runtime Yes | admin Yes | onboarding Yes
  - reads: trial expiry/state
  - writes: onboarding + trial repair
  - evidence: Source A + Source B
- `user_id` | type `uuid` | nullable `true` | default null | confidence High | runtime Yes | admin Yes | onboarding Yes
  - reads: primary logical lookup key
  - writes: onboarding + admin repair
  - evidence: Source A + Source B
- `stripe_customer_id` | type `text` | nullable `true` | default null | confidence High | runtime No | admin Yes | onboarding No
  - reads: billing mapping
  - writes: none in current app
  - evidence: Source A + Source B
- `stripe_subscription_id` | type `text` | nullable `true` | default null | confidence High | runtime No | admin Yes | onboarding No
  - reads: billing mapping
  - writes: none in current app
  - evidence: Source A + Source B

### Tier 2 (Verified Application Contract)
- `trial_notification_sent` | type unknown | nullable unknown | default app false | confidence High | runtime No | admin No | onboarding Yes
- `trial_notification_sent_at` | type unknown timestamp-like | nullable assumed true | default null | confidence Medium | runtime No | admin No | onboarding Yes
- `signup_ip` | type unknown text-like | nullable assumed true | default null | confidence High | runtime Yes | admin Yes | onboarding Yes
- `signup_country` | type unknown text-like | nullable assumed true | default null | confidence High | runtime No | admin Yes | onboarding Yes
- `signup_city` | type unknown text-like | nullable assumed true | default null | confidence High | runtime No | admin Yes | onboarding Yes
- `city` | type unknown text-like | nullable assumed true | default null | confidence High | runtime No | admin Yes | onboarding Yes
- `device_id` | type unknown text-like | nullable assumed true | default app fallback | confidence High | runtime Yes | admin Yes | onboarding Yes
- `device_fingerprint` | type unknown text-like | nullable assumed true | default app fallback | confidence High | runtime Yes | admin Yes | onboarding Yes
- `user_agent` | type unknown text-like | nullable assumed true | default null | confidence High | runtime No | admin Yes | onboarding Yes
- `browser` | type unknown text-like | nullable assumed true | default app UNKNOWN | confidence High | runtime No | admin Yes | onboarding No
- `operating_system` | type unknown text-like | nullable assumed true | default app UNKNOWN | confidence High | runtime No | admin Yes | onboarding No
- `trial_started_at` | type unknown timestamp-like | nullable assumed true | default app trial_start fallback | confidence High | runtime Yes | admin Yes | onboarding Yes
- `trial_attempts` | type unknown integer-like | nullable assumed true | default app 1 | confidence High | runtime Yes | admin Yes | onboarding Yes
- `repeat_ips` | type unknown integer-like | nullable assumed true | default app 0 | confidence High | runtime No | admin Yes | onboarding No
- `repeat_devices` | type unknown integer-like | nullable assumed true | default app 0 | confidence High | runtime No | admin Yes | onboarding No
- `risk_score` | type unknown integer-like | nullable assumed true | default app 0 | confidence High | runtime Yes | admin Yes | onboarding Yes
- `fraud_flags` | type unknown text-like | nullable assumed true | default app empty string | confidence High | runtime No | admin Yes | onboarding No
- `last_ip_activity` | type unknown timestamp-like | nullable assumed true | default app now/trial fallback | confidence High | runtime No | admin Yes | onboarding No
- `first_login_at` | type unknown timestamp-like | nullable assumed true | default null | confidence High | runtime No | admin Yes | onboarding No
- `last_login_at` | type unknown timestamp-like | nullable assumed true | default null | confidence High | runtime No | admin Yes | onboarding No
- `last_login_ip` | type unknown text-like | nullable assumed true | default null | confidence High | runtime No | admin Yes | onboarding No
- `last_login_country` | type unknown text-like | nullable assumed true | default null | confidence High | runtime No | admin Yes | onboarding No
- `last_login_city` | type unknown text-like | nullable assumed true | default null | confidence High | runtime No | admin Yes | onboarding No
- `total_logins` | type unknown integer-like | nullable assumed true | default app 0 | confidence High | runtime No | admin Yes | onboarding No
- `trial_whitelisted` | type unknown boolean-like | nullable assumed true | default app false | confidence High | runtime Yes | admin Yes | onboarding Yes
- `trial_ignored` | type unknown boolean-like | nullable assumed true | default app false | confidence High | runtime No | admin Yes | onboarding No
- `trial_blocked` | type unknown boolean-like | nullable assumed true | default app false | confidence High | runtime Yes | admin Yes | onboarding Yes
- `trial_notes` | type unknown text-like | nullable assumed true | default app empty string | confidence High | runtime No | admin Yes | onboarding No
- `role` | type unknown text-like | nullable assumed true | default app user | confidence High | runtime Yes | admin Yes | onboarding No
- `status` | type unknown text-like | nullable assumed true | default null | confidence Medium | runtime No | admin No | onboarding No
- `subscription_status` | type unknown text-like | nullable assumed true | default null | confidence Medium | runtime No | admin No | onboarding No
- `last_sign_in_at` | type unknown timestamp-like | nullable assumed true | default null | confidence Medium | runtime No | admin Yes | onboarding No

Tier 2 evidence (all fields):
- Source B `application_table_contracts.json`
- Source B code reads/writes in `pages/SaaS_Core.py` and `pages/Admin_Control_Center.py`

### Tier 3 and Tier 4
- Tier 3 (Historical only): none found for this table beyond Source A/B overlaps.
- Tier 4 (Unverified): none identified in current evidence set.

## Table: subscriptions

### Tier 1 (Verified Production)
- `id` | uuid | nullable false | default gen_random_uuid() | confidence High | runtime No | admin Yes | onboarding No
- `user_id` | uuid | nullable true | default null | confidence High | runtime Yes | admin Yes | onboarding Yes
- `plan` | text | nullable true | default null | confidence High | runtime Yes | admin Yes | onboarding Yes
- `status` | text | nullable true | default null | confidence High | runtime Yes | admin Yes | onboarding Yes
- `stripe_customer_id` | text | nullable true | default null | confidence High | runtime No | admin Yes | onboarding No
- `stripe_subscription_id` | text | nullable true | default null | confidence High | runtime No | admin Yes | onboarding No
- `created_at` | timestamp with time zone | nullable false | default now() | confidence High | runtime No | admin Yes | onboarding No

### Tier 2 (Verified Application Contract)
- `email` | type unknown text-like | nullable assumed true | default null | confidence High | runtime Yes | admin Yes | onboarding No
- `current_period_end` | type unknown timestamp-like | nullable assumed true | default null | confidence Medium | runtime No | admin Yes | onboarding No
- `trial_start` | type unknown timestamp-like | nullable assumed true | default null | confidence Medium | runtime No | admin Yes | onboarding No
- `trial_end` | type unknown timestamp-like | nullable assumed true | default null | confidence Medium | runtime No | admin Yes | onboarding No

Tier 2 evidence:
- Source B `application_table_contracts.json`
- Source B `pages/SaaS_Core.py` and `pages/Admin_Control_Center.py`

### Tier 3 and Tier 4
- Tier 3: none
- Tier 4: none

## Table: workspaces

### Tier 1 (Verified Production)
- `id` | uuid | nullable false | default gen_random_uuid() | confidence High | runtime No | admin No | onboarding No
- `user_id` | uuid | nullable true | default null | confidence High | runtime Yes | admin No | onboarding Yes
- `workspace_name` | text | nullable true | default null | confidence High | runtime Yes | admin No | onboarding Yes
- `created_at` | timestamp with time zone | nullable false | default now() | confidence High | runtime No | admin No | onboarding No

### Tier 2, Tier 3, Tier 4
- none identified

## Cross-Validation Summary
- Every application read has a corresponding field: PASS
- Every application write has a corresponding field: PASS
- Every production field represented: PASS
- Duplicate names resolved: PASS with status-normalization notes
- Conflicting data types documented: PASS (Tier 2 unknown metadata)
- Conflicting defaults documented: PASS (Tier 2 app defaults vs DB defaults unknown)
- Conflicting nullability assumptions documented: PASS (Tier 2 unresolved)

## Risk Assessment

- Login break risk: Critical
  - fields: `user_profiles.user_id`, `user_profiles.email`, `user_profiles.plan`, `user_profiles.account_status`, `user_profiles.role`
  - reason: session hydration and access state rely on these fields

- Onboarding break risk: Critical
  - fields: `user_profiles.trial_start`, `user_profiles.trial_end`, `subscriptions.user_id`, `subscriptions.plan`, `subscriptions.status`, `workspaces.user_id`, `workspaces.workspace_name`
  - reason: onboarding completion and provisioning checks depend on these writes

- Trial creation break risk: Critical
  - fields: `user_profiles.trial_start`, `user_profiles.trial_end`, `user_profiles.trial_started_at`, `user_profiles.trial_attempts`, `user_profiles.trial_blocked`
  - reason: trial window + abuse controls

- Stripe synchronization risk: High
  - fields: `user_profiles.stripe_customer_id`, `user_profiles.stripe_subscription_id`, `subscriptions.stripe_customer_id`, `subscriptions.stripe_subscription_id`, `subscriptions.current_period_end`
  - reason: billing reconciliation and admin views

- Admin reporting risk: High
  - fields: telemetry/fraud bundle + `subscriptions.current_period_end` + status fields
  - reason: dashboard and operations panel consume these values

- Fraud detection risk: High
  - fields: `signup_ip`, `device_fingerprint`, `trial_attempts`, `risk_score`, `fraud_flags`, `trial_whitelisted`, `trial_blocked`
  - reason: anti-abuse controls and risk scoring logic

- Telemetry risk: Medium
  - fields: `last_login_*`, `browser`, `operating_system`, `total_logins`, `last_ip_activity`
  - reason: does not always block core login, but degrades monitoring/diagnostics

## Migration Readiness Decision
NOT READY

Reason:
- A migration cannot be generated without guessing for Tier 2 SQL definitions and advanced object metadata.
