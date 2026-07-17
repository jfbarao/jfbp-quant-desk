# Phase 9A.3 Decision Summary

## Cookie Library
- `extra-streamlit-components`

## Selection Rationale
- Best maintained among evaluated Streamlit cookie options.
- Supports cookie options required for production/localhost compatibility.
- Minimal integration overhead in current architecture.

## Startup Flow
- Cookie read -> signature verify -> durable session lookup -> status checks -> refresh-based auth restore -> rebuild session state.

## Login Flow
- Existing Supabase login retained.
- Durable app session created on success.
- Signed opaque handle cookie issued.
- Session state populated as before.

## Logout Flow
- Current session revoke + cookie clear + state clear.
- Logout-all service wiring available (`supabase_logout_all`) without new UI.

## Restoration Flow
- Uses server-side refresh material from durable store.
- Uses fresh client auth refresh path.
- Clears invalid cookie and gracefully falls back to Secure Access on failure.

## Remaining Risks
- Component-cookie model cannot enforce HttpOnly in pure Streamlit.
- Requires strong XSS hygiene and secret management discipline.

## Production Readiness
- Ready for controlled staging validation after manual browser confirmation of cookie behavior and secret handling.
- Phase 9B (Stripe Checkout) should wait until the auth layer is accepted with the documented limitations below.

## Limitations
- HttpOnly cannot be enforced in the Streamlit component-cookie model.
- The current focused test suite does not explicitly exercise workspace or entitlement mismatch branches.
- Real-browser cookie handling still needs manual validation before a production claim.
