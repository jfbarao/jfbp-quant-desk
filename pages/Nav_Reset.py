from __future__ import annotations

import streamlit as st


st.set_page_config(page_title="Navigation Reset", layout="wide")


def _run() -> None:
    """One-shot trampoline page used to force a native page transition.

    This helps reset browser scroll position when a same-script rerun keeps the
    previous viewport offset.
    """
    primary_target = str(st.session_state.get("jfbp_nav_reset_return_target", "run_app.py") or "run_app.py").strip()
    candidates = st.session_state.get("jfbp_nav_reset_return_candidates", ["run_app.py", "app.py"])
    if not isinstance(candidates, list):
        candidates = ["run_app.py", "app.py"]

    ordered_targets = []
    for target in [primary_target] + [str(item or "").strip() for item in candidates]:
        if target and target not in ordered_targets:
            ordered_targets.append(target)

    for target in ordered_targets:
        try:
            st.switch_page(target)
            return
        except Exception:
            continue

    st.rerun()


_run()
