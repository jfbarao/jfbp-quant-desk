# Minimal Recovery Schema (Conceptual, No SQL)

## Constraint
Use only High Confidence evidence from Phase 0 and Phase 1.
No speculative objects.
No speculative constraints.
No speculative triggers.
No speculative RLS.

## Purpose
Smallest conceptual schema that supports:
- user signup
- login
- profile creation
- subscription creation
- workspace creation

## Conceptual Table Model

### user_profiles (minimal baseline)
Required fields:
- id (uuid identity)
- created_at (timestamp)
- user_id (user identity link used by runtime lookups)
- email
- full_name
- plan
- account_status
- trial_start
- trial_end
- stripe_customer_id
- stripe_subscription_id

Rationale:
- These are production-visible and High Confidence.
- They cover core onboarding, plan/status resolution, and billing identifiers.

Operational caveat:
- Current app writes additional telemetry and fraud fields during onboarding/login metadata persistence.
- Therefore this baseline alone may not support full existing runtime behavior unless app write payloads are constrained or Tier 2 fields are additionally defined from canonical evidence.

### subscriptions (minimal baseline)
Required fields:
- id
- created_at
- user_id
- plan
- status
- stripe_customer_id
- stripe_subscription_id

Rationale:
- High Confidence production-visible baseline required for subscription row creation and status handling.

Operational caveat:
- Email fallback behavior and lifecycle reporting fields from app contracts are outside minimal High Confidence production-visible set.

### workspaces (minimal baseline)
Required fields:
- id
- created_at
- user_id
- workspace_name

Rationale:
- Directly required for workspace creation in onboarding flow.

## Non-Included By Design
Not included in minimal recovery schema because physical metadata is not canonically proven:
- Tier 2 application-contract-only columns
- Foreign key definitions
- Unique/check constraints beyond explicit production-visible proof
- indexes
- triggers and trigger functions
- RLS policies
- grants

## Applicability Statement
This minimal conceptual schema is the smallest non-speculative baseline from High Confidence evidence only.
It is suitable only as a constrained recovery baseline, not as a full production-parity schema.
