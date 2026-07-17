# Phase 9A.2 Session Store Security Review

Status: Review of implemented foundation.

## Security Positives
- Durable table stores only hash of session handle; raw handle excluded.
- Refresh material encrypted at app layer before persistence.
- Encryption key is externalized through `SESSION_ENCRYPTION_KEY`.
- Ciphertext includes explicit version and key-version tag.
- RLS enabled and forced for `public.app_sessions`.
- `anon` and `authenticated` direct table rights removed.
- Service-role path isolated to dedicated store module operations.
- No token values included in raised error messages.

## Concurrency Safety
- Session creation and max-session enforcement occur inside a database `SECURITY DEFINER` function.
- Per-user advisory transaction lock avoids parallel create races from bypassing max-session policy.
- Eviction order is deterministic: oldest active sessions first.

## Rotation and Revocation
- Rotation marks parent session revoked with replacement linkage.
- Current-session revoke and revoke-all operations are explicit and auditable by reason.

## Residual Risks
- `SECURITY DEFINER` functions rely on strict privilege boundaries and should be reviewed in staged DB before production migration.
- Operational key-rotation runbook is not yet implemented in code paths (supported by format, not orchestrated).
- Until Phase 9A.3 wiring, active runtime auth still depends on current app login/rehydration flow.
