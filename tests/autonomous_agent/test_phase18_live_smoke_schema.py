"""Phase 18 schema tests."""
from __future__ import annotations

import json
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]


def test_phase18_policy():
    pol = json.loads((WORKSPACE / "configs/agent_zero/phase18_live_smoke_policy.json").read_text(encoding="utf-8"))
    assert pol["max_live_actions"] == 1
    assert pol["incident_rollback_plan_required"] is True
    assert pol["exciton_is_approval"] is False


def test_schema_files_exist():
    names = [
        "agent_zero_phase18_live_smoke_scope_v1.json",
        "agent_zero_phase18_live_write_permit_v1.json",
        "agent_zero_phase18_live_dispatch_result_v1.json",
        "agent_zero_platform_visibility_proof_v1.json",
        "agent_zero_phase18_incident_rollback_plan_v1.json",
        "agent_zero_phase18_live_smoke_monitor_snapshot_v1.json",
    ]
    for name in names:
        assert (WORKSPACE / "docs/schemas" / name).is_file()
