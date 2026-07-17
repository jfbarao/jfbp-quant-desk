# Phase 9A.1 Session Security Threat Model

Status: Threat model only. No implementation changes.

## Assets
- User authenticated session continuity
- Supabase refresh-capable auth material
- Session handle integrity
- Cross-user isolation

## Trust Boundaries
- Browser <-> Streamlit app
- Streamlit app <-> Supabase Auth
- Streamlit app <-> durable session table

## Threats and Controls

### 1) Stolen Cookie
Threat:
- Attacker obtains cookie value.

Controls:
- Cookie contains opaque handle only (no refresh token).
- Store only hashed handle server-side.
- Short idle timeout + absolute max.
- Device/user-agent consistency checks (soft controls).
- Session rotation and revocation support.

Residual risk:
- Replay possible if handle valid and no additional checks.

### 2) Replayed Session Handle
Threat:
- Captured handle reused.

Controls:
- Handle hash lookup + revocation checks.
- Optional binding hints (UA hash/fingerprint hash).
- Rotation on sensitive events and periodic refresh boundary.

### 3) Session Fixation
Threat:
- Attacker sets victim session handle before login.

Controls:
- Always generate new handle at login success.
- Invalidate pre-login anonymous handle on auth upgrade.

### 4) XSS Exposure
Threat:
- If cookie is script-readable in pure Streamlit, XSS can steal handle.

Controls:
- Opaque handle only, no raw refresh token client-side.
- CSP/hardening and output sanitization where possible.
- Prefer HttpOnly if future infra supports edge cookie setting.

### 5) CSRF Relevance
Threat:
- Cross-site request abuse.

Controls:
- SameSite=Lax for session handle cookie.
- CSRF token for state-changing endpoints if external APIs are added.

### 6) Database Compromise
Threat:
- Session table leak.

Controls:
- Store handle hash only.
- Encrypt refresh material at app layer.
- Principle-of-least-privilege DB access.
- Audit logging and key rotation.

### 7) Refresh Token Exposure
Threat:
- Refresh material stolen from app logs/db/client.

Controls:
- Never log token values.
- Keep refresh token server-side only.
- Encrypt at rest with managed key secret and key id metadata.

### 8) Concurrent Session Abuse
Threat:
- Unlimited active sessions increase abuse window.

Controls:
- Max concurrent sessions per user.
- Oldest-session revocation on limit breach.
- Admin/user logout-all capability.

### 9) Stale or Revoked Session Reuse
Threat:
- Expired/revoked sessions still accepted.

Controls:
- Enforce expiry/revocation checks on every rehydrate.
- Cleanup jobs + fail-closed behavior.

### 10) User Isolation Across Streamlit Sessions
Threat:
- Shared server object leaks auth state between users.

Controls:
- Never treat singleton in-memory cache as source of truth.
- Always bind session to cookie handle + user_id row.
- Validate user consistency before materializing runtime state.

### 11) Accidental Global Supabase Client Auth-State Sharing
Threat:
- Cached client object receives `set_session(...)` and leaks session context.

Controls:
- Avoid global mutable auth state for per-user security decisions.
- Recreate or isolate auth context per request/session restoration path.
- Ensure every privileged operation validates intended user id.

## Security Posture Summary
- Preferred: opaque handle cookie + durable server-side session with encrypted refresh material.
- This minimizes client-side secret exposure while preserving restart-safe rehydration.
