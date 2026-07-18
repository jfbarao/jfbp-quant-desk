# Phase 9A.3 Recovery Callback Formats

This document defines the intentionally supported password-recovery callback formats for the current Streamlit and Supabase Python runtime.

## Installed SDK basis

The current implementation is aligned to the installed Python Supabase Auth stack (`gotrue` 2.12.3 behavior observed during validation):

- `verify_otp({"type": "recovery", "token_hash": ...})` is supported for recovery.
- `verify_otp({"type": "recovery", "token": ..., "email": ...})` is supported for email OTP verification.
- `exchange_code_for_session(code)` may be used when the callback supplies a code-style exchange value.
- A callback that already contains `access_token` and `refresh_token` can be applied directly to the client session.

## Intentionally supported callback formats

The server-side recovery flow only supports callback data that arrives in the URL query string.

Supported formats:

1. `?type=recovery&token_hash=...`
   Reason: this is the cleanest server-compatible format for the installed Python SDK. The app calls `verify_otp` with `token_hash` and `type="recovery"`.

2. `?type=recovery&token=...&email=...`
   Reason: for plain OTP verification, the installed SDK requires the token plus exactly one identity field. The app passes `email` when present.

3. `?type=recovery&code=...`
   Reason: some auth flows expose a code exchange step. The app uses `exchange_code_for_session(...)` when the client supports it.

4. `?type=recovery&access_token=...&refresh_token=...`
   Reason: if the callback already contains a session, the app can apply it directly without calling OTP verification again.

## Intentionally unsupported callback formats

Unsupported format:

1. `#access_token=...&refresh_token=...`
   Reason: URL fragments are browser-local and are not delivered to Streamlit's Python server through `st.query_params`. A pure server-side Streamlit page cannot rely on fragment data unless a dedicated front-end bridge is implemented and maintained.

## Why this matters

If the Supabase email template or project callback behavior changes, recovery will only continue to work if the callback still arrives in one of the supported query-string formats above.

If a future SDK or template change starts delivering only URL fragments, this application must either:

1. introduce a maintained front-end callback bridge that safely converts fragment data into a server-visible format, or
2. change the recovery email/callback template to use `token_hash` or another supported query-string format.
