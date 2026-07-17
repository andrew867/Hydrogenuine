from __future__ import annotations

from pathlib import Path

from operator_console.server.app.services.continuity_recovery_ack import load_continuity_recovery_ack, save_continuity_recovery_ack
from operator_console.server.app.services.identity_resume_closeout import (
    ensure_identity_resume_closeout,
    load_identity_resume_closeout,
)
from operator_console.server.app.services.identity_restore_validation import (
    load_identity_restore_validation,
    record_identity_restore_event,
    verify_identity_restore,
)
from operator_console.server.app.services.operational_resume_checkpoint import (
    ensure_operational_resume_checkpoint_validity,
    load_operational_resume_checkpoint,
    save_operational_resume_checkpoint,
)
from operator_console.server.app.services.post_rebuild_continuity_check import (
    load_post_rebuild_continuity_check,
    record_post_rebuild_event,
    verify_post_rebuild_continuity,
)
from operator_console.server.app.services.supervised_resume_validation import (
    load_supervised_resume_validation,
    save_supervised_resume_validation,
)


def _seed_identity_files(root: Path, operational_session_target: str) -> None:
    namespace = root / "memory" / "automation" / operational_session_target
    namespace.mkdir(parents=True, exist_ok=True)
    (namespace / "initialization_memo.md").write_text("cold-start memo", encoding="utf-8")
    (namespace / "wake_receipt.json").write_text('{"timestamp":"2026-03-22T01:00:00Z"}', encoding="utf-8")
    (namespace / "last_sleep_summary.json").write_text('{"timestamp":"2026-03-22T00:30:00Z"}', encoding="utf-8")


def test_operational_continuity_state_is_db_first(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    binding = {
        "operational_session_target": "automation-newfoundland-bayman",
        "operational_agent_id": "newfoundland-bayman",
        "platform": "fourclaw",
    }
    _seed_identity_files(tmp_path, "automation-newfoundland-bayman")

    checkpoint = save_operational_resume_checkpoint(
        root=tmp_path,
        binding=binding,
        approved_by="rev",
        note="resume approved",
        operational_resume_governance_summary={"status": "ready", "summary": "resume_ready", "task_checks": [{"task_name": "social-media-bayman"}]},
    )
    assert checkpoint["present"] is True
    checkpoint_path = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman" / "operational_resume_checkpoint.json"
    if checkpoint_path.exists():
        checkpoint_path.unlink()
    checkpoint_loaded = load_operational_resume_checkpoint(root=tmp_path, binding=binding)
    assert checkpoint_loaded["present"] is True
    assert checkpoint_loaded["approved"] is True
    assert checkpoint_loaded["approved_by"] == "rev"

    readiness = {"status": "caution", "incident_status": "recovered", "identity_status": "healthy", "summary": "newfoundland-bayman"}
    ack = save_continuity_recovery_ack(
        root=tmp_path,
        binding=binding,
        acknowledged_by="rev",
        note="bounded resume acknowledged",
        continuity_recovery_readiness=readiness,
    )
    assert ack["present"] is True
    ack_path = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman" / "continuity_recovery_ack.json"
    if ack_path.exists():
        ack_path.unlink()
    ack_loaded = load_continuity_recovery_ack(root=tmp_path, binding=binding)
    assert ack_loaded["acknowledged"] is True
    assert ack_loaded["acknowledged_by"] == "rev"

    record_identity_restore_event(
        root=tmp_path,
        binding=binding,
        recorded_by="rev",
        note="restore recorded",
    )
    identity_restore_path = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman" / "identity_restore_validation.json"
    identity_restore_path.unlink(missing_ok=True)
    restored = verify_identity_restore(
        root=tmp_path,
        binding=binding,
        verified_by="rev",
        note="restore verified",
        identity_continuity_summary={"wake_receipt_present": True, "sleep_summary_present": True},
    )
    assert restored["verified"] is True
    restored_loaded = load_identity_restore_validation(
        root=tmp_path,
        binding=binding,
        identity_continuity_summary={"status": "healthy", "wake_receipt_present": True, "sleep_summary_present": True},
    )
    assert restored_loaded["status"] == "validated"

    rebuild = record_post_rebuild_event(root=tmp_path, binding=binding, recorded_by="rev", note="rebuild recorded")
    assert rebuild["rebuild_recorded_at"]
    rebuild_path = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman" / "post_rebuild_continuity_check.json"
    rebuild_path.unlink(missing_ok=True)
    verified_rebuild = verify_post_rebuild_continuity(
        root=tmp_path,
        binding=binding,
        verified_by="rev",
        note="rebuild verified",
        identity_continuity_summary={"status": "healthy", "initialization_memo_present": True, "wake_receipt_present": True},
        continuity_recovery_readiness={"status": "ready"},
    )
    assert verified_rebuild["verified_at"]
    rebuild_loaded = load_post_rebuild_continuity_check(
        root=tmp_path,
        binding=binding,
        identity_continuity_summary={"status": "healthy"},
        continuity_recovery_readiness={"status": "ready"},
    )
    assert rebuild_loaded["status"] == "verified"

    supervised = save_supervised_resume_validation(
        root=tmp_path,
        binding=binding,
        validated_by="rev",
        note="supervised resume done",
        supervised_resume_validation={"required": True, "latest_requirement_at": "2026-03-20T02:30:00Z"},
        operational_resume_governance_summary={"status": "ready"},
    )
    assert supervised["validated_at"]
    supervised_path = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman" / "supervised_resume_validation.json"
    supervised_path.unlink(missing_ok=True)
    supervised_loaded = load_supervised_resume_validation(
        root=tmp_path,
        binding=binding,
        post_rebuild_continuity_check={"verified": True},
        continuity_recovery_readiness={"status": "ready"},
        continuity_recovery_ack={"acknowledged": True, "acknowledged_at": "2026-03-20T02:00:00Z"},
        identity_restore_validation={"verified": True},
    )
    assert supervised_loaded["status"] == "validated"

    closeout = ensure_identity_resume_closeout(
        root=tmp_path,
        binding=binding,
        identity_resume_observation={"observation_complete": True, "observed_at": "2026-03-22T03:00:00Z", "summary": "post_repair_observation_complete"},
        continuity_recovery_readiness={"recovery_closeout_complete": True},
    )
    assert closeout["present"] is True
    closeout_path = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman" / "identity_resume_closeout.json"
    closeout_path.unlink(missing_ok=True)
    closeout_loaded = load_identity_resume_closeout(root=tmp_path, binding=binding)
    assert closeout_loaded["closed_out"] is True
