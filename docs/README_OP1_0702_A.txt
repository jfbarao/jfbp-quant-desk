🚧 BUILD MARKER: OP1-0702-A

Localhost-only patch package.

What changed:
- Preserved the canonical lifecycle sync from OP1-0701-H.
- Retired the old placeholder Decision Review value of 35.0.
- Added a checklist-based Decision Readiness score.
- Unified the Options Decision Center KPI and Step 5 approval panel around Decision Readiness.
- Removed OTCC_TRACE console noise while keeping a no-op hook for compatibility.

Files included:
- decision_packet.py
- trade_lifecycle_packet.py
- Options_Center.py
- Options_Trade_Construction_Center.py
- Trade_Command_Center.py
