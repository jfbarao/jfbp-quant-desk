# Removed/Isolated Non-Canonical Dependencies

## SaaS Core
- Removed subscriptions.email runtime query/update dependency in provisioning path.
- Removed persistence dependency on user_profiles non-canonical telemetry/control columns during writes.
- Founder notification idempotency/notes moved to safe session telemetry branch (non-blocking; no canonical DB write requirement).
- Trial snapshot query moved from non-canonical user_profiles telemetry columns to canonical trial/account columns.
- Subscription reconciliation now uses canonical subscriptions.user_id lookup for status/plan.

## Admin Control Center
- Removed subscriptions email-join fallback in customer merge assembly.
- _rest_first_row now blocks email filter queries for tables without canonical email column (notably subscriptions).
- Plan/status/profile writes now filtered by canonical allowlist immediately before persistence.
- Trial controls and notes updates that are non-canonical are handled as safe no-op compatibility writes with explicit message.
- Removed non-canonical subscription renewal/trial field dependency from customer record assembly (display remains available with fallback as unavailable).

## Compatibility behavior
- Upstream app telemetry/risk objects remain intact in memory.
- Only DB payloads to user_profiles/subscriptions/workspaces are constrained.
- Required canonical writes still surface failures.
