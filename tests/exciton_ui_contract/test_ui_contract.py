"""EXCITON Phase 0 — UI contract tests. No internet, no analytics, all panels referenced."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.exciton.panel_registry import REQUIRED_PANELS

WORKSPACE = Path(__file__).resolve().parents[2]
APP = WORKSPACE / "apps" / "exciton"


def _bundle() -> str:
    text = ""
    for name in ("index.html", "app.js", "styles.css"):
        text += (APP / name).read_text(encoding="utf-8")
    return text


def test_ui_files_exist():
    for name in ("index.html", "app.js", "styles.css"):
        assert (APP / name).exists()


@pytest.mark.parametrize("panel", REQUIRED_PANELS)
def test_ui_references_every_required_panel(panel):
    assert panel in _bundle()


def test_ui_has_stop_and_panic_controls():
    html = (APP / "index.html").read_text(encoding="utf-8")
    assert 'data-control="stop_agent"' in html
    assert 'data-control="panic_stop"' in html


def test_ui_has_refresh_and_notes_controls():
    html = (APP / "index.html").read_text(encoding="utf-8")
    assert 'data-control="refresh_status"' in html
    assert 'data-control="add_operator_note"' in html


def test_ui_has_no_external_network_or_analytics():
    bundle = _bundle().lower()
    # An external URL scheme anywhere in the bundle is the strongest signal of a network
    # dependency; analytics SDK tokens cover the rest. (Prose like "no analytics" is fine —
    # we match concrete references, not the word.)
    banned = [
        "://", "//cdn", "googletagmanager", "google-analytics", "gtag(",
        "mixpanel", "segment.com", "sentry.io", "fonts.googleapis", "fonts.gstatic",
        "src=\"http", "href=\"http",
    ]
    for needle in banned:
        assert needle not in bundle, f"external/analytics reference found: {needle}"


def test_ui_only_fetches_local_snapshot():
    app_js = (APP / "app.js").read_text(encoding="utf-8")
    # The only fetch targets are the local snapshot file and a local fixture path.
    assert "status_snapshot.json" in app_js
    assert "fetch(" in app_js
    # No absolute URLs in fetch calls.
    assert "fetch(\"http" not in app_js.replace(" ", "")


def test_ui_states_invariant_no_authority():
    html = (APP / "index.html").read_text(encoding="utf-8").lower()
    assert "permission_granted=false" in html
    assert "authority_created=false" in html
