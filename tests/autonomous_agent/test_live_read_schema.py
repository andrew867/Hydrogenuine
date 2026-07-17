"""Live read endurance schema tests."""
from __future__ import annotations

import json
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]


def test_policy_exists_and_blocks_writes():
    pol = json.loads((WORKSPACE / "configs/agent_zero/live_read_endurance_policy.json").read_text(encoding="utf-8"))
    assert pol["live_writes_allowed"] is False
    assert pol["read_only_required"] is True
    assert pol["write_scope_allowed"] is False


def test_schema_files_exist():
    names = [
        "agent_zero_live_read_credential_scope_v1.json",
        "agent_zero_live_read_source_identity_v1.json",
        "agent_zero_live_read_receipt_v1.json",
        "agent_zero_live_read_source_ref_v1.json",
        "agent_zero_live_read_freshness_v1.json",
        "agent_zero_live_read_monitor_snapshot_v1.json",
    ]
    for name in names:
        assert (WORKSPACE / "docs/schemas" / name).is_file()
