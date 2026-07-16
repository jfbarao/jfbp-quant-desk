# Phase 6 Test Results

Environment:
- Interpreter: /Users/josepereira/rs_clean/venv/bin/python
- Date: 2026-07-16

## Focused suite (smallest relevant first)
Command:
- /Users/josepereira/rs_clean/venv/bin/python -m pytest tests/test_phase6_canonical_compat.py -q

Result:
- 10 passed
- 0 failed
- 1 warning (supabase gotrue deprecation warning)

## Broader regression suite
Command:
- /Users/josepereira/rs_clean/venv/bin/python -m pytest -m "not integration" -q

Result:
- 10 passed
- 0 failed
- 3 deselected (integration-marked)
- 1 warning (same deprecation warning)

## Guardrail verification during tests
- No SQL executed.
- No migration generation.
- No Supabase schema operations.
