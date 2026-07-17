"""
Zero-budget validation seed.

Creates a deterministic local dataset that exercises the one-brain product shape
without any paid provider calls.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_gateway.db import get_connection
from hg_gateway.operational_state_ledger import save_operational_json_state
from operator_console.server.app.services.run_index_db import upsert_run

SEED_MARKER_KEY = "zero_budget_validation_seed"
SEED_OVERRIDE_PATH = Path("memory/automation/job_registry.json")


@dataclass(frozen=True)
class SeedTask:
    task_name: str
    session_target: str
    platform: str | None
    mode: str
    entity_title: str
    current_state: str
    last_wake_at: str
    last_activity_at: str
    run_id: str
    graph_id: str
    chat_id: str
    chat_title: str
    user_message: str
    assistant_message: str
    approval_id: str | None = None
    approval_title: str | None = None
    approval_summary: str | None = None
    approval_risk: str = "low"
    approval_status: str = "pending"
    reflection_id: str | None = None
    reflection_title: str | None = None
    reflection_summary: str | None = None
    recovery_status: str | None = None
    drift_root_id: str | None = None


ZERO_BUDGET_TASKS: list[SeedTask] = [
    SeedTask(
        task_name="zero-budget-state-sheet",
        session_target="automation-zero-budget-state-sheet",
        platform=None,
        mode="state-sheet",
        entity_title="State Sheet",
        current_state="healthy",
        last_wake_at="2026-03-25T08:00:00Z",
        last_activity_at="2026-03-25T08:12:00Z",
        run_id="zero-budget-state-sheet-run",
        graph_id="zero-budget-state-sheet",
        chat_id="zero-budget-state-sheet-chat",
        chat_title="State sheet conversation",
        user_message="What is true right now?",
        assistant_message="The current state is healthy, continuity is intact, and the next action is to launch work from this snapshot.",
    ),
    SeedTask(
        task_name="zero-budget-workflow",
        session_target="automation-zero-budget-workflow",
        platform=None,
        mode="workflow",
        entity_title="Workflow Lineage",
        current_state="working",
        last_wake_at="2026-03-25T08:05:00Z",
        last_activity_at="2026-03-25T08:15:00Z",
        run_id="zero-budget-workflow-run",
        graph_id="zero-budget-workflow",
        chat_id="zero-budget-workflow-chat",
        chat_title="Workflow launch conversation",
        user_message="Launch the workflow and show me the result path.",
        assistant_message="The workflow launched, the run is linked, and the next action is to inspect the run detail timeline.",
    ),
    SeedTask(
        task_name="zero-budget-proof",
        session_target="automation-zero-budget-proof",
        platform=None,
        mode="proof",
        entity_title="Proof and Provenance",
        current_state="review",
        last_wake_at="2026-03-25T08:03:00Z",
        last_activity_at="2026-03-25T08:18:00Z",
        run_id="zero-budget-proof-run",
        graph_id="zero-budget-proof",
        chat_id="zero-budget-proof-chat",
        chat_title="Why-this-reply conversation",
        user_message="Why did this reply happen?",
        assistant_message="The reply is linked to source memory, policy input, and evidence. Open the provenance panel for the full chain.",
        reflection_id="zero-budget-reflection-1",
        reflection_title="Reflection: explanation quality",
        reflection_summary="The explanation spine should expose source memory, policy, and evidence before any deeper detail.",
    ),
    SeedTask(
        task_name="zero-budget-recovery",
        session_target="automation-zero-budget-recovery",
        platform=None,
        mode="recovery",
        entity_title="Recovery",
        current_state="recovery-needed",
        last_wake_at="2026-03-25T07:58:00Z",
        last_activity_at="2026-03-25T08:20:00Z",
        run_id="zero-budget-recovery-run",
        graph_id="zero-budget-recovery",
        chat_id="zero-budget-recovery-chat",
        chat_title="Recovery conversation",
        user_message="Show the recovery path and what changed.",
        assistant_message="The recovery is anchored in the main timeline and the operator can continue from the recovery result view.",
        recovery_status="blocked",
        drift_root_id="zero-budget-root",
    ),
    SeedTask(
        task_name="zero-budget-governance",
        session_target="automation-zero-budget-governance",
        platform=None,
        mode="governance",
        entity_title="Governance",
        current_state="watch",
        last_wake_at="2026-03-25T07:50:00Z",
        last_activity_at="2026-03-25T08:22:00Z",
        run_id="zero-budget-governance-run",
        graph_id="zero-budget-governance",
        chat_id="zero-budget-governance-chat",
        chat_title="Governance conversation",
        user_message="What governance signals should I inspect?",
        assistant_message="Drift, mimicry, continuity, and approvals are visible and ready for operator review.",
        approval_id="zero-budget-approval-1",
        approval_title="Approve launch sequence",
        approval_summary="Approve the launch after checking continuity and provenance.",
        approval_risk="medium",
        approval_status="approved",
        drift_root_id="zero-budget-root",
    ),
]


def _workspace_root(workspace_root: Path | None = None) -> Path:
    if workspace_root is not None:
        return Path(workspace_root)
    try:
        from hg_lib.config import get_workspace_root

        return get_workspace_root()
    except Exception:
        return Path.cwd()


def _seed_marker_path(root: Path) -> Path:
    return root / "memory" / "automation" / "zero_budget_validation_seed.json"


def _job_registry_path(root: Path) -> Path:
    return root / SEED_OVERRIDE_PATH


def _load_existing_job_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _write_job_registry(root: Path) -> None:
    path = _job_registry_path(root)
    existing = _load_existing_job_registry(path)
    merged = dict(existing)
    for task in ZERO_BUDGET_TASKS:
        merged[task.task_name] = {
            "job_id": task.task_name,
            "session_target": task.session_target,
            "platform": task.platform,
            "mode": task.mode,
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(merged, indent=2, sort_keys=True), encoding="utf-8")


def _replace_row(conn: Any, table: str, where_clause: str, where_params: tuple[Any, ...], sql: str, params: tuple[Any, ...]) -> None:
    conn.execute(f"DELETE FROM {table} WHERE {where_clause}", where_params)
    conn.execute(sql, params)


def _seed_chat_and_related(conn: Any, root: Path, task: SeedTask) -> dict[str, Any]:
    now = task.last_activity_at
    _replace_row(
        conn,
        "chats",
        "tenant_id = ? AND chat_id = ?",
        ("default", task.chat_id),
        """
        INSERT INTO chats (
            chat_id, title, updated_at, unread_count, tenant_id,
            fingerprint_id, skin_id, steering_profile_ids, swarm_run_id, swarm_role
        ) VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?, ?)
        """,
        (
            task.chat_id,
            task.chat_title,
            now,
            "default",
            task.task_name,
            task.platform,
            json.dumps([task.task_name]),
            task.run_id,
            task.mode,
        ),
    )
    conn.execute("DELETE FROM messages WHERE tenant_id = ? AND chat_id = ?", ("default", task.chat_id))
    conn.execute("DELETE FROM agents WHERE chat_id = ?", (task.chat_id,))
    conn.execute(
        """
        INSERT INTO messages (
            message_id, chat_id, role, created_at, content, agent_id, tool_name, tool_payload, tool_result,
            approvals_required, tenant_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"{task.chat_id}-user",
            task.chat_id,
            "user",
            task.last_wake_at,
            task.user_message,
            task.task_name,
            None,
            None,
            None,
            None,
            "default",
        ),
    )
    conn.execute(
        """
        INSERT INTO messages (
            message_id, chat_id, role, created_at, content, agent_id, tool_name, tool_payload, tool_result,
            approvals_required, tenant_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"{task.chat_id}-assistant",
            task.chat_id,
            "assistant",
            task.last_activity_at,
            task.assistant_message,
            task.task_name,
            None,
            None,
            None,
            None,
            "default",
        ),
    )
    conn.execute("DELETE FROM agents WHERE chat_id = ? AND agent_id = ?", (task.chat_id, task.task_name))
    conn.execute(
        """
        INSERT INTO agents (chat_id, agent_id, label, status, parent_agent_id, tenant_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (task.chat_id, task.task_name, task.entity_title, "idle", None, "default"),
    )
    conn.execute("DELETE FROM events WHERE tenant_id = ? AND chat_id = ?", ("default", task.chat_id))
    conn.execute(
        "INSERT INTO events (tenant_id, chat_id, event_type, payload, created_at) VALUES (?, ?, ?, ?, ?)",
        (
            "default",
            task.chat_id,
            "workflow.launch",
            json.dumps({"task_name": task.task_name, "run_id": task.run_id}, sort_keys=True),
            task.last_activity_at,
        ),
    )
    conn.execute(
        "INSERT INTO events (tenant_id, chat_id, event_type, payload, created_at) VALUES (?, ?, ?, ?, ?)",
        (
            "default",
            task.chat_id,
            "proof.provenance",
            json.dumps({"message_id": f"{task.chat_id}-assistant", "summary": "source memory, policy, and evidence"}, sort_keys=True),
            task.last_activity_at,
        ),
    )
    conn.execute("DELETE FROM turn_provenance WHERE tenant_id = ? AND message_id = ?", ("default", f"{task.chat_id}-assistant"))
    conn.execute(
        """
        INSERT INTO turn_provenance (
            message_id, tenant_id, prompt_id, model_config_id, sampling_params_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            f"{task.chat_id}-assistant",
            "default",
            "default",
            "default",
            json.dumps({"scenario": task.mode, "temperature": 0.0, "max_tokens": 256}, sort_keys=True),
            task.last_activity_at,
        ),
    )
    if task.approval_id:
        conn.execute("DELETE FROM approval_chat_lock WHERE approval_id = ?", (task.approval_id,))
        conn.execute("DELETE FROM approvals WHERE tenant_id = ? AND id = ?", ("default", task.approval_id))
        conn.execute(
            """
            INSERT INTO approvals (
                id, created_at, resolved_at, status, kind, title, summary, risk,
                requested_by, payload, resolution_note, chat_id, assigned_principal_id, tenant_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.approval_id,
                task.last_wake_at,
                task.last_activity_at if task.approval_status != "pending" else None,
                task.approval_status,
                "workflow",
                task.approval_title,
                task.approval_summary,
                task.approval_risk,
                "demo-operator",
                json.dumps({"task_name": task.task_name, "run_id": task.run_id}, sort_keys=True),
                "approved for zero-budget demo" if task.approval_status == "approved" else None,
                task.chat_id,
                "demo-operator",
                "default",
            ),
        )
        conn.execute(
            "INSERT OR REPLACE INTO approval_chat_lock (approval_id, chat_id) VALUES (?, ?)",
            (task.approval_id, task.chat_id),
        )
    return {"chat_id": task.chat_id, "run_id": task.run_id}


def _seed_states(root: Path, task: SeedTask) -> None:
    session_target = task.session_target
    namespace_dir = root / "memory" / "automation" / session_target
    namespace_dir.mkdir(parents=True, exist_ok=True)
    wake_receipt = {
        "timestamp": task.last_wake_at,
        "wake_completed_at": task.last_wake_at,
        "wake_packet": task.user_message,
        "wake_packet_hash": f"{task.task_name}-wake-packet",
        "dag_inputs": {
            "goal": task.assistant_message,
            "task_name": task.task_name,
            "run_id": task.run_id,
            "chat_id": task.chat_id,
        },
    }
    cadence_request = {
        "requested_at": task.last_wake_at,
        "not_before": task.last_wake_at,
        "reason": f"zero-budget validation for {task.mode}",
        "requested_duration_minutes": 30,
        "minimum_sleep_minutes": 30,
        "scheduler_job_id": task.task_name if task.mode == "workflow" else None,
    }
    for filename, payload in (
        ("wake_receipt.json", wake_receipt),
        ("last_sleep_summary.json", {"timestamp": task.last_activity_at, "summary": task.current_state, "mode": task.mode}),
        ("cadence_request.json", cadence_request),
        ("summary_7d.json", {"summary": task.current_state, "updated_at": task.last_activity_at, "mode": task.mode}),
        ("initialization_memo.json", {"summary": task.entity_title, "updated_at": task.last_wake_at}),
    ):
        (namespace_dir / filename).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    continuity_payload = {
        "initialization_memo_present": True,
        "wake_receipt_present": True,
        "sleep_summary_present": True,
        "initialization_memo_path": f"memory/automation/{session_target}/initialization_memo.json",
        "last_wake_at": task.last_wake_at,
        "wake_receipt_recorded_at": task.last_wake_at,
        "last_sleep_at": task.last_activity_at,
        "sleep_summary_recorded_at": task.last_activity_at,
        "wake_receipt": wake_receipt,
    }
    save_operational_json_state(root, state_key=f"identity_continuity_state:{session_target}", payload=continuity_payload)
    save_operational_json_state(
        root,
        state_key=f"operational_cadence_request:{session_target}",
        payload=cadence_request,
    )
    save_operational_json_state(
        root,
        state_key=f"continuity_recovery_ack:{session_target}",
        payload={
            "acknowledged_at": task.last_activity_at,
            "acknowledged_by": "demo-operator",
            "note": "bounded resume acknowledged",
            "incident_status": "recovered" if task.recovery_status == "recovered" else "clean",
            "identity_status": "healthy",
            "blocking": [],
            "cautions": [] if task.recovery_status == "recovered" else ["identity_continuity_partial"],
            "summary": task.entity_title,
        },
    )
    save_operational_json_state(
        root,
        state_key=f"identity_restore_validation:{session_target}",
        payload={
            "restore_recorded_at": task.last_wake_at,
            "restore_recorded_by": "demo-operator",
            "restore_note": "restore path seeded for zero-budget validation",
            "verified_at": task.last_activity_at,
            "verified_by": "demo-operator",
            "verification_note": "validated locally",
        },
    )
    save_operational_json_state(
        root,
        state_key=f"post_rebuild_continuity_check:{session_target}",
        payload={
            "verification_required": True,
            "verified": True,
            "verified_at": task.last_activity_at,
            "verified_by": "demo-operator",
            "status": "verified",
            "summary": "post rebuild continuity verified",
        },
    )
    save_operational_json_state(
        root,
        state_key=f"supervised_resume_validation:{session_target}",
        payload={
            "required": True,
            "validated": True,
            "validated_at": task.last_activity_at,
            "validated_by": "demo-operator",
            "status": "validated",
            "summary": "supervised resume validated",
        },
    )
    save_operational_json_state(
        root,
        state_key=f"continuity_repair_observation:{session_target}",
        payload={
            "observation_required": True,
            "observation_complete": True,
            "latest_observed_at": task.last_activity_at,
            "observed_by": "demo-operator",
            "status": "observed",
            "summary": "first post repair cycle observed",
        },
    )
    save_operational_json_state(
        root,
        state_key=f"operational_resume_checkpoint:{session_target}",
        payload={
            "checkpoint_id": f"{task.task_name}-checkpoint",
            "summary": task.current_state,
            "valid": True,
            "invalidated_reason": None,
            "created_at": task.last_wake_at,
            "updated_at": task.last_activity_at,
        },
    )
    save_operational_json_state(
        root,
        state_key=f"identity_resume_procedure:{session_target}",
        payload={
            "open_steps": ["launch_work", "inspect_lineage"] if task.mode == "workflow" else ["inspect_state"],
            "completed_steps": ["record_wake_receipt"],
            "summary": "seeded walkthrough support",
        },
    )
    save_operational_json_state(
        root,
        state_key=f"identity_resume_observation:{session_target}",
        payload={
            "observation_required": True,
            "observation_complete": True,
            "summary": "first identity resume cycle observed",
        },
    )
    save_operational_json_state(
        root,
        state_key=f"identity_resume_closeout:{session_target}",
        payload={
            "closed": True,
            "closed_at": task.last_activity_at,
            "summary": "closeout complete",
        },
    )
    save_operational_json_state(
        root,
        state_key=f"operational_resume_governance_summary:{session_target}",
        payload={
            "required_actions": ["review_timeline", "review_provenance"],
            "summary": "operator review required",
        },
    )
    save_operational_json_state(
        root,
        state_key=f"action_rationale_summary:{session_target}",
        payload={
            "current_goal": task.current_state,
            "wake_receipt": wake_receipt,
            "summary": f"{task.entity_title} is current and explainable",
        },
    )
    save_operational_json_state(
        root,
        state_key=f"presence_initiative_summary:{session_target}",
        payload={
            "next_earliest_wake_at": task.last_activity_at,
            "summary": "presence check recorded",
            "cadence_request": cadence_request,
        },
    )


def _seed_review_notifications(root: Path, tasks: list[SeedTask]) -> None:
    from hg_core.human_notifications import record_human_notification

    for task in tasks:
        if not task.approval_id:
            continue
        record_human_notification(
            root,
            task_name=task.task_name,
            kind="agency_gate",
            message=f"{task.entity_title} approval is ready for review.",
            summary={
                "review_handoff": {
                    "approval_id": task.approval_id,
                    "title": task.approval_title,
                    "status": task.approval_status,
                    "draft_artifact": f"{task.task_name}-draft",
                    "resolution_context": {
                        "rationale": task.approval_summary,
                        "release_scope": "zero-budget validation",
                        "followup_expectation": "inspect the review trail after the demo",
                        "followup_window_hours": 24,
                    },
                },
                "execution": {
                    "status": "approved" if task.approval_status == "approved" else task.approval_status,
                    "blocked_reason": None,
                },
            },
            transport="log_only",
            recipient="The Reverend",
            tenant_id="default",
            operational_agent_id=task.task_name,
        )


def _seed_runs(tasks: list[SeedTask]) -> None:
    for task in tasks:
        upsert_run(
            {
                "run_id": task.run_id,
                "graph_id": task.graph_id,
                "status": "completed" if task.mode != "recovery" else "blocked",
                "started_at": task.last_wake_at,
                "ended_at": task.last_activity_at,
                "run_dir": f"/tmp/zero-budget/{task.run_id}",
                "correlation_id": task.chat_id,
            }
        )


def _seed_reflections(conn: Any, root: Path, tasks: list[SeedTask]) -> list[str]:
    created: list[str] = []
    conn.execute(
        """
        INSERT OR IGNORE INTO artifact_registry_classes (
            class_key, title, root_path, glob_pattern, description,
            editable, versioned, import_required, archive_policy, metadata_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            "reflection",
            "Reflection",
            "memory/reflections",
            "memory/reflections/*.json",
            "Reflection review artifacts",
            0,
            1,
            0,
            "retain",
            "{}",
        ),
    )
    for task in tasks:
        if not task.reflection_id:
            continue
        payload = {
            "artifact_id": task.reflection_id,
            "class_key": "reflection",
            "title": task.reflection_title or task.entity_title,
            "summary": task.reflection_summary or "reflection artifact",
            "findings_json": {
                "summary": task.reflection_summary or "reflection artifact",
                "next_action": "review on the main timeline",
            },
            "source_event_ids": [f"{task.chat_id}-event"],
            "source_memory_ids": [task.session_target],
            "source_links": [{"label": "timeline", "href": "#/timeline"}],
            "confidence": 0.92,
            "verification_status": "promoted",
            "reviewed_by": "demo-operator",
            "promoted_at": task.last_activity_at,
            "created_at": task.last_activity_at,
            "updated_at": task.last_activity_at,
        }
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        source_sha = __import__("hashlib").sha256(payload_json.encode("utf-8")).hexdigest()
        file_path = f"memory/reflections/{task.reflection_id}.json"
        version_id = f"artifact-version:{task.reflection_id}:1"
        conn.execute(
            """
            INSERT OR REPLACE INTO artifact_registry_entries (
                artifact_id, class_key, file_path, title, source_sha256, source_size_bytes, source_mtime,
                content_kind, mime_type, current_version_id, latest_status, active, imported_at, updated_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (
                task.reflection_id,
                "reflection",
                file_path,
                task.reflection_title or task.entity_title,
                source_sha,
                len(payload_json.encode("utf-8")),
                task.last_activity_at,
                "reflection",
                "application/json",
                version_id,
                "promoted",
                task.last_activity_at,
                task.last_activity_at,
                payload_json,
            ),
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO artifact_registry_versions (
                version_id, artifact_id, version_number, state, file_path, class_key, content_kind, mime_type,
                source_sha256, source_size_bytes, source_mtime, author_id, change_summary, created_at, updated_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version_id,
                task.reflection_id,
                1,
                "promoted",
                file_path,
                "reflection",
                "reflection",
                "application/json",
                source_sha,
                len(payload_json.encode("utf-8")),
                task.last_activity_at,
                "demo-operator",
                "seeded zero-budget reflection artifact",
                task.last_activity_at,
                task.last_activity_at,
                payload_json,
            ),
        )
        created.append(task.reflection_id)
    return created


def _seed_governance(conn: Any, root: Path, tasks: list[SeedTask]) -> dict[str, Any]:
    root_id = "zero-budget-root"
    now = tasks[0].last_wake_at if tasks else "2026-03-25T08:00:00Z"
    conn.execute(
        """
        INSERT OR REPLACE INTO constitutional_roots (
            root_id, workflow_family, title, root_goal, owner_id, accountable_actor,
            material_constraints_json, approved_subgoals_json, policy_version_id, status,
            drift_severity, last_checkpoint_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            root_id,
            "zero-budget",
            "Zero budget validation root",
            "Validate the one-brain product shape without paid calls.",
            "demo-operator",
            "demo-operator",
            json.dumps(["safe local only", "no paid provider use"], sort_keys=True),
            json.dumps(["timeline spine", "provenance default", "recovery anchored"], sort_keys=True),
            None,
            "active",
            "watch",
            None,
            now,
            now,
        ),
    )
    drift_event_id = "zero-budget-drift-1"
    conn.execute(
        """
        INSERT OR REPLACE INTO constitutional_drift_events (
            drift_event_id, root_id, severity, summary, details_json, acknowledged_at, acknowledged_by,
            override_status, created_at, receipt_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            drift_event_id,
            root_id,
            "watch",
            "Seeded drift baseline for zero-budget validation",
            json.dumps({"source": "zero_budget_seed", "scope": "local validation"}, sort_keys=True),
            None,
            None,
            None,
            now,
            None,
        ),
    )
    return {"root_id": root_id}


def seed_zero_budget_validation(workspace_root: Path | None = None) -> dict[str, Any]:
    root = _workspace_root(workspace_root)
    marker_path = _seed_marker_path(root)
    if marker_path.exists():
        try:
            payload = json.loads(marker_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and payload.get("version") == 1:
                return payload
        except Exception:
            pass

    _write_job_registry(root)
    summary: dict[str, Any] = {"version": 1, "workspace_root": str(root)}
    with get_connection() as conn:
        summary["governance"] = _seed_governance(conn, root, ZERO_BUDGET_TASKS)
        summary["reflections"] = _seed_reflections(conn, root, ZERO_BUDGET_TASKS)
        summary["runs"] = []
        summary["chats"] = []
        for task in ZERO_BUDGET_TASKS:
            chat_and_run = _seed_chat_and_related(conn, root, task)
            summary["chats"].append(chat_and_run["chat_id"])
            summary["runs"].append(chat_and_run["run_id"])
        conn.commit()

    for task in ZERO_BUDGET_TASKS:
        _seed_states(root, task)
    _seed_runs(ZERO_BUDGET_TASKS)
    _seed_review_notifications(root, ZERO_BUDGET_TASKS)
    summary["task_names"] = [task.task_name for task in ZERO_BUDGET_TASKS]
    save_operational_json_state(
        root,
        state_key=SEED_MARKER_KEY,
        payload={
            **summary,
            "reflections": summary["reflections"],
        },
    )
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary
