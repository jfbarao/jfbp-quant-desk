# Phase 10B - Controlled Production Validation

Date: 2026-07-19
Scope mode: Controlled live validation in progress (single-check authorization)
Repository: /Users/josepereira/rs_clean

## 1) Purpose and Scope

This phase validates the production authentication, onboarding, durable-session, entitlement, and Stripe Customer Portal flows.

Execution constraints:
- Validation is limited to one approved test-account lifecycle.
- The account must use a real, pre-approved inbox supplied by the operator.
- Do not invent, generate, or register fake email addresses.
- Do not execute any production signup, authentication action, database write, Stripe action, deployment, migration, or test-account lifecycle until explicit operator authorization is given.

## 2) Preconditions

All preconditions must be satisfied before the first live validation action:

- Phase 10A committed and production configuration certified ready.
- Production application URL identified and confirmed.
- Approved test inbox supplied by the operator.
- Operator approval explicitly granted before account creation.
- Production Supabase and Stripe environments clearly identified.
- Existing account state for the approved inbox checked before beginning.

Precondition status checklist:
- PASS: Phase 10A committed and certified ready
- PASS: Production application URL confirmed
- PENDING: Approved inbox supplied
- PASS: Operator live-action authorization granted (B10B-001 only)
- PENDING: Production Supabase environment confirmed
- PENDING: Production Stripe environment confirmed
- PENDING: Existing account state checked

## 3) Hard-Stop Gates

Stop immediately and do not continue if any gate fails:

- Signup verification email delivery or redirect
- Successful verified login
- Durable session restoration after refresh or browser restart
- Logout followed by confirmed access revocation
- Relogin using the same approved account

Governance rule:
- Do not proceed to Phase 10C unless every Phase 10B exit criterion passes.

## 4) Validation Sequence (Controlled, Operator-Approved)

Status legend: PASS, FAIL, PENDING, BLOCKED, NOT RUN

- B10B-001: Production signup page availability - PASS
- B10B-002: Approved account registration - NOT RUN
- B10B-003: Verification email receipt - NOT RUN
- B10B-004: Verification redirect destination - NOT RUN
- B10B-005: First login - NOT RUN
- B10B-006: user_profiles record creation - NOT RUN
- B10B-007: workspaces record creation - NOT RUN
- B10B-008: subscriptions record creation - NOT RUN
- B10B-009: Correct trial start and expiry - NOT RUN
- B10B-010: Correct trial countdown - NOT RUN
- B10B-011: Session cookie creation (value hidden) - NOT RUN
- B10B-012: Session survival after refresh - NOT RUN
- B10B-013: Session survival after browser close/reopen - NOT RUN
- B10B-014: Protected-page authorization - NOT RUN
- B10B-015: Logout - NOT RUN
- B10B-016: Protected-page denial after logout - NOT RUN
- B10B-017: Relogin - NOT RUN
- B10B-018: Password-reset email receipt and successful reset - NOT RUN
- B10B-019: Stripe Customer Portal redirect - NOT RUN
- B10B-020: Return from Stripe portal to correct application destination - NOT RUN

## 5) Evidence Format

Use this record structure for every check:

- Check ID
- Date and time (UTC)
- Environment
- Operator action
- Expected result
- Actual result
- Status: PASS, FAIL, BLOCKED, or NOT RUN
- Sanitized evidence reference
- Notes
- Defect reference (if applicable)

Recommended record template:

| Check ID | Date/Time (UTC) | Environment | Operator Action | Expected Result | Actual Result | Status | Sanitized Evidence Ref | Notes | Defect Ref |
|---|---|---|---|---|---|---|---|---|---|
| B10B-XXX | YYYY-MM-DDTHH:MM:SSZ | production | <action> | <expected> | <actual> | NOT RUN | <ref> | <notes> | <defect or N/A> |

Executed evidence record:

| Check ID | Date/Time (UTC) | Environment | Operator Action | Expected Result | Actual Result | Status | Sanitized Evidence Ref | Notes | Defect Ref |
|---|---|---|---|---|---|---|---|---|---|
| B10B-001 | 2026-07-19T15:54:57Z | production | Open fresh production app page and switch auth mode to Create Account without submit | Signup/trial registration page loads, no server error, form visible and usable, production context evident | Page loaded at public production app URL, no server error surface, Create Account form visible with required fields and action button; no submit performed | PASS | EV-B10B-001-20260719T155457Z (browser page 9c81f06e-4937-49a7-8997-8a61c13e0ad6 snapshots) | Public URL recorded only; no auth links, tokens, cookies, or PII captured | N/A |

## 6) Sanitization Controls

Committed evidence must not contain:

- Passwords
- Session cookies
- Access or refresh tokens
- Supabase keys
- Stripe keys
- Database URLs
- Full authentication links
- Secret values or secret-derived fragments

Masking requirement:
- Mask the approved email address wherever practical in committed evidence.
- Use a redacted representation such as user***@domain.tld in documentation.

## 7) Execution Log

A chronological execution log must be maintained for each operator-approved action and result.

- Log location: docs/session-persistence/phase10b/execution_log.md
- Every entry must include timestamp, actor, action, result, and evidence reference.

## 8) Exit Criteria

Phase 10B passes only when all criteria below are satisfied:

- Entire approved account lifecycle completes without manual database repair.
- All required records are created in the correct production project.
- Durable session restoration works.
- Logout and relogin invariants work.
- Password reset works.
- Stripe Customer Portal opens correctly.
- Trial entitlement and countdown are correct.
- Protected pages enforce authorization correctly.
- No unresolved Critical or High severity defects remain.

## 9) Final Decision

Reserve exactly one outcome:

- PHASE 10B PASS - AUTHORIZED FOR PHASE 10C
- PHASE 10B FAIL - PRODUCTION VALIDATION STOPPED
- PHASE 10B INCOMPLETE - OPERATOR ACTION REQUIRED

Current decision:
- PHASE 10B INCOMPLETE - OPERATOR ACTION REQUIRED

## 10) Live-Execution Safety Guard

Only authorized live checks may run. All non-authorized checks remain NOT RUN.
No production signup submission, authentication completion, database-write lifecycle action, Stripe flow action, deployment, or migration is authorized outside explicit operator approval scope.
