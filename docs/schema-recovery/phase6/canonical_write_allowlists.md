# Phase 6 Canonical Write Allowlists

Source of truth:
- runtime_state/schema_recovery_phase3_20260715_211215/normalized_catalog.json

Implementation boundary:
- core/canonical_schema.py
- CANONICAL_TABLE_COLUMNS
- filter_canonical_payload(table_name, payload, context, logger)

## public.user_profiles
- id
- created_at
- email
- full_name
- plan
- account_status
- trial_start
- trial_end
- user_id
- stripe_customer_id
- stripe_subscription_id

## public.subscriptions
- id
- user_id
- plan
- status
- stripe_customer_id
- stripe_subscription_id
- created_at

## public.workspaces
- id
- user_id
- workspace_name
- created_at

## Enforcement points
- pages/SaaS_Core.py
  - _create_profile_record
  - _create_subscription_record
  - _create_workspace_record
  - _save_login_metadata
- pages/Admin_Control_Center.py
  - update_customer_plan_status
  - update_customer_trial_controls
  - update_customer_profile_fields
  - apply_repair_provisioning

## Drift logging
- All filter calls log dropped fields with CANONICAL_FILTER table/context/dropped keys.
- Non-canonical query guard logs use CANONICAL_COMPAT messages.
