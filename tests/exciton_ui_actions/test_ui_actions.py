"""UI action contract tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.exciton.control_matrix import CONTROL_MATRIX

APP = Path(__file__).resolve().parents[2] / "apps" / "exciton"


def test_enabled_controls_map_to_matrix():
    html = (APP / "index.html").read_text(encoding="utf-8")
    for cid in ("REFRESH_STATUS", "STOP_SOAK", "PANIC_STOP", "CREATE_AUTO_APPROVAL_RULE"):
        assert cid in html
        assert cid in CONTROL_MATRIX


def test_approval_mode_control_exists():
    html = (APP / "index.html").read_text(encoding="utf-8")
    assert "CHANGE_APPROVAL_MODE" in html
    assert "READ_DRAFT_ONLY" in html
    assert "PUBLISH_DISABLED" in html


def test_operator_queue_api_used_in_js():
    js = (APP / "app.js").read_text(encoding="utf-8")
    assert "/api/exciton/operator-queue" in js


def test_web_queue_api_used_in_js():
    js = (APP / "app.js").read_text(encoding="utf-8")
    assert "/api/exciton/web-actions" in js


def test_auto_approval_api_used_in_js():
    js = (APP / "app.js").read_text(encoding="utf-8")
    assert "/api/exciton/auto-approval-rules" in js


def test_safe_blockers_visible():
    html = (APP / "index.html").read_text(encoding="utf-8")
    assert "safe-blockers" in html
