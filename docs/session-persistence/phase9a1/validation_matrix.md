# Phase 9A.1 Validation Matrix

Status: Test design only for later phases.

## Legend
- P0: must pass before production enablement
- P1: high-value regression
- P2: extended hardening

| Scenario | Priority | Expected Result | Notes |
|---|---|---|---|
| Hard refresh while logged in | P0 | User remains authenticated | Requires cookie+durable session rehydrate |
| Browser close and reopen | P0 | User remains authenticated within policy TTL | Verify idle timeout behavior |
| Streamlit process restart | P0 | User rehydrates successfully | Confirms no in-memory dependence |
| Streamlit redeploy | P0 | User rehydrates successfully | Multi-instance/restart safe |
| Two browsers same user | P0 | Both sessions valid up to concurrency policy | Verify max-session behavior |
| Two different users | P0 | No cross-user leakage | Isolation critical |
| Concurrent sessions > max | P1 | Oldest sessions revoked as policy defines | Audit revocation reason |
| Access token expiry | P0 | Silent refresh succeeds, session continues | No forced re-login if refresh valid |
| Cookie expiration | P0 | Session ends and Secure Access shown | Fail closed |
| Logout current session | P0 | Current browser logged out, other sessions unchanged | Unless configured otherwise |
| Logout all sessions | P1 | All sessions for user revoked | Requires explicit action |
| Password change event | P1 | Sessions revoked per policy | Recommend logout-all |
| Disabled account | P0 | Access blocked and sessions revoked | Verify startup + active session checks |
| Revoked session handle | P0 | Rehydrate denied, cookie cleared | Fail closed |
| Malformed cookie value | P0 | Graceful failure to Secure Access | No crash |
| Missing DB row for handle | P0 | Cookie cleared, Secure Access shown | No partial auth |
| Expired DB session row | P0 | Rehydrate denied, cleanup path exercised | No partial auth |
| Cross-user cookie replay attempt | P0 | Rehydrate blocked by server checks | Validate user/session binding |
| Session rotation on auth events | P1 | Old handle invalidated, new handle active | Prevent fixation/replay window |
| Remember Me off | P1 | Shorter TTL enforced | Policy adherence |
| Remember Me on | P1 | Extended TTL enforced | Still bounded by absolute max |

## Additional Observability Checks
- No token/refresh/cookie secrets in logs.
- Revocation and expiry metrics available for operations.
- Startup rehydrate failures are counted with sanitized reason codes.
