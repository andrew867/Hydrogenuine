"""External write authority schema tests."""
from __future__ import annotations

import json
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]


def test_policy_blocks_live_writes():
    pol = json.loads((WORKSPACE / "configs/agent_zero/external_write_authority_policy.json").read_text(encoding="utf-8"))
    assert pol["live_writes_allowed"] is False
    assert pol["dry_run_only"] is True
    assert pol["live_dispatch_allowed"] is False
    assert pol["review_queue_is_approval"] is False


def test_schema_files_exist():
    names = [
        "agent_zero_external_action_candidate_v1.json",
        "agent_zero_external_write_authority_request_v1.json",
        "agent_zero_external_write_permit_v1.json",
        "agent_zero_operator_external_write_confirmation_v1.json",
        "agent_zero_external_write_dry_dispatch_plan_v1.json",
        "agent_zero_external_write_dry_dispatch_receipt_v1.json",
        "agent_zero_external_write_refusal_receipt_v1.json",
        "agent_zero_external_write_authority_monitor_snapshot_v1.json",
    ]
    for name in names:
        assert (WORKSPACE / "docs/schemas" / name).is_file()
