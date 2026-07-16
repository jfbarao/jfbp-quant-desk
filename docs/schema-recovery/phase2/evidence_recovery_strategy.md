# Evidence Recovery Strategy (Phase 2)

## Goal
Resolve all unresolved metadata objects without guessing and without executing migration SQL.

## Unresolved Object Strategy

### 1) Tier 2 column SQL type/nullability/default metadata
- Why unresolved:
  - Production-visible artifacts do not expose these columns with authoritative DB definitions.
  - Application contracts prove usage but not canonical physical schema.
- Evidence source required:
  - Read-only canonical PostgreSQL metadata export from production for public.user_profiles and public.subscriptions.
  - Authoritative DDL dump including column definitions and defaults.
- Mandatory before migration: Yes
- Risk if recreated incorrectly: Critical
- Affected objects:
  - user_profiles Tier 2 set (telemetry, fraud, notification, fallback status fields)
  - subscriptions Tier 2 set (email, current_period_end, trial_start, trial_end)

### 2) Primary key canonical definitions
- Why unresolved:
  - OpenAPI indicates id as primary key marker, but exact constraint names/definitions are not exported.
- Evidence source required:
  - pg_catalog based PK definition export or canonical migration history.
- Mandatory before migration: Yes
- Risk if recreated incorrectly: High
- Affected objects:
  - PK definitions for all three tables

### 3) Foreign key definitions
- Why unresolved:
  - No FK metadata in Source A artifacts.
- Evidence source required:
  - pg_constraint and pg_attribute FK export, or canonical migrations.
- Mandatory before migration: Yes
- Risk if recreated incorrectly: Critical
- Affected objects:
  - all FK relationships for user_id and any Stripe linkage constraints

### 4) Unique constraints
- Why unresolved:
  - No authoritative UNIQUE metadata available.
- Evidence source required:
  - pg_constraint unique export or canonical DDL.
- Mandatory before migration: Yes
- Risk if recreated incorrectly: High
- Affected objects:
  - potential uniqueness on user_id and/or email in user_profiles and subscriptions

### 5) Check constraints
- Why unresolved:
  - No CHECK metadata available.
- Evidence source required:
  - pg_constraint check expressions or canonical DDL.
- Mandatory before migration: Yes
- Risk if recreated incorrectly: Medium
- Affected objects:
  - account_status, plan, status domain checks if present

### 6) Indexes
- Why unresolved:
  - No index metadata in current exports.
- Evidence source required:
  - pg_indexes export or schema dump with index DDL.
- Mandatory before migration: Yes
- Risk if recreated incorrectly: High
- Affected objects:
  - lookup and join paths on user_id/email/created_at and admin views

### 7) Triggers and trigger functions
- Why unresolved:
  - Trigger metadata/function references absent from available evidence.
- Evidence source required:
  - pg_trigger joined to pg_proc, plus function definitions.
- Mandatory before migration: Yes
- Risk if recreated incorrectly: High
- Affected objects:
  - automated timestamp, audit, denormalization, or sync behavior if used

### 8) RLS policies
- Why unresolved:
  - OpenAPI and derived DDL do not expose row-level security policies.
- Evidence source required:
  - pg_policies export and relrowsecurity flags from pg_class.
- Mandatory before migration: Yes
- Risk if recreated incorrectly: Critical
- Affected objects:
  - authenticated session writes and admin/service-role visibility

### 9) Grants
- Why unresolved:
  - Grant metadata not present in current artifacts.
- Evidence source required:
  - information_schema role table grants and table/schema grants export.
- Mandatory before migration: Yes
- Risk if recreated incorrectly: High
- Affected objects:
  - role access for anon/authenticated/service_role flows

## Recovery Priority Order
1. Tier 2 column physical metadata (Critical)
2. RLS policies and FK metadata (Critical)
3. Unique constraints, PK canonical DDL, indexes, grants (High)
4. Trigger and function definitions (High)
5. Check constraints (Medium)

## Practical Read-Only Evidence Channels
- Preferred:
  - canonical migration repository history (if recovered)
  - production pg_catalog exports (read-only)
- Acceptable:
  - verified platform schema export that includes constraints/indexes/RLS/triggers/functions
- Not sufficient alone:
  - OpenAPI/PostgREST schema projection
  - application code contracts
