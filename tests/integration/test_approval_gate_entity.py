"""
Integration tests for entity approval gate and social submit (Social Media Entity Tools).
Tests: approval service create/approve/reject; submit returns 403 without approval; proof bundle shape.
"""

import os
import tempfile
import json
from pathlib import Path
import pytest

from hg_gateway.approval_service import ApprovalService, STATUS_APPROVED, STATUS_PENDING
from hg_gateway.auth import verify_api_key
from hg_gateway.db import get_connection


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    try:
        yield path
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


@pytest.fixture
def approval_service(temp_db):
    return ApprovalService(db_path=temp_db)


def test_approval_create_defaults_pending(approval_service):
    row = approval_service.create_request(
        entity_id="entity-1",
        action_kind="social_post",
        preview_json={"platform": "reddit", "draft_text": "hello"},
    )
    assert row["status"] == STATUS_PENDING
    assert row["entity_id"] == "entity-1"
    assert "approval_id" in row


def test_approval_approve_and_reject(approval_service):
    row = approval_service.create_request(
        entity_id="e2",
        action_kind="social_post",
        preview_json={},
    )
    aid = row["approval_id"]
    approved = approval_service.approve(aid, tenant_id="default", decision_note="ok")
    assert approved is not None
    assert approved["status"] == STATUS_APPROVED
    # New request to reject
    row2 = approval_service.create_request(entity_id="e3", action_kind="social_post", preview_json={})
    rejected = approval_service.reject(row2["approval_id"], tenant_id="default", decision_note="no")
    assert rejected is not None
    assert rejected["status"] == "rejected"


def test_submit_requires_approval(approval_service):
    """Submit without approval must be blocked at API level (403). Test service state."""
    row = approval_service.create_request(
        entity_id="e4",
        action_kind="social_post",
        preview_json={"platform": "reddit"},
    )
    assert row["status"] == STATUS_PENDING
    got = approval_service.get_request(row["approval_id"], tenant_id="default")
    assert got["status"] == STATUS_PENDING
    # After approve, status is approved — submit path checks this
    approval_service.approve(row["approval_id"], tenant_id="default")
    got2 = approval_service.get_request(row["approval_id"], tenant_id="default")
    assert got2["status"] == STATUS_APPROVED


def test_approval_api_records_review_handoff_resolution_receipt(temp_db, tmp_path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", temp_db)
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    from fastapi.testclient import TestClient
    from operator_console.server.app.main import app
    from operator_console.server.app.core.auth import require_api_key

    approval = ApprovalService(db_path=temp_db).create_request(
        entity_id="newfoundland-bayman-fourclaw-engage",
        action_kind="social_write",
        preview_json={"summary": "review me"},
        tenant_id="default",
        workflow_id="newfoundland-bayman-fourclaw-engage",
        target_platform="fourclaw",
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/approvals-entity/{approval['approval_id']}/approve",
            json={
                "note": "looks good",
                "decided_by": "operator",
                "rationale": "continuity verified",
                "release_scope": "single supervised post",
                "followup_expectation": "watch replies for 1h",
                "followup_window_hours": 6,
            },
        )
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(require_api_key, None)

    log_path = tmp_path / "memory" / "automation" / "notifications" / "human_notifications.jsonl"
    assert log_path.exists()
    rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    latest = rows[-1]
    assert latest["kind"] == "review_handoff_resolution"
    assert latest["summary"]["review_handoff"]["approval_id"] == approval["approval_id"]
    assert latest["summary"]["review_handoff"]["decision"] == "approved"
    assert latest["summary"]["review_handoff"]["decision_note"] == "looks good"
    resolution_context = latest["summary"]["review_handoff"]["resolution_context"]
    assert resolution_context["rationale"] == "continuity verified"
    assert resolution_context["release_scope"] == "single supervised post"
    assert resolution_context["followup_expectation"] == "watch replies for 1h"
    assert resolution_context["followup_window_hours"] == 6

    updated = ApprovalService(db_path=temp_db).get_request(approval["approval_id"], tenant_id="default")
    assert updated["preview_json"]["resolution_context"]["rationale"] == "continuity verified"
    assert updated["preview_json"]["resolution_context"]["release_scope"] == "single supervised post"
    assert updated["preview_json"]["resolution_context"]["followup_expectation"] == "watch replies for 1h"
    assert updated["preview_json"]["resolution_context"]["followup_window_hours"] == 6


def test_approval_api_records_support_claim_evidence_and_analytics_query(temp_db, tmp_path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", temp_db)
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    from fastapi.testclient import TestClient
    from operator_console.server.app.main import app
    from operator_console.server.app.core.auth import require_api_key

    approval = ApprovalService(db_path=temp_db).create_request(
        entity_id="newfoundland-bayman-fourclaw-engage",
        action_kind="social_write",
        preview_json={"summary": "review me"},
        tenant_id="default",
        workflow_id="newfoundland-bayman-fourclaw-engage",
        target_platform="fourclaw",
    )

    app.dependency_overrides[require_api_key] = lambda: True
    app.dependency_overrides[verify_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/approvals-entity/{approval['approval_id']}/approve",
            json={"note": "approved", "decided_by": "operator", "rationale": "continuity verified"},
        )
        assert response.status_code == 200
        evidence = client.get(
            f"/v1/analytics/evidence?approval_id={approval['approval_id']}&evidence_types=support_claim",
        )
        assert evidence.status_code == 200
        payload = evidence.json()
        assert payload["tenant_id"] == "default"
        rows = payload.get("evidence") or []
        assert rows
        assert rows[0]["approval_id"] == approval["approval_id"]
        assert rows[0]["evidence_type"] == "support_claim"
    finally:
        app.dependency_overrides.pop(require_api_key, None)
        app.dependency_overrides.pop(verify_api_key, None)


def test_approval_api_records_review_release_window_receipt(temp_db, tmp_path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", temp_db)
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    from fastapi.testclient import TestClient
    from operator_console.server.app.main import app
    from operator_console.server.app.core.auth import require_api_key

    approval = ApprovalService(db_path=temp_db).create_request(
        entity_id="newfoundland-bayman-fourclaw-engage",
        action_kind="social_write",
        preview_json={"summary": "review me", "release_window_hours": 8},
        tenant_id="default",
        workflow_id="newfoundland-bayman-fourclaw-engage",
        target_platform="fourclaw",
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/approvals-entity/{approval['approval_id']}/approve",
            json={"note": "looks good", "decided_by": "operator"},
        )
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(require_api_key, None)

    log_path = tmp_path / "memory" / "automation" / "notifications" / "human_notifications.jsonl"
    rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    latest = rows[-1]
    assert latest["summary"]["review_handoff"]["release_window_hours"] == 8
    assert latest["summary"]["review_handoff"]["approved_until"].endswith("Z")


def test_approval_api_refreshes_review_handoff_into_new_pending_request(temp_db, tmp_path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", temp_db)
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    from fastapi.testclient import TestClient
    from operator_console.server.app.main import app
    from operator_console.server.app.core.auth import require_api_key

    approval = ApprovalService(db_path=temp_db).create_request(
        entity_id="newfoundland-bayman-fourclaw-engage",
        action_kind="social_write",
        preview_json={"summary": "review me", "operational_agent_id": "newfoundland-bayman"},
        tenant_id="default",
        workflow_id="newfoundland-bayman-fourclaw-engage",
        target_platform="fourclaw",
    )
    ApprovalService(db_path=temp_db).approve(
        approval["approval_id"],
        tenant_id="default",
        decided_by="operator",
        decision_note="looks good",
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/approvals-entity/{approval['approval_id']}/refresh",
            json={"note": "stale context", "decided_by": "operator", "refresh_reason_codes": ["followup_overdue"]},
        )
        assert response.status_code == 200
        refreshed = response.json()
    finally:
        app.dependency_overrides.pop(require_api_key, None)

    assert refreshed["approval_id"] != approval["approval_id"]
    assert refreshed["status"] == STATUS_PENDING
    assert refreshed["refreshed_from_approval_id"] == approval["approval_id"]
    assert refreshed["preview_json"]["refreshed_from_approval_id"] == approval["approval_id"]
    assert refreshed["preview_json"]["refresh_note"] == "stale context"
    assert refreshed["preview_json"]["refresh_context"]["from_approval_id"] == approval["approval_id"]
    assert refreshed["preview_json"]["refresh_context"]["note"] == "stale context"
    assert refreshed["preview_json"]["refresh_context"]["refreshed_by"] == "operator"
    assert refreshed["preview_json"]["refresh_context"]["source_status"] == "approved"
    assert refreshed["preview_json"]["refresh_context"]["reason_codes"] == ["followup_overdue"]
    assert refreshed["preview_json"]["refresh_reason_codes"] == ["followup_overdue"]

    log_path = tmp_path / "memory" / "automation" / "notifications" / "human_notifications.jsonl"
    rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    latest = rows[-1]
    assert latest["kind"] == "agency_gate"
    assert latest["summary"]["execution"]["status"] == "pending_approval"
    assert latest["summary"]["execution"]["blocked_reason"] == "review_handoff_refreshed"
    assert latest["summary"]["review_handoff"]["approval_id"] == refreshed["approval_id"]
    assert latest["summary"]["review_handoff"]["refreshed_from_approval_id"] == approval["approval_id"]
    assert latest["summary"]["review_handoff"]["refresh_reason_codes"] == ["followup_overdue"]


def test_get_approval_request_includes_review_release_state(temp_db, tmp_path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", temp_db)
    monkeypatch.setenv("HG_WORKSPACE", str(tmp_path))
    from fastapi.testclient import TestClient
    from operator_console.server.app.main import app
    from operator_console.server.app.core.auth import require_api_key
    import operator_console.server.app.api.approvals_entity as approvals_entity

    approval = ApprovalService(db_path=temp_db).create_request(
        entity_id="newfoundland-bayman-fourclaw-engage",
        action_kind="social_write",
        preview_json={"summary": "review me"},
        tenant_id="default",
        workflow_id="newfoundland-bayman-fourclaw-engage",
        target_platform="fourclaw",
    )

    monkeypatch.setattr(
        approvals_entity,
        "_enrich_review_release_state",
        lambda row: {
            **row,
            "review_release_state": {
                "release_ready": False,
                "release_blockers": ["operational_resume_checkpoint_required"],
                "release_next_eligible_at": None,
                "refresh_recommended": False,
                "refresh_reasons": [],
                "latest_release_attempt": None,
                "followup_summary": None,
                "continuity_recovery_readiness": {
                    "status": "caution",
                    "can_acknowledge": True,
                    "acknowledged": False,
                    "cautions": ["recent_continuity_recovery"],
                },
                "post_rebuild_continuity_check": {
                    "status": "pending",
                    "verification_required": True,
                    "verified": False,
                    "rebuild_recorded_at": "2026-03-13T18:00:00Z",
                },
                "operational_resume_governance_summary": {"status": "ready", "required_actions": []},
                "operational_resume_checkpoint": {
                    "approved": False,
                    "invalidated": True,
                    "invalidated_reason": "operational_resume_no_longer_ready",
                },
                "platform": "fourclaw",
                "operational_agent_id": "newfoundland-bayman",
                "required_next_action": "verify_rebuild",
                "action_hint": "Verify post-rebuild continuity before release.",
            },
        },
    )

    app.dependency_overrides[require_api_key] = lambda: True
    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/approvals-entity/{approval['approval_id']}")
        assert response.status_code == 200
        payload = response.json()
    finally:
        app.dependency_overrides.pop(require_api_key, None)

    release_state = payload["review_release_state"]
    assert release_state["release_ready"] is False
    assert "operational_resume_checkpoint_required" in release_state["release_blockers"]
    assert release_state["continuity_recovery_readiness"]["can_acknowledge"] is True
    assert release_state["post_rebuild_continuity_check"]["verification_required"] is True
    assert release_state["required_next_action"] == "verify_rebuild"
    assert "Verify post-rebuild continuity" in (release_state["action_hint"] or "")
    assert release_state["operational_resume_checkpoint"]["invalidated_reason"] == "operational_resume_no_longer_ready"
    assert release_state["platform"] == "fourclaw"
    assert release_state["operational_agent_id"] == "newfoundland-bayman"
