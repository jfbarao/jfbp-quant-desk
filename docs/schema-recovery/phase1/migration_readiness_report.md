# Migration Readiness Report (Phase 1)

## Decision
NOT READY

## Readiness Criteria Evaluation

1. Every production-visible field is accounted for
- Status: PASS
- Basis: All Source A columns for `user_profiles`, `subscriptions`, and `workspaces` are included in canonical specification.

2. Every application-required field is accounted for
- Status: PASS (catalog coverage)
- Basis: All observed reads/writes in `pages/SaaS_Core.py` and `pages/Admin_Control_Center.py` are mapped into the field catalog.

3. Every conflict is documented
- Status: PASS
- Basis: Documented in `schema_conflict_report.md`.

4. Every unverified field is isolated
- Status: PASS
- Basis: Tiering performed; no Tier 4 columns currently identified in available evidence set.

5. Migration can be generated without guessing
- Status: FAIL
- Basis:
  - Tier 2 columns do not have authoritative SQL type/nullability/default metadata.
  - Constraints/indexes/RLS/triggers/functions metadata is unavailable.

## Why NOT READY
- A migration generated now would require assumptions for Tier 2 database definitions.
- Recovery guardrails explicitly disallow guessing schema details.

## Missing Evidence Required To Reach READY
1. Authoritative production metadata channel for all Tier 2 columns, including:
- exact SQL type
- nullability
- default expressions

2. Canonical object metadata for:
- primary/foreign keys
- unique/check constraints
- indexes
- RLS enablement and policies
- triggers and trigger functions

3. Confirmation of intended status model precedence between:
- `user_profiles.account_status`
- `subscriptions.status`
- optional profile fallback fields (`status`, `subscription_status`)

## Next Safe Step (still no SQL execution)
- Phase 1.5 evidence acquisition: obtain canonical production object metadata through an approved read-only channel, then refresh this specification and re-evaluate readiness.
