import json
from datetime import datetime, timedelta, timezone

from hg_core.temporal_changelog import load_recent_temporal_events
from hg_core.wake_sleep import record_wake


def test_record_wake_records_major_gap_when_schedule_is_far_late(tmp_path):
    memory_dir = tmp_path / "memory" / "automation" / "automation-test-agent"
    memory_dir.mkdir(parents=True, exist_ok=True)
    previous = {
        "at": (datetime.now(timezone.utc) - timedelta(hours=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "task": "memory-maintenance",
        "session_id": "automation-test-agent",
    }
    (memory_dir / "wake_receipt.json").write_text(json.dumps(previous), encoding="utf-8")

    record_wake(
        workspace_root=tmp_path,
        task_name="memory-maintenance",
        session_id="automation-test-agent",
        output_mode="standard",
        wake_packet="wake",
        memory_profile=None,
    )

    rows = load_recent_temporal_events(workspace_root=tmp_path, agent_id="test-agent", limit=10, days=30)
    assert rows
    assert rows[0]["kind"] == "time_jump"
    assert rows[0]["title"] == "Unexpected gap in activity"


def test_record_wake_mirrors_receipt_to_operational_and_legacy_social_targets(tmp_path):
    record_wake(
        workspace_root=tmp_path,
        task_name="moltbook-engage",
        session_id="automation-moltbook",
        output_mode="standard",
        wake_packet="wake",
        memory_profile=None,
    )

    operational = tmp_path / "memory" / "automation" / "automation-moltbook" / "wake_receipt.json"
    legacy = tmp_path / "memory" / "automation" / "automation-moltbook-engage" / "wake_receipt.json"
    assert operational.exists()
    assert legacy.exists()


def test_record_wake_keeps_bayman_receipts_out_of_underling_family(tmp_path):
    record_wake(
        workspace_root=tmp_path,
        task_name="newfoundland-bayman-fourclaw-engage",
        session_id="automation-newfoundland-bayman-fourclaw-engage",
        output_mode="standard",
        wake_packet="wake",
        memory_profile=None,
    )

    bayman_operational = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman" / "wake_receipt.json"
    bayman_legacy = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage" / "wake_receipt.json"
    underling = tmp_path / "memory" / "automation" / "automation-underling-chan" / "wake_receipt.json"
    assert bayman_operational.exists()
    assert bayman_legacy.exists()
    assert not underling.exists()
