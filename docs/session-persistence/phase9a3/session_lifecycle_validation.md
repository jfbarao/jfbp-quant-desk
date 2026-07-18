# Phase 9A.3 Session Lifecycle Validation

## Covered Lifecycle Scenarios
- Login creates durable session and cookie.
- Browser refresh / rerun rehydrates through durable store.
- Browser restart simulation with fresh client rehydrates through cookie + durable store.
- Logout revokes current session and clears cookie.
- Logout-all revokes all sessions for current user.
- Malformed/tampered cookie clears safely.
- Revoked and expired rows clear safely.
- Remember Me and standard durations map to approved policy.
- No token leakage in cookie.

## Test Artifact
- `tests/test_phase9a3_cookie_rehydration.py`

## Primary Persistence
- Durable app session store is now primary for restoration.
- Existing in-memory cache retained as secondary optimization.
