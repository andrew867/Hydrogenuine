import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from hg_core.security.social_account_artifacts import record_social_account_session_binding
from hg_gateway import keystore_repo
from hg_gateway.db import get_connection
from hg_core.human_notifications import record_human_notification
from hg_gateway.operational_state_ledger import save_operational_json_state
from operator_console.server.app.services.identity_restore_validation import record_identity_restore_event, verify_identity_restore
from operator_console.server.app.services.post_rebuild_continuity_check import record_post_rebuild_event, verify_post_rebuild_continuity

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))
    from fastapi.testclient import TestClient
    from app.main import app
    import app.api.workflows as workflows_api
    _client_fixture = lambda: TestClient(app)
else:
    _client_fixture = None
    workflows_api = None


def _headers():
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture
def client():
    if _client_fixture is None:
        pytest.skip("operator_console/server not found")
    return _client_fixture()


@pytest.fixture
def fake_workspace(tmp_path, monkeypatch):
    root = tmp_path
    dags = root / "memory" / "automation" / "dags"
    dags.mkdir(parents=True)
    cadence_dir = root / "memory" / "automation" / "automation-underling-chan"
    cadence_dir.mkdir(parents=True, exist_ok=True)
    (cadence_dir / "cadence_request.json").write_text(
        json.dumps(
            {
                "task": "fourclaw-engage",
                "job_id": "social-media-underling",
                "requested_at": "2026-03-13T12:00:00Z",
                "not_before": "2099-03-13T12:03:00Z",
                "requested_duration_minutes": 3,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (root / "memory" / "automation" / "realtime_schedule.json").write_text(
        json.dumps(
            [
                {"job_id": "social-media-underling", "interval_minutes": 11, "inputs": {"workflow_id": "social-media", "task_name": "fourclaw-engage", "trigger": "realtime"}},
                {"job_id": "knowledge-research-auto", "interval_minutes": 60, "inputs": {"trigger": "realtime"}},
                {"job_id": "moltstack-draft", "cron": "0 21 * * *", "inputs": {"trigger": "realtime"}},
            ],
            indent=2,
        ),
        encoding="utf-8",
    )

    samples = {
        "social_media.json": {
            "graph_id": "social_media_v1",
            "version": "1.0",
            "run_policy": {"max_concurrency": 1},
            "inputs": {"goal": ""},
            "nodes": [
                {
                    "id": "choose",
                    "type": "tool",
                    "assigned_entity": "lifecycle.choose_social_work",
                    "depends_on": [],
                    "inputs": {"goal": "$graph.inputs.goal"},
                }
            ],
        },
        "fourclaw_auto_post.json": {
            "graph_id": "fourclaw_auto_post_v1",
            "version": "1.0",
            "run_policy": {"max_concurrency": 1},
            "inputs": {"goal": ""},
            "nodes": [
                {
                    "id": "post",
                    "type": "agent",
                    "assigned_entity": "fourclaw-auto-post",
                    "depends_on": [],
                    "inputs": {"goal": "$graph.inputs.goal"},
                }
            ],
        },
        "fourclaw_engage.json": {
            "graph_id": "fourclaw_engage_v1",
            "version": "1.0",
            "run_policy": {"max_concurrency": 1},
            "inputs": {"goal": ""},
            "nodes": [
                {
                    "id": "engage",
                    "type": "agent",
                    "assigned_entity": "fourclaw-engage",
                    "depends_on": [],
                    "inputs": {"goal": "$graph.inputs.goal"},
                }
            ],
        },
        "moltbook_auto_post.json": {
            "graph_id": "moltbook_auto_post_v1",
            "version": "1.0",
            "run_policy": {"max_concurrency": 1},
            "inputs": {"goal": ""},
            "nodes": [
                {
                    "id": "post",
                    "type": "agent",
                    "assigned_entity": "moltbook-auto-post",
                    "depends_on": [],
                    "inputs": {"goal": "$graph.inputs.goal"},
                }
            ],
        },
        "job_search_degree_agnostic_agent_runtime_v1.json": {
            "graph_id": "job_search_degree_agnostic_agent_runtime_v1",
            "version": "1.0",
            "run_policy": {"max_concurrency": 1},
            "inputs": {},
            "nodes": [
                {
                    "id": "scan",
                    "type": "agent",
                    "assigned_entity": "rcmp-job-search",
                    "depends_on": [],
                    "inputs": {},
                }
            ],
        },
    }

    for name, data in samples.items():
        (dags / name).write_text(json.dumps(data, indent=2), encoding="utf-8")

    monkeypatch.setattr(workflows_api, "_workspace_root", lambda: root)
    return root


def test_scheduled_jobs_requires_auth(client):
    r = client.get("/api/v1/workflows/scheduled-jobs")
    assert r.status_code in (401, 403)


def test_list_scheduled_jobs(client, fake_workspace):
    r = client.get("/api/v1/workflows/scheduled-jobs", headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    jobs = data.get("jobs", [])
    ids = {j.get("job_id") for j in jobs}
    assert "social-media-underling" in ids
    assert "knowledge-research-auto" in ids
    assert "moltstack-draft" in ids
    assert "fourclaw-auto-post-cadence" not in ids
    assert all("node_count" in j for j in jobs)

    social_job = next(j for j in jobs if j.get("job_id") == "social-media-underling")
    assert social_job.get("graph_id") == "social_media_v1"
    assert social_job.get("workflow_id") == "social-media"
    assert social_job.get("task_name") == "fourclaw-engage"
    assert social_job.get("cadence", {}).get("request", {}).get("job_id") == "social-media-underling"
    assert social_job.get("next_run", "").startswith("2099-03-13T12:03:00")
    assert social_job.get("continuity_recovery_readiness", {}).get("status") == "caution"
    assert "identity_continuity_partial" in (social_job.get("continuity_recovery_readiness", {}).get("cautions") or [])
    assert social_job.get("identity_resume_procedure", {}).get("status") == "missing"
    assert "write_initialization_memo" in (social_job.get("identity_resume_procedure", {}).get("open_steps") or [])
    assert "record_wake_receipt" in (social_job.get("continuity_repair_plan", {}).get("open_checks") or [])
    assert social_job.get("crew_dynamics_summary", {}).get("coordination_style") == "pipeline_baton"
    assert social_job.get("crew_dynamics_summary", {}).get("coordination_style_source") == "inferred_from_run_policy"
    assert social_job.get("crew_dynamics_summary", {}).get("swarm_member_count") >= 0
    assert isinstance(social_job.get("crew_dynamics_summary"), dict)
    assert social_job.get("release_gate_summary", {}).get("ok") is False
    assert social_job.get("release_gate_summary", {}).get("code") in {"missing_verdict", "backup_required"}
    knowledge_job = next(j for j in jobs if j.get("job_id") == "knowledge-research-auto")
    assert knowledge_job.get("continuity_recovery_readiness", {}).get("status") == "ready"
    assert knowledge_job.get("continuity_repair_plan", {}).get("status") == "not_applicable"
    assert knowledge_job.get("operational_resume_governance_summary", {}).get("status") == "not_applicable"


def test_list_scheduled_jobs_surfaces_workflow_status_summary(client, fake_workspace, monkeypatch):
    import app.services.scheduled_jobs_service as scheduled_jobs_service
    import app.services.review_handoff_summary as review_handoff_summary

    run_dir = fake_workspace / "memory" / "automation" / "dag_runs" / "run-social-1"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(
        json.dumps(
            {
                "run_id": "run-social-1",
                "graph_id": "social_media_v1",
                "final_status": "completed",
                "started_at": "2026-03-24T12:00:00Z",
                "ended_at": "2026-03-24T12:05:00Z",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (run_dir / "state.json").write_text(
        json.dumps(
            {
                "node_states": {
                    "launch": {"id": "launch", "status": "done", "assigned_entity": "task-launch"},
                    "post": {"id": "post", "status": "failed", "assigned_entity": "task-post"},
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(review_handoff_summary, "list_runs_index", lambda limit=200: [
        {
            "run_id": "run-social-1",
            "graph_id": "social_media_v1",
            "status": "completed",
            "started_at": "2026-03-24T12:00:00Z",
            "ended_at": "2026-03-24T12:05:00Z",
            "run_dir": str(run_dir),
        }
    ])

    r = client.get("/api/v1/workflows/scheduled-jobs", headers=_headers())
    assert r.status_code == 200
    jobs = r.json().get("jobs", [])
    social_job = next(j for j in jobs if j.get("job_id") == "social-media-underling")
    summary = social_job.get("workflow_status_summary") or {}
    assert summary.get("latest_run_id") == "run-social-1"
    assert summary.get("latest_run_status") == "completed"
    assert summary.get("status") == "completed"
    assert summary.get("latest_run_href") == "#/activity?run_id=run-social-1"
    assert summary.get("node_state_summary", {}).get("counts", {}).get("nodes") == 2
    assert summary.get("node_state_summary", {}).get("counts", {}).get("done") == 1
    assert summary.get("node_state_summary", {}).get("counts", {}).get("failed") == 1


def test_list_scheduled_jobs_merges_registry_with_fallback_social_alias(client, fake_workspace, monkeypatch):
    import app.services.scheduled_jobs_service as scheduled_jobs_service

    monkeypatch.setattr(
        scheduled_jobs_service,
        "_get_registry",
        lambda workspace_root: {
            "knowledge-research-auto": type("Job", (), {"dag_path": "memory/automation/dags/knowledge_research_auto.json"})(),
            "memory-maintenance": type("Job", (), {"dag_path": "memory/automation/dags/memory_maintenance.json"})(),
        },
    )

    r = client.get("/api/v1/workflows/scheduled-jobs", headers=_headers())
    assert r.status_code == 200
    jobs = r.json().get("jobs", [])
    ids = {j.get("job_id") for j in jobs}
    assert "social-media-underling" in ids
    social_job = next(j for j in jobs if j.get("job_id") == "social-media-underling")
    assert social_job.get("graph_id") == "social_media_v1"
    assert social_job.get("workflow_id") == "social-media"


def test_list_scheduled_jobs_surfaces_post_rebuild_continuity_check(client, fake_workspace, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(fake_workspace / "gateway.sqlite3"))
    operational_dir = fake_workspace / "memory" / "automation" / "automation-underling-chan"
    record_post_rebuild_event(
        root=fake_workspace,
        binding={"operational_session_target": "automation-underling-chan", "operational_agent_id": "underling-chan", "platform": "fourclaw"},
        recorded_by="rev",
        note="compose rebuild",
    )
    save_operational_json_state(
        fake_workspace,
        state_key="identity_continuity_state:automation-underling-chan",
        payload={
            "initialization_memo_present": True,
            "initialization_memo_path": "memory/automation/automation-underling-chan/initialization_memo.md",
            "wake_receipt_present": True,
            "wake_receipt_recorded_at": "2026-03-14T02:05:00Z",
            "wake_receipt": {"timestamp": "2026-03-14T02:05:00Z"},
            "last_wake_at": "2026-03-14T02:05:00Z",
            "sleep_summary_present": True,
            "sleep_summary_recorded_at": "2026-03-14T01:45:00Z",
            "last_sleep_at": "2026-03-14T01:45:00Z",
            "last_sleep_summary": {"timestamp": "2026-03-14T01:45:00Z"},
        },
    )

    r = client.get("/api/v1/workflows/scheduled-jobs", headers=_headers())
    assert r.status_code == 200
    jobs = r.json().get("jobs", [])
    social_job = next(j for j in jobs if j.get("job_id") == "social-media-underling")
    assert social_job.get("post_rebuild_continuity_check", {}).get("status") == "pending"
    assert "post_rebuild_continuity_check_pending" in (social_job.get("continuity_recovery_readiness", {}).get("cautions") or [])
    assert "verify_post_rebuild_continuity" in (social_job.get("continuity_repair_plan", {}).get("open_checks") or [])
    resume_summary = social_job.get("operational_resume_governance_summary") or {}
    assert resume_summary.get("status") == "caution"
    assert resume_summary.get("pending_count") == 1
    assert "verify_post_rebuild_continuity:fourclaw-engage" in (resume_summary.get("required_actions") or [])


def test_list_scheduled_jobs_surfaces_identity_restore_and_supervised_validation(client, fake_workspace, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(fake_workspace / "gateway.sqlite3"))
    operational_dir = fake_workspace / "memory" / "automation" / "automation-underling-chan"
    binding = {"operational_session_target": "automation-underling-chan", "operational_agent_id": "underling-chan", "platform": "fourclaw"}
    record_post_rebuild_event(
        root=fake_workspace,
        binding=binding,
        recorded_by="rev",
        note="compose rebuild",
    )
    verify_post_rebuild_continuity(
        root=fake_workspace,
        binding=binding,
        verified_by="rev",
        note="compose rebuild verified",
        identity_continuity_summary={"status": "healthy", "initialization_memo_present": True, "wake_receipt_present": True},
        continuity_recovery_readiness={"status": "ready"},
    )
    record_identity_restore_event(root=fake_workspace, binding=binding, recorded_by="rev", note="identity restore")
    verify_identity_restore(
        root=fake_workspace,
        binding=binding,
        verified_by="rev",
        note="identity restore verified",
        identity_continuity_summary={"wake_receipt_present": True, "sleep_summary_present": True},
    )
    save_operational_json_state(
        fake_workspace,
        state_key="identity_continuity_state:automation-underling-chan",
        payload={
            "initialization_memo_present": True,
            "initialization_memo_path": "memory/automation/automation-underling-chan/initialization_memo.md",
            "wake_receipt_present": True,
            "wake_receipt_recorded_at": "2026-03-14T02:05:00Z",
            "wake_receipt": {"timestamp": "2026-03-14T02:05:00Z"},
            "last_wake_at": "2026-03-14T02:05:00Z",
            "sleep_summary_present": True,
            "sleep_summary_recorded_at": "2026-03-14T01:45:00Z",
            "last_sleep_at": "2026-03-14T01:45:00Z",
            "last_sleep_summary": {"timestamp": "2026-03-14T01:45:00Z"},
        },
    )

    r = client.get("/api/v1/workflows/scheduled-jobs", headers=_headers())
    assert r.status_code == 200
    jobs = r.json().get("jobs", [])
    social_job = next(j for j in jobs if j.get("job_id") == "social-media-underling")
    assert social_job.get("identity_restore_validation", {}).get("status") == "validated"
    assert social_job.get("supervised_resume_validation", {}).get("status") == "pending"
    assert "run_supervised_resume_validation" in (social_job.get("continuity_repair_plan", {}).get("open_checks") or [])
    assert "supervised_resume_validation_required" in (social_job.get("bounded_autonomy_policy_summary", {}).get("blockers") or [])


def test_list_scheduled_jobs_surfaces_agency_control(client, fake_workspace):
    agency_path = fake_workspace / "memory" / "automation" / "automation-underling-chan" / "agency_control.json"
    agency_path.write_text(
        json.dumps(
            {
                "mode": "held",
                "reason": "maintenance window",
                "updated_at": "2026-03-13T12:01:00Z",
                "updated_by": "operator",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    r = client.get("/api/v1/workflows/scheduled-jobs", headers=_headers())
    assert r.status_code == 200
    jobs = r.json().get("jobs", [])
    social_job = next(j for j in jobs if j.get("job_id") == "social-media-underling")
    assert social_job.get("agency_control", {}).get("effective_mode") == "held"
    assert social_job.get("agency_control", {}).get("reason") == "maintenance window"
    assert social_job.get("next_run", "").startswith("203")


def test_list_scheduled_jobs_surfaces_resume_checkpoint_requirement(client, fake_workspace):
    operational_dir = fake_workspace / "memory" / "automation" / "automation-underling-chan"
    operational_dir.mkdir(parents=True, exist_ok=True)
    save_operational_json_state(
        fake_workspace,
        state_key="identity_continuity_state:automation-underling-chan",
        payload={
            "initialization_memo_present": True,
            "initialization_memo_path": "memory/automation/automation-underling-chan/initialization_memo.md",
            "wake_receipt_present": True,
            "wake_receipt_recorded_at": "2026-03-14T02:05:00Z",
            "wake_receipt": {"timestamp": "2026-03-14T02:05:00Z"},
            "last_wake_at": "2026-03-14T02:05:00Z",
            "sleep_summary_present": True,
            "sleep_summary_recorded_at": "2026-03-14T01:45:00Z",
            "last_sleep_at": "2026-03-14T01:45:00Z",
            "last_sleep_summary": {"timestamp": "2026-03-14T01:45:00Z"},
        },
    )

    r = client.get("/api/v1/workflows/scheduled-jobs", headers=_headers())
    assert r.status_code == 200
    jobs = r.json().get("jobs", [])
    social_job = next(j for j in jobs if j.get("job_id") == "social-media-underling")
    assert social_job.get("continuity_recovery_readiness", {}).get("status") == "ready"
    assert social_job.get("operational_resume_governance_summary", {}).get("status") == "ready"
    assert social_job.get("operational_resume_checkpoint", {}).get("approved") is False
    assert social_job.get("operational_resume_checkpoint_required") is True
    assert social_job.get("confidence_summary", {}).get("confidence_level") in {"uncertain", "cautious", "confident", "certain"}


def test_list_scheduled_jobs_surfaces_review_handoff_summary(client, fake_workspace):
    record_human_notification(
        fake_workspace,
        task_name="fourclaw-engage",
        kind="agency_gate",
        message="review handoff created",
        summary={
            "execution": {"status": "pending_approval", "platform": "fourclaw", "blocked_reason": "agency_control_review_only"},
            "agency_control": {"effective_mode": "review_only", "reason": "supervised rollout"},
            "review_handoff": {"approval_id": "approval-workflow-1", "title": "Review required: fourclaw engage"},
        },
        operational_agent_id="underling-chan",
    )
    r = client.get("/api/v1/workflows/scheduled-jobs", headers=_headers())
    assert r.status_code == 200
    jobs = r.json().get("jobs", [])
    social_job = next(j for j in jobs if j.get("job_id") == "social-media-underling")
    assert isinstance(social_job.get("commitment_summary"), dict)
    assert isinstance(social_job.get("confidence_summary"), dict)
    summary = social_job.get("review_handoff_summary") or {}
    assert summary.get("count") == 1
    assert summary.get("pending_count") == 1
    assert (summary.get("latest") or {}).get("approval_id") == "approval-workflow-1"
    assert (summary.get("latest") or {}).get("approval_href") == "#/approvals?workflow_id=fourclaw-engage&approval_id=approval-workflow-1"


def test_list_scheduled_jobs_review_handoff_summary_includes_release_blockers(client, fake_workspace):
    agency_path = fake_workspace / "memory" / "automation" / "automation-underling-chan" / "agency_control.json"
    agency_path.write_text(
        json.dumps(
            {
                "mode": "held",
                "reason": "maintenance window",
                "updated_at": "2026-03-13T12:01:00Z",
                "updated_by": "operator",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    record_human_notification(
        fake_workspace,
        task_name="fourclaw-engage",
        kind="agency_gate",
        message="review handoff created",
        summary={
            "execution": {"status": "pending_approval", "platform": "fourclaw", "blocked_reason": "agency_control_review_only"},
            "agency_control": {"effective_mode": "review_only", "reason": "supervised rollout"},
            "review_handoff": {"approval_id": "approval-workflow-2", "title": "Review required: fourclaw engage"},
        },
        operational_agent_id="underling-chan",
    )
    r = client.get("/api/v1/workflows/scheduled-jobs", headers=_headers())
    assert r.status_code == 200
    jobs = r.json().get("jobs", [])
    social_job = next(j for j in jobs if j.get("job_id") == "social-media-underling")
    assert isinstance(social_job.get("commitment_summary"), dict)
    summary = social_job.get("review_handoff_summary") or {}
    assert summary.get("release_ready") is False
    assert "agency_hold" in (summary.get("release_blockers") or [])


def test_list_scheduled_jobs_review_handoff_summary_includes_continuity_release_blocker(client, fake_workspace, monkeypatch):
    db_path = fake_workspace / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    keystore_repo.social_account_create(
        social_account_id="acct-underling-fourclaw",
        tenant_id="default",
        platform="fourclaw",
        account_alias="underling-fourclaw",
        entity_scope="underling-chan",
        persona_scope="underling_chan_operational",
        state="verified",
        db_path=str(db_path),
    )
    with get_connection(str(db_path)) as conn:
        conn.execute(
            """INSERT INTO browser_sessions (browser_session_id, tenant_id, entity_id, platform, state, started_at)
               VALUES (?, ?, ?, ?, ?, datetime('now'))""",
            ("session-bad", "default", "underling-chan", "fourclaw", "degraded"),
        )
        conn.execute(
            """INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at)
               VALUES (?, 'browser_session', ?, 'session_degraded', ?, ?, datetime('now'))""",
            ("proof-bad", "session-bad", "missing_restart_critical_browser_artifacts", '{"reason":"missing_restart_critical_browser_artifacts"}'),
        )
    record_social_account_session_binding(
        "acct-underling-fourclaw",
        browser_session_id="session-bad",
        platform="fourclaw",
        tenant_id="default",
        entity_id="underling-chan",
        account_alias="underling-fourclaw",
        state="active",
    )
    record_human_notification(
        fake_workspace,
        task_name="fourclaw-engage",
        kind="agency_gate",
        message="review handoff created",
        summary={
            "execution": {"status": "pending_approval", "platform": "fourclaw", "blocked_reason": "agency_control_review_only"},
            "agency_control": {"effective_mode": "review_only", "reason": "supervised rollout"},
            "review_handoff": {"approval_id": "approval-workflow-continuity", "title": "Review required: fourclaw engage"},
        },
        operational_agent_id="underling-chan",
    )
    r = client.get("/api/v1/workflows/scheduled-jobs", headers=_headers())
    assert r.status_code == 200
    jobs = r.json().get("jobs", [])
    social_job = next(j for j in jobs if j.get("job_id") == "social-media-underling")
    summary = social_job.get("review_handoff_summary") or {}
    assert summary.get("release_ready") is False
    assert "continuity_recovery" in (summary.get("release_blockers") or [])


def test_list_scheduled_jobs_review_handoff_summary_requires_operational_resume_checkpoint(client, fake_workspace, monkeypatch):
    import app.services.scheduled_jobs_service as scheduled_jobs_service

    monkeypatch.setattr(
        scheduled_jobs_service,
        "build_operational_resume_governance_summary",
        lambda **kwargs: {"status": "ready", "required_actions": []},
    )
    monkeypatch.setattr(
        scheduled_jobs_service,
        "ensure_operational_resume_checkpoint_validity",
        lambda **kwargs: {
            "approved": False,
            "invalidated": True,
            "invalidated_reason": "operational_resume_no_longer_ready",
        },
    )
    record_human_notification(
        fake_workspace,
        task_name="fourclaw-engage",
        kind="agency_gate",
        message="review handoff created",
        summary={
            "execution": {"status": "pending_approval", "platform": "fourclaw", "blocked_reason": "agency_control_review_only"},
            "agency_control": {"effective_mode": "review_only", "reason": "supervised rollout"},
            "review_handoff": {"approval_id": "approval-workflow-resume", "title": "Review required: fourclaw engage"},
        },
        operational_agent_id="underling-chan",
    )
    r = client.get("/api/v1/workflows/scheduled-jobs", headers=_headers())
    assert r.status_code == 200
    jobs = r.json().get("jobs", [])
    social_job = next(j for j in jobs if j.get("job_id") == "social-media-underling")
    summary = social_job.get("review_handoff_summary") or {}
    assert summary.get("release_ready") is False
    assert "operational_resume_checkpoint_required" in (summary.get("release_blockers") or [])


def test_run_scheduled_job_blocks_when_lane_is_held(client, fake_workspace):
    agency_path = fake_workspace / "memory" / "automation" / "automation-underling-chan" / "agency_control.json"
    agency_path.write_text(
        json.dumps(
            {
                "mode": "held",
                "reason": "maintenance window",
                "updated_at": "2026-03-13T12:01:00Z",
                "updated_by": "operator",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    workflows_api.enforce_release_gate = lambda **kwargs: {"ok": True}
    r = client.post("/api/v1/workflows/scheduled-jobs/social-media-underling/run", headers=_headers())
    assert r.status_code == 423
    detail = r.json().get("detail") or {}
    assert detail.get("code") == "AGENCY_CONTROL_HELD"


def test_run_scheduled_job_uses_workflow_family_for_release_gate(client, fake_workspace, monkeypatch):
    called = {}

    def _gate(**kwargs):
        called.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(workflows_api, "enforce_release_gate", _gate)
    monkeypatch.setattr(
        workflows_api,
        "list_scheduled_jobs",
        lambda root: [
            {
                "job_id": "social-media-underling",
                "workflow_id": "social-media",
                "agency_control": {"effective_mode": "normal"},
                "continuity_recovery_readiness": {"status": "ready", "resume_permitted": True, "blocking": [], "cautions": []},
                "operational_resume_governance_summary": {"status": "caution"},
                "operational_resume_checkpoint": {"approved": False},
                "identity_restore_validation": {"required": False},
                "supervised_resume_validation": {"required": False},
                "bounded_autonomy_policy_summary": {"blockers": []},
            }
        ],
    )
    monkeypatch.setattr(
        workflows_api,
        "read_scheduled_dag",
        lambda root, job_id: {"dag": {"graph_id": "social_media_v1", "inputs": {}}},
    )
    monkeypatch.setattr(
        workflows_api,
        "submit_run",
        lambda dag: {"ok": True, "run_id": "run-social", "status": "queued"},
    )

    r = client.post("/api/v1/workflows/scheduled-jobs/social-media-underling/run", headers=_headers())
    assert r.status_code == 200
    assert called.get("workflow_family") == "social-media"
    assert called.get("target_id") == "social-media"


def test_run_scheduled_job_merges_scheduled_inputs_into_dag_submission(client, fake_workspace, monkeypatch):
    captured = {}

    monkeypatch.setattr(workflows_api, "enforce_release_gate", lambda **kwargs: {"ok": True})
    monkeypatch.setattr(
        workflows_api,
        "list_scheduled_jobs",
        lambda root: [
            {
                "job_id": "social-media-underling",
                "workflow_id": "social-media",
                "task_name": "fourclaw-engage",
                "inputs": {"workflow_id": "social-media", "task_name": "fourclaw-engage", "trigger": "realtime"},
                "agency_control": {"effective_mode": "normal"},
                "continuity_recovery_readiness": {"status": "ready", "resume_permitted": True, "blocking": [], "cautions": []},
                "operational_resume_governance_summary": {"status": "not_applicable"},
                "operational_resume_checkpoint": {"approved": False},
                "identity_restore_validation": {"required": False},
                "supervised_resume_validation": {"required": False, "validated": True},
                "bounded_autonomy_policy_summary": {"blockers": []},
            }
        ],
    )
    monkeypatch.setattr(
        workflows_api,
        "read_scheduled_dag",
        lambda root, job_id: {"dag": {"graph_id": "social_media_v1", "inputs": {"goal": ""}}},
    )
    monkeypatch.setattr(
        workflows_api,
        "submit_run",
        lambda dag: (captured.setdefault("dag", dag), {"ok": True, "run_id": "run-social", "status": "queued"})[1],
    )

    r = client.post("/api/v1/workflows/scheduled-jobs/social-media-underling/run", headers=_headers())
    assert r.status_code == 200
    dag_inputs = captured["dag"]["inputs"]
    assert dag_inputs["task_name"] == "fourclaw-engage"
    assert dag_inputs["trigger"] == "realtime"
    assert dag_inputs["scheduler_job_id"] == "social-media-underling"


def test_run_scheduled_job_returns_workflow_status_summary(client, fake_workspace, monkeypatch):
    monkeypatch.setattr(workflows_api, "enforce_release_gate", lambda **kwargs: {"ok": True})
    monkeypatch.setattr(
        workflows_api,
        "list_scheduled_jobs",
        lambda root: [
            {
                "job_id": "social-media-underling",
                "workflow_id": "social-media",
                "task_name": "fourclaw-engage",
                "agency_control": {"effective_mode": "normal"},
                "continuity_recovery_readiness": {"status": "ready", "resume_permitted": True, "blocking": [], "cautions": []},
                "operational_resume_governance_summary": {"status": "not_applicable"},
                "operational_resume_checkpoint": {"approved": False},
                "identity_restore_validation": {"required": False},
                "supervised_resume_validation": {"required": False, "validated": True},
                "bounded_autonomy_policy_summary": {"blockers": []},
            }
        ],
    )
    monkeypatch.setattr(
        workflows_api,
        "read_scheduled_dag",
        lambda root, job_id: {"dag": {"graph_id": "social_media_v1", "inputs": {}}},
    )
    monkeypatch.setattr(
        workflows_api,
        "submit_run",
        lambda dag: {"ok": True, "run_id": "run-social", "status": "queued"},
    )
    monkeypatch.setattr("app.services.review_handoff_summary.list_runs_index", lambda limit=500: [])

    r = client.post("/api/v1/workflows/scheduled-jobs/social-media-underling/run", headers=_headers())
    assert r.status_code == 200
    body = r.json()
    summary = body.get("workflow_status_summary") or {}
    assert body.get("run_id") == "run-social"
    assert summary.get("launch", {}).get("run_id") == "run-social"
    assert summary.get("latest_run_id") == "run-social"
    assert summary.get("latest_run_status") == "queued"
    assert summary.get("activity_href") == "#/activity?workflow_id=social-media"


def test_run_scheduled_job_loads_schedule_entry_inputs_when_summary_omits_them(client, fake_workspace, monkeypatch):
    captured = {}

    monkeypatch.setattr(workflows_api, "enforce_release_gate", lambda **kwargs: {"ok": True})
    monkeypatch.setattr(
        workflows_api,
        "list_scheduled_jobs",
        lambda root: [
            {
                "job_id": "social-media-bayman",
                "workflow_id": "social-media",
                "task_name": "newfoundland-bayman-fourclaw-engage",
                "agency_control": {"effective_mode": "normal"},
                "continuity_recovery_readiness": {"status": "ready", "resume_permitted": True, "blocking": [], "cautions": []},
                "operational_resume_governance_summary": {"status": "not_applicable"},
                "operational_resume_checkpoint": {"approved": False},
                "identity_restore_validation": {"required": False},
                "supervised_resume_validation": {"required": False, "validated": True},
                "bounded_autonomy_policy_summary": {"blockers": []},
            }
        ],
    )
    monkeypatch.setattr(
        workflows_api,
        "read_scheduled_dag",
        lambda root, job_id: {"dag": {"graph_id": "social_media_v1", "inputs": {"goal": ""}}},
    )
    monkeypatch.setattr(
        workflows_api,
        "submit_run",
        lambda dag: (captured.setdefault("dag", dag), {"ok": True, "run_id": "run-bayman", "status": "queued"})[1],
    )

    class _Entry:
        def __init__(self):
            self.job_id = "social-media-bayman"
            self.inputs = {
                "workflow_id": "social-media",
                "task_name": "newfoundland-bayman-fourclaw-engage",
                "trigger": "realtime",
            }

    class _State:
        entries = [_Entry()]

    monkeypatch.setattr("hg_realtime.scheduler.schedule_config.load_schedule", lambda root: _State())

    r = client.post("/api/v1/workflows/scheduled-jobs/social-media-bayman/run", headers=_headers())
    assert r.status_code == 200
    dag_inputs = captured["dag"]["inputs"]
    assert dag_inputs["task_name"] == "newfoundland-bayman-fourclaw-engage"
    assert dag_inputs["trigger"] == "realtime"
    assert dag_inputs["scheduler_job_id"] == "social-media-bayman"


def test_run_scheduled_job_allows_non_operational_knowledge_lane(client, fake_workspace, monkeypatch):
    monkeypatch.setattr(workflows_api, "enforce_release_gate", lambda **kwargs: {"ok": True})
    monkeypatch.setattr(
        workflows_api,
        "list_scheduled_jobs",
        lambda root: [
            {
                "job_id": "knowledge-research-auto",
                "workflow_id": None,
                "agency_control": None,
                "continuity_recovery_readiness": {"status": "ready", "resume_permitted": True, "blocking": [], "cautions": []},
                "operational_resume_governance_summary": {"status": "not_applicable"},
                "operational_resume_checkpoint": {"approved": False},
                "identity_restore_validation": {"required": False},
                "supervised_resume_validation": {"required": False, "validated": True},
                "bounded_autonomy_policy_summary": {"blockers": []},
            }
        ],
    )
    monkeypatch.setattr(
        workflows_api,
        "read_scheduled_dag",
        lambda root, job_id: {"dag": {"graph_id": "knowledge_research_auto_v1", "inputs": {}}},
    )
    monkeypatch.setattr(
        workflows_api,
        "submit_run",
        lambda dag: {"ok": True, "run_id": "run-knowledge", "status": "queued"},
    )

    r = client.post("/api/v1/workflows/scheduled-jobs/knowledge-research-auto/run", headers=_headers())
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    assert body.get("run_id") == "run-knowledge"


def test_run_scheduled_job_blocks_when_continuity_recovery_is_blocked(client, fake_workspace, monkeypatch):
    db_path = fake_workspace / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    keystore_repo.social_account_create(
        social_account_id="acct-underling-fourclaw",
        tenant_id="default",
        platform="fourclaw",
        account_alias="underling-fourclaw",
        entity_scope="underling-chan",
        persona_scope="underling_chan_operational",
        state="verified",
        db_path=str(db_path),
    )
    with get_connection(str(db_path)) as conn:
        conn.execute(
            """INSERT INTO browser_sessions (browser_session_id, tenant_id, entity_id, platform, state, started_at)
               VALUES (?, ?, ?, ?, ?, datetime('now'))""",
            ("session-bad", "default", "underling-chan", "fourclaw", "degraded"),
        )
        conn.execute(
            """INSERT INTO proof_artifacts (proof_id, related_kind, related_id, artifact_type, path, metadata_json, created_at)
               VALUES (?, 'browser_session', ?, 'session_degraded', ?, ?, datetime('now'))""",
            ("proof-bad", "session-bad", "missing_restart_critical_browser_artifacts", '{"reason":"missing_restart_critical_browser_artifacts"}'),
        )
    record_social_account_session_binding(
        "acct-underling-fourclaw",
        browser_session_id="session-bad",
        platform="fourclaw",
        tenant_id="default",
        entity_id="underling-chan",
        account_alias="underling-fourclaw",
        state="active",
    )
    workflows_api.enforce_release_gate = lambda **kwargs: {"ok": True}
    r = client.post("/api/v1/workflows/scheduled-jobs/social-media-underling/run", headers=_headers())
    assert r.status_code == 423
    detail = r.json().get("detail") or {}
    assert detail.get("code") == "CONTINUITY_RECOVERY_BLOCKED"


def test_run_scheduled_job_blocks_when_continuity_recovery_ack_is_required(client, fake_workspace):
    workflows_api.enforce_release_gate = lambda **kwargs: {"ok": True}
    r = client.post("/api/v1/workflows/scheduled-jobs/social-media-underling/run", headers=_headers())
    assert r.status_code == 423
    detail = r.json().get("detail") or {}
    assert detail.get("code") == "CONTINUITY_RECOVERY_ACK_REQUIRED"


def test_run_scheduled_job_blocks_when_post_rebuild_continuity_check_is_required(client, fake_workspace, monkeypatch):
    monkeypatch.setattr(
        workflows_api,
        "list_scheduled_jobs",
        lambda root: [
            {
                "job_id": "social-media-underling",
                "agency_control": {"effective_mode": "normal"},
                "continuity_recovery_readiness": {
                    "status": "caution",
                    "resume_permitted": False,
                    "cautions": ["post_rebuild_continuity_check_pending"],
                },
            }
        ],
    )
    monkeypatch.setattr(
        workflows_api,
        "read_scheduled_dag",
        lambda root, job_id: {"dag": {"graph_id": "social_media_v1", "inputs": {}}},
    )
    workflows_api.enforce_release_gate = lambda **kwargs: {"ok": True}
    r = client.post("/api/v1/workflows/scheduled-jobs/social-media-underling/run", headers=_headers())
    assert r.status_code == 423
    detail = r.json().get("detail") or {}
    assert detail.get("code") == "POST_REBUILD_CONTINUITY_CHECK_REQUIRED"


def test_run_scheduled_job_blocks_when_operational_resume_checkpoint_is_required(client, fake_workspace, monkeypatch):
    monkeypatch.setattr(
        workflows_api,
        "list_scheduled_jobs",
        lambda root: [
            {
                "job_id": "social-media-underling",
                "agency_control": {"effective_mode": "normal"},
                "continuity_recovery_readiness": {
                    "status": "ready",
                    "resume_permitted": True,
                    "cautions": [],
                    "blocking": [],
                },
                "operational_resume_governance_summary": {
                    "status": "ready",
                    "required_actions": [],
                },
                "operational_resume_checkpoint": {
                    "approved": False,
                    "invalidated": True,
                    "invalidated_reason": "operational_resume_no_longer_ready",
                },
            }
        ],
    )
    monkeypatch.setattr(
        workflows_api,
        "read_scheduled_dag",
        lambda root, job_id: {"dag": {"graph_id": "social_media_v1", "inputs": {}}},
    )
    workflows_api.enforce_release_gate = lambda **kwargs: {"ok": True}
    r = client.post("/api/v1/workflows/scheduled-jobs/social-media-underling/run", headers=_headers())
    assert r.status_code == 423
    detail = r.json().get("detail") or {}
    assert detail.get("code") == "OPERATIONAL_RESUME_CHECKPOINT_REQUIRED"


def test_run_scheduled_job_blocks_when_identity_restore_validation_is_required(client, fake_workspace, monkeypatch):
    monkeypatch.setattr(
        workflows_api,
        "list_scheduled_jobs",
        lambda root: [
            {
                "job_id": "social-media-underling",
                "agency_control": {"effective_mode": "normal"},
                "continuity_recovery_readiness": {"status": "ready", "resume_permitted": True},
                "operational_resume_governance_summary": {"status": "ready"},
                "operational_resume_checkpoint": {"approved": True},
                "identity_restore_validation": {"summary": "verify_identity_restore_continuity"},
                "supervised_resume_validation": {"status": "not_required"},
                "bounded_autonomy_policy_summary": {"blockers": ["identity_restore_validation_required"]},
            }
        ],
    )
    monkeypatch.setattr(
        workflows_api,
        "read_scheduled_dag",
        lambda root, job_id: {"dag": {"graph_id": "social_media_v1", "inputs": {}}},
    )
    workflows_api.enforce_release_gate = lambda **kwargs: {"ok": True}
    response = client.post("/api/v1/workflows/scheduled-jobs/social-media-underling/run", headers=_headers())
    assert response.status_code == 423
    assert response.json()["detail"]["code"] == "IDENTITY_RESTORE_VALIDATION_REQUIRED"


def test_run_scheduled_job_blocks_when_outbound_budget_is_exhausted(client, fake_workspace):
    agency_path = fake_workspace / "memory" / "automation" / "automation-underling-chan" / "agency_control.json"
    agency_path.write_text(
        json.dumps(
            {
                "mode": "normal",
                "reason": "daily cap reached",
                "updated_at": "2026-03-13T12:01:00Z",
                "updated_by": "operator",
                "daily_outbound_budget": 1,
                "outbound_actions_window_hours": 24,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    with patch(
        "app.services.operational_agency_control._recent_outbound_budget_usage",
        return_value=(1, "2026-03-13T00:00:00Z"),
    ):
        workflows_api.enforce_release_gate = lambda **kwargs: {"ok": True}
        r = client.post("/api/v1/workflows/scheduled-jobs/social-media-underling/run", headers=_headers())
    assert r.status_code == 423
    detail = r.json().get("detail") or {}
    assert detail.get("code") == "AGENCY_OUTBOUND_BUDGET_EXHAUSTED"


def test_list_scheduled_jobs_surfaces_outbound_budget_reset(client, fake_workspace):
    agency_path = fake_workspace / "memory" / "automation" / "automation-underling-chan" / "agency_control.json"
    agency_path.write_text(
        json.dumps(
            {
                "mode": "normal",
                "reason": "daily cap reached",
                "updated_at": "2026-03-13T12:01:00Z",
                "updated_by": "operator",
                "daily_outbound_budget": 1,
                "outbound_actions_window_hours": 24,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    with patch(
        "app.services.operational_agency_control._recent_outbound_budget_usage",
        return_value=(1, "2026-03-13T00:00:00Z"),
    ):
        r = client.get("/api/v1/workflows/scheduled-jobs", headers=_headers())
    assert r.status_code == 200
    jobs = r.json().get("jobs", [])
    social_job = next(j for j in jobs if j.get("job_id") == "social-media-underling")
    agency_control = social_job.get("agency_control") or {}
    assert agency_control.get("outbound_budget_exhausted") is True
    assert agency_control.get("outbound_budget_next_reset_at") == "2026-03-14T00:00:00Z"


def test_get_and_save_scheduled_job_dag(client, fake_workspace):
    get_r = client.get("/api/v1/workflows/scheduled-jobs/fourclaw-engage/dag", headers=_headers())
    assert get_r.status_code == 200
    dag = get_r.json().get("dag")
    assert dag.get("graph_id") == "fourclaw_engage_v1"

    dag["nodes"].append(
        {
            "id": "report",
            "type": "eval",
            "assigned_entity": "evaluator",
            "depends_on": ["engage"],
            "inputs": {"expression": 1, "outputs": ["done"]},
        }
    )

    put_r = client.put(
        "/api/v1/workflows/scheduled-jobs/fourclaw-engage/dag",
        json={"dag": dag},
        headers=_headers(),
    )
    assert put_r.status_code == 200
    body = put_r.json()
    assert body.get("ok") is True

    dag_path = fake_workspace / "memory" / "automation" / "dags" / "fourclaw_engage.json"
    saved = json.loads(dag_path.read_text(encoding="utf-8"))
    assert any(n.get("id") == "report" for n in saved.get("nodes", []))

    backups = list((fake_workspace / "memory" / "automation" / "dags").glob("fourclaw_engage.json.bak-*"))
    assert backups


def test_save_invalid_dag_rejected(client, fake_workspace):
    invalid = {"graph_id": "bad", "nodes": [{"id": "x"}]}
    r = client.put(
        "/api/v1/workflows/scheduled-jobs/fourclaw-engage/dag",
        json={"dag": invalid},
        headers=_headers(),
    )
    assert r.status_code == 400
