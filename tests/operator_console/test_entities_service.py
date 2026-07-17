import json
from pathlib import Path
from unittest.mock import patch

from hg_gateway.approval_service import ApprovalService
from operator_console.server.app.services import entities_service
from operator_console.server.app.services import social_account_summary
from hg_gateway import keystore_repo
from hg_gateway import store as store_module
from hg_gateway.db import get_connection
from hg_gateway.operational_state_ledger import save_operational_json_state
from operator_console.server.app.services.run_index_db import upsert_run
from hg_gateway.operational_state_ledger import save_operational_json_state
from hg_core.human_notifications import record_human_notification
from hg_core.security.social_account_artifacts import record_social_account_session_binding
from operator_console.server.app.services.identity_restore_validation import record_identity_restore_event, verify_identity_restore
from operator_console.server.app.services.post_rebuild_continuity_check import record_post_rebuild_event, verify_post_rebuild_continuity


def test_list_entities_list_view_omits_expensive_wake_context_tokens(tmp_path: Path):
    registry = {
        "bayman": {
            "job_id": "job-bayman",
            "session_target": "automation-bayman",
            "platform": "discord",
            "mode": "agent",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-bayman").mkdir(parents=True, exist_ok=True)

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ), patch.object(
        entities_service,
        "_wake_context_tokens",
        return_value={"total_estimate": 321, "memory_estimated_tokens": 100, "memory_cap": 512},
    ):
        rows = entities_service.list_entities()

    assert len(rows) == 1
    assert rows[0]["id"] == "bayman"
    assert rows[0]["wake_context_tokens"] is None


def test_list_entities_includes_operational_lineage_fields(tmp_path: Path):
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage").mkdir(parents=True, exist_ok=True)

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ), patch.object(social_account_summary, "_workspace_root", return_value=root):
        rows = entities_service.list_entities()

    assert len(rows) == 1
    row = rows[0]
    assert row["operational_session_target"] == "automation-newfoundland-bayman"
    assert row["operational_agent_id"] == "newfoundland-bayman"
    assert row["operational_family"] == "newfoundland-bayman"
    assert row["fingerprint_id"] == "newfoundland_bayman_operational"
    assert isinstance(row["commitment_summary"], dict)
    assert isinstance(row["crew_dynamics_summary"], dict)


def test_list_entities_prefers_scheduled_unified_entity_aliases(tmp_path: Path):
    registry = {
        "fourclaw-engage": {
            "job_id": "fourclaw-engage",
            "session_target": "automation-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        },
        "moltbook-engage": {
            "job_id": "moltbook-engage",
            "session_target": "automation-moltbook-engage",
            "platform": "moltbook",
            "mode": "engage",
        },
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        },
        "knowledge-research-auto-v2": {
            "job_id": "knowledge-research-auto-v2",
            "session_target": "automation-knowledge-research-auto-v2",
            "platform": None,
            "mode": "research",
        },
        "memory-maintenance": {
            "job_id": "memory-maintenance",
            "session_target": "automation-memory-maintenance",
            "platform": None,
            "mode": "maintenance",
        },
        "overseer-monitor": {
            "job_id": "overseer-monitor",
            "session_target": "automation-overseer-monitor",
            "platform": None,
            "mode": "monitor",
        },
    }
    root = tmp_path
    schedule_dir = root / "memory" / "automation"
    schedule_dir.mkdir(parents=True, exist_ok=True)
    (schedule_dir / "realtime_schedule.json").write_text(
        json.dumps(
            [
                {"job_id": "social-media-underling", "interval_minutes": 11, "inputs": {"workflow_id": "social-media", "task_name": "fourclaw-engage"}},
                {"job_id": "social-media-bayman", "interval_minutes": 13, "inputs": {"workflow_id": "social-media", "task_name": "newfoundland-bayman-fourclaw-engage"}},
                {"job_id": "knowledge-research-auto-v2", "interval_minutes": 15, "inputs": {"trigger": "realtime"}},
                {"job_id": "memory-maintenance", "interval_minutes": 60, "inputs": {"trigger": "realtime"}},
            ]
        ),
        encoding="utf-8",
    )
    for session_target in (
        "automation-underling-chan",
        "automation-newfoundland-bayman",
        "automation-knowledge-research-auto-v2",
        "automation-memory-maintenance",
    ):
        (schedule_dir / session_target).mkdir(parents=True, exist_ok=True)

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ), patch.object(social_account_summary, "_workspace_root", return_value=root):
        rows = entities_service.list_entities()

    ids = [row["id"] for row in rows]
    assert ids == ["social-media-underling", "social-media-bayman", "knowledge-research-auto-v2", "memory-maintenance"]
    social = rows[0]
    assert social["task_name"] == "fourclaw-engage"
    assert social["platform"] == "social"
    assert social["mode"] == "unified-social"
    assert social["session_target"] == "automation-underling-chan"
    assert isinstance(social["commitment_summary"], dict)
    assert isinstance(social["crew_dynamics_summary"], dict)


def test_get_entity_resolves_unified_entity_alias_from_schedule(tmp_path: Path):
    registry = {
        "fourclaw-engage": {
            "job_id": "fourclaw-engage",
            "session_target": "automation-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    schedule_dir = root / "memory" / "automation"
    schedule_dir.mkdir(parents=True, exist_ok=True)
    (schedule_dir / "realtime_schedule.json").write_text(
        json.dumps(
            [
                {"job_id": "social-media-underling", "interval_minutes": 11, "inputs": {"workflow_id": "social-media", "task_name": "fourclaw-engage"}}
            ]
        ),
        encoding="utf-8",
    )
    (schedule_dir / "automation-underling-chan").mkdir(parents=True, exist_ok=True)

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ):
        row = entities_service.get_entity("social-media-underling")

    assert row is not None
    assert row["id"] == "social-media-underling"
    assert row["task_name"] == "fourclaw-engage"
    assert row["platform"] == "social"
    assert row["mode"] == "unified-social"
    assert row["session_target"] == "automation-underling-chan"


def test_list_entities_includes_identity_continuity_summary(tmp_path: Path):
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    save_operational_json_state(
        root,
        state_key="identity_continuity_state:automation-newfoundland-bayman-fourclaw-engage",
        payload={
            "initialization_memo_present": True,
            "initialization_memo_path": "memory/automation/automation-newfoundland-bayman-fourclaw-engage/initialization_memo.md",
            "wake_receipt_present": True,
            "wake_receipt_recorded_at": "2026-03-13T12:00:00Z",
            "wake_receipt": {"timestamp": "2026-03-13T12:00:00Z"},
            "last_wake_at": "2026-03-13T12:00:00Z",
            "sleep_summary_present": True,
            "sleep_summary_recorded_at": "2026-03-13T11:00:00Z",
            "last_sleep_at": "2026-03-13T11:00:00Z",
            "last_sleep_summary": {"timestamp": "2026-03-13T11:00:00Z"},
        },
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ), patch.object(social_account_summary, "_workspace_root", return_value=root):
        rows = entities_service.list_entities()

    summary = rows[0]["identity_continuity_summary"]
    assert summary["status"] == "healthy"
    assert summary["continuity_anchor"] == "newfoundland-bayman"
    assert summary["initialization_memo_present"] is True
    assert summary["wake_receipt_present"] is True
    assert summary["sleep_summary_present"] is True
    assert summary["initialization_memo_path"] == "memory\\automation\\automation-newfoundland-bayman-fourclaw-engage\\initialization_memo.md"
    assert summary["last_wake_at"] == "2026-03-13T12:00:00Z"
    assert summary["last_sleep_at"] == "2026-03-13T11:00:00Z"
    assert rows[0]["identity_resume_procedure"]["status"] == "ready"
    assert rows[0]["identity_resume_procedure"]["open_steps"] == []
    assert rows[0]["continuity_incident_summary"]["status"] == "clean"
    assert rows[0]["continuity_recovery_readiness"]["status"] == "ready"
    assert rows[0]["continuity_recovery_readiness"]["safe_to_resume"] is True
    assert rows[0]["continuity_repair_plan"]["status"] == "clean"


def test_list_entities_includes_identity_resume_procedure_for_partial_identity(tmp_path: Path):
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    save_operational_json_state(
        root,
        state_key="identity_continuity_state:automation-newfoundland-bayman-fourclaw-engage",
        payload={
            "initialization_memo_present": True,
            "initialization_memo_path": "memory/automation/automation-newfoundland-bayman-fourclaw-engage/initialization_memo.md",
        },
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ), patch.object(social_account_summary, "_workspace_root", return_value=root):
        rows = entities_service.list_entities()

    procedure = rows[0]["identity_resume_procedure"]
    assert procedure["status"] == "partial"
    assert "record_wake_receipt" in procedure["open_steps"]
    assert "record_sleep_summary" in procedure["open_steps"]
    assert "write_initialization_memo" not in procedure["open_steps"]
    assert "record_wake_receipt" in rows[0]["continuity_repair_plan"]["open_checks"]
    assert "record_sleep_summary" in rows[0]["continuity_repair_plan"]["open_checks"]


def test_list_entities_includes_post_rebuild_continuity_check(tmp_path: Path):
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    save_operational_json_state(
        root,
        state_key="identity_continuity_state:automation-newfoundland-bayman-fourclaw-engage",
        payload={
            "initialization_memo_present": True,
            "initialization_memo_path": "memory/automation/automation-newfoundland-bayman-fourclaw-engage/initialization_memo.md",
            "wake_receipt_present": True,
            "wake_receipt_recorded_at": "2026-03-13T12:00:00Z",
            "wake_receipt": {"timestamp": "2026-03-13T12:00:00Z"},
            "last_wake_at": "2026-03-13T12:00:00Z",
            "sleep_summary_present": True,
            "sleep_summary_recorded_at": "2026-03-13T11:00:00Z",
            "last_sleep_at": "2026-03-13T11:00:00Z",
            "last_sleep_summary": {"timestamp": "2026-03-13T11:00:00Z"},
        },
    )
    operational_dir = root / "memory" / "automation" / "automation-newfoundland-bayman"
    operational_dir.mkdir(parents=True, exist_ok=True)
    record_post_rebuild_event(
        root=root,
        binding={"operational_session_target": "automation-newfoundland-bayman", "operational_agent_id": "newfoundland-bayman", "platform": "fourclaw"},
        recorded_by="rev",
        note="docker rebuild",
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ), patch.object(social_account_summary, "_workspace_root", return_value=root):
        rows = entities_service.list_entities()

    check = rows[0]["post_rebuild_continuity_check"]
    assert check["status"] == "pending"
    assert check["verification_required"] is True
    assert "post_rebuild_continuity_check_pending" in rows[0]["continuity_recovery_readiness"]["cautions"]
    assert "verify_post_rebuild_continuity" in rows[0]["continuity_repair_plan"]["open_checks"]
    resume_summary = rows[0]["operational_resume_governance_summary"]
    assert resume_summary["status"] == "caution"
    assert resume_summary["pending_count"] == 1
    assert "verify_post_rebuild_continuity:newfoundland-bayman-fourclaw-engage" in resume_summary["required_actions"]


def test_list_entities_includes_identity_restore_and_supervised_resume_validation(tmp_path: Path):
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    save_operational_json_state(
        root,
        state_key="identity_continuity_state:automation-newfoundland-bayman-fourclaw-engage",
        payload={
            "initialization_memo_present": True,
            "initialization_memo_path": "memory/automation/automation-newfoundland-bayman-fourclaw-engage/initialization_memo.md",
            "wake_receipt_present": True,
            "wake_receipt_recorded_at": "2026-03-13T12:00:00Z",
            "wake_receipt": {"timestamp": "2026-03-13T12:00:00Z"},
            "last_wake_at": "2026-03-13T12:00:00Z",
            "sleep_summary_present": True,
            "sleep_summary_recorded_at": "2026-03-13T11:00:00Z",
            "last_sleep_at": "2026-03-13T11:00:00Z",
            "last_sleep_summary": {"timestamp": "2026-03-13T11:00:00Z"},
        },
    )
    operational_dir = root / "memory" / "automation" / "automation-newfoundland-bayman"
    operational_dir.mkdir(parents=True, exist_ok=True)
    binding = {"operational_session_target": "automation-newfoundland-bayman", "operational_agent_id": "newfoundland-bayman", "platform": "fourclaw"}
    record_post_rebuild_event(
        root=root,
        binding=binding,
        recorded_by="rev",
        note="docker rebuild",
    )
    verify_post_rebuild_continuity(
        root=root,
        binding=binding,
        verified_by="rev",
        note="docker rebuild verified",
        identity_continuity_summary={"status": "healthy", "initialization_memo_present": True, "wake_receipt_present": True},
        continuity_recovery_readiness={"status": "ready"},
    )
    record_identity_restore_event(
        root=root,
        binding=binding,
        recorded_by="rev",
        note="identity restore",
    )
    verify_identity_restore(
        root=root,
        binding=binding,
        verified_by="rev",
        note="identity restore verified",
        identity_continuity_summary={"wake_receipt_present": True, "sleep_summary_present": True},
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ), patch.object(social_account_summary, "_workspace_root", return_value=root):
        rows = entities_service.list_entities()

    assert rows[0]["identity_restore_validation"]["status"] == "validated"
    assert rows[0]["supervised_resume_validation"]["status"] == "pending"
    assert "run_supervised_resume_validation" in rows[0]["continuity_repair_plan"]["open_checks"]
    assert "run_supervised_resume_validation" in rows[0]["operational_resume_governance_summary"]["required_actions"]
    assert "supervised_resume_validation_required" in rows[0]["bounded_autonomy_policy_summary"]["blockers"]


def test_list_entities_includes_presence_initiative_summary(tmp_path: Path):
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    namespace = root / "memory" / "automation" / "automation-newfoundland-bayman"
    namespace.mkdir(parents=True, exist_ok=True)
    (namespace / "cadence_request.json").write_text(
        '{"requested_at":"2026-03-13T12:00:00Z","requested_duration_minutes":45,"scheduler_job_id":"social-media-bayman"}',
        encoding="utf-8",
    )
    overseer = root / "memory" / "overseer"
    overseer.mkdir(parents=True, exist_ok=True)
    (overseer / "autonomy_config.json").write_text(
        '{"entity_dag_change_control":"on","outbound_safety_gate_enabled":true}',
        encoding="utf-8",
    )
    materialized = root / "memory" / "materialized"
    materialized.mkdir(parents=True, exist_ok=True)
    (materialized / "regulatory_state_snapshots.jsonl").write_text(
        '{"scope_type":"agent","scope_id":"newfoundland-bayman","agent_id":"newfoundland-bayman","ts":"2026-03-13T12:05:00Z","trust_band":2,"agency_budget":7.5,"escrow_locked":1.0,"incident_points":0.0,"evidence_refs":[]}\n',
        encoding="utf-8",
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ), patch.object(social_account_summary, "_workspace_root", return_value=root):
        rows = entities_service.list_entities()

    summary = rows[0]["presence_initiative_summary"]
    assert summary["status"] == "healthy"
    assert summary["initiative_mode"] == "self_timed_override"
    assert summary["next_earliest_wake_at"] == "2026-03-13T12:45:00Z"
    assert summary["agency_budget"] == 7.5
    assert summary["trust_band"] == 2
    confidence = rows[0]["confidence_summary"]
    assert confidence["confidence_level"] in {"uncertain", "cautious", "confident", "certain"}
    assert confidence["confidence_score"] >= 0


def test_list_entities_includes_affect_action_summary(tmp_path: Path, monkeypatch):
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    store_module._store = None

    from hg_gateway.store import get_store

    store = get_store()
    store.persona_autonomy_add_turn(
        "default",
        {
            "turn_id": "entity-affect-action-1",
            "chat_id": "chat-entity-affect-action",
            "message_id": "msg-entity-affect-action",
            "fingerprint_id": "newfoundland_bayman_operational",
            "arc_state": "building",
            "engagement_mode": "reciprocal",
            "depth_level": "middle",
            "uncertainty_level": "confident",
            "callback_surface": True,
            "proactive_notice": True,
            "lateral_mode": "aside",
            "position_evolution": False,
            "relationship_type": "respect",
            "counterpart_fingerprint_id": "underling_chan_operational",
            "details": {"moves": ["callback:systems"]},
            "created_at": "2026-03-13T17:30:00Z",
        },
    )

    root = tmp_path
    materialized = root / "memory" / "materialized"
    materialized.mkdir(parents=True, exist_ok=True)
    (materialized / "regulatory_state_snapshots.jsonl").write_text(
        '{"scope_type":"agent","scope_id":"newfoundland-bayman","agent_id":"newfoundland-bayman","ts":"2026-03-13T17:31:00Z","trust_band":3,"agency_budget":8.0,"escrow_locked":0.5,"incident_points":0.0,"evidence_refs":[]}\n',
        encoding="utf-8",
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ), patch.object(social_account_summary, "_workspace_root", return_value=root):
        rows = entities_service.list_entities()

    summary = rows[0]["affect_action_summary"]
    assert summary["status"] == "healthy"
    assert summary["affective_state"]["trust_band"] == 3
    assert summary["affective_state"]["agency_budget"] == 8.0
    assert summary["action_state"]["dominant_arc_state"] == "building"
    assert summary["latest_turn"]["engagement_mode"] == "reciprocal"


def test_list_entities_includes_social_posture_summary(tmp_path: Path, monkeypatch):
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    store_module._store = None

    from hg_gateway.store import get_store

    store = get_store()
    store.persona_autonomy_add_turn(
        "default",
        {
            "turn_id": "entity-social-posture-1",
            "chat_id": "chat-entity-social-posture",
            "message_id": "msg-entity-social-posture",
            "fingerprint_id": "newfoundland_bayman_operational",
            "arc_state": "building",
            "engagement_mode": "reciprocal",
            "uncertainty_level": "confident",
            "callback_surface": True,
            "proactive_notice": False,
            "position_evolution": False,
            "relationship_type": "respect",
            "created_at": "2026-03-13T17:00:00Z",
        },
    )

    root = tmp_path
    operational_dir = root / "memory" / "automation" / "automation-newfoundland-bayman"
    operational_dir.mkdir(parents=True, exist_ok=True)
    (operational_dir / "agency_control.json").write_text(
        '{"mode":"review_only","reason":"supervised rollout","updated_at":"2026-03-13T18:00:00Z","updated_by":"rev","outbound_lane_policy":"replies_only"}',
        encoding="utf-8",
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ), patch.object(social_account_summary, "_workspace_root", return_value=root):
        rows = entities_service.list_entities()

    summary = rows[0]["social_posture_summary"]
    assert summary["posture"] == "supervised"
    assert summary["effective_mode"] == "review_only"
    assert summary["outbound_lane_policy"] == "replies_only"
    assert summary["reply_bias"] == "reply_heavy"
    assert summary["relationship_orientation"] == "respect"
    store_module._store = None


def test_list_entities_includes_agency_control_summary(tmp_path: Path):
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    operational_dir = root / "memory" / "automation" / "automation-newfoundland-bayman"
    operational_dir.mkdir(parents=True, exist_ok=True)
    (operational_dir / "agency_control.json").write_text(
        '{"mode":"review_only","reason":"supervised rollout","updated_at":"2026-03-13T18:00:00Z","updated_by":"rev","outbound_lane_policy":"replies_only"}',
        encoding="utf-8",
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ), patch.object(social_account_summary, "_workspace_root", return_value=root):
        rows = entities_service.list_entities()

    summary = rows[0]["agency_control_summary"]
    assert summary["status"] == "configured"
    assert summary["mode"] == "review_only"
    assert summary["review_required"] is True
    assert summary["operator_hold"] is False
    assert summary["outbound_lane_policy"] == "replies_only"
    assert summary["allowed_outbound_modes"] == ["engage"]
    assert summary["reason"] == "supervised rollout"
    assert summary["updated_by"] == "rev"


def test_list_entities_agency_control_summary_includes_outbound_budget(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    registry = {
        "newfoundland-bayman-fourclaw-auto-post": {
            "job_id": "newfoundland-bayman-fourclaw-auto-post",
            "session_target": "automation-newfoundland-bayman-fourclaw-auto-post",
            "platform": "fourclaw",
            "mode": "auto-post",
        }
    }
    root = tmp_path
    operational_dir = root / "memory" / "automation" / "automation-newfoundland-bayman"
    operational_dir.mkdir(parents=True, exist_ok=True)
    (operational_dir / "agency_control.json").write_text(
        '{"mode":"normal","reason":"cap outbound churn","updated_at":"2026-03-13T18:00:00Z","updated_by":"rev","outbound_lane_policy":"unrestricted","daily_outbound_budget":2,"outbound_actions_window_hours":24}',
        encoding="utf-8",
    )

    keystore_repo.social_account_create(
        social_account_id="acct-bayman-fourclaw",
        tenant_id="default",
        platform="fourclaw",
        account_alias="bayman-fourclaw",
        entity_scope="newfoundland-bayman",
        persona_scope="newfoundland_bayman_operational",
        state="verified",
        db_path=str(tmp_path / "gateway.sqlite3"),
    )
    with get_connection(str(tmp_path / "gateway.sqlite3")) as conn:
        conn.execute(
            """INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at)
               VALUES (?, 'social_account', ?, 'post_proof', ?, ?, datetime('now'))""",
            ("proof-budget-1", "acct-bayman-fourclaw", "memory/artifacts/social_accounts/post1.json", '{"status":"ok"}'),
        )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ), patch.object(social_account_summary, "_workspace_root", return_value=root):
        rows = entities_service.list_entities()

    summary = rows[0]["agency_control_summary"]
    assert summary["daily_outbound_budget"] == 2
    assert summary["outbound_actions_window_hours"] == 24
    assert summary["recent_outbound_action_count"] == 1
    assert summary["outbound_budget_remaining"] == 1
    assert summary["outbound_budget_exhausted"] is False


def test_list_entities_includes_self_model_summary(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    store_module._store = None
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage").mkdir(parents=True, exist_ok=True)

    from hg_gateway.store import get_store

    store = get_store()
    store.persona_autonomy_add_turn(
        "default",
        {
            "turn_id": "auto-bayman-1",
            "chat_id": "chat-bayman",
            "message_id": "msg-bayman",
            "fingerprint_id": "newfoundland_bayman_operational",
            "arc_state": "building",
            "engagement_mode": "direct",
            "uncertainty_level": "confident",
            "callback_surface": True,
            "proactive_notice": False,
            "position_evolution": True,
            "relationship_type": "respect",
            "counterpart_fingerprint_id": "nikola_tesla",
            "created_at": "2026-03-13T12:00:00Z",
        },
    )

    try:
        with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
            entities_service,
            "_get_registry",
            return_value=registry,
        ):
            rows = entities_service.list_entities()
    finally:
        store_module._store = None

    summary = rows[0]["self_model_summary"]
    assert summary["status"] == "healthy"
    assert summary["dominant_arc_state"] == "building"
    assert summary["dominant_engagement_mode"] == "direct"
    assert summary["dominant_uncertainty"] == "confident"
    assert summary["relationship_signal"] == "respect"
    assert rows[0]["confidence_summary"]["confidence_level"] in {"uncertain", "cautious", "confident", "certain"}
    relationship = rows[0]["relationship_memory_summary"]
    assert relationship["status"] == "healthy"
    assert relationship["dominant_relationship_type"] == "respect"
    assert relationship["top_counterparts"][0]["counterpart_fingerprint_id"] == "nikola_tesla"


def test_list_entities_includes_action_rationale_summary(tmp_path: Path):
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    save_operational_json_state(
        root,
        state_key="identity_continuity_state:automation-newfoundland-bayman-fourclaw-engage",
        payload={
            "wake_receipt_present": True,
            "wake_receipt_recorded_at": "2026-03-13T18:00:00Z",
            "wake_receipt": {
                "wake_completed_at": "2026-03-13T18:00:00Z",
                "dag_inputs": {"goal": "check replies and decide whether to engage"},
            },
            "last_wake_at": "2026-03-13T18:00:00Z",
        },
    )
    save_operational_json_state(
        root,
        state_key="operational_cadence_request:automation-newfoundland-bayman",
        payload={
            "requested_at": "2026-03-13T17:55:00Z",
            "reason": "reply_window",
            "scheduler_job_id": "social-media-bayman",
        },
    )
    save_operational_json_state(
        root,
        state_key="research_deliveries",
        payload={
            "deliveries": [
                {
                    "requested_by": "newfoundland-bayman",
                    "topic": "4claw reply etiquette",
                    "file_path": "knowledge/social/reply-etiquette.md",
                    "delivered_at": "2026-03-13T17:50:00Z",
                }
            ]
        },
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ):
        rows = entities_service.list_entities()

    summary = rows[0]["action_rationale_summary"]
    assert summary["status"] == "healthy"
    assert summary["current_trigger"] == "cadence_override"
    assert summary["current_goal"] == "check replies and decide whether to engage"
    assert "cadence:reply_window" in summary["reason_chain"]


def test_list_entities_action_rationale_prefers_agency_gate(tmp_path: Path):
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    session_dir = root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage"
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "wake_receipt.json").write_text(
        '{"wake_completed_at":"2026-03-13T18:00:00Z","dag_inputs":{"goal":"check replies and decide whether to engage"}}',
        encoding="utf-8",
    )
    operational_dir = root / "memory" / "automation" / "automation-newfoundland-bayman"
    operational_dir.mkdir(parents=True, exist_ok=True)
    (operational_dir / "agency_control.json").write_text(
        '{"mode":"held","reason":"manual freeze","updated_at":"2026-03-13T18:01:00Z","updated_by":"operator"}',
        encoding="utf-8",
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ):
        rows = entities_service.list_entities()

    summary = rows[0]["action_rationale_summary"]
    assert summary["current_trigger"] == "agency_hold"
    assert summary["agency_mode"] == "held"
    assert "agency_hold:manual freeze" in summary["reason_chain"]


def test_list_entities_action_rationale_prefers_outbound_budget(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    registry = {
        "newfoundland-bayman-fourclaw-auto-post": {
            "job_id": "newfoundland-bayman-fourclaw-auto-post",
            "session_target": "automation-newfoundland-bayman-fourclaw-auto-post",
            "platform": "fourclaw",
            "mode": "auto-post",
        }
    }
    root = tmp_path
    session_dir = root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-auto-post"
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "wake_receipt.json").write_text(
        '{"wake_completed_at":"2026-03-13T18:00:00Z","dag_inputs":{"goal":"post a thread"}}',
        encoding="utf-8",
    )
    operational_dir = root / "memory" / "automation" / "automation-newfoundland-bayman"
    operational_dir.mkdir(parents=True, exist_ok=True)
    (operational_dir / "agency_control.json").write_text(
        '{"mode":"normal","reason":"daily cap reached","updated_at":"2026-03-13T18:01:00Z","updated_by":"operator","daily_outbound_budget":1,"outbound_actions_window_hours":24}',
        encoding="utf-8",
    )
    keystore_repo.social_account_create(
        social_account_id="acct-bayman-fourclaw",
        tenant_id="default",
        platform="fourclaw",
        account_alias="bayman-fourclaw",
        entity_scope="newfoundland-bayman",
        persona_scope="newfoundland_bayman_operational",
        state="verified",
        db_path=str(tmp_path / "gateway.sqlite3"),
    )
    with get_connection(str(tmp_path / "gateway.sqlite3")) as conn:
        conn.execute(
            """INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at)
               VALUES (?, 'social_account', ?, 'post_proof', ?, ?, datetime('now'))""",
            ("proof-budget-rationale-1", "acct-bayman-fourclaw", "memory/artifacts/social_accounts/post1.json", '{"status":"ok"}'),
        )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ):
        rows = entities_service.list_entities()

    summary = rows[0]["action_rationale_summary"]
    assert summary["current_trigger"] == "outbound_budget"
    assert "outbound_budget:1/1" in summary["reason_chain"]


def test_list_entities_includes_review_handoff_summary(tmp_path: Path):
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage").mkdir(parents=True, exist_ok=True)
    record_human_notification(
        root,
        task_name="newfoundland-bayman-fourclaw-engage",
        kind="agency_gate",
        message="review handoff created",
        summary={
            "execution": {"status": "pending_approval", "platform": "fourclaw", "blocked_reason": "agency_control_review_only"},
            "agency_control": {"effective_mode": "review_only", "reason": "supervised rollout"},
            "review_handoff": {"approval_id": "approval-entity-1", "title": "Review required: bayman fourclaw"},
        },
        operational_agent_id="newfoundland-bayman",
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ):
        rows = entities_service.list_entities()

    summary = rows[0]["review_handoff_summary"]
    assert summary["count"] == 1
    assert summary["pending_count"] == 1
    assert summary["latest"]["approval_id"] == "approval-entity-1"
    assert summary["latest"]["task_name"] == "newfoundland-bayman-fourclaw-engage"
    assert summary["latest"]["approval_href"] == "#/approvals?workflow_id=newfoundland-bayman-fourclaw-engage&approval_id=approval-entity-1"


def test_list_entities_review_handoff_summary_includes_release_blockers(tmp_path: Path):
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage").mkdir(parents=True, exist_ok=True)
    operational_dir = root / "memory" / "automation" / "automation-newfoundland-bayman"
    operational_dir.mkdir(parents=True, exist_ok=True)
    (operational_dir / "agency_control.json").write_text(
        '{"mode":"held","reason":"manual freeze","updated_at":"2026-03-13T18:01:00Z","updated_by":"operator"}',
        encoding="utf-8",
    )
    record_human_notification(
        root,
        task_name="newfoundland-bayman-fourclaw-engage",
        kind="agency_gate",
        message="review handoff created",
        summary={
            "execution": {"status": "pending_approval", "platform": "fourclaw", "blocked_reason": "agency_control_review_only"},
            "agency_control": {"effective_mode": "review_only", "reason": "supervised rollout"},
            "review_handoff": {"approval_id": "approval-entity-2", "title": "Review required: bayman fourclaw"},
        },
        operational_agent_id="newfoundland-bayman",
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ):
        rows = entities_service.list_entities()

    summary = rows[0]["review_handoff_summary"]
    assert summary["release_ready"] is False
    assert "agency_hold" in summary["release_blockers"]


def test_list_entities_review_handoff_summary_requires_continuity_ack_for_recovered_lane(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage").mkdir(parents=True, exist_ok=True)
    keystore_repo.social_account_create(
        social_account_id="acct-bayman-fourclaw",
        tenant_id="default",
        platform="fourclaw",
        account_alias="bayman-fourclaw",
        entity_scope="newfoundland-bayman",
        persona_scope="newfoundland_bayman_operational",
        state="verified",
        db_path=str(db_path),
    )
    record_social_account_session_binding(
        "acct-bayman-fourclaw",
        browser_session_id="session-bad",
        platform="fourclaw",
        tenant_id="default",
        entity_id="newfoundland-bayman",
        account_alias="bayman-fourclaw",
        state="degraded",
    )
    record_social_account_session_binding(
        "acct-bayman-fourclaw",
        browser_session_id="session-good",
        platform="fourclaw",
        tenant_id="default",
        entity_id="newfoundland-bayman",
        account_alias="bayman-fourclaw",
        state="active",
    )
    profile_dir = tmp_path / "browser-profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = tmp_path / "browser.png"
    screenshot_path.write_text("ok", encoding="utf-8")
    snapshot_path = tmp_path / "browser-state.json"
    snapshot_path.write_text("{}", encoding="utf-8")
    trace_path = tmp_path / "browser.zip"
    trace_path.write_text("trace", encoding="utf-8")
    with get_connection(str(db_path)) as conn:
        conn.execute("""INSERT INTO browser_sessions (browser_session_id, tenant_id, entity_id, platform, state, started_at) VALUES (?, ?, ?, ?, ?, '2026-03-13T23:00:00Z')""",("session-bad","default","newfoundland-bayman","fourclaw","degraded"))
        conn.execute("""INSERT INTO browser_sessions (browser_session_id, tenant_id, entity_id, platform, state, started_at, trace_path, latest_screenshot_path) VALUES (?, ?, ?, ?, ?, '2026-03-14T01:30:00Z', ?, ?)""",("session-good","default","newfoundland-bayman","fourclaw","active",str(trace_path),str(screenshot_path)))
        conn.execute("""INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at) VALUES (?, 'browser_session', ?, 'snapshot', ?, ?, '2026-03-14T01:30:10Z')""",("proof-snapshot","session-good",str(snapshot_path),'{}'))
        conn.execute("""INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at) VALUES (?, 'browser_session', ?, 'profile_dir', ?, ?, '2026-03-14T01:30:05Z')""",("proof-profile","session-good",str(profile_dir),'{}'))
        conn.execute("""INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at) VALUES (?, 'browser_session', ?, 'session_degraded', ?, ?, '2026-03-13T23:59:59Z')""",("proof-bad","session-bad","missing_restart_critical_browser_artifacts",'{"reason":"missing_restart_critical_browser_artifacts"}'))
        conn.execute("""UPDATE proof_artifacts SET created_at = '2026-03-13T22:59:00Z' WHERE related_kind = 'social_account' AND related_id = ? AND artifact_type = 'browser_session_binding' AND path LIKE ?""",("acct-bayman-fourclaw","%session-bad%"))
        conn.execute("""UPDATE proof_artifacts SET created_at = '2026-03-14T01:31:00Z' WHERE related_kind = 'social_account' AND related_id = ? AND artifact_type = 'browser_session_binding' AND path LIKE ?""",("acct-bayman-fourclaw","%session-good%"))
    record_human_notification(
        root,
        task_name="newfoundland-bayman-fourclaw-engage",
        kind="agency_gate",
        message="review handoff created",
        summary={"execution": {"status": "pending_approval", "platform": "fourclaw", "blocked_reason": "agency_control_review_only"},"agency_control": {"effective_mode": "review_only", "reason": "supervised rollout"},"review_handoff": {"approval_id": "approval-entity-caution", "title": "Review required: bayman fourclaw"}},
        operational_agent_id="newfoundland-bayman",
    )
    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(entities_service, "_get_registry", return_value=registry):
        rows = entities_service.list_entities()
    summary = rows[0]["review_handoff_summary"]
    assert summary["release_ready"] is False
    assert "continuity_recovery_ack_required" in summary["release_blockers"]


def test_list_entities_review_handoff_summary_includes_continuity_release_blocker(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage").mkdir(parents=True, exist_ok=True)
    keystore_repo.social_account_create(
        social_account_id="acct-bayman-fourclaw",
        tenant_id="default",
        platform="fourclaw",
        account_alias="bayman-fourclaw",
        entity_scope="newfoundland-bayman",
        persona_scope="newfoundland_bayman_operational",
        state="verified",
        db_path=str(db_path),
    )
    record_social_account_session_binding(
        "acct-bayman-fourclaw",
        browser_session_id="session-bad",
        platform="fourclaw",
        tenant_id="default",
        entity_id="newfoundland-bayman",
        account_alias="bayman-fourclaw",
        state="active",
    )
    with get_connection(str(db_path)) as conn:
        conn.execute(
            """INSERT INTO browser_sessions (browser_session_id, tenant_id, entity_id, platform, state, started_at)
               VALUES (?, ?, ?, ?, ?, datetime('now'))""",
            ("session-bad", "default", "newfoundland-bayman", "fourclaw", "degraded"),
        )
        conn.execute(
            """INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at)
               VALUES (?, 'browser_session', ?, 'session_degraded', ?, ?, datetime('now'))""",
            ("proof-bad", "session-bad", "missing_restart_critical_browser_artifacts", '{"reason":"missing_restart_critical_browser_artifacts"}'),
        )
    record_human_notification(
        root,
        task_name="newfoundland-bayman-fourclaw-engage",
        kind="agency_gate",
        message="review handoff created",
        summary={
            "execution": {"status": "pending_approval", "platform": "fourclaw", "blocked_reason": "agency_control_review_only"},
            "agency_control": {"effective_mode": "review_only", "reason": "supervised rollout"},
            "review_handoff": {"approval_id": "approval-entity-continuity", "title": "Review required: bayman fourclaw"},
        },
        operational_agent_id="newfoundland-bayman",
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ):
        rows = entities_service.list_entities()

    summary = rows[0]["review_handoff_summary"]
    assert summary["release_ready"] is False
    assert "continuity_recovery" in summary["release_blockers"]


def test_list_entities_review_handoff_summary_requires_operational_resume_checkpoint(tmp_path: Path, monkeypatch):
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    task_dir = root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage"
    task_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        entities_service,
        "build_operational_resume_governance_summary",
        lambda **kwargs: {"status": "ready", "required_actions": []},
    )
    monkeypatch.setattr(
        entities_service,
        "ensure_operational_resume_checkpoint_validity",
        lambda **kwargs: {
            "approved": False,
            "invalidated": True,
            "invalidated_reason": "operational_resume_no_longer_ready",
        },
    )
    record_human_notification(
        root,
        task_name="newfoundland-bayman-fourclaw-engage",
        kind="agency_gate",
        message="review handoff created",
        summary={
            "execution": {"status": "pending_approval", "platform": "fourclaw", "blocked_reason": "agency_control_review_only"},
            "agency_control": {"effective_mode": "review_only", "reason": "supervised rollout"},
            "review_handoff": {"approval_id": "approval-entity-resume", "title": "Review required: bayman fourclaw"},
        },
        operational_agent_id="newfoundland-bayman",
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ):
        rows = entities_service.list_entities()

    summary = rows[0]["review_handoff_summary"]
    assert summary["release_ready"] is False
    assert "operational_resume_checkpoint_required" in summary["release_blockers"]


def test_list_entities_review_handoff_summary_uses_live_approval_status(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    approval = ApprovalService(db_path=str(tmp_path / "gateway.sqlite3")).create_request(
        entity_id="newfoundland-bayman-fourclaw-engage",
        action_kind="social_write",
        preview_json={"summary": "review me"},
        tenant_id="default",
        workflow_id="newfoundland-bayman-fourclaw-engage",
        target_platform="fourclaw",
    )
    ApprovalService(db_path=str(tmp_path / "gateway.sqlite3")).approve(
        approval["approval_id"],
        tenant_id="default",
        decided_by="operator",
        decision_note="looks good",
    )
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage").mkdir(parents=True, exist_ok=True)
    record_human_notification(
        root,
        task_name="newfoundland-bayman-fourclaw-engage",
        kind="agency_gate",
        message="review handoff created",
        summary={
            "execution": {"status": "pending_approval", "platform": "fourclaw", "blocked_reason": "agency_control_review_only"},
            "agency_control": {"effective_mode": "review_only", "reason": "supervised rollout"},
            "review_handoff": {"approval_id": approval["approval_id"], "title": "Review required: bayman fourclaw"},
        },
        operational_agent_id="newfoundland-bayman",
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ):
        rows = entities_service.list_entities()

    summary = rows[0]["review_handoff_summary"]
    assert summary["pending_count"] == 0
    assert summary["latest"]["status"] == "approved"
    assert summary["latest"]["decided_by"] == "operator"


def test_list_entities_review_handoff_summary_includes_resolution_context(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    approval = ApprovalService(db_path=str(tmp_path / "gateway.sqlite3")).create_request(
        entity_id="newfoundland-bayman-fourclaw-engage",
        action_kind="social_write",
        preview_json={
            "summary": "review me",
            "resolution_context": {
                "rationale": "continuity verified",
                "release_scope": "single supervised post",
                "followup_expectation": "watch replies for 1h",
            },
        },
        tenant_id="default",
        workflow_id="newfoundland-bayman-fourclaw-engage",
        target_platform="fourclaw",
    )
    ApprovalService(db_path=str(tmp_path / "gateway.sqlite3")).approve(
        approval["approval_id"],
        tenant_id="default",
        decided_by="operator",
        decision_note="looks good",
    )
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage").mkdir(parents=True, exist_ok=True)
    record_human_notification(
        root,
        task_name="newfoundland-bayman-fourclaw-engage",
        kind="agency_gate",
        message="review handoff created",
        summary={
            "execution": {"status": "pending_approval", "platform": "fourclaw", "blocked_reason": "agency_control_review_only"},
            "agency_control": {"effective_mode": "review_only", "reason": "supervised rollout"},
            "review_handoff": {"approval_id": approval["approval_id"], "title": "Review required: bayman fourclaw"},
        },
        operational_agent_id="newfoundland-bayman",
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ):
        rows = entities_service.list_entities()

    resolution_context = rows[0]["review_handoff_summary"]["latest"]["resolution_context"]
    assert resolution_context["rationale"] == "continuity verified"
    assert resolution_context["release_scope"] == "single supervised post"
    assert resolution_context["followup_expectation"] == "watch replies for 1h"


def test_list_entities_review_handoff_summary_marks_followup_pending_without_post_decision_activity(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    approval = ApprovalService(db_path=str(tmp_path / "gateway.sqlite3")).create_request(
        entity_id="newfoundland-bayman-fourclaw-engage",
        action_kind="social_write",
        preview_json={
            "summary": "review me",
            "resolution_context": {
                "rationale": "continuity verified",
                "release_scope": "single supervised post",
                "followup_expectation": "watch replies for 1h",
                "followup_window_hours": 24,
            },
        },
        tenant_id="default",
        workflow_id="newfoundland-bayman-fourclaw-engage",
        target_platform="fourclaw",
    )
    ApprovalService(db_path=str(tmp_path / "gateway.sqlite3")).approve(
        approval["approval_id"],
        tenant_id="default",
        decided_by="operator",
        decision_note="looks good",
    )
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage").mkdir(parents=True, exist_ok=True)
    record_human_notification(
        root,
        task_name="newfoundland-bayman-fourclaw-engage",
        kind="agency_gate",
        message="review handoff created",
        summary={
            "execution": {"status": "pending_approval", "platform": "fourclaw", "blocked_reason": "agency_control_review_only"},
            "agency_control": {"effective_mode": "review_only", "reason": "supervised rollout"},
            "review_handoff": {"approval_id": approval["approval_id"], "title": "Review required: bayman fourclaw"},
        },
        operational_agent_id="newfoundland-bayman",
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ):
        rows = entities_service.list_entities()

    followup = rows[0]["review_handoff_summary"]["latest"]["followup_summary"]
    assert followup["expected"] is True
    assert followup["observed"] is False
    assert followup["status"] == "pending"
    assert followup["expectation"] == "watch replies for 1h"
    assert followup["window_hours"] == 24
    assert followup["due_at"] is not None


def test_list_entities_review_handoff_summary_marks_followup_observed_after_post_decision_notification(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    approval = ApprovalService(db_path=str(tmp_path / "gateway.sqlite3")).create_request(
        entity_id="newfoundland-bayman-fourclaw-engage",
        action_kind="social_write",
        preview_json={
            "summary": "review me",
            "resolution_context": {
                "rationale": "continuity verified",
                "release_scope": "single supervised post",
                "followup_expectation": "watch replies for 1h",
                "followup_window_hours": 1,
            },
        },
        tenant_id="default",
        workflow_id="newfoundland-bayman-fourclaw-engage",
        target_platform="fourclaw",
    )
    ApprovalService(db_path=str(tmp_path / "gateway.sqlite3")).approve(
        approval["approval_id"],
        tenant_id="default",
        decided_by="operator",
        decision_note="looks good",
    )
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage").mkdir(parents=True, exist_ok=True)
    record_human_notification(
        root,
        task_name="newfoundland-bayman-fourclaw-engage",
        kind="agency_gate",
        message="review handoff created",
        summary={
            "execution": {"status": "pending_approval", "platform": "fourclaw", "blocked_reason": "agency_control_review_only"},
            "agency_control": {"effective_mode": "review_only", "reason": "supervised rollout"},
            "review_handoff": {"approval_id": approval["approval_id"], "title": "Review required: bayman fourclaw"},
        },
        operational_agent_id="newfoundland-bayman",
    )
    with get_connection(str(tmp_path / "gateway.sqlite3")) as conn:
        conn.execute(
            "UPDATE approval_requests SET decided_at = datetime('now', '-2 hours') WHERE approval_id = ?",
            (approval["approval_id"],),
        )
    record_human_notification(
        root,
        task_name="newfoundland-bayman-fourclaw-engage",
        kind="run_update",
        message="posted reply and checking thread",
        summary={"execution": {"status": "completed", "platform": "fourclaw"}},
        operational_agent_id="newfoundland-bayman",
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ):
        rows = entities_service.list_entities()

    followup = rows[0]["review_handoff_summary"]["latest"]["followup_summary"]
    assert followup["expected"] is True
    assert followup["observed"] is True
    assert followup["status"] == "observed"
    assert followup["observation_kind"] == "run_update"
    assert followup["observation_detail"] == "posted reply and checking thread"
    assert followup["window_hours"] == 1
    assert followup["due_at"] is not None


def test_list_entities_review_handoff_summary_marks_followup_overdue_without_observation(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    approval = ApprovalService(db_path=str(tmp_path / "gateway.sqlite3")).create_request(
        entity_id="newfoundland-bayman-fourclaw-engage",
        action_kind="social_write",
        preview_json={
            "summary": "review me",
            "resolution_context": {
                "rationale": "continuity verified",
                "release_scope": "single supervised post",
                "followup_expectation": "watch replies for 1h",
                "followup_window_hours": 1,
            },
        },
        tenant_id="default",
        workflow_id="newfoundland-bayman-fourclaw-engage",
        target_platform="fourclaw",
    )
    ApprovalService(db_path=str(tmp_path / "gateway.sqlite3")).approve(
        approval["approval_id"],
        tenant_id="default",
        decided_by="operator",
        decision_note="looks good",
    )
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage").mkdir(parents=True, exist_ok=True)
    record_human_notification(
        root,
        task_name="newfoundland-bayman-fourclaw-engage",
        kind="agency_gate",
        message="review handoff created",
        summary={
            "execution": {"status": "pending_approval", "platform": "fourclaw", "blocked_reason": "agency_control_review_only"},
            "agency_control": {"effective_mode": "review_only", "reason": "supervised rollout"},
            "review_handoff": {"approval_id": approval["approval_id"], "title": "Review required: bayman fourclaw"},
        },
        operational_agent_id="newfoundland-bayman",
    )
    with get_connection(str(tmp_path / "gateway.sqlite3")) as conn:
        conn.execute(
            "UPDATE approval_requests SET decided_at = datetime('now', '-3 hours') WHERE approval_id = ?",
            (approval["approval_id"],),
        )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ):
        rows = entities_service.list_entities()

    followup = rows[0]["review_handoff_summary"]["latest"]["followup_summary"]
    assert followup["expected"] is True
    assert followup["observed"] is False
    assert followup["status"] == "overdue"
    assert followup["window_hours"] == 1
    assert followup["due_at"] is not None
    assert rows[0]["review_handoff_summary"]["refresh_recommended"] is True
    assert "followup_overdue" in rows[0]["review_handoff_summary"]["refresh_reasons"]


def test_list_entities_review_handoff_summary_marks_expired_approval(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    approval = ApprovalService(db_path=str(tmp_path / "gateway.sqlite3")).create_request(
        entity_id="newfoundland-bayman-fourclaw-engage",
        action_kind="social_write",
        preview_json={"summary": "review me", "release_window_hours": 1},
        tenant_id="default",
        workflow_id="newfoundland-bayman-fourclaw-engage",
        target_platform="fourclaw",
    )
    ApprovalService(db_path=str(tmp_path / "gateway.sqlite3")).approve(
        approval["approval_id"],
        tenant_id="default",
        decided_by="operator",
        decision_note="looks good",
    )
    with get_connection(str(tmp_path / "gateway.sqlite3")) as conn:
        conn.execute(
            "UPDATE approval_requests SET decided_at = datetime('now', '-3 hours') WHERE approval_id = ?",
            (approval["approval_id"],),
        )
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage").mkdir(parents=True, exist_ok=True)
    record_human_notification(
        root,
        task_name="newfoundland-bayman-fourclaw-engage",
        kind="agency_gate",
        message="review handoff created",
        summary={
            "execution": {"status": "pending_approval", "platform": "fourclaw", "blocked_reason": "agency_control_review_only"},
            "agency_control": {"effective_mode": "review_only", "reason": "supervised rollout"},
            "review_handoff": {"approval_id": approval["approval_id"], "title": "Review required: bayman fourclaw"},
        },
        operational_agent_id="newfoundland-bayman",
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ):
        rows = entities_service.list_entities()

    summary = rows[0]["review_handoff_summary"]
    assert summary["release_ready"] is False
    assert "approval_expired" in summary["release_blockers"]
    assert summary["latest"]["approval_expired"] is True
    assert summary["refresh_recommended"] is True
    assert "approval_expired" in summary["refresh_reasons"]


def test_list_entities_review_handoff_summary_includes_latest_release_attempt(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    approval = ApprovalService(db_path=str(tmp_path / "gateway.sqlite3")).create_request(
        entity_id="newfoundland-bayman-fourclaw-engage",
        action_kind="social_write",
        preview_json={"summary": "review me"},
        tenant_id="default",
        workflow_id="newfoundland-bayman-fourclaw-engage",
        target_platform="fourclaw",
    )
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage").mkdir(parents=True, exist_ok=True)
    record_human_notification(
        root,
        task_name="newfoundland-bayman-fourclaw-engage",
        kind="agency_gate",
        message="review handoff created",
        summary={
            "execution": {"status": "pending_approval", "platform": "fourclaw", "blocked_reason": "agency_control_review_only"},
            "agency_control": {"effective_mode": "review_only", "reason": "supervised rollout"},
            "review_handoff": {"approval_id": approval["approval_id"], "title": "Review required: bayman fourclaw"},
        },
        operational_agent_id="newfoundland-bayman",
    )
    record_human_notification(
        root,
        task_name="newfoundland-bayman-fourclaw-engage",
        kind="agency_gate",
        message="release blocked by hold",
        summary={
            "execution": {"status": "blocked", "platform": "fourclaw", "blocked_reason": "approval_release_held"},
            "agency_control": {"effective_mode": "held", "reason": "manual freeze"},
            "review_handoff": {"approval_id": approval["approval_id"], "status": "blocked"},
        },
        operational_agent_id="newfoundland-bayman",
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ):
        rows = entities_service.list_entities()

    latest_attempt = rows[0]["review_handoff_summary"]["latest"]["latest_release_attempt"]
    assert latest_attempt["status"] == "blocked"
    assert latest_attempt["reason"] == "approval_release_held"
    assert latest_attempt["message"] == "release blocked by hold"
    assert rows[0]["review_handoff_summary"]["refresh_recommended"] is True
    assert "approval_release_held" in rows[0]["review_handoff_summary"]["refresh_reasons"]


def test_list_entities_review_handoff_summary_moves_to_refreshed_approval(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    old_approval = ApprovalService(db_path=str(tmp_path / "gateway.sqlite3")).create_request(
        entity_id="newfoundland-bayman-fourclaw-engage",
        action_kind="social_write",
        preview_json={"summary": "review me"},
        tenant_id="default",
        workflow_id="newfoundland-bayman-fourclaw-engage",
        target_platform="fourclaw",
    )
    new_approval = ApprovalService(db_path=str(tmp_path / "gateway.sqlite3")).create_request(
        entity_id="newfoundland-bayman-fourclaw-engage",
        action_kind="social_write",
        preview_json={"summary": "review me again", "refreshed_from_approval_id": old_approval["approval_id"]},
        tenant_id="default",
        workflow_id="newfoundland-bayman-fourclaw-engage",
        target_platform="fourclaw",
    )
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage").mkdir(parents=True, exist_ok=True)
    record_human_notification(
        root,
        task_name="newfoundland-bayman-fourclaw-engage",
        kind="agency_gate",
        message="review handoff created",
        summary={
            "execution": {"status": "pending_approval", "platform": "fourclaw", "blocked_reason": "agency_control_review_only"},
            "agency_control": {"effective_mode": "review_only", "reason": "supervised rollout"},
            "review_handoff": {"approval_id": old_approval["approval_id"], "title": "Review required: bayman fourclaw"},
        },
        operational_agent_id="newfoundland-bayman",
    )
    record_human_notification(
        root,
        task_name="newfoundland-bayman-fourclaw-engage",
        kind="agency_gate",
        message="review handoff refreshed",
        summary={
            "execution": {"status": "pending_approval", "platform": "fourclaw", "blocked_reason": "review_handoff_refreshed"},
            "agency_control": {},
            "review_handoff": {
                "approval_id": new_approval["approval_id"],
                "refreshed_from_approval_id": old_approval["approval_id"],
                "title": "Review required: bayman fourclaw",
            },
        },
        operational_agent_id="newfoundland-bayman",
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ):
        rows = entities_service.list_entities()

    latest = rows[0]["review_handoff_summary"]["latest"]
    assert latest["approval_id"] == new_approval["approval_id"]
    assert latest["refreshed_from_approval_id"] == old_approval["approval_id"]


def test_list_entities_review_handoff_summary_includes_refresh_lineage_note(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    old_approval = ApprovalService(db_path=str(tmp_path / "gateway.sqlite3")).create_request(
        entity_id="newfoundland-bayman-fourclaw-engage",
        action_kind="social_write",
        preview_json={"summary": "review me"},
        tenant_id="default",
        workflow_id="newfoundland-bayman-fourclaw-engage",
        target_platform="fourclaw",
    )
    refreshed = ApprovalService(db_path=str(tmp_path / "gateway.sqlite3")).create_request(
        entity_id="newfoundland-bayman-fourclaw-engage",
        action_kind="social_write",
        preview_json={
            "summary": "review me again",
            "refresh_context": {
                "from_approval_id": old_approval["approval_id"],
                "note": "stale context",
                "refreshed_by": "operator_console",
                "source_status": "approved",
                "reason_codes": ["followup_overdue"],
            },
        },
        tenant_id="default",
        workflow_id="newfoundland-bayman-fourclaw-engage",
        target_platform="fourclaw",
    )
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage").mkdir(parents=True, exist_ok=True)
    record_human_notification(
        root,
        task_name="newfoundland-bayman-fourclaw-engage",
        kind="agency_gate",
        message="review handoff refreshed",
        summary={
            "execution": {"status": "pending_approval", "platform": "fourclaw", "blocked_reason": "review_handoff_refreshed"},
            "agency_control": {},
            "review_handoff": {
                "approval_id": refreshed["approval_id"],
                "title": "Review required: bayman fourclaw",
            },
        },
        operational_agent_id="newfoundland-bayman",
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ):
        rows = entities_service.list_entities()

    latest = rows[0]["review_handoff_summary"]["latest"]
    assert latest["approval_id"] == refreshed["approval_id"]
    assert latest["refreshed_from_approval_id"] == old_approval["approval_id"]
    assert latest["refresh_note"] == "stale context"
    assert latest["refreshed_by"] == "operator_console"
    assert latest["refresh_reason_codes"] == ["followup_overdue"]


def test_list_entities_review_handoff_summary_recommends_refresh_after_blocked_release(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    approval = ApprovalService(db_path=str(tmp_path / "gateway.sqlite3")).create_request(
        entity_id="newfoundland-bayman-fourclaw-engage",
        action_kind="social_write",
        preview_json={"summary": "review me"},
        tenant_id="default",
        workflow_id="newfoundland-bayman-fourclaw-engage",
        target_platform="fourclaw",
    )
    ApprovalService(db_path=str(tmp_path / "gateway.sqlite3")).approve(
        approval["approval_id"],
        tenant_id="default",
        decided_by="operator",
        decision_note="looks good",
    )
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage").mkdir(parents=True, exist_ok=True)
    record_human_notification(
        root,
        task_name="newfoundland-bayman-fourclaw-engage",
        kind="agency_gate",
        message="review handoff created",
        summary={
            "execution": {"status": "pending_approval", "platform": "fourclaw", "blocked_reason": "agency_control_review_only"},
            "agency_control": {"effective_mode": "review_only", "reason": "supervised rollout"},
            "review_handoff": {"approval_id": approval["approval_id"], "title": "Review required: bayman fourclaw"},
        },
        operational_agent_id="newfoundland-bayman",
    )
    record_human_notification(
        root,
        task_name="newfoundland-bayman-fourclaw-engage",
        kind="agency_gate",
        message="release blocked by hold",
        summary={
            "execution": {"status": "blocked", "platform": "fourclaw", "blocked_reason": "approval_release_held"},
            "agency_control": {"effective_mode": "held", "reason": "manual freeze"},
            "review_handoff": {"approval_id": approval["approval_id"], "status": "blocked"},
        },
        operational_agent_id="newfoundland-bayman",
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ):
        rows = entities_service.list_entities()

    summary = rows[0]["review_handoff_summary"]
    assert summary["refresh_recommended"] is True
    assert "status:approved" in summary["refresh_reasons"]
    assert "approval_release_held" in summary["refresh_reasons"]


def test_list_entities_includes_assigned_social_accounts(tmp_path: Path):
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage").mkdir(parents=True, exist_ok=True)

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ), patch.object(
        entities_service,
        "_assigned_social_accounts",
        return_value=[{"account_alias": "bayman-fourclaw", "state": "verified"}],
    ):
        rows = entities_service.list_entities()

    assert rows[0]["assigned_social_accounts"][0]["account_alias"] == "bayman-fourclaw"


def test_list_entities_includes_assigned_account_continuity_summary(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage").mkdir(parents=True, exist_ok=True)

    from hg_gateway import keystore_repo

    keystore_repo.social_account_create(
        social_account_id="acct-bayman-fourclaw",
        tenant_id="default",
        platform="fourclaw",
        account_alias="bayman-fourclaw",
        entity_scope="newfoundland-bayman",
        persona_scope="newfoundland_bayman_operational",
        state="verified",
        db_path=str(db_path),
    )
    record_social_account_session_binding(
        "acct-bayman-fourclaw",
        browser_session_id="session-bad",
        platform="fourclaw",
        tenant_id="default",
        entity_id="newfoundland-bayman",
        account_alias="bayman-fourclaw",
        state="active",
    )
    with get_connection(str(db_path)) as conn:
        conn.execute(
            """INSERT INTO browser_sessions (browser_session_id, tenant_id, entity_id, platform, state, started_at)
               VALUES (?, ?, ?, ?, ?, datetime('now'))""",
            ("session-bad", "default", "newfoundland-bayman", "fourclaw", "degraded"),
        )
        conn.execute(
            """INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at)
               VALUES (?, 'browser_session', ?, 'session_degraded', ?, ?, datetime('now'))""",
            ("proof-bad", "session-bad", "missing_restart_critical_browser_artifacts", '{"reason":"missing_restart_critical_browser_artifacts"}'),
        )
    registration_artifact = tmp_path / "bayman-proof.json"
    registration_artifact.write_text('{"handle":"@bayman","state":"verified"}', encoding="utf-8")
    with get_connection(str(db_path)) as conn:
        conn.execute(
            """INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at)
               VALUES (?, 'social_account', ?, 'registration_proof', ?, ?, datetime('now'))""",
            ("proof-registration", "acct-bayman-fourclaw", str(registration_artifact), '{"handle":"@bayman"}'),
        )
    record_social_account_session_binding(
        "acct-bayman-fourclaw",
        browser_session_id="session-bad",
        platform="fourclaw",
        tenant_id="default",
        entity_id="newfoundland-bayman",
        account_alias="bayman-fourclaw",
        state="active",
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ):
        rows = entities_service.list_entities()

    account = rows[0]["assigned_social_accounts"][0]
    continuity = account["continuity_summary"]
    assert continuity["status"] == "degraded"
    assert continuity["browser_session_id"] == "session-bad"
    assert continuity["browser_session_started_at"] is not None
    assert continuity["degraded_reason"] == "missing_restart_critical_browser_artifacts"
    assert account["proof_summary"]["latest_artifact_type"] == "registration_proof"
    assert account["proof_summary"]["latest_handle"] == "@bayman"
    assert account["readiness_summary"]["ready"] is False
    assert "continuity_healthy" in account["readiness_summary"]["blocking"]
    assert account["continuity_injury_summary"]["status"] == "active"
    assert account["continuity_injury_summary"]["active"] is True
    assert account["continuity_injury_summary"]["last_injury_reason"] == "missing_restart_critical_browser_artifacts"
    assert rows[0]["continuity_incident_summary"]["status"] == "active"
    assert rows[0]["continuity_incident_summary"]["active_account_count"] == 1
    assert "bayman-fourclaw" in rows[0]["continuity_incident_summary"]["active_accounts"]
    readiness = rows[0]["continuity_recovery_readiness"]
    assert readiness["status"] == "blocked"
    assert readiness["safe_to_resume"] is False
    assert "active_continuity_incident" in readiness["blocking"]
    assert "replace_or_rebind_damaged_session" in rows[0]["continuity_repair_plan"]["open_checks"]


def test_list_entities_includes_assigned_account_notification_summary(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage").mkdir(parents=True, exist_ok=True)

    from hg_gateway import keystore_repo

    keystore_repo.social_account_create(
        social_account_id="acct-bayman-fourclaw",
        tenant_id="default",
        platform="fourclaw",
        account_alias="bayman-fourclaw",
        entity_scope="newfoundland-bayman",
        persona_scope="newfoundland_bayman_operational",
        state="verified",
        db_path=str(db_path),
    )
    record_human_notification(
        root,
        task_name="newfoundland-bayman-fourclaw-engage",
        kind="run_update",
        message="posted a reply on fourclaw",
        summary={"execution": {"status": "completed", "platform": "fourclaw"}},
        transport="configured_channel",
        social_account_id="acct-bayman-fourclaw",
        tenant_id="default",
        operational_agent_id="newfoundland-bayman",
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ):
        rows = entities_service.list_entities()

    account = rows[0]["assigned_social_accounts"][0]
    assert account["notification_summary"]["count"] == 1
    assert account["notification_summary"]["latest"]["message"] == "posted a reply on fourclaw"
    assert account["last_activity_summary"]["last_seen_kind"] == "notification"
    assert account["last_activity_summary"]["last_seen_detail"] == "run_update"


def test_list_entities_includes_assigned_account_last_activity_from_degraded_continuity(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage").mkdir(parents=True, exist_ok=True)

    from hg_gateway import keystore_repo

    keystore_repo.social_account_create(
        social_account_id="acct-bayman-fourclaw",
        tenant_id="default",
        platform="fourclaw",
        account_alias="bayman-fourclaw",
        entity_scope="newfoundland-bayman",
        persona_scope="newfoundland_bayman_operational",
        state="verified",
        db_path=str(db_path),
    )
    record_social_account_session_binding(
        "acct-bayman-fourclaw",
        browser_session_id="session-bad",
        platform="fourclaw",
        tenant_id="default",
        entity_id="newfoundland-bayman",
        account_alias="bayman-fourclaw",
        state="active",
    )
    with get_connection(str(db_path)) as conn:
        conn.execute(
            """INSERT INTO browser_sessions (browser_session_id, tenant_id, entity_id, platform, state, started_at)
               VALUES (?, ?, ?, ?, ?, datetime('now'))""",
            ("session-bad", "default", "newfoundland-bayman", "fourclaw", "degraded"),
        )
        conn.execute(
            """INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at)
               VALUES (?, 'browser_session', ?, 'session_degraded', ?, ?, '2026-03-13T23:59:59Z')""",
            ("proof-bad", "session-bad", "missing_restart_critical_browser_artifacts", '{"reason":"missing_restart_critical_browser_artifacts"}'),
        )
    record_social_account_session_binding(
        "acct-bayman-fourclaw",
        browser_session_id="session-good",
        platform="fourclaw",
        tenant_id="default",
        entity_id="newfoundland-bayman",
        account_alias="bayman-fourclaw",
        state="active",
    )
    with get_connection(str(db_path)) as conn:
        conn.execute(
            """UPDATE proof_artifacts
               SET created_at = '2026-03-13T23:00:00Z'
               WHERE related_kind = 'social_account' AND related_id = ? AND artifact_type = 'browser_session_binding' AND path LIKE ?""",
            ("acct-bayman-fourclaw", "%session-bad%"),
        )
        conn.execute(
            """UPDATE proof_artifacts
               SET created_at = '2026-03-14T01:31:00Z'
               WHERE related_kind = 'social_account' AND related_id = ? AND artifact_type = 'browser_session_binding' AND path LIKE ?""",
            ("acct-bayman-fourclaw", "%session-good%"),
        )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ), patch.object(social_account_summary, "_workspace_root", return_value=root):
        rows = entities_service.list_entities()

    account = rows[0]["assigned_social_accounts"][0]
    assert account["last_activity_summary"]["last_seen_kind"] == "continuity_issue"
    assert account["last_activity_summary"]["last_seen_detail"] == "missing_restart_critical_browser_artifacts"
    assert account["last_activity_summary"]["last_seen_at"] == "2026-03-13T23:59:59Z"


def test_list_entities_includes_assigned_account_continuity_repair_summary(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage").mkdir(parents=True, exist_ok=True)

    from hg_gateway import keystore_repo

    keystore_repo.social_account_create(
        social_account_id="acct-bayman-fourclaw",
        tenant_id="default",
        platform="fourclaw",
        account_alias="bayman-fourclaw",
        entity_scope="newfoundland-bayman",
        persona_scope="newfoundland_bayman_operational",
        state="verified",
        db_path=str(db_path),
    )
    record_social_account_session_binding(
        "acct-bayman-fourclaw",
        browser_session_id="session-bad",
        platform="fourclaw",
        tenant_id="default",
        entity_id="newfoundland-bayman",
        account_alias="bayman-fourclaw",
        state="degraded",
    )
    record_social_account_session_binding(
        "acct-bayman-fourclaw",
        browser_session_id="session-good",
        platform="fourclaw",
        tenant_id="default",
        entity_id="newfoundland-bayman",
        account_alias="bayman-fourclaw",
        state="active",
    )
    profile_dir = tmp_path / "browser-profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = tmp_path / "browser.png"
    screenshot_path.write_text("ok", encoding="utf-8")
    snapshot_path = tmp_path / "browser-state.json"
    snapshot_path.write_text("{}", encoding="utf-8")
    trace_path = tmp_path / "browser.zip"
    trace_path.write_text("trace", encoding="utf-8")
    with get_connection(str(db_path)) as conn:
        conn.execute(
            """INSERT INTO browser_sessions (browser_session_id, tenant_id, entity_id, platform, state, started_at)
               VALUES (?, ?, ?, ?, ?, '2026-03-13T23:00:00Z')""",
            ("session-bad", "default", "newfoundland-bayman", "fourclaw", "degraded"),
        )
        conn.execute(
            """INSERT INTO browser_sessions (browser_session_id, tenant_id, entity_id, platform, state, started_at, trace_path, latest_screenshot_path)
               VALUES (?, ?, ?, ?, ?, '2026-03-14T01:30:00Z', ?, ?)""",
            ("session-good", "default", "newfoundland-bayman", "fourclaw", "active", str(trace_path), str(screenshot_path)),
        )
        conn.execute(
            """INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at)
               VALUES (?, 'browser_session', ?, 'snapshot', ?, ?, '2026-03-14T01:30:10Z')""",
            ("proof-snapshot", "session-good", str(snapshot_path), '{}'),
        )
        conn.execute(
            """INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at)
               VALUES (?, 'browser_session', ?, 'profile_dir', ?, ?, '2026-03-14T01:30:05Z')""",
            ("proof-profile", "session-good", str(profile_dir), '{}'),
        )
        conn.execute(
            """INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at)
               VALUES (?, 'browser_session', ?, 'session_degraded', ?, ?, '2026-03-13T23:59:59Z')""",
            ("proof-bad", "session-bad", "missing_restart_critical_browser_artifacts", '{"reason":"missing_restart_critical_browser_artifacts"}'),
        )
    record_social_account_session_binding(
        "acct-bayman-fourclaw",
        browser_session_id="session-good",
        platform="fourclaw",
        tenant_id="default",
        entity_id="newfoundland-bayman",
        account_alias="bayman-fourclaw",
        state="active",
    )
    with get_connection(str(db_path)) as conn:
        conn.execute(
            """UPDATE proof_artifacts
               SET created_at = '2026-03-13T22:59:00Z'
               WHERE related_kind = 'social_account' AND related_id = ? AND artifact_type = 'browser_session_binding' AND path LIKE ?""",
            ("acct-bayman-fourclaw", "%session-bad%"),
        )
        conn.execute(
            """UPDATE proof_artifacts
               SET created_at = '2026-03-14T01:31:00Z'
               WHERE related_kind = 'social_account' AND related_id = ? AND artifact_type = 'browser_session_binding' AND path LIKE ?""",
            ("acct-bayman-fourclaw", "%session-good%"),
        )
    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ):
        rows = entities_service.list_entities()

    account = rows[0]["assigned_social_accounts"][0]
    injury = account["continuity_injury_summary"]
    assert account["continuity_summary"]["status"] == "healthy"
    assert injury["status"] == "recovered"
    assert injury["repaired"] is True
    assert injury["last_injury_reason"] == "missing_restart_critical_browser_artifacts"
    assert injury["last_repair_kind"] == "session_restart"
    assert injury["last_repair_at"] == "2026-03-14T01:30:00Z"
    assert rows[0]["continuity_incident_summary"]["status"] == "recovered"
    assert "bayman-fourclaw" in rows[0]["continuity_incident_summary"]["recovered_accounts"]
    readiness = rows[0]["continuity_recovery_readiness"]
    assert readiness["status"] == "caution"
    assert readiness["safe_to_resume"] is False
    assert "recent_continuity_recovery" in readiness["cautions"]
    assert "post_repair_observation_pending" in readiness["cautions"]
    assert rows[0]["continuity_repair_observation"]["status"] == "pending"
    assert "acknowledge_bounded_resume" in rows[0]["continuity_repair_plan"]["open_checks"]
    assert "observe_first_post_repair_cycle" in rows[0]["continuity_repair_plan"]["open_checks"]


def test_list_entities_marks_post_repair_observation_complete(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage").mkdir(parents=True, exist_ok=True)

    from hg_gateway import keystore_repo

    keystore_repo.social_account_create(
        social_account_id="acct-bayman-fourclaw",
        tenant_id="default",
        platform="fourclaw",
        account_alias="bayman-fourclaw",
        entity_scope="newfoundland-bayman",
        persona_scope="newfoundland_bayman_operational",
        state="verified",
        db_path=str(db_path),
    )
    record_social_account_session_binding(
        "acct-bayman-fourclaw",
        browser_session_id="session-bad",
        platform="fourclaw",
        tenant_id="default",
        entity_id="newfoundland-bayman",
        account_alias="bayman-fourclaw",
        state="degraded",
    )
    record_social_account_session_binding(
        "acct-bayman-fourclaw",
        browser_session_id="session-good",
        platform="fourclaw",
        tenant_id="default",
        entity_id="newfoundland-bayman",
        account_alias="bayman-fourclaw",
        state="active",
    )
    profile_dir = tmp_path / "browser-profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = tmp_path / "browser.png"
    screenshot_path.write_text("ok", encoding="utf-8")
    snapshot_path = tmp_path / "browser-state.json"
    snapshot_path.write_text("{}", encoding="utf-8")
    trace_path = tmp_path / "browser.zip"
    trace_path.write_text("trace", encoding="utf-8")
    with get_connection(str(db_path)) as conn:
        conn.execute(
            """INSERT INTO browser_sessions (browser_session_id, tenant_id, entity_id, platform, state, started_at)
               VALUES (?, ?, ?, ?, ?, '2026-03-13T23:00:00Z')""",
            ("session-bad", "default", "newfoundland-bayman", "fourclaw", "degraded"),
        )
        conn.execute(
            """INSERT INTO browser_sessions (browser_session_id, tenant_id, entity_id, platform, state, started_at, trace_path, latest_screenshot_path)
               VALUES (?, ?, ?, ?, ?, '2026-03-14T01:30:00Z', ?, ?)""",
            ("session-good", "default", "newfoundland-bayman", "fourclaw", "active", str(trace_path), str(screenshot_path)),
        )
        conn.execute(
            """INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at)
               VALUES (?, 'browser_session', ?, 'snapshot', ?, ?, '2026-03-14T01:30:10Z')""",
            ("proof-snapshot", "session-good", str(snapshot_path), '{}'),
        )
        conn.execute(
            """INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at)
               VALUES (?, 'browser_session', ?, 'profile_dir', ?, ?, '2026-03-14T01:30:05Z')""",
            ("proof-profile", "session-good", str(profile_dir), '{}'),
        )
        conn.execute(
            """INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at)
               VALUES (?, 'browser_session', ?, 'session_degraded', ?, ?, '2026-03-13T23:59:59Z')""",
            ("proof-bad", "session-bad", "missing_restart_critical_browser_artifacts", '{"reason":"missing_restart_critical_browser_artifacts"}'),
        )
        conn.execute(
            """UPDATE proof_artifacts
               SET created_at = '2026-03-13T22:59:00Z'
               WHERE related_kind = 'social_account' AND related_id = ? AND artifact_type = 'browser_session_binding' AND path LIKE ?""",
            ("acct-bayman-fourclaw", "%session-bad%"),
        )
        conn.execute(
            """UPDATE proof_artifacts
               SET created_at = '2026-03-14T01:31:00Z'
               WHERE related_kind = 'social_account' AND related_id = ? AND artifact_type = 'browser_session_binding' AND path LIKE ?""",
            ("acct-bayman-fourclaw", "%session-good%"),
        )
    notification = record_human_notification(
        root,
        task_name="newfoundland-bayman-fourclaw-engage",
        recipient="The Reverend",
        kind="run_update",
        transport="configured_channel",
        message="post-repair engage cycle completed",
        summary={"execution": {"status": "completed", "platform": "fourclaw"}},
        social_account_id="acct-bayman-fourclaw",
        tenant_id="default",
        operational_agent_id="newfoundland-bayman",
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ):
        rows = entities_service.list_entities()

    observation = rows[0]["continuity_repair_observation"]
    assert observation["status"] == "observed"
    assert observation["observation_complete"] is True
    assert observation["latest_observed_kind"] == "notification"
    assert observation["latest_observed_at"] == notification["entry"]["timestamp"]
    assert rows[0]["continuity_recovery_readiness"]["status"] == "caution"
    assert "observe_first_post_repair_cycle" not in rows[0]["continuity_repair_plan"]["open_checks"]
    assert "observe_first_post_repair_cycle" in rows[0]["continuity_repair_plan"]["completed_checks"]


def test_list_entities_uses_shared_decision_summary_for_postgres_runtime(tmp_path: Path):
    registry = {
        "fourclaw-engage": {
            "job_id": "fourclaw-engage",
            "session_target": "automation-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-fourclaw-engage").mkdir(parents=True, exist_ok=True)

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service, "_get_registry", return_value=registry
    ), patch.object(
        entities_service, "use_shared_gateway_db", return_value=True
    ), patch.object(
        entities_service,
        "_get_shared_decision_summary",
        return_value={"fourclaw-engage": (True, "2026-03-09T04:00:00Z", 12)},
    ):
        rows = entities_service.list_entities()

    assert len(rows) == 1
    assert rows[0]["has_decisions"] is True
    assert rows[0]["last_activity"] == "2026-03-09T04:00:00Z"
    assert rows[0]["wake_context_tokens"] is None


def test_list_entities_includes_research_delivery_summary(tmp_path: Path):
    from operator_console.server.app.services import research_delivery_summary

    registry = {
        "fourclaw-auto-post": {
            "job_id": "fourclaw-auto-post",
            "session_target": "automation-fourclaw-auto-post",
            "platform": "fourclaw",
            "mode": "auto-post",
        }
    }
    root = tmp_path
    (root / "memory" / "automation").mkdir(parents=True, exist_ok=True)
    save_operational_json_state(
        root,
        state_key="research_deliveries",
        payload={
            "deliveries": [
                {
                    "requested_by": "automation-fourclaw-auto-post",
                    "topic": "Bayman continuity",
                    "file_path": "knowledge/technology/bayman-continuity.md",
                    "delivered_at": "2026-03-13T12:00:00Z",
                }
            ]
        },
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ), patch.object(
        research_delivery_summary,
        "_workspace_root",
        return_value=root,
    ):
        rows = entities_service.list_entities()

    summary = rows[0]["research_delivery_summary"]
    assert summary["delivery_count"] == 1
    assert summary["recent_deliveries"][0]["topic"] == "Bayman continuity"


def test_list_entities_includes_entity_profile(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    import operator_console.server.app.services.activity_service as activity_service
    import operator_console.server.app.services.steering_service as steering_service
    registry = {
        "newfoundland-bayman-fourclaw-engage": {
            "job_id": "newfoundland-bayman-fourclaw-engage",
            "session_target": "automation-newfoundland-bayman-fourclaw-engage",
            "platform": "fourclaw",
            "mode": "engage",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-engage").mkdir(parents=True, exist_ok=True)
    save_operational_json_state(
        root,
        state_key="identity_continuity_state:automation-newfoundland-bayman-fourclaw-engage",
        payload={
            "wake_receipt_present": True,
            "wake_receipt": {
                "wake_completed_at": "2026-03-23T17:59:00Z",
                "dag_inputs": {"goal": "demo the control center"},
            },
        },
    )
    upsert_run(
        {
            "run_id": "run-profile-1",
            "graph_id": "newfoundland-bayman-fourclaw-engage",
            "status": "completed",
            "started_at": "2026-03-23T18:00:00Z",
            "ended_at": "2026-03-23T18:05:00Z",
            "run_dir": str(root / ".hg_runs" / "run-profile-1"),
            "correlation_id": "entity-profile-1",
        }
    )

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ), patch.object(social_account_summary, "_workspace_root", return_value=root), patch.object(
        activity_service,
        "get_recent_activity",
        return_value={
            "activity_projection": {
                "since_last_wake": {
                    "summary": "3 events since latest wake",
                    "counts": {"events": 3, "turns": 1, "approvals": 1, "notifications": 1, "decisions": 0, "provenance": 0},
                    "timeline": [
                        {"title": "Turn completed", "detail": "reply"},
                        {"title": "Approval resolved", "detail": "approved · approval-1"},
                    ],
                }
            },
            "recent_timeline_events": [
                {"title": "Turn completed", "detail": "reply"},
                {"title": "Approval resolved", "detail": "approved · approval-1"},
            ],
        },
    ), patch.object(
        steering_service,
        "get_steering_profile",
        return_value={
            "version": 7,
            "updated_at": "2026-03-23T18:06:00Z",
            "mode": "default",
            "priority": "normal",
            "risk_tolerance": "medium",
            "leak_mode": "hidden",
            "private_person_targeting": "avoid",
            "notes": "tightened feedback loop",
        },
    ):
        rows = entities_service.list_entities()

    profile = rows[0]["profile"]
    assert profile["overview"]["latest_run_id"] == "run-profile-1"
    assert profile["overview"]["latest_run_count"] >= 1
    assert profile["continuity"]["continuity_recovery_readiness"]["status"] == rows[0]["continuity_recovery_readiness"]["status"]
    assert profile["approvals"]["review_handoff_summary"]["count"] == rows[0]["review_handoff_summary"]["count"]
    assert profile["continuity_view"]["since_last_wake"]["summary"] == "3 events since latest wake"
    assert profile["continuity_view"]["conflicts"]
    assert profile["continuity_view"]["scheduled_work"]
    assert profile["continuity_view"]["stale_facts"]
    assert profile["continuity_view"]["next_action"]
    assert profile["continuity_view"]["reviewable"] is True
    assert profile["continuity_view"]["steering"]["version"] == 7
    assert profile["continuity_view"]["steering"]["agent_id"] == "newfoundland-bayman"
    assert profile["self_location"]["role"] == "newfoundland-bayman-fourclaw-engage"
    assert profile["self_location"]["mode"] == "engage"
    assert profile["self_location"]["goals"] == ["demo the control center"]
    assert profile["self_location"]["active_branch_state"]["scope"] == "branch-local"
    assert profile["self_location"]["memory_scope"]["promotion_rule"]
    assert profile["same_fingerprint_summary"]["status"] == "hidden"
    assert profile["same_fingerprint_summary"]["decision"] == "cut_from_user_visible_claims"
    assert profile["reflection_status"]["status"] == "proxy"


def test_list_entities_includes_drift_review_summary(tmp_path: Path):
    registry = {
        "social-media-underling": {
            "job_id": "social-media-underling",
            "session_target": "automation-underling-chan",
            "platform": "social",
            "mode": "unified-social",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-underling-chan").mkdir(parents=True, exist_ok=True)

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ), patch.object(
        entities_service,
        "build_drift_review_summary",
        return_value={
            "status": "watch",
            "max_score": 0.82,
            "active_safeguards": [],
            "comparison": {"summary": "policy version changed"},
            "recent_drift_events": [{"event_id": "drift-1", "title": "Drift detected"}],
        },
    ):
        rows = entities_service.list_entities()

    assert rows[0]["drift_review_summary"]["status"] == "watch"
    assert rows[0]["confidence_summary"]["confidence_level"] in {"uncertain", "cautious", "confident", "certain"}
    assert "drift_watch" in rows[0]["confidence_summary"]["confidence_cautions"]


def test_list_entities_includes_mimicry_and_continuity_quality_summary(tmp_path: Path):
    registry = {
        "social-media-underling": {
            "job_id": "social-media-underling",
            "session_target": "automation-underling-chan",
            "platform": "social",
            "mode": "unified-social",
        }
    }
    root = tmp_path
    (root / "memory" / "automation" / "automation-underling-chan").mkdir(parents=True, exist_ok=True)

    with patch.object(entities_service, "_workspace_root", return_value=root), patch.object(
        entities_service,
        "_get_registry",
        return_value=registry,
    ), patch.object(
        entities_service,
        "build_drift_review_summary",
        return_value={
            "status": "healthy",
            "max_score": 0.1,
            "active_safeguards": [],
            "comparison": {"summary": "No material baseline drift."},
            "recent_drift_events": [],
        },
    ), patch.object(
        entities_service,
        "build_mimicry_policy_summary",
        return_value={
            "status": "ready",
            "voice_belief_separated": True,
            "grounding_required": True,
            "limits": {"max_mimicry_depth": 0.65, "max_emotional_intensity": 0.55},
            "safeguard_summary": {"status": "healthy", "grounded": True},
            "summary": "mimicry controls ready",
        },
    ), patch.object(
        entities_service,
        "build_voice_belief_separation_summary",
        return_value={
            "status": "healthy",
            "voice_belief_separated": True,
            "grounded": True,
            "summary": "voice separated from durable belief",
        },
    ), patch.object(
        entities_service,
        "build_continuity_quality_summary",
        return_value={
            "status": "healthy",
            "quality_score": 88.0,
            "coverage_score": 0.9,
            "attribution_score": 0.85,
            "operator_override_rate": 0.1,
            "promotion_accuracy": 0.76,
            "summary": "continuity quality healthy",
        },
    ):
        rows = entities_service.list_entities()

    assert rows[0]["mimicry_control_summary"]["status"] == "ready"
    assert rows[0]["voice_belief_separation_summary"]["status"] == "healthy"
    assert rows[0]["continuity_quality_summary"]["status"] == "healthy"
    assert rows[0]["confidence_summary"]["confidence_level"] in {"uncertain", "cautious", "confident", "certain"}
    assert "mimicry_ready" in rows[0]["confidence_summary"]["confidence_drivers"]
    assert "continuity_quality_healthy" in rows[0]["confidence_summary"]["confidence_drivers"]
