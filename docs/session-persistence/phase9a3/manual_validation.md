# Phase 9A.3 Manual Validation Policy and Cleanup Correction

Date: 2026-07-17
Environment: Development only

## Policy Correction

Live fake-account creation is prohibited for manual validation.

Do not create additional Supabase Auth users through signup, trial, onboarding, provisioning, subscription, password reset, or support notification flows.

Approved manual-validation identities:
- Existing dedicated development test account
- Existing manually created development-only QA account

For multi-session validation, reuse the same approved account across separate browser sessions/profiles.

For cross-user isolation, use two pre-existing approved QA accounts. If a second approved account does not already exist, stop and request approval before creating one.

The live Supabase restoration proof is an integration test and must not run as part of ordinary local testing or CI defaults.

Standard default test command:
- `python -m pytest -q -m "not integration"`

## Cleanup Audit Scope

Temporary-account matching patterns:
- phase9a3-*
- phase9a3-manual-*
- *@example.com

Project guardrails used before deletion:
- APP_ENV must be development
- Supabase project reference must be qkqexvlprzjqjtsarqbz

## Cleanup Summary

Temporary accounts found: 7

Deleted temporary auth users:
- phase9a3-manual-u2-af56c8cc@example.com
- phase9a3-manual-u1-33ff11c0@example.com
- phase9a3-manual-2-d850ab7c@example.com
- phase9a3-manual-1-15efc5f5@example.com
- e2eredirect+1784240664@example.com
- redirectshape+1784240367@example.com
- redirectcheck+1784240341@example.com

Dependent development rows removed:
- user_profiles: 3 rows
- workspaces: 3 rows
- subscriptions: 3 rows

Post-cleanup verification:
- Remaining matching auth users: 0
- user_profiles rows for deleted user_ids: 0
- workspaces rows for deleted user_ids: 0
- subscriptions rows for deleted user_ids: 0
- user_profiles rows with %@example.com email: 0

Notes:
- Several optional tables were not present in this development project (for example app_sessions/onboarding/notifications variants), so no rows could exist there.
- Cleanup used direct admin and table deletions only; no signup, password reset, or support notification flows were triggered.

## Test Harness Guardrail

Live user creation in the Phase 9A.2 restoration proof test is now opt-in only.

The proof is marked as an integration test and is excluded from normal test execution unless explicitly selected.

Required flag:
- ENABLE_LIVE_SUPABASE_USER_CREATION=1

Without this flag, the live test skips by default.

Approved command for intentional live execution:

```bash
ENABLE_LIVE_SUPABASE_USER_CREATION=1 \
python -m pytest -q -m integration \
tests/test_phase9a2_supabase_restoration_proof.py
```
