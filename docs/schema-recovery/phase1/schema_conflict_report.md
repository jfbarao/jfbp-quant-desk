# Schema Conflict Report (Phase 1)

## Conflict 1 - Production-visible schema is narrower than application contract
Severity: Critical

### Description
Source A exposes only a minimal `user_profiles` and `subscriptions` schema. Application code requires additional telemetry/fraud/provisioning fields not visible in production Swagger.

### Evidence
- Source A: `runtime_state/prod_schema_export_zqzujesufquifrtqnanb_20260716_031915/openapi_tables_extract.json`
- Source B: `pages/SaaS_Core.py`, `pages/Admin_Control_Center.py`, `runtime_state/schema_recovery_phase0_20260715_203519/application_table_contracts.json`

### Impact
- Creating development schema from Source A only will break onboarding, fraud telemetry, and several admin workflows.

## Conflict 2 - Subscription email fallback path vs Swagger-visible model
Severity: High

### Description
Application code reads/writes `subscriptions.email` in fallback flows, but Source A `subscriptions` does not expose an `email` column.

### Evidence
- `pages/SaaS_Core.py` email fallback update by `subscriptions.email`
- `pages/Admin_Control_Center.py` `_rest_first_row(... email=...)`
- Source A `subscriptions.properties` has no `email`

### Impact
- Email-based fallback matching may fail if schema is generated from Source A only.

## Conflict 3 - Additional subscription lifecycle fields not in Source A
Severity: Medium

### Description
`current_period_end`, `trial_start`, `trial_end` are consumed in admin reporting, but not present in Source A subscriptions schema.

### Evidence
- `pages/Admin_Control_Center.py` customer record construction reads these keys.
- `runtime_state/schema_recovery_phase0_20260715_203519/application_table_contracts.json` grouped subscription fields.

### Impact
- Admin reporting and lifecycle display may degrade or show incomplete data.

## Conflict 4 - Status field duality and precedence
Severity: Medium

### Description
Status is represented in multiple places:
- `user_profiles.account_status`
- `subscriptions.status`
- fallback `user_profiles.status` and `user_profiles.subscription_status`

### Evidence
- `pages/SaaS_Core.py:build_saas_user_from_auth`
- `pages/Admin_Control_Center.py:_build_customer_record`

### Impact
- Inconsistent status values across tables may produce divergent access decisions.

## Conflict 5 - Unknown Tier 2 SQL metadata
Severity: Critical

### Description
Tier 2 fields are evidenced by app contracts but lack authoritative SQL type/nullability/default definitions in repository-accessible production metadata.

### Evidence
- Source A only contains Tier 1 metadata.
- No catalog/DDL metadata for Tier 2 fields available in repo artifacts.

### Impact
- Any migration generated now for Tier 2 would require guessing, violating recovery guardrails.

## Conflict 6 - Advanced object metadata absent
Severity: High

### Description
No authoritative constraints/FK/indexes/RLS/triggers/functions metadata is available through current evidence channels.

### Evidence
- `production_tables_ddl_export.sql` explicitly notes limitation.
- Phase 0 reports identify this gap.

### Impact
- Even perfect column recreation could remain behaviorally divergent from production security/performance model.
