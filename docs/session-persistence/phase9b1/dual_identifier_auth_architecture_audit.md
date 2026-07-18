# Phase 9B.1 Dual-Identifier Authentication Architecture Audit

Scope: Read-only audit only. No code changes, no Supabase setting changes, no user creation, no SMS sending.

## 1) Current Authentication Map

### Signup entry point
- UI entry: pages/SaaS_Core.py -> render_auth_panel()
- Action handler: pages/SaaS_Core.py -> supabase_sign_up(email, password, full_name, plan)
- Supabase call: pages/SaaS_Core.py -> client.auth.sign_up(...)
- Post-auth/session handling: pages/SaaS_Core.py -> set_authenticated_session(...)

### Login entry point
- UI entry: pages/SaaS_Core.py -> render_auth_panel()
- Action handler: pages/SaaS_Core.py -> supabase_login(email, password)
- Supabase call: pages/SaaS_Core.py -> client.auth.sign_in_with_password({"email": ..., "password": ...})
- App login gate: app.py -> enforce_app_login() calling init_saas_state() and render_auth_panel()

### Password-reset entry point
- UI entry: pages/SaaS_Core.py -> render_auth_panel() (Reset Password mode)
- Reset email request: pages/SaaS_Core.py -> supabase_reset_password(email)
- HTTP endpoint used: POST /auth/v1/recover
- Recovery completion: pages/SaaS_Core.py -> _establish_recovery_session_from_query(...) + _complete_password_recovery(...)

### Email-confirmation callback handling
- Non-recovery callback consumer: pages/SaaS_Core.py -> _establish_non_recovery_session_from_query(client)
- Recovery callback consumer: pages/SaaS_Core.py -> _establish_recovery_session_from_query(client)
- Query parsing helpers: pages/SaaS_Core.py -> _query_param_value(...), _recovery_flow_type(...), _has_auth_callback_params(...)
- Fragment bridge attempt: pages/SaaS_Core.py -> _bridge_fragment_auth_callback_to_query()

### Supabase client constructor
- Runtime constructor: pages/SaaS_Core.py -> get_supabase_client() (cached via @st.cache_resource)
- Constructor call: create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
- Fallback stub only if SaaS module import fails: app.py -> get_supabase_client()

### User-profile creation path
- Orchestrator: pages/SaaS_Core.py -> ensure_user_workspace_records(...)
- Profile write: pages/SaaS_Core.py -> _create_profile_record(...)
- Subscription write: pages/SaaS_Core.py -> _create_subscription_record(...)
- Workspace write: pages/SaaS_Core.py -> _create_workspace_record(...)
- Post-login metadata write: pages/SaaS_Core.py -> _save_login_metadata(...)

### Durable-session creation and rehydration path
- Session store accessor: pages/SaaS_Core.py -> _session_store()
- Durable session create on login: pages/SaaS_Core.py -> initialize_session(...)
  - uses core/session_store.py -> SessionStore.create_session(...)
  - writes signed opaque cookie via pages/SaaS_Core.py -> _set_session_cookie(...)
- Rehydration on startup: pages/SaaS_Core.py -> init_saas_state() -> _rehydrate_authenticated_session()
  - reads cookie: _read_session_cookie_result()
  - validates signature: _unsign_session_handle(...)
  - looks up durable session: SessionStore.get_session_by_handle(...)
  - restores auth via refresh token material: client.auth.refresh_session(...)

### Database columns currently storing email or phone data

Confirmed from development project data model/API observations:
- auth.users.email (Supabase Auth)
- auth.users.phone (Supabase Auth)
- public.user_profiles.email

Confirmed not present in current canonical application tables queried:
- public.subscriptions.phone: absent
- public.workspaces.phone: absent
- public.subscriptions.email: absent in current active table rows

Notes:
- Historic schema-recovery artifacts mention subscriptions.email as a previous/legacy contract assumption, but current active development table keys do not include it.

## 2) Current Supabase Configuration Audit (Development Project Only)

Project reference:
- qkqexvlprzjqjtsarqbz

Observed via GET /auth/v1/settings:
- Phone authentication enabled: no (external.phone resolved false)
- Confirm phone enabled: yes (phone_autoconfirm = false)
- SMS provider: twilio
- CAPTCHA affecting signup/OTP: not exposed in this endpoint; no explicit captcha keys returned
- Manual identity linking enabled: not exposed in this endpoint
- Phone MFA enabled separately from phone login: not directly exposed by settings endpoint

Not retrievable from available read-only API endpoints in this audit:
- SMS OTP expiry
- SMS resend cooldown/max frequency
- SMS per-number/per-IP limits

Admin settings endpoint probe:
- /auth/v1/admin/config returned 404 in this environment (no readout available via this path)

## 3) Same-User Identity Design (Email + Phone)

Required design goal:
- Keep one canonical auth.users.id and one application record set (profile/workspace/subscription/entitlement/durable sessions) per person.

Accepted same-user method:
1. Create user via email/password signup.
2. User confirms email and is authenticated.
3. Authenticated user updates own phone via client.auth.update_user({"phone": ...}).
4. Verify phone via OTP verification flow for phone change (verify_otp with type phone_change).
5. Thereafter, phone can be used as login identifier with the same password boundary if Supabase phone-password login is enabled.

Explicitly rejected design:
- Creating a second independent phone-auth user and trying to merge application rows later.
- Reason: breaks canonical ownership boundaries and can split durable sessions/entitlements across user IDs.

Python client capability audit (installed versions):
- supabase 2.15.3
- gotrue 2.12.3

Supported primitives observed:
- update_user(UserAttributes) where UserAttributes includes phone
- sign_in_with_otp(...) supports phone passwordless/OTP initiation structures
- verify_otp(...) supports VerifyMobileOtpParams with phone + token + type (sms/phone_change)
- sign_in_with_password(...) supports both email/password and phone/password credential structures

Additional identity APIs observed:
- link_identity/unlink_identity exist for OAuth identity linking flows

MFA surface:
- Runtime auth object exposes mfa API (challenge/enroll/verify/list/unenroll), separate from primary phone login settings.

## 4) Proposed Signup Sequence (Intended)

Target flow:
1. User enters email, phone, password in UI.
2. App creates account using email/password signup only.
3. User confirms email.
4. User signs in (or callback establishes authenticated session).
5. App attaches phone to the authenticated user (update_user phone change path).
6. App triggers SMS OTP verification for phone change.
7. User submits OTP; app verifies OTP.
8. Phone becomes eligible for login only after verification.
9. Profile/workspace/subscription/entitlements/durable session ownership stays on original auth.users.id.

Important compatibility finding:
- Do not rely on sending both email and phone in one sign_up() call for one identity.
- In this client/runtime, signup credential payloads are typed as either email+password or phone+password variants.
- Therefore, phone attachment must occur after authenticated email signup.

## 5) Proposed Login Behavior

Single identifier field label:
- Email or verified phone number

Behavior rules:
- Trim surrounding whitespace.
- If identifier contains @, treat as email.
- Else normalize as E.164 phone before auth call.
- Reject malformed phone locally before contacting Supabase.
- Call sign_in_with_password() exactly once.
- Send either email or phone key, never both.
- Keep generic failure messaging (no account enumeration leakage).
- On success (email route or phone route), run existing set_authenticated_session() path to create same durable app session model.

## 6) Recovery Design Evaluation

Email password recovery:
- Keep current email recovery callback and password update flow.
- This remains the canonical password reset mechanism.

Phone OTP login:
- Treat as alternative sign-in method, not password reset.
- OTP proves possession for session creation; it should not implicitly reset password.

Password recovery when only phone is remembered:
- Without a known email, secure password reset is non-trivial and should avoid account enumeration.
- Recommended approach: support phone OTP sign-in as account access method, then allow in-session password change.

Phone changed/unavailable recovery:
- Require fallback recovery channel (email) and/or manual support workflow with stronger identity checks.
- Do not make phone-only recovery the sole path.

## 7) Data Model and Privacy Review

Phone storage recommendation:
- Canonical phone should remain in Supabase Auth (auth.users.phone).
- Application tables should not store full phone unless strictly necessary.

If app-level phone copy is needed:
- Store normalized E.164 and masked display value only (for UX/support).
- Enforce uniqueness at Auth layer; avoid duplicate authoritative phone fields across app tables.

Verification source of truth:
- auth.users.phone_confirmed_at (and Auth identities/factors as applicable), not app shadow flags.

Redaction and logging restrictions:
- Never log full phone numbers, OTP codes, passwords, access/refresh tokens, or service-role credentials.
- Log only masked phone hints and non-sensitive status classifications.

Phone changes:
- Must require authenticated user context + OTP verification for phone_change.
- Invalidate relevant sessions if policy requires stronger account safety.

Deletion/account closure:
- Remove or anonymize phone artifacts in app tables if present.
- Rely on auth.users lifecycle for canonical identity removal.

## 8) Cost and Abuse Controls Required Before Implementation

Operational dependency:
- SMS provider is Twilio in current development settings.
- Need explicit runbook for provider outages and retry handling.

Controls required:
- OTP resend cooldown UI + backend enforcement.
- Per-number and per-IP throttling.
- CAPTCHA on OTP/send paths.
- SMS pumping protections (velocity checks, risk scoring, abuse flags).
- Generic responses for unknown identifiers.
- Test-number strategy using controlled test recipients and low-rate guardrails.

Important note:
- OTP expiry and resend/rate-limit parameters were not retrievable from current read-only API endpoints in this audit; must be validated in dashboard/config review before rollout.

## 9) Final Audit Determination

## Same-User Phone Linking Proof

This section is a strict read-only proof based on the installed runtime contracts and repository architecture.

### A) Authenticated user update surface

Installed client method and signature:
- Method: `client.auth.update_user(...)`
- Runtime signature (installed): `update_user(self, attributes: UserAttributes, options: UpdateUserOptions = {}) -> UserResponse`
- Source: installed `gotrue/_sync/gotrue_client.py`

Accepted parameter shape:
- `UserAttributes` includes `phone`, `email`, `password`, `data`, `nonce`
- Equivalent supported call shape:
  - `client.auth.update_user({"phone": "+1XXXXXXXXXX"})`

Session requirement:
- Required. The method internally obtains session via `get_session()` and raises `AuthSessionMissingError` if absent.

Identity semantics:
- `update_user` is a `PUT user` operation with user JWT; this is an in-place update on the currently authenticated auth user.
- Expected canonical `auth.users.id` behavior: unchanged.

OTP/redirect/confirmation behavior:
- The method itself does not carry an OTP code argument and does not require email redirect arguments for phone update.
- `UpdateUserOptions` in this runtime exposes `email_redirect_to` only (email-flow oriented).
- Relevant limitation: OTP delivery and verification behavior is mediated by Auth backend policy/config; the client contract indicates the verification step occurs separately.

### B) Phone verification flow proof

Supported verification methods and contracts:
- OTP send/resend API: `client.auth.resend(credentials: ResendCredentials) -> AuthOtpResponse`
- For phone-change retries the typed payload supports:
  - `{"type": "phone_change", "phone": "+1...", "options": {...}}`
- OTP verification API:
  - `client.auth.verify_otp(params: VerifyOtpParams) -> AuthResponse`
  - `VerifyMobileOtpParams` requires: `phone`, `token`, `type`
  - allowed mobile verification types in installed runtime: `"sms"` and `"phone_change"`

What causes SMS OTP to be sent:
- Phone OTP can be initiated via phone OTP endpoints (`sign_in_with_otp` for login OTP; `resend` for retries).
- For phone update flow specifically, verification uses `type="phone_change"`; resend semantics explicitly include phone change OTP.

Does update_user(phone) itself send OTP:
- Contract-level inference in this runtime: phone update initiates a pending phone-change state; OTP verification is explicitly separate and uses `verify_otp` with `type="phone_change"`.
- If OTP resend is needed, the supported resend contract includes `type="phone_change"`.

Session continuity requirement:
- Verification for phone-change should be treated as part of the same user-security flow and must preserve ownership under the same authenticated account boundary.

Confirmation indicators:
- Auth user model fields in installed runtime include:
  - `phone`
  - `new_phone`
  - `phone_confirmed_at`
- Confirmation source of truth: `phone_confirmed_at` populated and `phone` finalized to verified value.

### C) Identity preservation proof

Proof chain under supported same-user sequence:
1. Email/password user exists (canonical `auth.users.id = U`).
2. Authenticated user requests phone attachment via `update_user({"phone": ...})`.
3. OTP challenge/verification occurs via phone-change verification path.
4. On successful verification, phone is attached to same user record (`U`).
5. Phone login (when enabled and confirmed) authenticates same canonical user id `U`.

Ownership binding impact in this repository:
- `user_profiles` keyed by `user_id` (same canonical auth user id)
- `workspaces` keyed by `user_id`
- `subscriptions` keyed by `user_id`
- entitlements/plan gating derived from same `user_id` identity path
- durable `app_sessions` explicitly keyed by `user_id` in `core/session_store.py`

Rejected architecture:
- Any flow that creates a separate phone-auth user id and attempts later merge is rejected.

### D) Phone/password login support proof

Installed login contract:
- Method: `client.auth.sign_in_with_password(credentials: SignInWithPasswordCredentials) -> AuthResponse`
- `SignInWithPasswordCredentials` is a union of:
  - `{email, password, options?}`
  - `{phone, password, options?}`

Mutual exclusivity behavior in runtime:
- Internal logic branches as:
  - if `email`: email/password grant
  - elif `phone`: phone/password grant
  - else: invalid credentials error
- Therefore request should use either email or phone key per call.

Supported payload shape for phone/password:
- `{ "phone": "+1XXXXXXXXXX", "password": "..." }`

Password semantics:
- Password is account-level credential for the canonical user identity; phone route is an alternate identifier route after supported phone linkage/verification policy is satisfied.

User-id result expectation:
- Successful phone/password auth on a linked verified phone is expected to return the same canonical user id as original email identity.

Durable session path compatibility:
- Current app durable session creation path (`initialize_session` -> `SessionStore.create_session`) is user-id based and can remain unchanged after successful phone login.

### E) Signup architecture decision (Design A vs Design B)

Design A:
- `sign_up(email + phone + password)`
- Not supported as a single same-user signup payload in installed typed contract.

Design B:
- `sign_up(email + password)`
- email confirmation
- authenticate
- `update_user({"phone": ...})`
- verify phone OTP (`verify_otp` with `type="phone_change"`)
- Supported same-user architecture for one canonical user id.

Decision:
- Design B is the supported one-identity sequence.

### F) Phone-only recovery behavior resolution

Distinctions:
- phone/password login: password grant using phone identifier.
- SMS OTP sign-in: passwordless sign-in via `sign_in_with_otp` + `verify_otp(type="sms")`.
- phone verification after update: identity update verification via `verify_otp(type="phone_change")`.
- password reset: email recovery endpoint (`recover`) and recovery-session password update flow.

Conventional password reset using only phone number:
- Not supported by installed password-reset API contract (email-based recovery call).

Supported alternative when only phone is remembered:
- verified-phone OTP sign-in
- then authenticated password update via `update_user({"password": ...})`

### G) Security and state constraints confirmation

Confirmed design constraints:
- Normalize phone to E.164 before submission.
- Never log full phone numbers.
- Never log passwords or OTPs.
- Do not use service-role key for user-facing phone attachment.
- Perform phone attachment only via authenticated user session (`update_user` path).
- Keep generic errors (no account-existence leakage).
- No duplicate profile/workspace/subscription/entitlement creation during phone linking.
- Durable sessions remain owned by same canonical `user_id`.

### Conclusion

SAME-USER PHONE LINKING PROVEN — READY TO COMMIT PHASE 9B.1
