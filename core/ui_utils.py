from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components


def scroll_to_top() -> None:
    """Reset viewport scroll position to top on each page load.

    Uses a tiny components iframe script because it is the most reliable way to
    execute browser-side scrolling in Streamlit across reruns/navigation.
    """
    components.html(
        """
        <script>
            (function () {
                try {
                    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
                } catch (e) {
                    window.scrollTo(0, 0);
                }

                try {
                    if (window.parent && window.parent !== window) {
                        window.parent.scrollTo({ top: 0, left: 0, behavior: 'auto' });
                    }
                } catch (e) {
                    try {
                        if (window.parent && window.parent !== window) {
                            window.parent.scrollTo(0, 0);
                        }
                    } catch (ignored) {}
                }

                try {
                    const root = window.parent?.document?.querySelector('[data-testid="stAppViewContainer"]');
                    if (root) {
                        root.scrollTo({ top: 0, left: 0, behavior: 'auto' });
                    }
                } catch (e) {}
            })();
        </script>
        """,
        height=0,
        width=0,
    )
