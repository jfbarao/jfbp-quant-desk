from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components


def scroll_to_top(navigation_counter: int = 0) -> None:
    """Reset viewport scroll position to top on each page load.

    Uses a tiny components iframe script because it is the most reliable way to
    execute browser-side scrolling in Streamlit across reruns/navigation.
    """
    html = """
        <script>
            (function () {
                var navCounter = __NAV_COUNTER__;
                var startedAt = Date.now();
                var lockDurationMs = 1400;

                function withinLockWindow() {
                    return (Date.now() - startedAt) <= lockDurationMs;
                }

                function disableScrollRestoration(win) {
                    try {
                        if (win && win.history && 'scrollRestoration' in win.history) {
                            win.history.scrollRestoration = 'manual';
                        }
                    } catch (e) {}
                }

                function getDoc() {
                    try {
                        if (window.parent && window.parent !== window && window.parent.document) {
                            return window.parent.document;
                        }
                    } catch (e) {}
                    return document;
                }

                function resetScroll() {
                    var doc = getDoc();
                    var candidates = [
                        doc.scrollingElement,
                        doc.documentElement,
                        doc.body,
                        doc.querySelector('[data-testid="stAppViewContainer"]'),
                        doc.querySelector('[data-testid="stApp"]'),
                        doc.querySelector('section.main'),
                        doc.querySelector('.main'),
                        doc.querySelector('.stApp'),
                        doc.querySelector('[data-testid="block-container"]'),
                        doc.querySelector('.block-container')
                    ];

                    try {
                        window.scrollTo(0, 0);
                    } catch (e) {}

                    try {
                        if (window.parent && window.parent !== window) {
                            window.parent.scrollTo(0, 0);
                        }
                    } catch (e) {}

                    try {
                        document.documentElement.scrollTop = 0;
                    } catch (e) {}

                    try {
                        document.body.scrollTop = 0;
                    } catch (e) {}

                    try {
                        for (var i = 0; i < candidates.length; i += 1) {
                            var node = candidates[i];
                            if (!node) {
                                continue;
                            }
                            try {
                                node.scrollTop = 0;
                            } catch (e) {}
                            try {
                                if (typeof node.scrollTo === 'function') {
                                    node.scrollTo(0, 0);
                                }
                            } catch (e) {}
                        }
                    } catch (e) {}

                    try {
                        var shell = doc.querySelector('[data-testid="stApp"]') || doc.body;
                        if (shell && typeof shell.scrollIntoView === 'function') {
                            shell.scrollIntoView(true);
                        }
                    } catch (e) {}
                }

                disableScrollRestoration(window);
                try {
                    if (window.parent && window.parent !== window) {
                        disableScrollRestoration(window.parent);
                    }
                } catch (e) {}

                function lockToTopTick() {
                    resetScroll();
                    if (withinLockWindow()) {
                        setTimeout(lockToTopTick, 90);
                    }
                }

                resetScroll();
                setTimeout(resetScroll, 80);
                setTimeout(resetScroll, 220);
                setTimeout(resetScroll, 500);
                setTimeout(resetScroll, 1000);
                setTimeout(resetScroll, 1800);
                lockToTopTick();

                try {
                    document.body.setAttribute('data-jfbp-nav-counter', String(navCounter));
                } catch (e) {}
            })();
        </script>
        """.replace("__NAV_COUNTER__", str(int(navigation_counter)))

    key = f"jfbp_scroll_reset_{int(navigation_counter)}"
    try:
        components.html(html, height=1, width=1, key=key)
    except TypeError:
        components.html(html, height=1, width=1)
