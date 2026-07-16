# Repository vs Production Schema Audit (Phase 0)

## Scope
- Repository audited read-only for canonical schema/migration sources.
- Comparison baseline:
  - runtime_state/prod_schema_export_zqzujesufquifrtqnanb_20260716_031915/openapi_tables_extract.json
  - runtime_state/prod_schema_export_zqzujesufquifrtqnanb_20260716_031915/production_tables_ddl_export.sql

## Canonical Migration Search Result
- No canonical migration directory or SQL migration chain was found in repository source.
- Missing expected locations in this repo:
  - supabase/
  - supabase/migrations/
  - migrations/
  - database/
  - db/
  - schema/
  - .github/

## Relevant Sources Found
1. runtime_state/prod_schema_export_zqzujesufquifrtqnanb_20260716_031915/production_tables_ddl_export.sql
- Classification: generated active artifact.
- Defines all three target tables in Swagger-visible scope.
- Matches production Swagger columns/types/defaults.
- Does not include index/constraint/RLS/trigger/function definitions.

2. runtime_state/prod_schema_export_zqzujesufquifrtqnanb_20260716_031915/openapi_tables_extract.json
- Classification: generated active artifact.
- Machine-readable production baseline for table columns and defaults.
- Partial PK visibility only (id tagged as PK in description).
- No FK/UNIQUE/CHECK/index/trigger/RLS/function metadata.

3. pages/SaaS_Core.py
- Classification: active runtime contract.
- Reads/writes all three tables.
- Requires many user_profiles telemetry/risk/onboarding fields not visible in production Swagger baseline.
- Compatible with itself but conflicts with Swagger-visible minimal schema.

4. pages/Admin_Control_Center.py
- Classification: active admin runtime contract.
- Reads and writes user_profiles/subscriptions, and documents recommended fields.
- Expects additional metadata and operational columns beyond Swagger-visible baseline.
- Compatible with admin workflows but only partially aligned with production Swagger-visible schema.

5. runtime_state/schema_recovery_dev_qkqexvlprzjqjtsarqbz_20260716_030658/base_schema_draft.sql
- Classification: generated draft.
- Aligned to Swagger-visible production columns/types/defaults.
- Not canonical migration source.

6. runtime_state/schema_recovery_20260715_user_profiles/user_profiles_schema_summary.json
- Classification: archived historical snapshot.
- Covers user_profiles summary only.
- Useful corroboration, not a canonical migration source.

## Comparison Summary
- Repository contains no authoritative migration chain for creating or evolving:
  - public.user_profiles
  - public.subscriptions
  - public.workspaces
- Strongest schema evidence currently present in repo is generated from production Swagger artifacts under runtime_state.
- Application runtime contracts (SaaS_Core/Admin_Control_Center) imply broader schema needs than production Swagger exposes.

## Conflicts and Gaps
- Conflict A: app-required columns (telemetry/risk/provisioning) are not present in production Swagger-visible table definitions.
- Gap B: canonical metadata for constraints/indexes/RLS/triggers/functions is not represented in repository migration files.
- Gap C: no first-party migration ownership trail exists in source tree.

## Conclusion
- Canonical existing migration found: no.
- Best available schema source in repository: production-derived runtime_state artifacts.
- Repository source of truth for full database object model: absent.
