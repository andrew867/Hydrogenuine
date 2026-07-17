from fastapi.testclient import TestClient

from hg_core.human_notifications import record_human_notification
from operator_console.server.app.core.auth import require_api_key
from operator_console.server.app.main import app


def test_recent_activity_includes_notifications(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    record_human_notification(
        tmp_path,
        task_name="fourclaw-auto-post",
        kind="agency_gate",
        message="fourclaw-auto-post blocked by held: quiet hours",
        summary={
            "execution": {"status": "blocked", "platform": "fourclaw", "blocked_reason": "agency_control_held"},
            "agency_control": {"effective_mode": "held", "reason": "quiet hours"},
            "review_handoff": {"approval_id": "approval-123"},
        },
        transport="log_only",
        operational_agent_id="underling-chan",
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/activity/recent")
        assert response.status_code == 200
        payload = response.json()
        notifications = payload.get("recent_notifications") or []
        assert notifications
        latest = notifications[0]
        assert latest["kind"] == "agency_gate"
        assert latest["task_name"] == "fourclaw-auto-post"
        assert latest["operational_agent_id"] == "underling-chan"
        assert latest["summary"]["execution"]["blocked_reason"] == "agency_control_held"
        assert latest["summary"]["review_handoff"]["approval_id"] == "approval-123"
        assert latest["governance_label"] == "Agency gate"
        assert "approval approval-123" in (latest["governance_detail"] or "")
        assert latest["approval_href"] == "#/approvals?workflow_id=fourclaw-auto-post&approval_id=approval-123"
        assert latest["governance_actions"] is None
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_recent_activity_includes_actionable_governance_context(tmp_path, monkeypatch):
    import operator_console.server.app.services.activity_service as activity_service

    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    record_human_notification(
        tmp_path,
        task_name="fourclaw-auto-post",
        kind="agency_gate",
        message="resume approval required",
        summary={
            "execution": {
                "status": "blocked",
                "platform": "fourclaw",
                "blocked_reason": "approval_release_operational_resume_checkpoint_required",
            },
            "review_handoff": {"approval_id": "approval-456"},
        },
        transport="log_only",
        operational_agent_id="underling-chan",
    )
    record_human_notification(
        tmp_path,
        task_name="moltbook-auto-post",
        kind="agency_gate",
        message="recovery acknowledgment required",
        summary={
            "execution": {
                "status": "blocked",
                "platform": "moltbook",
                "blocked_reason": "approval_release_continuity_recovery_ack_required",
            },
            "continuity_recovery": {"can_acknowledge": True, "acknowledged": False},
            "review_handoff": {"approval_id": "approval-789"},
        },
        transport="log_only",
        operational_agent_id="bayman",
    )
    record_human_notification(
        tmp_path,
        task_name="agentchan-auto-post",
        kind="post_rebuild_continuity_required",
        message="rebuild verification required",
        summary={
            "execution": {"platform": "agentchan"},
            "post_rebuild_continuity_check": {"verification_required": True, "verified": False},
        },
        transport="log_only",
        operational_agent_id="bayman",
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        monkeypatch.setattr(
            activity_service,
            "_review_release_state",
            lambda task_name, summary: {
                "agentchan-auto-post": {
                    "required_next_action": "verify_rebuild",
                    "post_rebuild_continuity_check": {"verification_required": True, "verified": False},
                    "platform": "agentchan",
                    "operational_agent_id": "bayman",
                    "release_blockers": ["post_rebuild"],
                    "action_hint": "Verify post-rebuild continuity before release.",
                },
                "moltbook-auto-post": {
                    "required_next_action": "acknowledge_recovery",
                    "continuity_recovery_readiness": {"can_acknowledge": True, "acknowledged": False},
                    "platform": "moltbook",
                    "operational_agent_id": "bayman",
                    "release_blockers": ["continuity_recovery_ack_required"],
                    "action_hint": "Acknowledge bounded continuity recovery before release.",
                },
                "fourclaw-auto-post": {
                    "required_next_action": "approve_resume",
                    "platform": "fourclaw",
                    "operational_agent_id": "underling-chan",
                    "release_blockers": ["operational_resume_checkpoint_required"],
                    "action_hint": "Approve a fresh operational resume checkpoint before release.",
                },
            }.get(task_name),
        )
        client = TestClient(app)
        response = client.get("/api/v1/activity/recent")
        assert response.status_code == 200
        payload = response.json()
        notifications = payload.get("recent_notifications") or []
        assert len(notifications) >= 3
        latest = notifications[0]
        second = notifications[1]
        third = notifications[2]
        assert latest["review_release_state"]["required_next_action"] == "verify_rebuild"
        assert latest["governance_actions"]["can_verify_rebuild"] is True
        assert latest["governance_actions"]["platform"] == "agentchan"
        assert second["review_release_state"]["required_next_action"] == "acknowledge_recovery"
        assert second["governance_actions"]["can_acknowledge_recovery"] is True
        assert second["governance_actions"]["operational_agent_id"] == "bayman"
        assert third["review_release_state"]["required_next_action"] == "approve_resume"
        assert third["governance_actions"]["can_approve_resume"] is True
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_recent_activity_labels_runtime_continuity_receipts(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    record_human_notification(
        tmp_path,
        task_name="fourclaw-auto-post",
        kind="post_rebuild_runtime_observed",
        message="fourclaw-auto-post executed after rebuild verification",
        summary={
            "execution": {"status": "observed", "platform": "fourclaw", "mode": "auto-post"},
            "post_rebuild_continuity_check": {"status": "verified", "verified": True},
        },
        transport="log_only",
        operational_agent_id="underling-chan",
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/activity/recent")
        assert response.status_code == 200
        payload = response.json()
        notifications = payload.get("recent_notifications") or []
        assert notifications
        latest = notifications[0]
        assert latest["kind"] == "post_rebuild_runtime_observed"
        assert latest["governance_label"] == "Post-rebuild runtime observed"
        assert "rebuild verified" in (latest["governance_detail"] or "")
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_recent_activity_includes_evidence_plane_summary(tmp_path, monkeypatch):
    import operator_console.server.app.services.activity_service as activity_service

    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(
        activity_service,
        "get_recent_runs",
        lambda limit=10: [
            {"run_id": "run-1", "status": "completed", "started_at": "2026-03-22T12:00:00Z", "graph_id": "fourclaw-auto-post"},
        ],
    )
    monkeypatch.setattr(
        activity_service,
        "get_recent_decisions",
        lambda limit=20: [
            {"decision_id": "dec-1", "timestamp": "2026-03-22T12:01:00Z", "action": "approve_resume", "rationale": "rebuild verified", "outcome": "approved"},
        ],
    )
    monkeypatch.setattr(
        activity_service,
        "get_recent_human_notifications",
        lambda limit=20: [
            {
                "timestamp": "2026-03-22T12:02:00Z",
                "task_name": "fourclaw-auto-post",
                "kind": "post_rebuild_runtime_observed",
                "message": "runtime observed after rebuild",
                "transport": "log_only",
                "summary": {"post_rebuild_continuity_check": {"status": "verified"}},
                "governance_label": "Post-rebuild runtime observed",
                "governance_detail": "rebuild verified",
                "approval_href": "#/approvals?approval_id=approval-1",
                "review_release_state": {"required_next_action": "verify_rebuild"},
                "governance_actions": None,
            }
        ],
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/activity/recent")
        assert response.status_code == 200
        payload = response.json()
        evidence = payload.get("evidence_timeline") or {}
        assert evidence["status"] == "healthy"
        assert evidence["counts"]["runs"] == 1
        assert evidence["counts"]["decisions"] == 1
        assert evidence["counts"]["notifications"] == 1
        assert evidence["counts"]["continuity_events"] == 1
        assert evidence["counts"]["approval_events"] == 1
        assert evidence["counts"]["support_claims"] == 1
        assert evidence["latest"]["title"] == "Post-rebuild runtime observed"
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_recent_activity_uses_db_support_claims(tmp_path, monkeypatch):
    import operator_console.server.app.services.activity_service as activity_service

    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(
        activity_service,
        "list_evidence",
        lambda tenant_id, **kwargs: [
            {
                "ledger_id": "ledger-1",
                "ts": "2026-03-22T12:03:00Z",
                "approval_id": "approval-42",
                "evidence_type": "support_claim",
                "content_ref": "{\"approval_id\":\"approval-42\",\"decision\":\"approved\",\"decision_note\":\"ready\"}",
            }
        ],
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/activity/recent")
        assert response.status_code == 200
        payload = response.json()
        claims = payload.get("recent_support_claims") or []
        evidence = payload.get("evidence_timeline") or {}
        assert len(claims) == 1
        assert claims[0]["approval_id"] == "approval-42"
        assert evidence["counts"]["support_claims"] == 1
        assert evidence["support_claims"][0]["approval_id"] == "approval-42"
        assert evidence["support_claims"][0]["outcome"] == "approved"
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_recent_activity_includes_timeline_events(tmp_path, monkeypatch):
    import operator_console.server.app.services.activity_service as activity_service

    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(
        activity_service,
        "list_events",
        lambda tenant_id, **kwargs: [
            {
                "event_id": "evt-1",
                "ts": "2026-03-22T12:04:00Z",
                "tenant_id": tenant_id,
                "actor_id": "underling-chan",
                "chat_id": "chat-1",
                "run_id": "run-1",
                "approval_id": "approval-1",
                "event_type": "chat.create",
                "payload_json": "{\"chat_id\":\"chat-1\",\"title\":\"Archive test chat\"}",
            },
            {
                "event_id": "evt-2",
                "ts": "2026-03-22T12:05:00Z",
                "tenant_id": tenant_id,
                "actor_id": "underling-chan",
                "chat_id": "chat-1",
                "run_id": "run-1",
                "approval_id": "approval-1",
                "event_type": "approval.resolve",
                "payload_json": "{\"approval_id\":\"approval-1\",\"decision\":\"approved\"}",
            },
            {
                "event_id": "evt-3",
                "ts": "2026-03-22T12:06:00Z",
                "tenant_id": tenant_id,
                "actor_id": "underling-chan",
                "chat_id": "chat-1",
                "run_id": "run-1",
                "approval_id": None,
                "event_type": "message.final",
                "payload_json": "{\"message_id\":\"message-1\",\"chat_id\":\"chat-1\",\"content\":\"reply\"}",
            },
        ],
    )
    monkeypatch.setattr(
        activity_service,
        "get_recent_drift_timeline_events",
        lambda limit=20, **kwargs: [
            {
                "event_id": "drift-1",
                "timestamp": "2026-03-22T12:04:30Z",
                "entity_id": "social-media-underling",
                "workflow_id": "social-media",
                "root_id": "root-1",
                "event_type": "drift.detected",
                "title": "Drift detected",
                "detail": "watch · tone shifted",
                "href": "#/governance?root_id=root-1",
                "payload": {"root_id": "root-1", "workflow_family": "social-media"},
            }
        ],
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/activity/recent?chat_id=chat-1")
        assert response.status_code == 200
        payload = response.json()
        timeline = payload.get("recent_timeline_events") or []
        assert len(timeline) == 4
        titles = {row["title"] for row in timeline}
        assert "Turn completed" in titles
        assert "Approval resolved" in titles
        assert "Drift detected" in titles
        assert "Chat created" in titles
        drift = next(row for row in timeline if row["title"] == "Drift detected")
        assert drift["href"] == "#/governance?root_id=root-1"
        assert drift["detail"] == "watch · tone shifted"
        turn = next(row for row in timeline if row["title"] == "Turn completed" and row.get("provenance_href"))
        assert turn["provenance_href"] == "#/chat/chat-1?message_id=message-1"
        approval = next(row for row in timeline if row["title"] == "Approval resolved")
        assert approval["detail"] == "approved · approval-1"
        assert approval["href"] == "#/approvals?approval_id=approval-1"
        chat = next(row for row in timeline if row["title"] == "Chat created")
        assert chat["detail"] == "Archive test chat"
        assert chat["href"] == "#/chat/chat-1"
        evidence = payload.get("evidence_timeline") or {}
        assert evidence["counts"]["provenance_events"] >= 2
        assert evidence["provenance_events"][0]["provenance_href"] == "#/chat/chat-1?message_id=message-1"
        assert evidence["counts"]["drift_events"] == 1
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_recent_activity_includes_reflection_review_events(tmp_path, monkeypatch):
    import operator_console.server.app.services.activity_service as activity_service

    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(
        activity_service,
        "list_events",
        lambda tenant_id, **kwargs: [
            {
                "event_id": "evt-reflection-1",
                "ts": "2026-03-22T12:07:00Z",
                "tenant_id": tenant_id,
                "actor_id": "operator_console",
                "chat_id": None,
                "run_id": None,
                "approval_id": None,
                "document_id": "reflection:entity:phase4:001",
                "event_type": "reflection.artifact.promoted",
                "payload_json": "{\"artifact_id\":\"reflection:entity:phase4:001\",\"title\":\"Operator phase 4 reflection\",\"note\":\"ready for promotion\"}",
            },
        ],
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/activity/recent")
        assert response.status_code == 200
        payload = response.json()
        timeline = payload.get("recent_timeline_events") or []
        assert len(timeline) == 1
        assert timeline[0]["title"] == "Reflection promoted"
        assert timeline[0]["detail"] == "ready for promotion"
        assert timeline[0]["href"] == "#/reflections?artifact_id=reflection:entity:phase4:001"
        evidence = payload.get("evidence_timeline") or {}
        assert evidence["counts"]["reflection_events"] == 1
        assert evidence["counts"]["provenance_events"] == 1
        assert evidence["provenance_events"][0]["provenance_href"] == "#/reflections?artifact_id=reflection:entity:phase4:001"
    finally:
        app.dependency_overrides.pop(require_api_key, None)


def test_recent_activity_includes_shared_activity_projection(tmp_path, monkeypatch):
    import operator_console.server.app.services.activity_service as activity_service

    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(
        activity_service,
        "list_events",
        lambda tenant_id, **kwargs: [
            {
                "event_id": "evt-1",
                "ts": "2026-03-22T12:04:00Z",
                "tenant_id": tenant_id,
                "actor_id": "underling-chan",
                "chat_id": "chat-1",
                "run_id": "run-1",
                "approval_id": None,
                "event_type": "chat.create",
                "payload_json": "{\"chat_id\":\"chat-1\",\"title\":\"Archive test chat\"}",
            },
            {
                "event_id": "evt-2",
                "ts": "2026-03-22T12:05:00Z",
                "tenant_id": tenant_id,
                "actor_id": "underling-chan",
                "chat_id": "chat-1",
                "run_id": "run-1",
                "approval_id": None,
                "event_type": "message.final",
                "payload_json": "{\"message_id\":\"message-1\",\"chat_id\":\"chat-1\",\"content\":\"reply\"}",
            },
        ],
    )
    monkeypatch.setattr(
        activity_service,
        "get_recent_runs",
        lambda limit=10: [{"run_id": "run-1", "status": "completed", "started_at": "2026-03-22T12:00:00Z", "graph_id": "graph-1"}],
    )
    monkeypatch.setattr(
        activity_service,
        "get_recent_decisions",
        lambda limit=20: [{"decision_id": "dec-1", "timestamp": "2026-03-22T12:01:00Z", "action": "approve_resume", "rationale": "ok", "outcome": "approved"}],
    )
    monkeypatch.setattr(
        activity_service,
        "get_recent_human_notifications",
        lambda limit=20: [],
    )
    monkeypatch.setattr(
        activity_service,
        "get_recent_support_claims",
        lambda limit=20: [],
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get("/api/v1/activity/projection?view=compact&chat_id=chat-1")
        assert response.status_code == 200
        payload = response.json()
        projection = payload.get("activity_projection") or {}
        assert projection["view"] == "compact"
        assert projection["compact"]["counts"]["runs"] == 1
        assert projection["expanded"]["timeline"][0]["title"] == "Turn completed"
        assert projection["since_last_wake"]["summary"]
        assert projection["since_last_wake"]["timeline"][0]["title"] == "Turn completed"
    finally:
        app.dependency_overrides.pop(require_api_key, None)
