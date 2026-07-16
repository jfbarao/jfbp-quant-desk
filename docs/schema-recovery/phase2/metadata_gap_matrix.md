# Metadata Gap Matrix (Phase 2)

## Scope
- Tables analyzed: user_profiles, subscriptions, workspaces
- Source basis: Phase 0 and Phase 1 canonical artifacts
- SQL execution: none

## Coverage Summary
- Total tables: 3
- Total columns cataloged: 58
- Columns with at least one unresolved metadata attribute: 58
- Reason: every column still has unresolved object-level metadata (FK/UNIQUE/CHECK), and many columns also have unresolved core metadata.

## Column Metadata Status Model
- Verified: evidence is explicit and authoritative in available artifacts.
- Unknown: no authoritative metadata in available artifacts.
- Conflicting: two validated sources imply incompatible assumptions.

## Table-Level Column Findings

### user_profiles
- SQL type:
  - Verified for Tier 1 columns from production-visible schema.
  - Unknown for all Tier 2 columns.
- Nullable:
  - Conflicting for user_id and email (production-visible nullable vs application assumes operationally required).
  - Unknown for Tier 2 columns.
- Default:
  - Verified only for id and created_at at DB level.
  - Unknown for Tier 2 (app fallback values are not DB defaults).
- PK participation:
  - Verified for id as primary key marker in production-visible OpenAPI.
  - Unknown for all other columns.
- FK participation: Unknown for all columns.
- UNIQUE participation: Unknown for all columns.
- CHECK participation: Unknown for all columns.

### subscriptions
- SQL type:
  - Verified for Tier 1 columns.
  - Unknown for Tier 2 columns email, current_period_end, trial_start, trial_end.
- Nullable:
  - Conflicting for user_id (nullable in production-visible contract vs operationally required by app behavior).
  - Unknown for Tier 2 columns.
- Default:
  - Verified for id and created_at.
  - Unknown for Tier 2 columns.
- PK participation:
  - Verified marker for id only.
  - Unknown for all other columns.
- FK participation: Unknown for all columns.
- UNIQUE participation: Unknown for all columns.
- CHECK participation: Unknown for all columns.

### workspaces
- SQL type: Verified for all visible columns.
- Nullable: Verified in production-visible contract; operational assumptions imply user_id should be non-null for app correctness.
- Default: Verified for id and created_at only.
- PK participation: Verified marker for id only.
- FK participation: Unknown.
- UNIQUE participation: Unknown.
- CHECK participation: Unknown.

## Table Object Evidence Status

For each table (user_profiles, subscriptions, workspaces):
- Primary key: Conflicting
  - id is marked as primary key in production-visible OpenAPI, but canonical PK DDL is not available.
- Foreign keys: Unknown
- Unique constraints: Unknown
- Check constraints: Unknown
- Indexes: Unknown
- Triggers: Unknown
- RLS policies: Unknown
- Grants: Unknown
- Trigger functions: Unknown

## Canonical Machine-Readable Matrix
- Full matrix: runtime_state/schema_recovery_phase2_20260715_204821/metadata_gap_matrix.json
