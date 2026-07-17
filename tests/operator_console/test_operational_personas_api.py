from __future__ import annotations

import json

from fastapi.testclient import TestClient

from operator_console.server.app.main import app
from operator_console.server.app.core.auth import require_api_key
from hg_gateway import keystore_repo
from hg_gateway import store as store_module
from hg_core.human_notifications import record_human_notification
from hg_core.security.social_account_artifacts import record_social_account_session_binding
from hg_gateway.db import get_connection
from hg_gateway.operational_state_ledger import save_operational_json_state
from operator_console.server.app.services.post_rebuild_continuity_check import record_post_rebuild_event
from operator_console.server.app.services.post_rebuild_continuity_check import record_post_rebuild_event
from operator_console.server.app.services.run_index_db import upsert_run


def test_operational_personas_api_lists_platform_bindings():
    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/personas/operational")
        assert response.status_code == 200
        payload = response.json()
        items = payload.get("items") or []
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in items}
        assert ("fourclaw", "underling-chan") in by_binding
        assert ("moltbook", "moltbook") in by_binding
        assert ("aichan", "underling-chan") in by_binding
        assert ("agentchan", "underling-chan") in by_binding
        assert ("moltx", "moltx") in by_binding
        assert ("moltstack", "moltstack") in by_binding
        assert ("fourclaw", "newfoundland-bayman") in by_binding
        assert ("moltbook", "newfoundland-bayman") in by_binding
        assert by_binding[("fourclaw", "underling-chan")]["fingerprint_id"] == "underling_chan_operational"
        assert by_binding[("moltbook", "moltbook")]["persona_set"] == "operational"
        assert by_binding[("aichan", "underling-chan")]["fingerprint_id"] == "underling_chan_operational"
        assert by_binding[("agentchan", "underling-chan")]["fingerprint_id"] == "underling_chan_operational"
        assert by_binding[("fourclaw", "newfoundland-bayman")]["fingerprint_id"] == "newfoundland_bayman_operational"
        assert isinstance(by_binding[("fourclaw", "underling-chan")]["commitment_summary"], dict)
        assert "fourclaw-auto-post" in by_binding[("fourclaw", "underling-chan")]["tasks"]
        assert "newfoundland-bayman-fourclaw-auto-post" in by_binding[("fourclaw", "newfoundland-bayman")]["tasks"]
        fourclaw = by_binding[("fourclaw", "underling-chan")]
        assert isinstance(fourclaw["crew_dynamics_summary"], dict)
        assert isinstance(fourclaw.get("linked_tasks"), list)
        assert any(task.get("id") == "fourclaw-auto-post" for task in fourclaw["linked_tasks"])
        assert isinstance(fourclaw.get("memory_health"), dict)
        assert "status" in fourclaw["memory_health"]
        assert isinstance(fourclaw.get("identity_continuity_summary"), dict)
        assert isinstance(fourclaw.get("jump_links"), dict)
        assert fourclaw["jump_links"]["approvals"] == "#/approvals"
        assert isinstance(by_binding[("fourclaw", "newfoundland-bayman")].get("assigned_social_accounts"), list)
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_personas_api_includes_identity_continuity_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    save_operational_json_state(
        tmp_path,
        state_key="identity_continuity_state:automation-newfoundland-bayman",
        payload={
            "initialization_memo_present": True,
            "initialization_memo_path": "memory/automation/automation-newfoundland-bayman/initialization_memo.md",
            "wake_receipt_present": True,
            "wake_receipt_recorded_at": "2026-03-13T15:00:00Z",
            "wake_receipt": {"timestamp": "2026-03-13T15:00:00Z"},
            "last_wake_at": "2026-03-13T15:00:00Z",
            "sleep_summary_present": True,
            "sleep_summary_recorded_at": "2026-03-13T14:00:00Z",
            "last_sleep_at": "2026-03-13T14:00:00Z",
            "last_sleep_summary": {"timestamp": "2026-03-13T14:00:00Z"},
        },
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/personas/operational")
        assert response.status_code == 200
        items = response.json().get("items") or []
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in items}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        summary = bayman["identity_continuity_summary"]
        assert summary["status"] in {"healthy", "partial"}
        assert summary["continuity_anchor"] == "newfoundland-bayman"
        assert summary["initialization_memo_present"] is True
        assert summary["wake_receipt_present"] is True
        assert summary["sleep_summary_present"] is True
        assert summary["last_wake_at"] == "2026-03-13T15:00:00Z"
        assert bayman["identity_resume_procedure"]["status"] == "ready"
        assert bayman["continuity_incident_summary"]["status"] == "clean"
        assert bayman["continuity_recovery_readiness"]["status"] == "ready"
        assert bayman["continuity_repair_plan"]["status"] == "clean"
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_personas_api_includes_entity_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    import operator_console.server.app.services.activity_service as activity_service
    import operator_console.server.app.services.steering_service as steering_service
    save_operational_json_state(
        tmp_path,
        state_key="identity_continuity_state:automation-newfoundland-bayman-fourclaw-engage",
        payload={
            "wake_receipt_present": True,
            "wake_receipt": {
                "wake_completed_at": "2026-03-23T17:59:00Z",
                "dag_inputs": {"goal": "demo the control center"},
            },
        },
    )
    save_operational_json_state(
        tmp_path,
        state_key="identity_continuity_state:automation-newfoundland-bayman-fourclaw-auto-post",
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
            "run_dir": str(tmp_path / ".hg_runs" / "run-profile-1"),
            "correlation_id": "persona-profile-1",
        }
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        with monkeypatch.context() as m:
            m.setattr(
                activity_service,
                "get_recent_activity",
                lambda **kwargs: {
                    "activity_projection": {
                        "since_last_wake": {
                            "summary": "5 events since latest wake",
                            "counts": {"events": 5, "turns": 2, "approvals": 1, "notifications": 1, "decisions": 1, "provenance": 0},
                            "timeline": [
                                {"title": "Turn completed", "detail": "reply"},
                                {"title": "Approval resolved", "detail": "approved · approval-7"},
                            ],
                        }
                    },
                    "recent_timeline_events": [
                        {"title": "Turn completed", "detail": "reply"},
                        {"title": "Approval resolved", "detail": "approved · approval-7"},
                    ],
                },
            )
            m.setattr(
                steering_service,
                "get_steering_profile",
                lambda agent_id: {
                    "version": 11,
                    "updated_at": "2026-03-23T18:06:00Z",
                    "mode": "default",
                    "priority": "normal",
                    "risk_tolerance": "medium",
                    "leak_mode": "hidden",
                    "private_person_targeting": "avoid",
                    "notes": "tightened feedback loop",
                },
            )
            response = client.get("/api/v1/personas/operational")
        assert response.status_code == 200
        items = response.json().get("items") or []
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in items}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        profile = bayman["profile"]
        assert profile["overview"]["entity_id"] == bayman["id"]
        assert profile["overview"]["latest_run_id"] == "run-profile-1"
        assert profile["overview"]["latest_run_count"] >= 1
        assert profile["continuity"]["continuity_recovery_readiness"]["status"] == bayman["continuity_recovery_readiness"]["status"]
        assert profile["continuity_view"]["since_last_wake"]["summary"] == "5 events since latest wake"
        assert profile["continuity_view"]["conflicts"]
        assert profile["continuity_view"]["scheduled_work"]
        assert profile["continuity_view"]["stale_facts"]
        assert profile["continuity_view"]["next_action"]
        assert profile["continuity_view"]["steering"]["version"] == 11
        assert profile["self_location"]["role"].startswith("newfoundland-bayman-fourclaw-")
        assert profile["self_location"]["mode"] in {"engage", "operational"}
        assert profile["self_location"]["summary"]
        assert profile["self_location"]["memory_scope"]["scope"] in {"shared", "branch-local"}
        assert profile["same_fingerprint_summary"]["status"] in {"hidden", "missing"}
        assert profile["approvals"]["pending_approvals"] == bayman["pending_approvals"]
        assert profile["reflection_status"]["status"] == "proxy"
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_personas_api_includes_identity_resume_procedure_for_partial_identity(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    save_operational_json_state(
        tmp_path,
        state_key="identity_continuity_state:automation-newfoundland-bayman",
        payload={
            "initialization_memo_present": True,
            "initialization_memo_path": "memory/automation/automation-newfoundland-bayman/initialization_memo.md",
        },
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/personas/operational")
        assert response.status_code == 200
        items = response.json().get("items") or []
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in items}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        procedure = bayman["identity_resume_procedure"]
        assert procedure["status"] == "partial"
        assert "record_wake_receipt" in procedure["open_steps"]
        assert "record_sleep_summary" in procedure["open_steps"]
        assert "record_wake_receipt" in bayman["continuity_repair_plan"]["open_checks"]
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_personas_api_includes_post_rebuild_continuity_check(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    operational_dir = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman"
    operational_dir.mkdir(parents=True, exist_ok=True)
    record_post_rebuild_event(
        root=tmp_path,
        binding={"operational_session_target": "automation-newfoundland-bayman", "operational_agent_id": "newfoundland-bayman", "platform": "fourclaw"},
        recorded_by="rev",
        note="docker rebuild",
    )
    save_operational_json_state(
        tmp_path,
        state_key="identity_continuity_state:automation-newfoundland-bayman",
        payload={
            "initialization_memo_present": True,
            "initialization_memo_path": "memory/automation/automation-newfoundland-bayman/initialization_memo.md",
            "wake_receipt_present": True,
            "wake_receipt_recorded_at": "2026-03-14T02:10:00Z",
            "wake_receipt": {"timestamp": "2026-03-14T02:10:00Z"},
            "last_wake_at": "2026-03-14T02:10:00Z",
            "sleep_summary_present": True,
            "sleep_summary_recorded_at": "2026-03-14T01:50:00Z",
            "last_sleep_at": "2026-03-14T01:50:00Z",
            "last_sleep_summary": {"timestamp": "2026-03-14T01:50:00Z"},
        },
    )
    task_namespace = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-auto-post"
    task_namespace.mkdir(parents=True, exist_ok=True)

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/personas/operational")
        assert response.status_code == 200
        items = response.json().get("items") or []
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in items}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        check = bayman["post_rebuild_continuity_check"]
        assert check["status"] == "pending"
        assert check["verification_required"] is True
        assert check["rebuild_recorded_by"] == "rev"
        assert "post_rebuild_continuity_check_pending" in bayman["continuity_recovery_readiness"]["cautions"]
        assert "verify_post_rebuild_continuity" in bayman["continuity_repair_plan"]["open_checks"]
        resume_summary = bayman["operational_resume_governance_summary"]
        assert resume_summary["status"] == "caution"
        assert resume_summary["pending_count"] >= 1
        assert resume_summary["verification_required_count"] >= 1
        assert "verify_post_rebuild_continuity:newfoundland-bayman-fourclaw-auto-post" in resume_summary["required_actions"]
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_personas_api_includes_presence_initiative_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    namespace = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman"
    namespace.mkdir(parents=True, exist_ok=True)
    (namespace / "cadence_request.json").write_text(
        '{"requested_at":"2026-03-13T16:00:00Z","requested_duration_minutes":30,"scheduler_job_id":"social-media-bayman"}',
        encoding="utf-8",
    )
    overseer = tmp_path / "memory" / "overseer"
    overseer.mkdir(parents=True, exist_ok=True)
    (overseer / "autonomy_config.json").write_text(
        '{"entity_dag_change_control":"on","outbound_safety_gate_enabled":true}',
        encoding="utf-8",
    )
    materialized = tmp_path / "memory" / "materialized"
    materialized.mkdir(parents=True, exist_ok=True)
    (materialized / "regulatory_state_snapshots.jsonl").write_text(
        '{"scope_type":"agent","scope_id":"newfoundland-bayman","agent_id":"newfoundland-bayman","ts":"2026-03-13T16:05:00Z","trust_band":3,"agency_budget":11.0,"escrow_locked":0.0,"incident_points":0.0,"evidence_refs":[]}\n',
        encoding="utf-8",
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/personas/operational")
        assert response.status_code == 200
        items = response.json().get("items") or []
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in items}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        summary = bayman["presence_initiative_summary"]
        assert summary["initiative_mode"] == "self_timed_override"
        assert summary["next_earliest_wake_at"] == "2026-03-13T16:30:00Z"
        assert summary["agency_budget"] == 11.0
        assert summary["trust_band"] == 3
        assert bayman["confidence_summary"]["confidence_level"] in {"uncertain", "cautious", "confident", "certain"}
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_personas_api_includes_agency_control_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    operational_dir = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman"
    operational_dir.mkdir(parents=True, exist_ok=True)
    (operational_dir / "agency_control.json").write_text(
        '{"mode":"held","reason":"manual freeze","updated_at":"2026-03-13T16:10:00Z","updated_by":"operator"}',
        encoding="utf-8",
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/personas/operational")
        assert response.status_code == 200
        items = response.json().get("items") or []
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in items}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        summary = bayman["agency_control_summary"]
        assert summary["status"] == "configured"
        assert summary["mode"] == "held"
        assert summary["operator_hold"] is True
        assert summary["review_required"] is True
        assert summary["reason"] == "manual freeze"
        assert summary["updated_by"] == "operator"
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_persona_agency_control_patch_persists(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.patch(
            "/api/v1/personas/operational/fourclaw/newfoundland-bayman/agency-control",
            json={"mode": "review_only", "reason": "supervised rollout", "updated_by": "rev", "outbound_lane_policy": "replies_only"},
        )
        assert response.status_code == 200
        summary = response.json()["agency_control_summary"]
        assert summary["mode"] == "review_only"
        assert summary["review_required"] is True
        assert summary["outbound_lane_policy"] == "replies_only"
        assert summary["allowed_outbound_modes"] == ["engage"]
        assert summary["reason"] == "supervised rollout"
        assert summary["updated_by"] == "rev"
        persisted = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman" / "agency_control.json"
        assert persisted.exists()
        listed = client.get("/api/v1/personas/operational").json()["items"]
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in listed}
        assert by_binding[("fourclaw", "newfoundland-bayman")]["agency_control_summary"]["mode"] == "review_only"
        assert by_binding[("fourclaw", "newfoundland-bayman")]["agency_control_summary"]["outbound_lane_policy"] == "replies_only"
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_persona_agency_control_patch_persists_outbound_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.patch(
            "/api/v1/personas/operational/fourclaw/newfoundland-bayman/agency-control",
            json={
                "mode": "normal",
                "reason": "cap outbound churn",
                "updated_by": "rev",
                "outbound_lane_policy": "unrestricted",
                "daily_outbound_budget": 3,
                "outbound_actions_window_hours": 12,
            },
        )
        assert response.status_code == 200
        summary = response.json()["agency_control_summary"]
        assert summary["daily_outbound_budget"] == 3
        assert summary["outbound_actions_window_hours"] == 12
        assert summary["recent_outbound_action_count"] == 0
        assert summary["outbound_budget_remaining"] == 3
        assert summary["outbound_budget_exhausted"] is False
        persisted = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman" / "agency_control.json"
        payload = json.loads(persisted.read_text(encoding="utf-8"))
        assert payload["daily_outbound_budget"] == 3
        assert payload["outbound_actions_window_hours"] == 12
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_personas_api_includes_self_model_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    store_module._store = None

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
            "proactive_notice": True,
            "position_evolution": False,
            "relationship_type": "respect",
            "created_at": "2026-03-13T17:00:00Z",
        },
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/personas/operational")
        assert response.status_code == 200
        items = response.json().get("items") or []
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in items}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        summary = bayman["self_model_summary"]
        assert summary["status"] == "healthy"
        assert summary["dominant_arc_state"] == "building"
        assert summary["dominant_engagement_mode"] == "direct"
        assert summary["relationship_signal"] == "respect"
        assert bayman["confidence_summary"]["confidence_level"] in {"uncertain", "cautious", "confident", "certain"}
        relationship = bayman["relationship_memory_summary"]
        assert relationship["status"] == "healthy"
        assert relationship["dominant_relationship_type"] == "respect"
        social_posture = bayman["social_posture_summary"]
        assert social_posture["posture"] == "broadcast"
        assert social_posture["relationship_orientation"] == "respect"
    finally:
        store_module._store = None
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_personas_api_includes_affect_action_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    store_module._store = None

    from hg_gateway.store import get_store

    store = get_store()
    store.persona_autonomy_add_turn(
        "default",
        {
            "turn_id": "operational-affect-action-1",
            "chat_id": "chat-operational-affect-action",
            "message_id": "msg-operational-affect-action",
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
            "created_at": "2026-03-13T17:00:00Z",
        },
    )
    materialized = tmp_path / "memory" / "materialized"
    materialized.mkdir(parents=True, exist_ok=True)
    (materialized / "regulatory_state_snapshots.jsonl").write_text(
        '{"scope_type":"agent","scope_id":"newfoundland-bayman","agent_id":"newfoundland-bayman","ts":"2026-03-13T17:01:00Z","trust_band":2,"agency_budget":6.0,"escrow_locked":0.0,"incident_points":0.0,"evidence_refs":[]}\n',
        encoding="utf-8",
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/personas/operational")
        assert response.status_code == 200
        items = response.json().get("items") or []
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in items}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        summary = bayman["affect_action_summary"]
        assert summary["status"] == "healthy"
        assert summary["affective_state"]["trust_band"] == 2
        assert summary["action_state"]["dominant_engagement_mode"] == "reciprocal"
        assert summary["latest_turn"]["relationship_type"] == "respect"
    finally:
        store_module._store = None
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_personas_api_includes_action_rationale_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    save_operational_json_state(
        tmp_path,
        state_key="identity_continuity_state:automation-newfoundland-bayman-fourclaw-auto-post",
        payload={
            "wake_receipt_present": True,
            "wake_receipt_recorded_at": "2026-03-13T19:00:00Z",
            "wake_receipt": {
                "wake_completed_at": "2026-03-13T19:00:00Z",
                "dag_inputs": {"goal": "post if there is a strong thread angle"},
            },
            "last_wake_at": "2026-03-13T19:00:00Z",
        },
    )
    save_operational_json_state(
        tmp_path,
        state_key="operational_cadence_request:automation-newfoundland-bayman",
        payload={
            "requested_at": "2026-03-13T18:55:00Z",
            "reason": "fresh_post_window",
            "scheduler_job_id": "social-media-bayman",
        },
    )
    save_operational_json_state(
        tmp_path,
        state_key="research_deliveries",
        payload={
            "deliveries": [
                {
                    "requested_by": "newfoundland-bayman",
                    "topic": "Bayman posting angle",
                    "file_path": "knowledge/social/bayman-posting-angle.md",
                    "delivered_at": "2026-03-13T18:50:00Z",
                }
            ]
        },
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/personas/operational")
        assert response.status_code == 200
        items = response.json().get("items") or []
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in items}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        summary = bayman["action_rationale_summary"]
        assert summary["current_trigger"] == "cadence_override"
        assert summary["current_goal"] == "post if there is a strong thread angle"
        assert "cadence:fresh_post_window" in summary["reason_chain"]
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_personas_api_action_rationale_prefers_agency_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    save_operational_json_state(
        tmp_path,
        state_key="identity_continuity_state:automation-newfoundland-bayman-fourclaw-auto-post",
        payload={
            "wake_receipt_present": True,
            "wake_receipt_recorded_at": "2026-03-13T19:00:00Z",
            "wake_receipt": {
                "wake_completed_at": "2026-03-13T19:00:00Z",
                "dag_inputs": {"goal": "post if there is a strong thread angle"},
            },
            "last_wake_at": "2026-03-13T19:00:00Z",
        },
    )
    operational_dir = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman"
    operational_dir.mkdir(parents=True, exist_ok=True)
    (operational_dir / "agency_control.json").write_text(
        '{"mode":"review_only","reason":"supervised rollout","updated_at":"2026-03-13T19:01:00Z","updated_by":"rev"}',
        encoding="utf-8",
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/personas/operational")
        assert response.status_code == 200
        items = response.json().get("items") or []
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in items}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        summary = bayman["action_rationale_summary"]
        assert summary["current_trigger"] == "review_gate"
        assert summary["agency_mode"] == "review_only"
        assert "review_gate:supervised rollout" in summary["reason_chain"]
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_personas_api_action_rationale_prefers_outbound_budget(tmp_path, monkeypatch):
    db_path = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    save_operational_json_state(
        tmp_path,
        state_key="identity_continuity_state:automation-newfoundland-bayman-fourclaw-auto-post",
        payload={
            "wake_receipt_present": True,
            "wake_receipt_recorded_at": "2026-03-13T19:00:00Z",
            "wake_receipt": {
                "wake_completed_at": "2026-03-13T19:00:00Z",
                "dag_inputs": {"goal": "post if there is a strong thread angle"},
            },
            "last_wake_at": "2026-03-13T19:00:00Z",
        },
    )
    operational_dir = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman"
    operational_dir.mkdir(parents=True, exist_ok=True)
    (operational_dir / "agency_control.json").write_text(
        '{"mode":"normal","reason":"daily cap reached","updated_at":"2026-03-13T19:01:00Z","updated_by":"rev","daily_outbound_budget":1,"outbound_actions_window_hours":24}',
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
        db_path=str(db_path),
    )
    with get_connection(str(db_path)) as conn:
        conn.execute(
            """INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at)
               VALUES (?, 'social_account', ?, 'post_proof', ?, ?, datetime('now'))""",
            ("proof-budget-persona-1", "acct-bayman-fourclaw", "memory/artifacts/social_accounts/post1.json", '{"status":"ok"}'),
        )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/personas/operational")
        assert response.status_code == 200
        items = response.json().get("items") or []
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in items}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        summary = bayman["action_rationale_summary"]
        assert summary["current_trigger"] == "outbound_budget"
        assert "outbound_budget:1/1" in summary["reason_chain"]
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_personas_api_includes_review_handoff_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    record_human_notification(
        tmp_path,
        task_name="newfoundland-bayman-fourclaw-auto-post",
        kind="agency_gate",
        message="review handoff created",
        summary={
            "execution": {"status": "pending_approval", "platform": "fourclaw", "blocked_reason": "agency_control_review_only"},
            "agency_control": {"effective_mode": "review_only", "reason": "supervised rollout"},
            "review_handoff": {"approval_id": "approval-persona-1", "title": "Review required: bayman fourclaw"},
        },
        operational_agent_id="newfoundland-bayman",
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/personas/operational")
        assert response.status_code == 200
        items = response.json().get("items") or []
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in items}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        summary = bayman["review_handoff_summary"]
        assert summary["count"] == 1
        assert summary["pending_count"] == 1
        assert summary["latest"]["approval_id"] == "approval-persona-1"
        assert summary["latest"]["task_name"] == "newfoundland-bayman-fourclaw-auto-post"
        assert summary["latest"]["approval_href"] == "#/approvals?workflow_id=newfoundland-bayman-fourclaw-auto-post&approval_id=approval-persona-1"
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_personas_api_review_handoff_summary_includes_release_blockers(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    operational_dir = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman"
    operational_dir.mkdir(parents=True, exist_ok=True)
    (operational_dir / "agency_control.json").write_text(
        '{"mode":"held","reason":"manual freeze","updated_at":"2026-03-13T19:01:00Z","updated_by":"rev"}',
        encoding="utf-8",
    )
    record_human_notification(
        tmp_path,
        task_name="newfoundland-bayman-fourclaw-auto-post",
        kind="agency_gate",
        message="review handoff created",
        summary={
            "execution": {"status": "pending_approval", "platform": "fourclaw", "blocked_reason": "agency_control_review_only"},
            "agency_control": {"effective_mode": "review_only", "reason": "supervised rollout"},
            "review_handoff": {"approval_id": "approval-persona-2", "title": "Review required: bayman fourclaw"},
        },
        operational_agent_id="newfoundland-bayman",
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/personas/operational")
        assert response.status_code == 200
        items = response.json().get("items") or []
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in items}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        summary = bayman["review_handoff_summary"]
        assert summary["release_ready"] is False
        assert "agency_hold" in summary["release_blockers"]
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_personas_api_review_handoff_summary_includes_continuity_release_blocker(tmp_path, monkeypatch):
    db_path = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    for session_target in (
        "automation-newfoundland-bayman",
        "automation-newfoundland-bayman-fourclaw-auto-post",
        "automation-newfoundland-bayman-fourclaw-engage",
    ):
        namespace = tmp_path / "memory" / "automation" / session_target
        namespace.mkdir(parents=True, exist_ok=True)
        (namespace / "initialization_memo.md").write_text("cold-start memo", encoding="utf-8")
        (namespace / "wake_receipt.json").write_text('{"timestamp":"2026-03-14T01:00:00Z"}', encoding="utf-8")
        (namespace / "last_sleep_summary.json").write_text('{"timestamp":"2026-03-14T00:30:00Z"}', encoding="utf-8")
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
        tmp_path,
        task_name="newfoundland-bayman-fourclaw-auto-post",
        kind="agency_gate",
        message="review handoff created",
        summary={
            "execution": {"status": "pending_approval", "platform": "fourclaw", "blocked_reason": "agency_control_review_only"},
            "agency_control": {"effective_mode": "review_only", "reason": "supervised rollout"},
            "review_handoff": {"approval_id": "approval-persona-continuity", "title": "Review required: bayman fourclaw"},
        },
        operational_agent_id="newfoundland-bayman",
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/personas/operational")
        assert response.status_code == 200
        items = response.json().get("items") or []
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in items}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        summary = bayman["review_handoff_summary"]
        assert summary["release_ready"] is False
        assert "continuity_recovery" in summary["release_blockers"]
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_personas_api_includes_assigned_account_proof_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    app.dependency_overrides[require_api_key] = lambda: True
    try:
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
        client = TestClient(app)
        client.post(
            "/api/v1/keystore/accounts/acct-bayman-fourclaw/proof-artifacts",
            headers={"Authorization": "Bearer test-api-key", "X-Tenant-ID": "default"},
            json={
                "artifact_type": "registration_proof",
                "label": "bayman-fourclaw-registration",
                "handle": "@bayman",
                "url": "https://example.invalid/bayman",
                "payload": {"state": "verified"},
            },
        )
        response = client.get("/api/v1/personas/operational")
        assert response.status_code == 200
        items = response.json().get("items") or []
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in items}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        assigned = bayman["assigned_social_accounts"]
        target = next(account for account in assigned if account["social_account_id"] == "acct-bayman-fourclaw")
        assert target["proof_summary"]["artifact_count"] >= 1
        assert target["proof_summary"]["latest_artifact_type"] == "registration_proof"
        assert target["proof_summary"]["latest_handle"] == "@bayman"
        assert target["readiness_summary"]["ready"] is False
        assert "login_binding_present" in target["readiness_summary"]["blocking"]
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_personas_api_includes_assigned_account_continuity_summary(tmp_path, monkeypatch):
    db_path = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    app.dependency_overrides[require_api_key] = lambda: True
    try:
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
        with get_connection(str(db_path)) as conn:
            conn.execute(
                """INSERT INTO browser_sessions (browser_session_id, tenant_id, entity_id, platform, state, started_at)
                   VALUES (?, ?, ?, ?, ?, datetime('now'))""",
                ("session-bad", "default", "newfoundland-bayman", "fourclaw", "degraded"),
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
                """INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at)
                   VALUES (?, 'browser_session', ?, 'session_degraded', ?, ?, datetime('now'))""",
                ("proof-bad", "session-bad", "missing_restart_critical_browser_artifacts", '{"reason":"missing_restart_critical_browser_artifacts"}'),
            )
        client = TestClient(app)
        response = client.get("/api/v1/personas/operational")
        assert response.status_code == 200
        items = response.json().get("items") or []
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in items}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        target = next(account for account in bayman["assigned_social_accounts"] if account["social_account_id"] == "acct-bayman-fourclaw")
        assert target["continuity_summary"]["status"] == "degraded"
        assert target["continuity_summary"]["browser_session_id"] == "session-bad"
        assert target["continuity_summary"]["browser_session_started_at"] is not None
        assert target["continuity_summary"]["degraded_reason"] == "missing_restart_critical_browser_artifacts"
        assert target["readiness_summary"]["ready"] is False
        assert "continuity_healthy" in target["readiness_summary"]["blocking"]
        assert target["continuity_injury_summary"]["status"] == "active"
        assert target["continuity_injury_summary"]["last_injury_reason"] == "missing_restart_critical_browser_artifacts"
        assert bayman["continuity_incident_summary"]["status"] == "active"
        assert "bayman-fourclaw" in bayman["continuity_incident_summary"]["active_accounts"]
        assert bayman["continuity_recovery_readiness"]["status"] == "blocked"
        assert "active_continuity_incident" in bayman["continuity_recovery_readiness"]["blocking"]
        assert "replace_or_rebind_damaged_session" in bayman["continuity_repair_plan"]["open_checks"]
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_personas_api_includes_assigned_account_continuity_repair_summary(tmp_path, monkeypatch):
    db_path = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    app.dependency_overrides[require_api_key] = lambda: True
    try:
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
        client = TestClient(app)
        response = client.get("/api/v1/personas/operational")
        assert response.status_code == 200
        items = response.json().get("items") or []
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in items}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        target = next(account for account in bayman["assigned_social_accounts"] if account["social_account_id"] == "acct-bayman-fourclaw")
        assert target["continuity_summary"]["status"] == "healthy"
        assert target["continuity_injury_summary"]["status"] == "recovered"
        assert target["continuity_injury_summary"]["repaired"] is True
        assert target["continuity_injury_summary"]["last_repair_kind"] == "session_restart"
        assert target["continuity_injury_summary"]["last_repair_at"] == "2026-03-14T01:30:00Z"
        assert bayman["continuity_incident_summary"]["status"] == "recovered"
        assert "bayman-fourclaw" in bayman["continuity_incident_summary"]["recovered_accounts"]
        assert bayman["continuity_recovery_readiness"]["status"] == "caution"
        assert "recent_continuity_recovery" in bayman["continuity_recovery_readiness"]["cautions"]
        assert bayman["continuity_repair_observation"]["status"] == "observed"
        assert bayman["continuity_repair_observation"]["summary"] == "post_repair_observation_complete"
        assert "acknowledge_bounded_resume" in bayman["continuity_repair_plan"]["open_checks"]
        assert "observe_first_post_repair_cycle" not in bayman["continuity_repair_plan"]["open_checks"]
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_persona_continuity_recovery_acknowledge_persists(tmp_path, monkeypatch):
    db_path = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
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
               VALUES (?, 'browser_session', ?, 'session_degraded', ?, ?, '2026-03-14T01:20:00Z')""",
            ("proof-repaired", "session-good", "missing_restart_critical_browser_artifacts", '{"reason":"missing_restart_critical_browser_artifacts"}'),
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

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/personas/operational/fourclaw/newfoundland-bayman/continuity-recovery/ack",
            json={"acknowledged_by": "rev", "note": "repair reviewed"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["continuity_recovery_ack"]["acknowledged"] is True
        assert payload["continuity_recovery_ack"]["acknowledged_by"] == "rev"
        assert payload["identity_resume_observation"]["status"] == "pending"
        assert payload["continuity_recovery_readiness"]["acknowledged"] is True
        assert payload["continuity_recovery_readiness"]["resume_permitted"] is True
        assert "identity_resume_observation_pending" in payload["continuity_recovery_readiness"]["cautions"]
        assert "acknowledge_bounded_resume" not in payload["continuity_repair_plan"]["open_checks"]
        assert "observe_first_identity_resume_cycle" in payload["continuity_repair_plan"]["open_checks"]
        assert payload["notification_payload"]["kind"] == "continuity_recovery_ack"
        assert payload["closeout_notification_payload"] is None
        assert payload["identity_closeout_notification_payload"] is None
        listed = client.get("/api/v1/personas/operational").json()["items"]
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in listed}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        assert bayman["continuity_recovery_readiness"]["acknowledged"] is True
        assert bayman["continuity_recovery_readiness"]["resume_permitted"] is True
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_persona_identity_resume_observation_closes_after_post_ack_wake(tmp_path, monkeypatch):
    db_path = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    save_operational_json_state(
        tmp_path,
        state_key="identity_continuity_state:automation-newfoundland-bayman",
        payload={
            "status": "partial",
            "initialization_memo_present": True,
            "initialization_memo_path": "memory/automation/automation-newfoundland-bayman/initialization_memo.md",
        },
    )
    save_operational_json_state(
        tmp_path,
        state_key="identity_continuity_state:automation-newfoundland-bayman-fourclaw-auto-post",
        payload={
            "status": "partial",
            "initialization_memo_present": True,
            "initialization_memo_path": "memory/automation/automation-newfoundland-bayman-fourclaw-auto-post/initialization_memo.md",
        },
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/personas/operational/fourclaw/newfoundland-bayman/continuity-recovery/ack",
            json={"acknowledged_by": "rev", "note": "identity recovery reviewed"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["identity_resume_observation"]["status"] == "pending"
        save_operational_json_state(
            tmp_path,
            state_key="identity_continuity_state:automation-newfoundland-bayman",
            payload={
                "status": "healthy",
                "initialization_memo_present": True,
                "initialization_memo_path": "memory/automation/automation-newfoundland-bayman/initialization_memo.md",
                "wake_receipt_present": True,
                "wake_receipt_recorded_at": "9999-03-14T02:00:01Z",
                "last_wake_at": "9999-03-14T02:00:01Z",
                "sleep_summary_present": True,
                "sleep_summary_recorded_at": "9999-03-14T01:30:00Z",
                "last_sleep_at": "9999-03-14T01:30:00Z",
            },
        )
        save_operational_json_state(
            tmp_path,
            state_key="identity_continuity_state:automation-newfoundland-bayman-fourclaw-auto-post",
            payload={
                "status": "healthy",
                "initialization_memo_present": True,
                "initialization_memo_path": "memory/automation/automation-newfoundland-bayman-fourclaw-auto-post/initialization_memo.md",
                "wake_receipt_present": True,
                "wake_receipt_recorded_at": "9999-03-14T02:00:01Z",
                "last_wake_at": "9999-03-14T02:00:01Z",
                "sleep_summary_present": True,
                "sleep_summary_recorded_at": "9999-03-14T01:30:00Z",
                "last_sleep_at": "9999-03-14T01:30:00Z",
            },
        )

        listed = client.get("/api/v1/personas/operational").json()["items"]
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in listed}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        assert bayman["identity_resume_observation"]["status"] == "observed"
        assert bayman["identity_resume_observation"]["observation_complete"] is True
        assert bayman["identity_resume_closeout"]["closed_out"] is True
        assert "identity_resume_observation_pending" not in bayman["continuity_recovery_readiness"]["cautions"]
        assert "observe_first_identity_resume_cycle" in bayman["continuity_repair_plan"]["completed_checks"]
        assert "observe_first_identity_resume_cycle" not in bayman["continuity_repair_plan"]["open_checks"]
        notification_log = tmp_path / "memory" / "automation" / "notifications" / "human_notifications.jsonl"
        log_text = notification_log.read_text(encoding="utf-8")
        assert '"kind": "identity_resume_closeout"' in log_text
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_persona_post_rebuild_record_and_verify(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    operational_dir = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman"
    operational_dir.mkdir(parents=True, exist_ok=True)
    (operational_dir / "initialization_memo.md").write_text("cold-start memo", encoding="utf-8")
    task_namespace = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-auto-post"
    task_namespace.mkdir(parents=True, exist_ok=True)
    save_operational_json_state(
        tmp_path,
        state_key="identity_continuity_state:automation-newfoundland-bayman",
        payload={
            "status": "healthy",
            "initialization_memo_present": True,
            "initialization_memo_path": "memory/automation/automation-newfoundland-bayman/initialization_memo.md",
            "wake_receipt_present": True,
            "wake_receipt_recorded_at": "2099-03-14T02:10:00Z",
            "wake_receipt": {"timestamp": "2099-03-14T02:10:00Z"},
            "sleep_summary_present": True,
            "sleep_summary_recorded_at": "2099-03-14T01:50:00Z",
            "last_wake_at": "2099-03-14T02:10:00Z",
            "last_sleep_at": "2099-03-14T01:50:00Z",
        },
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        record_response = client.post(
            "/api/v1/personas/operational/fourclaw/newfoundland-bayman/post-rebuild/record",
            json={"recorded_by": "rev", "note": "demo stack rebuilt", "rebuilt_at": "2026-03-13T18:00:00Z"},
        )
        assert record_response.status_code == 200
        record_payload = record_response.json()
        assert record_payload["post_rebuild_continuity_check"]["status"] == "pending"
        assert record_payload["notification_payload"]["kind"] == "post_rebuild_continuity_required"

        verify_response = client.post(
            "/api/v1/personas/operational/fourclaw/newfoundland-bayman/post-rebuild/verify",
            json={"verified_by": "rev", "note": "wake and continuity look clean"},
        )
        assert verify_response.status_code == 200
        verify_payload = verify_response.json()
        assert verify_payload["post_rebuild_continuity_check"]["status"] == "verified"
        assert verify_payload["post_rebuild_continuity_check"]["verified"] is True
        assert verify_payload["notification_payload"]["kind"] == "post_rebuild_continuity_verified"
        listed = client.get("/api/v1/personas/operational").json()["items"]
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in listed}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        assert bayman["post_rebuild_continuity_check"]["status"] == "verified"
        assert "verify_post_rebuild_continuity" in bayman["continuity_repair_plan"]["completed_checks"]
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_persona_identity_restore_record_verify_and_supervised_validation(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    operational_dir = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman"
    operational_dir.mkdir(parents=True, exist_ok=True)
    (operational_dir / "initialization_memo.md").write_text("cold-start memo", encoding="utf-8")
    (operational_dir / "post_rebuild_continuity_check.json").write_text(
        '{"rebuild_recorded_at":"2026-03-13T18:00:00Z","rebuild_recorded_by":"rev","verified_at":"2026-03-13T18:10:00Z","verified_by":"rev"}',
        encoding="utf-8",
    )
    task_namespace = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman-fourclaw-auto-post"
    task_namespace.mkdir(parents=True, exist_ok=True)
    save_operational_json_state(
        tmp_path,
        state_key="identity_continuity_state:automation-newfoundland-bayman",
        payload={
            "status": "healthy",
            "initialization_memo_present": True,
            "initialization_memo_path": "memory/automation/automation-newfoundland-bayman/initialization_memo.md",
            "wake_receipt_present": True,
            "wake_receipt_recorded_at": "2099-03-14T02:10:00Z",
            "wake_receipt": {"timestamp": "2099-03-14T02:10:00Z"},
            "sleep_summary_present": True,
            "sleep_summary_recorded_at": "2099-03-14T01:50:00Z",
            "last_wake_at": "2099-03-14T02:10:00Z",
            "last_sleep_at": "2099-03-14T01:50:00Z",
        },
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        record_response = client.post(
            "/api/v1/personas/operational/fourclaw/newfoundland-bayman/identity-restore/record",
            json={"recorded_by": "rev", "note": "identity restored", "restored_at": "2026-03-13T19:00:00Z"},
        )
        assert record_response.status_code == 200
        assert record_response.json()["identity_restore_validation"]["status"] == "pending"

        verify_response = client.post(
            "/api/v1/personas/operational/fourclaw/newfoundland-bayman/identity-restore/verify",
            json={"verified_by": "rev", "note": "wake and sleep continuity verified"},
        )
        assert verify_response.status_code == 200
        verify_payload = verify_response.json()
        assert verify_payload["identity_restore_validation"]["status"] == "validated"
        assert verify_payload["supervised_resume_validation"]["status"] == "pending"
        assert "run_supervised_resume_validation" in verify_payload["continuity_repair_plan"]["open_checks"]

        supervised_response = client.post(
            "/api/v1/personas/operational/fourclaw/newfoundland-bayman/supervised-resume-validation",
            json={"validated_by": "rev", "note": "supervised resume looked clean"},
        )
        assert supervised_response.status_code == 200
        payload = supervised_response.json()
        assert payload["supervised_resume_validation"]["status"] == "validated"
        assert "supervised_resume_validation_required" not in (payload["bounded_autonomy_policy_summary"]["blockers"] or [])

        listed = client.get("/api/v1/personas/operational").json()["items"]
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in listed}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        assert bayman["identity_restore_validation"]["status"] == "validated"
        assert bayman["supervised_resume_validation"]["status"] == "validated"
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_persona_resume_checkpoint_requires_ready_status(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    operational_dir = tmp_path / "memory" / "automation" / "automation-newfoundland-bayman"
    operational_dir.mkdir(parents=True, exist_ok=True)

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/personas/operational/fourclaw/newfoundland-bayman/resume-checkpoint",
            json={"approved_by": "rev", "note": "not actually ready"},
        )
        assert response.status_code == 409
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_persona_resume_checkpoint_persists_when_ready(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    save_operational_json_state(
        tmp_path,
        state_key="identity_continuity_state:automation-newfoundland-bayman",
        payload={
            "initialization_memo_present": True,
            "initialization_memo_path": "memory/automation/automation-newfoundland-bayman/initialization_memo.md",
            "wake_receipt_present": True,
            "wake_receipt_recorded_at": "2026-03-14T02:10:00Z",
            "wake_receipt": {"timestamp": "2026-03-14T02:10:00Z"},
            "last_wake_at": "2026-03-14T02:10:00Z",
            "sleep_summary_present": True,
            "sleep_summary_recorded_at": "2026-03-14T01:50:00Z",
            "last_sleep_at": "2026-03-14T01:50:00Z",
            "last_sleep_summary": {"timestamp": "2026-03-14T01:50:00Z"},
        },
    )
    save_operational_json_state(
        tmp_path,
        state_key="identity_continuity_state:automation-newfoundland-bayman-fourclaw-auto-post",
        payload={
            "initialization_memo_present": True,
            "initialization_memo_path": "memory/automation/automation-newfoundland-bayman-fourclaw-auto-post/initialization_memo.md",
            "wake_receipt_present": True,
            "wake_receipt_recorded_at": "2026-03-14T02:10:00Z",
            "wake_receipt": {"timestamp": "2026-03-14T02:10:00Z"},
            "last_wake_at": "2026-03-14T02:10:00Z",
            "sleep_summary_present": True,
            "sleep_summary_recorded_at": "2026-03-14T01:50:00Z",
            "last_sleep_at": "2026-03-14T01:50:00Z",
            "last_sleep_summary": {"timestamp": "2026-03-14T01:50:00Z"},
        },
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        record_response = client.post(
            "/api/v1/personas/operational/fourclaw/newfoundland-bayman/post-rebuild/record",
            json={"recorded_by": "rev", "note": "demo stack rebuilt", "rebuilt_at": "2026-03-13T18:00:00Z"},
        )
        assert record_response.status_code == 200
        verify_response = client.post(
            "/api/v1/personas/operational/fourclaw/newfoundland-bayman/post-rebuild/verify",
            json={"verified_by": "rev", "note": "continuity verified"},
        )
        assert verify_response.status_code == 200
        supervised_response = client.post(
            "/api/v1/personas/operational/fourclaw/newfoundland-bayman/supervised-resume-validation",
            json={"validated_by": "rev", "note": "supervised resume looked clean"},
        )
        assert supervised_response.status_code == 200
        checkpoint_response = client.post(
            "/api/v1/personas/operational/fourclaw/newfoundland-bayman/resume-checkpoint",
            json={"approved_by": "rev", "note": "safe to resume"},
        )
        assert checkpoint_response.status_code == 200
        payload = checkpoint_response.json()
        assert payload["operational_resume_governance_summary"]["status"] == "ready"
        assert payload["operational_resume_checkpoint"]["approved"] is True
        assert payload["operational_resume_checkpoint"]["approved_by"] == "rev"
        assert payload["notification_payload"]["kind"] == "operational_resume_checkpoint"
        listed = client.get("/api/v1/personas/operational").json()["items"]
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in listed}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        assert bayman["operational_resume_checkpoint"]["approved"] is True
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_persona_resume_checkpoint_invalidates_after_new_rebuild(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    save_operational_json_state(
        tmp_path,
        state_key="identity_continuity_state:automation-newfoundland-bayman",
        payload={
            "initialization_memo_present": True,
            "initialization_memo_path": "memory/automation/automation-newfoundland-bayman/initialization_memo.md",
            "wake_receipt_present": True,
            "wake_receipt_recorded_at": "2026-03-14T02:10:00Z",
            "wake_receipt": {"timestamp": "2026-03-14T02:10:00Z"},
            "last_wake_at": "2026-03-14T02:10:00Z",
            "sleep_summary_present": True,
            "sleep_summary_recorded_at": "2026-03-14T01:50:00Z",
            "last_sleep_at": "2026-03-14T01:50:00Z",
            "last_sleep_summary": {"timestamp": "2026-03-14T01:50:00Z"},
        },
    )
    save_operational_json_state(
        tmp_path,
        state_key="identity_continuity_state:automation-newfoundland-bayman-fourclaw-auto-post",
        payload={
            "initialization_memo_present": True,
            "initialization_memo_path": "memory/automation/automation-newfoundland-bayman-fourclaw-auto-post/initialization_memo.md",
            "wake_receipt_present": True,
            "wake_receipt_recorded_at": "2026-03-14T02:10:00Z",
            "wake_receipt": {"timestamp": "2026-03-14T02:10:00Z"},
            "last_wake_at": "2026-03-14T02:10:00Z",
            "sleep_summary_present": True,
            "sleep_summary_recorded_at": "2026-03-14T01:50:00Z",
            "last_sleep_at": "2026-03-14T01:50:00Z",
            "last_sleep_summary": {"timestamp": "2026-03-14T01:50:00Z"},
        },
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        assert client.post(
            "/api/v1/personas/operational/fourclaw/newfoundland-bayman/post-rebuild/record",
            json={"recorded_by": "rev", "note": "demo stack rebuilt", "rebuilt_at": "2026-03-13T18:00:00Z"},
        ).status_code == 200
        assert client.post(
            "/api/v1/personas/operational/fourclaw/newfoundland-bayman/post-rebuild/verify",
            json={"verified_by": "rev", "note": "continuity verified"},
        ).status_code == 200
        checkpoint_response = client.post(
            "/api/v1/personas/operational/fourclaw/newfoundland-bayman/resume-checkpoint",
            json={"approved_by": "rev", "note": "safe to resume"},
        )
        assert checkpoint_response.status_code == 200
        assert checkpoint_response.json()["operational_resume_checkpoint"]["approved"] is True

        later_rebuild = client.post(
            "/api/v1/personas/operational/fourclaw/newfoundland-bayman/post-rebuild/record",
            json={"recorded_by": "rev", "note": "second rebuild", "rebuilt_at": "2099-03-14T03:00:00Z"},
        )
        assert later_rebuild.status_code == 200

        listed = client.get("/api/v1/personas/operational").json()["items"]
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in listed}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        checkpoint = bayman["operational_resume_checkpoint"]
        assert checkpoint["approved"] is False
        assert checkpoint["invalidated"] is True
        assert checkpoint["invalidated_reason"] == "operational_resume_no_longer_ready"
        notification_log = tmp_path / "memory" / "automation" / "notifications" / "human_notifications.jsonl"
        log_text = notification_log.read_text(encoding="utf-8")
        assert '"kind": "operational_resume_checkpoint_invalidated"' in log_text
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_persona_continuity_recovery_acknowledge_closes_out_observed_lane(tmp_path, monkeypatch):
    db_path = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    for session_target in (
        "automation-newfoundland-bayman",
        "automation-newfoundland-bayman-fourclaw-auto-post",
        "automation-newfoundland-bayman-fourclaw-engage",
    ):
        namespace = tmp_path / "memory" / "automation" / session_target
        namespace.mkdir(parents=True, exist_ok=True)
        (namespace / "initialization_memo.md").write_text("cold-start memo", encoding="utf-8")
        save_operational_json_state(
            tmp_path,
            state_key=f"identity_continuity_state:{session_target}",
            payload={
                "status": "healthy",
                "initialization_memo_present": True,
                "initialization_memo_path": f"memory/automation/{session_target}/initialization_memo.md",
                "wake_receipt_present": True,
                "wake_receipt_recorded_at": "2099-03-14T01:00:00Z",
                "wake_receipt": {"timestamp": "2099-03-14T01:00:00Z"},
                "sleep_summary_present": True,
                "sleep_summary_recorded_at": "2099-03-14T00:30:00Z",
                "last_wake_at": "2099-03-14T01:00:00Z",
                "last_sleep_at": "2099-03-14T00:30:00Z",
            },
        )
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
    record_human_notification(
        tmp_path,
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

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/personas/operational/fourclaw/newfoundland-bayman/continuity-recovery/ack",
            json={"acknowledged_by": "rev", "note": "repair reviewed after clean cycle"},
        )
        assert response.status_code == 200
        ack_payload = response.json()
        save_operational_json_state(
            tmp_path,
            state_key="identity_continuity_state:automation-newfoundland-bayman",
            payload={
                "status": "healthy",
                "initialization_memo_present": True,
                "initialization_memo_path": str(tmp_path / "memory" / "automation" / "automation-newfoundland-bayman" / "initialization_memo.md"),
                "wake_receipt_present": True,
                "wake_receipt_recorded_at": "2099-03-22T02:10:00Z",
                "wake_receipt": {"timestamp": "2099-03-22T02:10:00Z"},
                "sleep_summary_present": True,
                "sleep_summary_recorded_at": "2099-03-22T01:50:00Z",
                "last_wake_at": "2099-03-22T02:10:00Z",
                "last_sleep_at": "2099-03-22T01:50:00Z",
            },
        )
        response = client.get("/api/v1/personas/operational")
        assert response.status_code == 200
        items = response.json().get("items") or []
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in items}
        listed_payload = by_binding[("fourclaw", "newfoundland-bayman")]
        assert listed_payload["continuity_repair_observation"]["status"] == "observed"
        assert listed_payload["continuity_recovery_readiness"]["status"] == "ready"
        assert listed_payload["continuity_recovery_readiness"]["recovery_closeout_complete"] is True
        assert listed_payload["continuity_repair_plan"]["status"] == "clean"
        assert "observe_first_post_repair_cycle" not in listed_payload["continuity_repair_plan"]["open_checks"]
        assert "post_repair_resume_ready" in listed_payload["continuity_repair_plan"]["completed_checks"]
        assert ack_payload["notification_payload"]["kind"] == "continuity_recovery_ack"
        assert ack_payload["closeout_notification_payload"]["kind"] == "continuity_recovery_closeout"
        assert ack_payload["identity_closeout_notification_payload"]["kind"] == "identity_resume_closeout"
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_personas_api_includes_assigned_account_notification_summary(tmp_path, monkeypatch):
    db_path = tmp_path / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    app.dependency_overrides[require_api_key] = lambda: True
    try:
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
            tmp_path,
            task_name="newfoundland-bayman-fourclaw-engage",
            kind="run_update",
            message="bayman replied on fourclaw",
            summary={"execution": {"status": "completed", "platform": "fourclaw"}},
            transport="configured_channel",
            social_account_id="acct-bayman-fourclaw",
            tenant_id="default",
            operational_agent_id="newfoundland-bayman",
        )
        client = TestClient(app)
        response = client.get("/api/v1/personas/operational")
        assert response.status_code == 200
        items = response.json().get("items") or []
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in items}
        bayman = by_binding[("fourclaw", "newfoundland-bayman")]
        target = next(account for account in bayman["assigned_social_accounts"] if account["social_account_id"] == "acct-bayman-fourclaw")
        assert target["notification_summary"]["count"] == 1
        assert target["notification_summary"]["latest"]["message"] == "bayman replied on fourclaw"
        assert target["last_activity_summary"]["last_seen_kind"] == "notification"
        assert target["last_activity_summary"]["last_seen_detail"] == "run_update"
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_operational_personas_api_includes_research_delivery_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    save_operational_json_state(
        tmp_path,
        state_key="research_deliveries",
        payload={
            "deliveries": [
                {
                    "requested_by": "underling-chan",
                    "topic": "Agent orchestration",
                    "file_path": "knowledge/technology/agent-orchestration.md",
                    "delivered_at": "2026-03-13T10:00:00Z",
                }
            ]
        },
    )
    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/personas/operational")
        assert response.status_code == 200
        items = response.json().get("items") or []
        by_binding = {(item["platform"], item.get("operational_agent_id")): item for item in items}
        underling = by_binding[("fourclaw", "underling-chan")]
        summary = underling["research_delivery_summary"]
        assert summary["delivery_count"] == 1
        assert summary["recent_deliveries"][0]["topic"] == "Agent orchestration"
    finally:
        app.dependency_overrides.pop(require_api_key, None)
