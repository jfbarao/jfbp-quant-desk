# Phase 9C Production Configuration Contract

Date: 2026-07-18
Scope: Authentication + durable-session production configuration contract (sanitized)
Repository: /Users/josepereira/rs_clean

## 1. Canonical Secret Sources

Runtime reads configuration from Streamlit secrets first, then environment fallback.

- Primary: `.streamlit/secrets.toml` or deployment-managed Streamlit secret store.
- Secondary fallback: process environment variables.
- Canonical readers:
  - `core/environment_validation.py` via `_secret_value(...)` and `build_runtime_config_from_secrets(...)`
  - `pages/SaaS_Core.py` via `_secret_value(...)`
  - `core/session_store.py` via `_secret_value(...)`
  - `core/session_crypto.py` via `_secret_value(...)`

No secret values are recorded in this contract.

## 2. Required Production Keys

### Environment and Boundary

- `APP_ENV`
  - Required: yes
  - Expected: `production`
  - Format: literal string in `{development, production}` (aliases accepted by validator)
  - Consumer: `core/environment_validation.py`, `app.py`, `pages/SaaS_Core.py`
  - Missing/invalid behavior: fail closed at startup (`validate_runtime_environment`)
  - Server-only: yes
  - Rotation impact: none

- `SUPABASE_URL`
  - Required: yes
  - Expected class: production project URL (`https://<production-ref>.supabase.co`)
  - Consumer: Supabase client init + SessionStore REST/RPC
  - Missing/invalid behavior: fail closed in environment validation
  - Server-only: yes
  - Rotation impact: restart required; active sessions become unusable if project changes

- `SUPABASE_ANON_KEY`
  - Required: yes
  - Expected class: production anon JWT key matching production project ref
  - Consumer: browser/runtime auth client (`create_client`)
  - Missing/invalid behavior: fail closed in environment validation
  - Server-only: no (publishable by design)
  - Rotation impact: restart required; existing auth clients may need re-auth

- `SUPABASE_SERVICE_ROLE_KEY`
  - Required: yes
  - Expected class: production service-role key matching production project ref
  - Consumer: `core/session_store.py` REST/RPC and server-side provisioning paths
  - Missing/invalid behavior: fail closed in environment validation; SessionStore init raises if missing
  - Server-only: strictly yes
  - Rotation impact: restart required; preserve old key only for overlap cutover if needed

- `SUPABASE_EMAIL_REDIRECT_TO`
  - Required: yes
  - Expected class: HTTPS production app callback/entry URL, non-localhost
  - Consumer: signup callback flow in `pages/SaaS_Core.py`
  - Missing/invalid behavior: fail closed in environment validation
  - Server-only: no
  - Rotation impact: no active-session invalidation; restart recommended

### Session and Cookie Keys

- `SESSION_ENCRYPTION_KEY`
  - Required: yes
  - Expected format: strong random secret, minimum 32 characters (validator enforced)
  - Consumer: `core/session_crypto.py` for refresh material encryption/decryption
  - Missing/invalid behavior: fail closed in environment validation and `SessionCrypto`
  - Server-only: strictly yes
  - Rotation impact: restart required; decrypt of existing ciphertext may fail unless versioned old key remains configured
  - Replica consistency: must match across replicas for active ciphertext interoperability

- `SESSION_COOKIE_SIGNING_KEY`
  - Required: yes
  - Expected format: strong random secret, minimum 32 characters (validator enforced)
  - Consumer: `pages/SaaS_Core.py` cookie signature and verification
  - Missing/invalid behavior: fail closed in environment validation; cookie signing/verify errors at runtime
  - Server-only: strictly yes
  - Rotation impact: restart required; existing signed cookies become invalid after rotation
  - Replica consistency: must match across replicas to avoid cross-instance logout/rehydration failures

- `SESSION_ENCRYPTION_KEY_VERSION`
  - Required: recommended
  - Expected format: version label such as `v1`
  - Consumer: `core/session_crypto.py`
  - Missing behavior: defaults to `v1`
  - Server-only: yes
  - Rotation impact: required for controlled multi-key rotation

- `SESSION_ENCRYPTION_KEY_<VERSION>`
  - Required: optional, for backward decryption during rotation
  - Expected format: key material matching previous ciphertext version
  - Consumer: `core/session_crypto.py` decrypt path
  - Server-only: yes
  - Rotation impact: allows graceful rolling rotation without immediate ciphertext invalidation

### Stripe and Billing

- `STRIPE_MODE`
  - Required: yes
  - Expected: `live` in production (`test` in development)
  - Consumer: `core/environment_validation.py`
  - Missing/invalid behavior: fail closed in environment validation
  - Server-only: yes
  - Rotation impact: restart required

- `STRIPE_SECRET_KEY`
  - Required: yes for checkout/portal operations
  - Expected format: `sk_live_...` when `STRIPE_MODE=live`
  - Consumer: `pages/SaaS_Core.py` checkout session creation
  - Missing/invalid behavior: checkout fails with sanitized runtime message; env validator rejects mode/key prefix mismatch
  - Server-only: strictly yes
  - Rotation impact: restart required; no durable-session invalidation

- `STRIPE_BILLING_PORTAL_URL`
  - Required: yes in production, prohibited in development (validator enforced)
  - Expected format: valid HTTPS Stripe billing portal login URL
  - Consumer: `app.py` Manage Plan button resolver
  - Missing/invalid behavior: fail closed in environment validation; UI also fails closed by hiding portal button outside production
  - Server-only: no (URL only)
  - Rotation impact: restart recommended

- `MARKET_PULSE_PRICE_ID`, `PRO_PRICE_ID`, `ELITE_PRICE_ID`
  - Required: yes for paid plan upgrades
  - Expected format: Stripe price IDs
  - Consumer: `pages/SaaS_Core.py`
  - Missing behavior: checkout action fails clearly with missing-key message
  - Server-only: yes
  - Rotation impact: no session invalidation

- `STRIPE_SUCCESS_URL`, `STRIPE_CANCEL_URL`
  - Required: optional but recommended
  - Expected format: valid app URLs matching environment boundary
  - Consumer: `pages/SaaS_Core.py`
  - Missing behavior: code falls back to configured app URL defaults
  - Server-only: no

## 3. Session Cookie Contract

- Cookie name: `opaque_session_handle`
- Stored payload: signed opaque session handle only
- Not stored in cookie: access token, refresh token, JWT, service keys
- Signature algorithm: HMAC-SHA256
- `Secure` flag: enabled only when `APP_ENV` resolves to production
- `SameSite`: `lax`
- `Path`: `/`
- Domain: default host scope (not manually overridden)

## 4. Restart and Rotation Rules

- Restart required after changing:
  - `SUPABASE_URL`
  - `SUPABASE_ANON_KEY`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `SESSION_ENCRYPTION_KEY`
  - `SESSION_COOKIE_SIGNING_KEY`
  - `STRIPE_MODE`
  - `STRIPE_SECRET_KEY`
  - `STRIPE_BILLING_PORTAL_URL`

- Rotating `SESSION_COOKIE_SIGNING_KEY` invalidates existing browser cookies immediately.
- Rotating `SESSION_ENCRYPTION_KEY` can invalidate stored refresh material unless prior-version keys are retained.
- All session and crypto keys must match across all production replicas.

## 5. Client Exposure Rules

Safe client-visible values:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY` (publishable)
- redirect URLs
- Stripe portal and success/cancel URLs

Must remain server-only:
- `SUPABASE_SERVICE_ROLE_KEY`
- `SESSION_ENCRYPTION_KEY`
- `SESSION_COOKIE_SIGNING_KEY`
- `SESSION_ENCRYPTION_KEY_<VERSION>`
- `STRIPE_SECRET_KEY`

## 6. Sanitized Example (Placeholders Only)

```toml
APP_ENV = "production"
SUPABASE_URL = "<production-supabase-url>"
SUPABASE_ANON_KEY = "<production-anon-key>"
SUPABASE_SERVICE_ROLE_KEY = "<production-service-role-key>"
SUPABASE_EMAIL_REDIRECT_TO = "<production-confirmation-url>"
SESSION_ENCRYPTION_KEY = "<strong-random-key-min-32-chars>"
SESSION_COOKIE_SIGNING_KEY = "<strong-random-key-min-32-chars>"
SESSION_ENCRYPTION_KEY_VERSION = "v1"
STRIPE_MODE = "live"
STRIPE_SECRET_KEY = "<production-stripe-secret-key>"
STRIPE_BILLING_PORTAL_URL = "<production-stripe-billing-portal-url>"
MARKET_PULSE_PRICE_ID = "<price-id>"
PRO_PRICE_ID = "<price-id>"
ELITE_PRICE_ID = "<price-id>"
STRIPE_SUCCESS_URL = "<production-success-url>"
STRIPE_CANCEL_URL = "<production-cancel-url>"
```