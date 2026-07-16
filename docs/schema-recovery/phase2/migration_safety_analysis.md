# Migration Safety Analysis (Phase 2)

## Method
For each unresolved metadata class, evaluate failure mode if recreated incorrectly.

## Safety Matrix

### Tier 2 column physical definitions (type/nullability/default)
- Risk rank: Critical
- If incorrect, failures may include:
  - Signup and profile creation failures due to insert/update payload mismatch
  - Login session hydration inconsistencies
  - Trial creation and fraud-control regressions
  - Admin dashboard rendering errors for risk and telemetry fields
  - Stripe and subscription reporting degradation

### Primary key definitions
- Risk rank: High
- If incorrect, failures may include:
  - Duplicate logical rows for users
  - Broken upsert/update targeting by user identity
  - Unstable admin reconciliation and onboarding repair flows

### Foreign keys
- Risk rank: Critical
- If incorrect, failures may include:
  - Orphaned profile/subscription/workspace rows
  - Broken user lifecycle and referential drift
  - Unexpected delete/update side effects if cascades differ

### Unique constraints
- Risk rank: High
- If incorrect, failures may include:
  - Multiple active rows per user or email
  - Ambiguous row selection in login/admin lookup paths
  - Subscription sync conflicts

### Check constraints
- Risk rank: Medium
- If incorrect, failures may include:
  - Invalid status/plan states accepted or valid states rejected
  - Admin operation failures on plan/status transitions

### Indexes
- Risk rank: High
- If incorrect, failures may include:
  - Severe latency in login/onboarding/admin operations
  - Timeouts in customer directory and reconciliation workflows
  - Degraded analytics and telemetry queries

### Triggers
- Risk rank: High
- If incorrect, failures may include:
  - Missing automatic updates (timestamps, audit hooks, denormalization)
  - Inconsistent business-state propagation across objects

### Trigger functions
- Risk rank: High
- If incorrect, failures may include:
  - Trigger execution failures at runtime
  - Silent behavior drift if function logic mismatches production

### RLS policies
- Risk rank: Critical
- If incorrect, failures may include:
  - Login/onboarding writes blocked for authenticated users
  - Over-permissive access exposing customer data
  - Admin console inability to read/write expected rows

### Grants
- Risk rank: High
- If incorrect, failures may include:
  - Service role and app role access failures
  - API layer permission errors in runtime and admin paths

## Behavior-Failure Mapping
- Login: sensitive to user_profiles identity fields, RLS, grants, PK/UNIQUE
- Signup: sensitive to profile insert schema and RLS/grants
- Trial creation: sensitive to trial fields, check constraints, RLS
- Subscription sync: sensitive to subscriptions schema, FK/UNIQUE, grants
- Stripe webhook processing: sensitive to subscription/profile billing fields and permissions
- Admin dashboard: sensitive to telemetry fields, indexes, grants, RLS
- Fraud detection: sensitive to telemetry/fraud fields, nullability/defaults
- Analytics/telemetry: sensitive to indexes and field typing consistency
