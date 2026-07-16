# Recommended Recovery Source (Phase 0)

## Decision
**Outcome C:** No reliable canonical migration exists in repository source, so a new recovery migration must be generated from production evidence plus verified application contracts.

## Why Outcome C
- No canonical migration files or migration directories were found.
- Existing SQL definitions in repository are generated runtime_state artifacts, not source-controlled migration history.
- Application contracts in pages/SaaS_Core.py and pages/Admin_Control_Center.py require additional columns not visible in production Swagger baseline.

## Strongest Available Source Stack
1. Production-derived baseline (Swagger scope):
- runtime_state/prod_schema_export_zqzujesufquifrtqnanb_20260716_031915/openapi_tables_extract.json
- runtime_state/prod_schema_export_zqzujesufquifrtqnanb_20260716_031915/production_tables_ddl_export.sql

2. Verified application contracts:
- pages/SaaS_Core.py
- pages/Admin_Control_Center.py
- runtime_state/schema_recovery_phase0_20260715_203519/application_table_contracts.json

## Recovery Strategy (Next Phase, migration planning only)
1. Phase 1A: Recreate missing base tables in development from production-derived DDL baseline (Swagger scope only).
2. Phase 1B: Reconcile application-required columns absent from Swagger baseline and define additive table evolution for development.
3. Phase 1C: Validate schema against runtime contracts using read-only checks and onboarding simulation pathways.
4. Phase 1D: Separate advanced object recovery (constraints/indexes/RLS/triggers/functions) once canonical metadata channel is available.

## Execution Status
- No SQL executed.
- No migration generated or applied in this phase.
- No changes made to production or development databases.

## Exact Next Migration Phase to Perform
**Schema Recovery Phase 1 — Development Base Table Recreation Plan (no execution until explicit approval).**
