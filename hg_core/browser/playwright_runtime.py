"""
Playwright-backed browser session and screenshot capture (Social Media Entity Tools).
Stub: when Playwright is not installed or not requested, falls back to base BrowserRuntime.
Real integration: launch browser, navigate, capture screenshot to artifact path, update DB.
"""

from __future__ import annotations

from hg_core.browser.runtime import BrowserRuntime

_RUNTIME: BrowserRuntime | None = None


def get_playwright_runtime() -> BrowserRuntime:
    """Return a Playwright-backed runtime if available, otherwise the base stub runtime."""
    global _RUNTIME
    if _RUNTIME is not None:
        return _RUNTIME
    try:
        from hg_core.browser._playwright_impl import PlaywrightBrowserRuntime  # noqa: F401
        _RUNTIME = PlaywrightBrowserRuntime()
    except ImportError:
        _RUNTIME = BrowserRuntime()
    return _RUNTIME
