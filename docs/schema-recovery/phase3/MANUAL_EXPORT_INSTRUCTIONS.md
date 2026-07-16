# Phase 3 Manual Metadata Export Instructions (Production, Read-Only)

## Safety Rules
- Run only read-only queries from `docs/schema-recovery/phase3/manual_metadata_queries.sql`.
- Do not run any schema/data-changing SQL.
- Do not run `rls_auto_enable` RPC.
- Do not include credentials in exports or screenshots.

## 1) Open Supabase
1. Sign in to Supabase dashboard.
2. Open project selector.
3. Confirm the target project reference is exactly: `zqzujesufquifrtqnanb`.
4. Stop immediately if the reference is different.

## 2) Open SQL Editor
1. In the confirmed production project, open SQL Editor.
2. Create a new query tab.
3. Open `docs/schema-recovery/phase3/manual_metadata_queries.sql` locally and copy one query block at a time.

## 3) Run Queries One-by-One
Execute Q1 through Q10 separately. After each query:
1. Verify it is read-only output.
2. Export result as CSV (preferred) or JSON.
3. Use the exact filenames below.

## 4) Required Export Filenames
- `q1_target_tables.csv`
- `q2_columns.csv`
- `q3_constraints.csv`
- `q4_indexes.csv`
- `q5_rls_policies.csv`
- `q6_table_sequence_grants.csv`
- `q7_triggers.csv`
- `q8_referenced_functions.csv`
- `q9_function_grants.csv`
- `q10_expression_sources.csv`

## 5) Place Returned Files Locally
Create this folder locally and place all exported files there:
- `runtime_state/schema_recovery_phase3_20260715_211215/manual_exports/`

## 6) Post-Export Validation Hand-off
After files are placed locally, run Phase 3 validation to produce:
- `production_columns.json`
- `production_constraints.json`
- `production_indexes.json`
- `production_rls_policies.json`
- `production_grants.json`
- `production_triggers.json`
- `production_functions.json`
- `metadata_completeness_report.md`

## 7) Explicit Do-Not-Approve List
Do not approve or execute statements containing:
- CREATE
- ALTER
- DROP
- INSERT
- UPDATE
- DELETE
- GRANT
- REVOKE
- RPC invocations (including `rls_auto_enable`)
