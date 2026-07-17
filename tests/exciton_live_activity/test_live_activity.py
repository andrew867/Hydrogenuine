"""Live activity trace panel."""

from __future__ import annotations

import json

from hg_runtime.exciton.gate_helpers import scan_forbidden
from hg_runtime.exciton.live_activity import build_live_activity


def test_live_activity_has_operational_fields():
    data = build_live_activity()
    assert "current_loop_state" in data
    assert "current_task" in data
    assert "last_output_summary" in data
    assert data["permission_granted"] is False
    assert data["authority_created"] is False


def test_no_secrets_in_activity_fields():
    data = build_live_activity()
    bad = [b for b in scan_forbidden(data) if "completion_units" not in b]
    assert not bad


def test_no_cot_key():
    data = build_live_activity()
    assert "chain_of_thought" not in json.dumps(data).lower()
