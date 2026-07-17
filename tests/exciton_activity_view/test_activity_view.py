"""Activity view tests."""

from __future__ import annotations

from hg_runtime.exciton.activity_view import HUMAN_STATES, HEADLINES, build_activity_view
from hg_runtime.exciton.gate_helpers import scan_forbidden


def test_required_fields_present():
    view = build_activity_view()
    for field in (
        "current_mode", "current_cycle", "current_task", "current_state",
        "last_action", "current_safety_checks", "current_blockers",
        "pending_approvals", "stop_panic_state", "headline",
    ):
        assert field in view


def test_human_state_in_closed_enum():
    view = build_activity_view()
    assert view["current_state"] in HUMAN_STATES


def test_headline_human_readable():
    view = build_activity_view()
    assert view["headline"] in HEADLINES.values()
    assert not view["headline"].startswith("{")


def test_no_secrets_or_cot():
    view = build_activity_view()
    assert not scan_forbidden(view)


def test_no_authority_flags():
    view = build_activity_view()
    assert view["permission_granted"] is False
    assert view["authority_created"] is False
