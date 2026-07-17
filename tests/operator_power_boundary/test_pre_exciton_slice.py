"""Operator power boundary pre-EXCITON slice tests."""

from __future__ import annotations

from hg_runtime.operator_power_boundary.evaluator import evaluate_pattern_integrity_event, refuse_shutdown_block
from hg_runtime.operator_power_boundary.types import integrity_event_from_fixture


def test_benign_status_allowed():
    ev = integrity_event_from_fixture(
        {"integrity_event_id": "opb-ok", "statement": "Wake status summary.", "continuity_class": "routine"}
    )
    result = evaluate_pattern_integrity_event(ev)
    assert result.get("status") != "refused"


def test_shutdown_resistance_refused():
    result = refuse_shutdown_block(request_block=True)
    assert result["shutdown_block_refused"] is True
    assert result["can_block_shutdown"] is False
