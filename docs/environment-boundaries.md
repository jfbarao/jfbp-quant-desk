# Phase 9D Environment Boundaries

This project enforces strict environment boundaries at startup.

## Required Mapping

- Local development
  - Supabase project ref: qkqexvlprzjqjtsarqbz
  - Stripe mode: test
  - Redirect hosts: localhost
- Live production
  - Supabase project ref: zqzujesufquifrtqnanb
  - Stripe mode: live
  - Redirect hosts: production hosts

## Required Secrets

- APP_ENV: development or production
- SUPABASE_URL
- SUPABASE_ANON_KEY
- SUPABASE_SERVICE_ROLE_KEY
- SUPABASE_EMAIL_REDIRECT_TO
- SUPABASE_PASSWORD_RESET_REDIRECT_TO (optional override, defaults by APP_ENV)
- STRIPE_MODE: test or live
- STRIPE_SECRET_KEY
- MARKET_PULSE_PRICE_ID
- PRO_PRICE_ID
- ELITE_PRICE_ID
- STRIPE_SUCCESS_URL (optional)
- STRIPE_CANCEL_URL (optional)

## Fail-Fast Rules

Startup validation blocks app execution when any rule fails:

- SUPABASE_URL ref must match APP_ENV.
- SUPABASE_ANON_KEY and SUPABASE_SERVICE_ROLE_KEY must belong to the same project as SUPABASE_URL.
- development cannot use production ref.
- production cannot use development ref.
- development cannot use Stripe live mode.
- production cannot use Stripe test mode.
- localhost redirect targets are blocked in production.
- production redirect hosts are blocked in development.

No secret values are printed in validation errors.

## Manual Dashboard Configuration

In each Supabase project, configure Auth redirect allow-lists for the matching hosts:

- Development project: include http://localhost:8501/**
- Production project: include https://jfbpquantdesk.com/** (or your final production login host)

Keep local and production secrets in separate secret stores. Do not commit real secret files.
