# Schema Recovery Investigation (Phases 0-2)

## Purpose
This directory preserves the permanent documentation and analysis from the schema recovery investigation for the development environment.

## Confirmed Missing Development Tables
The development project was confirmed missing these public tables:
- public.user_profiles
- public.subscriptions
- public.workspaces

## Phase Outcomes
- Phase 0: no canonical migration source was found in repository history.
- Phase 1: migration readiness concluded NOT READY.
- Phase 2: recommendation concluded OPTION A.

## Current Decision
No migration may be generated until canonical PostgreSQL metadata is acquired through an approved read-only evidence channel.

## Required Future Metadata
Before migration authoring, the following canonical metadata is required:
- physical column definitions
- PK/FK/UNIQUE/CHECK constraints
- indexes
- RLS policies and grants
- triggers and functions
