# Grantor Fidelity Exception

Approval date: 2026-07-16
Migration file: `supabase/migrations/20260716_104439_restore_canonical_auth_schema.sql`

## Reason
The recovered Q6 grant metadata does not include the original PostgreSQL grantor identity. The authoritative recovered artifacts prove the target object, grantee, privilege, and grant-option state, but not the historical grantor role.

## Evidence Limitation
- Canonical catalog evidence is sufficient to recover grant semantics.
- Canonical catalog evidence is not sufficient to recover grantor identity.
- The limitation is recorded in `runtime_state/schema_recovery_phase7_20260716_104632/migration_vs_catalog_diff.json`.

## Scope
- This exception is limited to the development recovery migration only.
- It does not authorize production execution.
- It must not be generalized to any production migration workflow.

## Accepted Behavior
- Exact grantor identity is treated as non-authoritative for this recovery path.
- The migration executor is treated as the effective grantor when the development migration is reviewed or applied.
- Canonical privilege semantics remain authoritative:
  - object
  - grantee
  - privilege
  - grant option
- The exception does not change grantee, privilege, or grant-option state.

## Security Implications
- Grant authorization semantics remain constrained to the recovered privilege set.
- The exception is acceptable only because it does not broaden privileges or alter the canonical grant structure.
- The exception must never be reused as justification for production schema recovery or privilege restoration.

## Why the Remaining Fidelity Is Sufficient for Development
The development review target is to reconstruct the canonical authorization shape, not to recreate historical operator identity. The recovered privilege set is the meaningful operational state for development verification, while grantor identity is an unrecoverable historical detail in the available exports.
