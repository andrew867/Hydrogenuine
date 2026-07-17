"""Services for visual editing of scheduled DAG job files. Single source: DAG_JOB_REGISTRY (Phase 10)."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from hg_core.job_registry import get_operational_agent_id

from .continuity_incident_summary import build_continuity_incident_summary
from .continuity_recovery_ack import load_continuity_recovery_ack
from .continuity_repair_observation import build_continuity_repair_observation
from .continuity_repair_plan import build_continuity_repair_plan
from .continuity_recovery_readiness import build_continuity_recovery_readiness
from .identity_restore_validation import load_identity_restore_validation
from .identity_continuity_summary import build_identity_continuity_summary
from .identity_resume_closeout import load_identity_resume_closeout
from .identity_resume_observation import build_identity_resume_observation
from .identity_resume_procedure import build_identity_resume_procedure
from .bounded_autonomy_policy import build_bounded_autonomy_policy_summary
from .crew_dynamics_summary import build_crew_dynamics_summary
from .commitment_summary import build_commitment_summary
from .confidence_summary import build_confidence_summary
from .operational_resume_governance_summary import build_operational_resume_governance_summary
from .operational_resume_checkpoint import ensure_operational_resume_checkpoint_validity
from .post_rebuild_continuity_check import load_post_rebuild_continuity_check
from .presence_initiative_summary import build_presence_initiative_summary
from .review_handoff_summary import build_review_handoff_summary, build_workflow_status_summary
from .self_model_summary import build_self_model_summary
from .social_account_summary import build_social_account_operator_summary
from .supervised_resume_validation import load_supervised_resume_validation
from .validator_adapter import validate

# Fallback when DAG_JOB_REGISTRY cannot be loaded (e.g. no workspace/scripts). Must match scripts/dag_runtime_jobs.py.
SCHEDULED_JOB_TO_DAG: dict[str, str] = {
    "social-media": "memory/automation/dags/social_media.json",
    "fourclaw-auto-post-cadence": "memory/automation/dags/fourclaw_auto_post.json",
    "fourclaw-engage": "memory/automation/dags/fourclaw_engage.json",
    "moltbook-auto-post": "memory/automation/dags/moltbook_auto_post.json",
    "moltbook-engage": "memory/automation/dags/moltbook_engage.json",
    "aichan-auto-post": "memory/automation/dags/aichan_auto_post.json",
    "aichan-engage": "memory/automation/dags/aichan_engage.json",
    "agentchan-auto-post": "memory/automation/dags/agentchan_auto_post.json",
    "agentchan-engage": "memory/automation/dags/agentchan_engage.json",
    "rcmp-job-search-monitor": "memory/automation/dags/job_search_degree_agnostic_agent_runtime_v1.json",
    "knowledge-research-auto": "memory/automation/dags/knowledge_research_auto.json",
    "knowledge-research-auto-v2": "memory/automation/dags/knowledge_research_auto_v2.json",
    "overseer-monitor": "memory/automation/dags/overseer_monitor.json",
    "moltstack-draft": "memory/automation/dags/moltstack_draft.json",
    "moltstack-publish": "memory/automation/dags/moltstack_publish.json",
    "memory-maintenance": "memory/automation/dags/memory_maintenance.json",
}


def _get_registry(workspace_root: Path | None) -> dict[str, Any] | None:
    """Load DAG_JOB_REGISTRY from scripts/dag_runtime_jobs. Returns job_id -> DagRuntimeJob (with .dag_path)."""
    root = workspace_root
    if not root:
        try:
            from hg_lib.config import get_workspace_root
            root = get_workspace_root()
        except Exception:
            return None
    if not root:
        return None
    scripts_dir = root / "scripts"
    if not scripts_dir.is_dir():
        return None
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        from dag_runtime_jobs import DAG_JOB_REGISTRY  # type: ignore[import-untyped]
        return DAG_JOB_REGISTRY
    except Exception:
        return None


def _job_to_dag_path(job: Any) -> str:
    return getattr(job, "dag_path", "") or ""


def _get_job_to_dag(workspace_root: Path | None) -> dict[str, str]:
    """Single source: DAG_JOB_REGISTRY when available, else SCHEDULED_JOB_TO_DAG."""
    reg = _get_registry(workspace_root)
    if reg is not None:
        merged = SCHEDULED_JOB_TO_DAG.copy()
        merged.update({jid: _job_to_dag_path(job) for jid, job in reg.items() if _job_to_dag_path(job)})
        return merged
    return SCHEDULED_JOB_TO_DAG.copy()


def _resolve_path(workspace_root: Path, rel_path: str) -> Path:
    root = workspace_root.resolve()
    target = (root / rel_path).resolve()
    if root not in target.parents and target != root:
        raise ValueError("resolved DAG path escaped workspace")
    return target


def _schedule_alias_to_workflow_id(workspace_root: Path, job_id: str) -> str | None:
    try:
        from hg_realtime.scheduler.schedule_config import load_schedule

        state = load_schedule(workspace_root)
    except Exception:
        return None
    for entry in state.entries:
        if entry.job_id != job_id:
            continue
        workflow_id = str((entry.inputs or {}).get("workflow_id") or "").strip()
        return workflow_id or None
    return None


def _cadence_state_for_job(workspace_root: Path, job_id: str, task_name: str) -> dict[str, Any] | None:
    if not task_name:
        return None
    try:
        from hg_core.job_registry import get_operational_agent_id
        from hg_realtime.scheduler.schedule_config import ScheduleEntry, cadence_override_path_for_entry
    except Exception:
        return None
    entry = ScheduleEntry(job_id=job_id, interval_minutes=1, inputs={"task_name": task_name})
    path = cadence_override_path_for_entry(entry, workspace_root)
    if path is None or not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return {
        "operational_agent_id": str(get_operational_agent_id(task_name) or "").strip(),
        "path": str(path),
        "request": payload,
    }


def _agency_control_state_for_job(workspace_root: Path, task_name: str) -> dict[str, Any] | None:
    if not task_name:
        return None
    try:
        from .operational_agency_control import build_agency_control_summary
        from hg_core.job_registry import get_operational_agent_id, get_operational_session_target
    except Exception:
        return None
    return build_agency_control_summary(
        root=workspace_root,
        binding={
            "operational_agent_id": get_operational_agent_id(task_name),
            "operational_session_target": get_operational_session_target(task_name),
        },
        session_target=task_name,
    )


def _runtime_tenant_id() -> str:
    import os

    return (os.getenv("HG_OPERATOR_TENANT_ID") or os.getenv("HG_DEFAULT_TENANT_ID") or "default").strip() or "default"


def _assigned_social_accounts_for_job(task_name: str) -> list[dict[str, Any]]:
    if not task_name:
        return []
    try:
        from hg_core.job_registry import get_operational_binding
        from hg_gateway import keystore_repo
    except Exception:
        return []
    binding = get_operational_binding(task_name) or {}
    operational_agent_id = str(binding.get("operational_agent_id") or "").strip()
    platform = str(binding.get("platform") or "").strip()
    fingerprint_id = str(binding.get("fingerprint_id") or "").strip()
    if not operational_agent_id or not platform:
        return []
    try:
        accounts = keystore_repo.social_account_list(tenant_id=_runtime_tenant_id(), platform=platform)
    except Exception:
        return []
    matches: list[dict[str, Any]] = []
    for account in accounts:
        entity_scope = str(account.get("entity_scope") or "").strip()
        persona_scope = str(account.get("persona_scope") or "").strip()
        if entity_scope != operational_agent_id and (not fingerprint_id or persona_scope != fingerprint_id):
            continue
        matches.append(
            {
                "social_account_id": account.get("social_account_id"),
                "account_alias": account.get("account_alias"),
                "platform": account.get("platform"),
                "state": account.get("state"),
                **build_social_account_operator_summary(str(account.get("social_account_id") or ""), account=account),
            }
        )
    return matches


def _operational_binding_for_job(task_name: str) -> dict[str, Any]:
    if not task_name:
        return {}
    try:
        from hg_core.job_registry import get_operational_binding
    except Exception:
        return {}
    binding = get_operational_binding(task_name)
    return binding if isinstance(binding, dict) else {}


def _release_gate_summary_for_job(job_id: str, workflow_id: str | None) -> dict[str, Any]:
    try:
        from hg_core.gate import get_release_gate_status
    except Exception:
        return {"ok": False, "blocked": True, "reason": "release gate unavailable", "code": "gate_unavailable"}
    workflow_family = str(workflow_id or job_id or "").strip() or job_id
    return get_release_gate_status(
        workflow_family=workflow_family,
        target_kind="workflow",
        target_id=workflow_family,
    )


def _identity_continuity_for_job(workspace_root: Path, task_name: str) -> dict[str, Any]:
    if not task_name:
        return {
            "status": "not_applicable",
            "continuity_anchor": None,
            "task_name": None,
            "session_target": None,
            "operational_session_target": None,
            "memory_namespace": None,
            "fingerprint_id": None,
            "compatible_agent_ids": [],
            "compatible_session_targets": [],
            "initialization_memo_present": False,
            "initialization_memo_path": None,
            "wake_receipt_present": False,
            "sleep_summary_present": False,
            "last_wake_at": None,
            "last_sleep_at": None,
        }
    try:
        from hg_core.job_registry import get_operational_binding
    except Exception:
        return build_identity_continuity_summary(root=workspace_root, task_name=task_name, session_target=task_name)
    binding = get_operational_binding(task_name) or {}
    session_target = str(binding.get("operational_session_target") or task_name).strip() or task_name
    return build_identity_continuity_summary(
        root=workspace_root,
        task_name=task_name,
        session_target=session_target,
        binding=binding,
    )


def list_scheduled_jobs(workspace_root: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    job_to_dag = _get_job_to_dag(workspace_root)
    by_job: dict[str, Any] = {}
    scheduled_job_ids: set[str] | None = None
    try:
        from hg_realtime.scheduler.schedule_config import load_schedule

        state = load_schedule(workspace_root)
        if state.entries:
            scheduled_job_ids = {entry.job_id for entry in state.entries}
            by_job = {entry.job_id: entry for entry in state.entries}
    except Exception:
        scheduled_job_ids = None
    if scheduled_job_ids is None:
        job_ids = sorted(job_to_dag.keys())
    else:
        job_ids = sorted(scheduled_job_ids)
    for job_id in job_ids:
        dag_rel = job_to_dag.get(job_id)
        entry = by_job.get(job_id)
        if not dag_rel:
            workflow_id = _schedule_alias_to_workflow_id(workspace_root, job_id)
            if workflow_id:
                dag_rel = job_to_dag.get(workflow_id)
        if not dag_rel:
            continue
        workflow_id = str((entry.inputs or {}).get("workflow_id") or "").strip() if entry else ""
        task_name = str((entry.inputs or {}).get("task_name") or "").strip() if entry else ""
        task_binding = _operational_binding_for_job(task_name)
        has_operational_lane = bool(task_name and (task_binding.get("operational_agent_id") or task_binding.get("operational_session_target")))
        dag_path = _resolve_path(workspace_root, dag_rel)
        graph_id = None
        node_count = None
        exists = dag_path.exists()
        if exists:
            try:
                payload = json.loads(dag_path.read_text(encoding="utf-8"))
                graph_id = payload.get("graph_id")
                nodes = payload.get("nodes", [])
                node_count = len(nodes) if isinstance(nodes, list) else None
            except (OSError, json.JSONDecodeError):
                pass
        agency_control = _agency_control_state_for_job(workspace_root, task_name) if has_operational_lane else None
        identity_continuity = _identity_continuity_for_job(workspace_root, task_name)
        assigned_social_accounts = _assigned_social_accounts_for_job(task_name) if has_operational_lane else []
        continuity_incident = build_continuity_incident_summary(
            identity_continuity_summary=identity_continuity,
            assigned_social_accounts=assigned_social_accounts,
        )
        if has_operational_lane:
            identity_resume_procedure = build_identity_resume_procedure(
                identity_continuity_summary=identity_continuity,
            )
            continuity_recovery_ack = load_continuity_recovery_ack(
                root=workspace_root,
                binding=task_binding,
                session_target=task_name,
            )
            identity_resume_observation = build_identity_resume_observation(
                identity_continuity_summary=identity_continuity,
                continuity_recovery_ack=continuity_recovery_ack,
            )
            continuity_repair_observation = build_continuity_repair_observation(
                assigned_social_accounts=assigned_social_accounts,
            )
            base_continuity_recovery_readiness = build_continuity_recovery_readiness(
                identity_continuity_summary=identity_continuity,
                continuity_incident_summary=continuity_incident,
                continuity_recovery_ack=continuity_recovery_ack,
                continuity_repair_observation=continuity_repair_observation,
                identity_resume_observation=identity_resume_observation,
            )
            post_rebuild_continuity_check = load_post_rebuild_continuity_check(
                root=workspace_root,
                binding=task_binding,
                session_target=task_name,
                identity_continuity_summary=identity_continuity,
                continuity_recovery_readiness=base_continuity_recovery_readiness,
            )
            identity_restore_validation = load_identity_restore_validation(
                root=workspace_root,
                binding=task_binding,
                session_target=task_name,
                identity_continuity_summary=identity_continuity,
            )
            continuity_recovery_readiness = build_continuity_recovery_readiness(
                identity_continuity_summary=identity_continuity,
                continuity_incident_summary=continuity_incident,
                continuity_recovery_ack=continuity_recovery_ack,
                continuity_repair_observation=continuity_repair_observation,
                identity_resume_observation=identity_resume_observation,
                post_rebuild_continuity_check=post_rebuild_continuity_check,
                identity_restore_validation=identity_restore_validation,
            )
            preliminary_continuity_repair_plan = build_continuity_repair_plan(
                identity_continuity_summary=identity_continuity,
                identity_resume_procedure=identity_resume_procedure,
                identity_resume_observation=identity_resume_observation,
                continuity_incident_summary=continuity_incident,
                continuity_recovery_readiness=continuity_recovery_readiness,
                continuity_repair_observation=continuity_repair_observation,
                post_rebuild_continuity_check=post_rebuild_continuity_check,
                identity_restore_validation=identity_restore_validation,
            )
            preliminary_operational_resume_governance_summary = build_operational_resume_governance_summary(
                root=workspace_root,
                binding=task_binding,
                task_names=[task_name] if task_name else [],
                linked_tasks=[{"id": task_name, "session_target": task_name}] if task_name else [],
                continuity_recovery_readiness=continuity_recovery_readiness,
                continuity_repair_plan=preliminary_continuity_repair_plan,
                identity_restore_validation=identity_restore_validation,
            )
            supervised_resume_validation = load_supervised_resume_validation(
                root=workspace_root,
                binding=task_binding,
                session_target=task_name,
                post_rebuild_continuity_check=post_rebuild_continuity_check,
                continuity_recovery_readiness=continuity_recovery_readiness,
                continuity_recovery_ack=continuity_recovery_ack,
                identity_restore_validation=identity_restore_validation,
            )
            continuity_repair_plan = build_continuity_repair_plan(
                identity_continuity_summary=identity_continuity,
                identity_resume_procedure=identity_resume_procedure,
                identity_resume_observation=identity_resume_observation,
                continuity_incident_summary=continuity_incident,
                continuity_recovery_readiness=continuity_recovery_readiness,
                continuity_repair_observation=continuity_repair_observation,
                post_rebuild_continuity_check=post_rebuild_continuity_check,
                identity_restore_validation=identity_restore_validation,
                supervised_resume_validation=supervised_resume_validation,
            )
            operational_resume_governance_summary = build_operational_resume_governance_summary(
                root=workspace_root,
                binding=task_binding,
                task_names=[task_name] if task_name else [],
                linked_tasks=[{"id": task_name, "session_target": task_name}] if task_name else [],
                continuity_recovery_readiness=continuity_recovery_readiness,
                continuity_repair_plan=continuity_repair_plan,
                identity_restore_validation=identity_restore_validation,
                supervised_resume_validation=supervised_resume_validation,
            )
            operational_resume_checkpoint = ensure_operational_resume_checkpoint_validity(
                root=workspace_root,
                binding=task_binding,
                session_target=task_name,
                operational_resume_governance_summary=operational_resume_governance_summary,
            )
            bounded_autonomy_policy_summary = build_bounded_autonomy_policy_summary(
                agency_control_summary=agency_control,
                continuity_recovery_readiness=continuity_recovery_readiness,
                operational_resume_governance_summary=operational_resume_governance_summary,
                operational_resume_checkpoint=operational_resume_checkpoint,
                identity_restore_validation=identity_restore_validation,
                supervised_resume_validation=supervised_resume_validation,
            )
            crew_dynamics_summary = build_crew_dynamics_summary(
                root=workspace_root,
                task_name=task_name,
                session_target=task_name,
                binding=task_binding,
            )
            commitment_summary = build_commitment_summary(
                root=workspace_root,
                task_name=task_name,
                session_target=task_name,
                binding=task_binding,
            )
            confidence_summary = build_confidence_summary(
                self_model_summary=build_self_model_summary(task_binding),
                presence_initiative_summary=build_presence_initiative_summary(
                    root=workspace_root,
                    task_name=task_name,
                    session_target=task_name,
                    binding=task_binding,
                ),
                continuity_recovery_readiness=continuity_recovery_readiness,
                operational_resume_governance_summary=operational_resume_governance_summary,
                operational_resume_checkpoint=operational_resume_checkpoint,
                bounded_autonomy_policy_summary=bounded_autonomy_policy_summary,
                commitment_summary=commitment_summary,
                action_rationale_summary=None,
                identity_continuity_summary=identity_continuity,
                agency_control_summary=agency_control,
            )
            operational_resume_checkpoint_required = (
                str(operational_resume_governance_summary.get("status") or "").strip().lower() == "ready"
                and not bool(operational_resume_checkpoint.get("approved"))
            )
        else:
            identity_resume_procedure = {"status": "not_applicable", "open_step_count": 0, "completed_step_count": 0, "open_steps": [], "completed_steps": [], "summary": "not_applicable"}
            continuity_recovery_ack = {"present": False, "acknowledged": False, "path": None}
            identity_resume_observation = {"status": "not_applicable", "observation_required": False, "observation_complete": True, "acknowledged_at": None, "observed_at": None, "summary": "not_applicable"}
            continuity_repair_observation = {"status": "not_applicable", "observation_required": False, "observation_complete": True, "repair_required_account_count": 0, "observed_account_count": 0, "repair_required_accounts": [], "observed_accounts": [], "latest_repair_at": None, "latest_observed_at": None, "latest_observed_kind": None, "latest_observed_detail": None, "summary": "not_applicable"}
            post_rebuild_continuity_check = {"present": False, "status": "not_applicable", "verification_required": False, "verified": False, "summary": "not_applicable", "path": None}
            identity_restore_validation = {"status": "not_applicable", "required": False, "verified": False, "recorded": False, "path": None}
            continuity_recovery_readiness = {
                "status": "ready",
                "safe_to_resume": True,
                "resume_permitted": True,
                "repair_required": False,
                "acknowledged": False,
                "acknowledged_at": None,
                "acknowledged_by": None,
                "ack_note": None,
                "can_acknowledge": False,
                "blocking": [],
                "cautions": [],
                "identity_status": "not_applicable",
                "incident_status": "not_applicable",
                "continuity_anchor": None,
                "latest_event_at": None,
                "latest_event_kind": None,
                "latest_event_detail": None,
                "summary": "not_applicable",
                "post_repair_observation": continuity_repair_observation,
                "identity_resume_observation": identity_resume_observation,
                "post_rebuild_continuity_check": post_rebuild_continuity_check,
                "identity_restore_validation": identity_restore_validation,
                "recovery_closeout_complete": True,
            }
            continuity_repair_plan = {
                "status": "not_applicable",
                "repair_required": False,
                "open_check_count": 0,
                "completed_check_count": 0,
                "open_checks": [],
                "completed_checks": [],
                "latest_event_detail": None,
                "identity_resume_observation": identity_resume_observation,
                "post_repair_observation": continuity_repair_observation,
                "post_rebuild_continuity_check": post_rebuild_continuity_check,
                "identity_restore_validation": identity_restore_validation,
                "supervised_resume_validation": {"status": "not_applicable", "required": False, "validated": True, "path": None},
                "summary": "not_applicable",
            }
            operational_resume_governance_summary = {
                "status": "not_applicable",
                "resume_ready": True,
                "blocking": [],
                "cautions": [],
                "required_actions": [],
                "task_count": 0,
                "verification_required_count": 0,
                "verified_count": 0,
                "pending_count": 0,
                "blocked_count": 0,
                "task_checks": [],
                "identity_restore_validation": identity_restore_validation,
                "supervised_resume_validation": {"status": "not_applicable", "required": False, "validated": True, "path": None},
                "summary": "not_applicable",
            }
            operational_resume_checkpoint = {"present": False, "approved": False, "approved_at": None, "approved_by": None, "task_checks_snapshot": [], "path": None, "created": False}
            supervised_resume_validation = {"status": "not_applicable", "required": False, "validated": True, "path": None}
            bounded_autonomy_policy_summary = {
                "status": "ready",
                "blockers": [],
                "required_actions": [],
                "next_eligible_at": None,
                "action_hint": None,
                "summary": "not_applicable",
            }
            crew_dynamics_summary = {
                "status": "missing",
                "workflow_id": None,
                "coordination_style": None,
                "coordination_style_source": None,
                "coordination_checkpoints": [],
                "run_policy": {},
                "swarm_run_id": None,
                "swarm_role": None,
                "swarm_turn_count": 0,
                "swarm_member_count": 0,
                "swarm_orchestrator_present": False,
                "dominant_relationship_type": None,
                "dominant_engagement_mode": None,
                "top_counterparts": [],
                "recent_swarm_events": [],
                "recent_swarm_members": [],
                "naturalness_summary": None,
                "autonomy_summary": None,
            }
            commitment_summary = {
                "status": "not_applicable",
                "count": 0,
                "open_count": 0,
                "fulfilled_count": 0,
                "expired_count": 0,
                "overdue_count": 0,
                "recent_commitments": [],
                "next_due_at": None,
                "latest_commitment": None,
                "required_actions": [],
            }
            confidence_summary = {
                "status": "not_applicable",
                "confidence_level": "uncertain",
                "confidence_score": 0,
                "dominant_uncertainty": None,
                "trust_band": None,
                "agency_budget": None,
                "confidence_drivers": [],
                "confidence_cautions": [],
                "confidence_blockers": [],
                "next_action": None,
                "summary": "not_applicable",
            }
            operational_resume_checkpoint_required = False
        workflow_status_summary = build_workflow_status_summary(
            workspace_root,
            workflow_id=workflow_id or None,
            job_id=job_id,
            graph_id=graph_id or None,
        )
        if not workflow_status_summary.get("latest_run_id") and workflow_id:
            workflow_status_summary["activity_href"] = f"#/activity?workflow_id={workflow_id}"
        out.append(
            {
                "job_id": job_id,
                "dag_path": dag_rel,
                "exists": exists,
                "graph_id": graph_id,
                "node_count": node_count,
                "workflow_id": workflow_id or None,
                "task_name": task_name or None,
                "platform": str(task_binding.get("platform") or "").strip() or None,
                "operational_agent_id": str(task_binding.get("operational_agent_id") or "").strip() or None,
                "cadence": _cadence_state_for_job(workspace_root, job_id, task_name),
                "agency_control": agency_control,
                "identity_continuity_summary": identity_continuity,
                "identity_resume_procedure": identity_resume_procedure,
                "identity_resume_observation": identity_resume_observation,
                "identity_resume_closeout": load_identity_resume_closeout(root=workspace_root, binding=task_binding, session_target=task_name),
                "continuity_incident_summary": continuity_incident,
                "continuity_recovery_ack": continuity_recovery_ack,
                "continuity_repair_observation": continuity_repair_observation,
                "post_rebuild_continuity_check": post_rebuild_continuity_check,
                "identity_restore_validation": identity_restore_validation,
                "continuity_recovery_readiness": continuity_recovery_readiness,
                "continuity_repair_plan": continuity_repair_plan,
                "operational_resume_governance_summary": operational_resume_governance_summary,
                "operational_resume_checkpoint": operational_resume_checkpoint,
                "supervised_resume_validation": supervised_resume_validation,
                "bounded_autonomy_policy_summary": bounded_autonomy_policy_summary,
                "crew_dynamics_summary": crew_dynamics_summary,
                "commitment_summary": commitment_summary,
                "confidence_summary": confidence_summary,
                "workflow_status_summary": workflow_status_summary,
                "release_gate_summary": _release_gate_summary_for_job(job_id, workflow_id or None),
                "operational_resume_checkpoint_required": operational_resume_checkpoint_required,
                "review_handoff_summary": build_review_handoff_summary(
                    workspace_root,
                    task_names=[task_name] if task_name else [],
                    workflow_id=workflow_id or None,
                    job_id=job_id,
                    graph_id=graph_id or None,
                    operational_agent_id=get_operational_agent_id(task_name) if task_name else "",
                    agency_control_summary=agency_control,
                    continuity_recovery_readiness=continuity_recovery_readiness,
                    operational_resume_governance_summary=operational_resume_governance_summary,
                    operational_resume_checkpoint=operational_resume_checkpoint,
                ),
            }
        )
    return out


def read_scheduled_dag(workspace_root: Path, job_id: str) -> dict[str, Any]:
    job_to_dag = _get_job_to_dag(workspace_root)
    dag_rel = job_to_dag.get(job_id)
    if not dag_rel:
        workflow_id = _schedule_alias_to_workflow_id(workspace_root, job_id)
        if workflow_id:
            dag_rel = job_to_dag.get(workflow_id)
    if not dag_rel:
        raise KeyError(job_id)
    dag_path = _resolve_path(workspace_root, dag_rel)
    if not dag_path.exists():
        raise FileNotFoundError(str(dag_path))
    dag = json.loads(dag_path.read_text(encoding="utf-8"))
    return {
        "job_id": job_id,
        "dag_path": dag_rel,
        "dag": dag,
    }


def save_scheduled_dag(workspace_root: Path, job_id: str, dag: dict[str, Any]) -> dict[str, Any]:
    job_to_dag = _get_job_to_dag(workspace_root)
    dag_rel = job_to_dag.get(job_id)
    if not dag_rel:
        workflow_id = _schedule_alias_to_workflow_id(workspace_root, job_id)
        if workflow_id:
            dag_rel = job_to_dag.get(workflow_id)
    if not dag_rel:
        raise KeyError(job_id)

    validation = validate(dag)
    if not validation.get("ok"):
        raise ValueError(json.dumps({"code": "INVALID_DAG", "errors": validation.get("errors", [])}))

    dag_path = _resolve_path(workspace_root, dag_rel)
    dag_path.parent.mkdir(parents=True, exist_ok=True)

    backup_path = None
    if dag_path.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = dag_path.with_name(f"{dag_path.name}.bak-{stamp}")
        backup_path.write_text(dag_path.read_text(encoding="utf-8"), encoding="utf-8")

    dag_path.write_text(json.dumps(dag, indent=2) + "\n", encoding="utf-8")
    return {
        "job_id": job_id,
        "dag_path": dag_rel,
        "saved": True,
        "backup_path": str(backup_path) if backup_path else None,
    }
