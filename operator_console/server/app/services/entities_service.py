"""
Entities service: list and detail for job_registry tasks (entities) with
memory/automation dir stats (has_decisions, last_activity), and entity graph (entities/facts from agent_memory.db).
"""

import json
import time
from pathlib import Path
from typing import Any

from hg_gateway.shared_storage import get_entity_graph as get_shared_entity_graph, list_agent_decisions
from hg_gateway.shared_storage import use_shared_gateway_db
from ..services.action_rationale_summary import build_action_rationale_summary
from ..services.affect_action_summary import build_affect_action_summary
from ..services.bounded_autonomy_policy import build_bounded_autonomy_policy_summary
from ..services.commitment_summary import build_commitment_summary
from ..services.crew_dynamics_summary import build_crew_dynamics_summary
from ..services.confidence_summary import build_confidence_summary
from ..services.continuity_incident_summary import build_continuity_incident_summary
from ..services.continuity_incident_summary import build_continuity_quality_summary
from ..services.continuity_recovery_ack import load_continuity_recovery_ack
from ..services.continuity_repair_observation import build_continuity_repair_observation
from ..services.continuity_repair_plan import build_continuity_repair_plan
from ..services.continuity_recovery_readiness import build_continuity_recovery_readiness
from ..services.drift_review_summary import build_drift_review_summary
from ..services.entity_profile import build_entity_profile
from ..services.identity_restore_validation import load_identity_restore_validation
from ..services.identity_continuity_summary import build_identity_continuity_summary
from ..services.identity_resume_closeout import load_identity_resume_closeout
from ..services.identity_resume_observation import build_identity_resume_observation
from ..services.identity_resume_procedure import build_identity_resume_procedure
from ..services.operational_agency_control import build_agency_control_summary
from ..services.operational_resume_checkpoint import ensure_operational_resume_checkpoint_validity
from ..services.operational_resume_governance_summary import build_operational_resume_governance_summary
from ..services.post_rebuild_continuity_check import load_post_rebuild_continuity_check
from ..services.presence_initiative_summary import build_presence_initiative_summary
from ..services.research_delivery_summary import build_research_delivery_summary
from ..services.review_handoff_summary import build_review_handoff_summary
from ..services.relationship_memory_summary import build_relationship_memory_summary
from hg_core.governance.contracts import build_mimicry_policy_summary
from hg_core.governance.independence import build_voice_belief_separation_summary
from ..services.self_model_summary import build_self_model_summary
from ..services.social_account_summary import build_social_account_operator_summary
from ..services.social_posture_summary import build_social_posture_summary
from ..services.supervised_resume_validation import load_supervised_resume_validation
from .run_index_db import list_runs as list_index_runs
from hg_realtime.scheduler.schedule_config import load_schedule

_WAKE_TOKEN_CACHE: dict[str, tuple[float, dict[str, Any] | None]] = {}
_ENTITY_DECISION_SUMMARY_CACHE: tuple[float, dict[str, tuple[bool, str | None, int]]] | None = None
_VISIBLE_SCHEDULED_ENTITY_TASKS = {"knowledge-research-auto-v2", "memory-maintenance"}


def reset_caches_for_tests() -> None:
    """Clear the module-level TTL caches. Test-isolation helper only.

    ``_WAKE_TOKEN_CACHE`` and ``_ENTITY_DECISION_SUMMARY_CACHE`` are process-global
    caches with a multi-minute TTL. Across tests (which run well within the TTL) a
    summary computed against one test's workspace/store leaks to the next test,
    regardless of that test's HG_WORKSPACE/tmp_path isolation — a stale
    action_rationale / entity-decision status (OSI2 pipeline 107 victims). Resetting
    per test restores isolation. Production behaviour is unchanged (the caches are
    still populated/expired normally in a running server)."""
    global _ENTITY_DECISION_SUMMARY_CACHE
    _WAKE_TOKEN_CACHE.clear()
    _ENTITY_DECISION_SUMMARY_CACHE = None


def _wake_token_cache_ttl_seconds() -> float:
    import os

    raw = (os.environ.get("HG_ENTITY_WAKE_TOKEN_CACHE_TTL") or "300").strip()
    try:
        return max(5.0, float(raw))
    except ValueError:
        return 300.0


def _workspace_root() -> Path | None:
    try:
        from hg_lib.config import get_workspace_root
        return get_workspace_root()
    except Exception:
        return None


def _get_registry() -> dict[str, dict[str, Any]]:
    try:
        from hg_core.job_registry import get_registry
        return get_registry()
    except Exception:
        return {}


def _load_visible_entity_specs(root: Path, registry: dict[str, dict[str, Any]]) -> list[dict[str, Any]] | None:
    try:
        state = load_schedule(root)
    except Exception:
        return None
    if not state.entries:
        return None
    specs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for entry in state.entries:
        job_id = str(entry.job_id or "").strip()
        inputs = dict(entry.inputs or {})
        workflow_id = str(inputs.get("workflow_id") or "").strip()
        source_task_name = str(inputs.get("task_name") or "").strip()

        if workflow_id == "social-media" and job_id and source_task_name and source_task_name in registry:
            source_info = registry[source_task_name]
            binding = _operational_binding(source_task_name)
            specs.append(
                {
                    "entity_id": job_id,
                    "task_name": source_task_name,
                    "job_id": job_id,
                    "platform": "social",
                    "mode": "unified-social",
                    "session_target": str(binding.get("operational_session_target") or source_info.get("session_target") or "").strip(),
                    "source_info": source_info,
                    "source_platform": source_info.get("platform"),
                }
            )
            seen_ids.add(job_id)
            continue

        if job_id in _VISIBLE_SCHEDULED_ENTITY_TASKS and job_id in registry and job_id not in seen_ids:
            source_info = registry[job_id]
            specs.append(
                {
                    "entity_id": job_id,
                    "task_name": job_id,
                    "job_id": source_info.get("job_id", job_id),
                    "platform": source_info.get("platform"),
                    "mode": source_info.get("mode"),
                    "session_target": str(source_info.get("session_target") or "").strip(),
                    "source_info": source_info,
                    "source_platform": source_info.get("platform"),
                }
            )
            seen_ids.add(job_id)

    return specs if specs else None


def _default_entity_specs(registry: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "entity_id": task_name,
            "task_name": task_name,
            "job_id": info.get("job_id", task_name),
            "platform": info.get("platform"),
            "mode": info.get("mode"),
            "session_target": str(info.get("session_target") or "").strip(),
            "source_info": info,
            "source_platform": info.get("platform"),
        }
        for task_name, info in registry.items()
    ]


def _visible_entity_specs(root: Path | None, registry: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    if not root:
        return _default_entity_specs(registry)
    scheduled_specs = _load_visible_entity_specs(root, registry)
    if scheduled_specs is not None:
        return scheduled_specs
    return _default_entity_specs(registry)


def _resolve_entity_spec(entity_id: str, root: Path | None, registry: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    for spec in _visible_entity_specs(root, registry):
        if spec.get("entity_id") == entity_id:
            return spec
    return None


def _decisions_info(session_target: str, root: Path) -> tuple[bool, str | None]:
    """Return (has_decisions, last_activity_iso)."""
    decisions_db_path = root / "memory" / "automation" / session_target / "agent_memory.db"
    if use_shared_gateway_db(decisions_db_path):
        decisions = list_agent_decisions(session_target.replace("automation-", "", 1) if session_target.startswith("automation-") else session_target)
        if not decisions:
            return False, None
        last = max(decisions, key=lambda d: d.get("timestamp") or "")
        return True, last.get("timestamp")
    return False, None


def _persona_dir(platform: str | None, root: Path) -> str | None:
    if not platform:
        return None
    try:
        from hg_lib.config import get_persona_dir
        p = get_persona_dir(platform, "default")
        if p and p.exists():
            return str(p)
    except Exception:
        pass
    # Fallback path
    base = root / "skills" / "automation" / "personas" / platform / "default"
    return str(base) if base.exists() else None


def _wake_context_tokens(task_name: str) -> dict[str, Any] | None:
    """Return wake context token estimate for a task, or None if unavailable."""
    now = time.time()
    cached = _WAKE_TOKEN_CACHE.get(task_name)
    if cached and cached[0] > now:
        if isinstance(cached[1], dict):
            return dict(cached[1])
        return cached[1]
    try:
        from hg_core.context_loader import get_wake_context_token_estimate
        value = get_wake_context_token_estimate(task_name)
        _WAKE_TOKEN_CACHE[task_name] = (
            now + _wake_token_cache_ttl_seconds(),
            dict(value) if isinstance(value, dict) else value,
        )
        return value
    except Exception:
        _WAKE_TOKEN_CACHE[task_name] = (now + 30.0, None)
        return None


def _decision_summary_cache_ttl_seconds() -> float:
    return 30.0


def _build_shared_decision_summary(registry: dict[str, dict[str, Any]]) -> dict[str, tuple[bool, str | None, int]]:
    try:
        from hg_core.job_registry import get_compatible_agent_ids
    except Exception:
        return {}

    summary: dict[str, tuple[bool, str | None, int]] = {}
    for task_name in registry:
        timestamps: list[str] = []
        count = 0
        for agent_id in get_compatible_agent_ids(task_name):
            decisions = list_agent_decisions(agent_id, limit=500)
            if not decisions:
                continue
            count += len(decisions)
            timestamps.extend(
                str(item.get("timestamp") or "")
                for item in decisions
                if item.get("timestamp")
            )
        summary[task_name] = (count > 0, max(timestamps) if timestamps else None, count)
    return summary


def _runtime_tenant_id() -> str:
    import os

    return (os.getenv("HG_OPERATOR_TENANT_ID") or os.getenv("HG_DEFAULT_TENANT_ID") or "default").strip() or "default"


def _operational_binding(task_name: str) -> dict[str, Any]:
    try:
        from hg_core.job_registry import get_operational_binding

        binding = get_operational_binding(task_name)
        return binding if isinstance(binding, dict) else {}
    except Exception:
        return {}


def _get_shared_decision_summary(registry: dict[str, dict[str, Any]]) -> dict[str, tuple[bool, str | None, int]]:
    global _ENTITY_DECISION_SUMMARY_CACHE

    now = time.time()
    if _ENTITY_DECISION_SUMMARY_CACHE and _ENTITY_DECISION_SUMMARY_CACHE[0] > now:
        return dict(_ENTITY_DECISION_SUMMARY_CACHE[1])
    summary = _build_shared_decision_summary(registry)
    _ENTITY_DECISION_SUMMARY_CACHE = (now + _decision_summary_cache_ttl_seconds(), summary)
    return dict(summary)


def _recent_runs(limit: int = 50) -> list[dict[str, Any]]:
    try:
        return [dict(row) for row in list_index_runs(limit=limit)]
    except Exception:
        return []


def _assigned_social_accounts(binding: dict[str, Any]) -> list[dict[str, Any]]:
    operational_agent_id = str(binding.get("operational_agent_id") or "").strip()
    platform = str(binding.get("platform") or "").strip()
    fingerprint_id = str(binding.get("fingerprint_id") or "").strip()
    if not operational_agent_id or not platform:
        return []
    try:
        from hg_gateway import keystore_repo

        accounts = keystore_repo.social_account_list(tenant_id=_runtime_tenant_id(), platform=platform)
    except Exception:
        return []
    matches = []
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
                "entity_scope": account.get("entity_scope"),
                "persona_scope": account.get("persona_scope"),
                "login_secret_alias_id": account.get("login_secret_alias_id"),
                "mfa_secret_alias_id": account.get("mfa_secret_alias_id"),
                **build_social_account_operator_summary(str(account.get("social_account_id") or ""), account=account),
            }
        )
    return matches


def _build_entity_payload(
    *,
    entity_id: str,
    task_name: str,
    root: Path | None,
    registry: dict[str, dict[str, Any]],
    session_target: str,
    job_id: str,
    platform: Any,
    mode: Any,
    source_platform: Any,
    include_wake_tokens: bool,
    include_decisions_count: bool,
    recent_runs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    binding = _operational_binding(task_name)
    research_delivery_summary = build_research_delivery_summary(task_name, binding=binding)
    agency_control_summary = build_agency_control_summary(
        root=root,
        binding=binding,
        session_target=session_target,
    )
    has_decisions = False
    last_activity = None
    decisions_count = 0
    if root and session_target:
        decisions_db_path = root / "memory" / "automation" / session_target / "agent_memory.db"
        if use_shared_gateway_db(decisions_db_path):
            shared_summary = _get_shared_decision_summary(registry)
            has_decisions, last_activity, decisions_count = shared_summary.get(task_name, (False, None, 0))
        else:
            has_decisions, last_activity = _decisions_info(session_target, root)
            if include_decisions_count and has_decisions:
                shared_summary = _get_shared_decision_summary(registry)
                has_decisions, last_activity, decisions_count = shared_summary.get(task_name, (False, None, 0))
    assigned_social_accounts = _assigned_social_accounts(binding)
    identity_continuity_summary = build_identity_continuity_summary(
        root=root,
        task_name=task_name,
        session_target=session_target,
        binding=binding,
    )
    continuity_incident_summary = build_continuity_incident_summary(
        identity_continuity_summary=identity_continuity_summary,
        assigned_social_accounts=assigned_social_accounts,
    )
    identity_resume_procedure = build_identity_resume_procedure(
        identity_continuity_summary=identity_continuity_summary,
    )
    continuity_recovery_ack = load_continuity_recovery_ack(
        root=root,
        binding=binding,
        session_target=session_target,
    )
    identity_resume_observation = build_identity_resume_observation(
        identity_continuity_summary=identity_continuity_summary,
        continuity_recovery_ack=continuity_recovery_ack,
    )
    continuity_repair_observation = build_continuity_repair_observation(
        assigned_social_accounts=assigned_social_accounts,
    )
    base_continuity_recovery_readiness = build_continuity_recovery_readiness(
        identity_continuity_summary=identity_continuity_summary,
        continuity_incident_summary=continuity_incident_summary,
        continuity_recovery_ack=continuity_recovery_ack,
        continuity_repair_observation=continuity_repair_observation,
        identity_resume_observation=identity_resume_observation,
    )
    post_rebuild_continuity_check = load_post_rebuild_continuity_check(
        root=root,
        binding=binding,
        session_target=session_target,
        identity_continuity_summary=identity_continuity_summary,
        continuity_recovery_readiness=base_continuity_recovery_readiness,
    )
    identity_restore_validation = load_identity_restore_validation(
        root=root,
        binding=binding,
        session_target=session_target,
        identity_continuity_summary=identity_continuity_summary,
    )
    continuity_recovery_readiness = build_continuity_recovery_readiness(
        identity_continuity_summary=identity_continuity_summary,
        continuity_incident_summary=continuity_incident_summary,
        continuity_recovery_ack=continuity_recovery_ack,
        continuity_repair_observation=continuity_repair_observation,
        identity_resume_observation=identity_resume_observation,
        post_rebuild_continuity_check=post_rebuild_continuity_check,
        identity_restore_validation=identity_restore_validation,
    )
    preliminary_continuity_repair_plan = build_continuity_repair_plan(
        identity_continuity_summary=identity_continuity_summary,
        identity_resume_procedure=identity_resume_procedure,
        identity_resume_observation=identity_resume_observation,
        continuity_incident_summary=continuity_incident_summary,
        continuity_recovery_readiness=continuity_recovery_readiness,
        continuity_repair_observation=continuity_repair_observation,
        post_rebuild_continuity_check=post_rebuild_continuity_check,
        identity_restore_validation=identity_restore_validation,
    )
    supervised_resume_validation = load_supervised_resume_validation(
        root=root,
        binding=binding,
        session_target=session_target,
        post_rebuild_continuity_check=post_rebuild_continuity_check,
        continuity_recovery_readiness=continuity_recovery_readiness,
        continuity_recovery_ack=continuity_recovery_ack,
        identity_restore_validation=identity_restore_validation,
    )
    continuity_repair_plan = build_continuity_repair_plan(
        identity_continuity_summary=identity_continuity_summary,
        identity_resume_procedure=identity_resume_procedure,
        identity_resume_observation=identity_resume_observation,
        continuity_incident_summary=continuity_incident_summary,
        continuity_recovery_readiness=continuity_recovery_readiness,
        continuity_repair_observation=continuity_repair_observation,
        post_rebuild_continuity_check=post_rebuild_continuity_check,
        identity_restore_validation=identity_restore_validation,
        supervised_resume_validation=supervised_resume_validation,
    )
    operational_resume_governance_summary = build_operational_resume_governance_summary(
        root=root,
        binding=binding,
        task_names=[task_name],
        linked_tasks=[{"id": task_name, "session_target": session_target}],
        continuity_recovery_readiness=continuity_recovery_readiness,
        continuity_repair_plan=continuity_repair_plan,
        identity_restore_validation=identity_restore_validation,
        supervised_resume_validation=supervised_resume_validation,
    )
    operational_resume_checkpoint = ensure_operational_resume_checkpoint_validity(
        root=root,
        binding=binding,
        session_target=session_target,
        operational_resume_governance_summary=operational_resume_governance_summary,
    )
    bounded_autonomy_policy_summary = build_bounded_autonomy_policy_summary(
        agency_control_summary=agency_control_summary,
        continuity_recovery_readiness=continuity_recovery_readiness,
        operational_resume_governance_summary=operational_resume_governance_summary,
        operational_resume_checkpoint=operational_resume_checkpoint,
        identity_restore_validation=identity_restore_validation,
        supervised_resume_validation=supervised_resume_validation,
    )
    presence_initiative_summary = build_presence_initiative_summary(
        root=root,
        task_name=task_name,
        session_target=session_target,
        binding=binding,
    )
    self_model_summary = build_self_model_summary(binding)
    relationship_memory_summary = build_relationship_memory_summary(binding)
    crew_dynamics_summary = build_crew_dynamics_summary(
        root=root,
        task_name=task_name,
        session_target=session_target,
        binding=binding,
    )
    commitment_summary = build_commitment_summary(
        root=root,
        task_name=task_name,
        session_target=session_target,
        binding=binding,
    )
    drift_review_summary = build_drift_review_summary(
        workflow_family=entity_id,
        entity_id=entity_id,
        limit=8,
    )
    action_rationale_summary = build_action_rationale_summary(
        root=root,
        task_name=task_name,
        session_target=session_target,
        binding=binding,
        research_delivery_summary=research_delivery_summary,
        agency_control_summary=agency_control_summary,
    )
    affect_action_summary = build_affect_action_summary(
        root=root,
        task_name=task_name,
        session_target=session_target,
        binding=binding,
    )
    review_handoff_summary = build_review_handoff_summary(
        root,
        task_names=[task_name],
        operational_agent_id=str(binding.get("operational_agent_id") or ""),
        agency_control_summary=agency_control_summary,
        continuity_recovery_readiness=continuity_recovery_readiness,
        operational_resume_governance_summary=operational_resume_governance_summary,
        operational_resume_checkpoint=operational_resume_checkpoint,
    )
    mimicry_control_summary = build_mimicry_policy_summary()
    voice_belief_separation_summary = build_voice_belief_separation_summary(
        mimicry_policy_summary=mimicry_control_summary,
        self_model_summary=self_model_summary,
    )
    continuity_quality_summary = build_continuity_quality_summary(
        identity_continuity_summary=identity_continuity_summary,
        continuity_incident_summary=continuity_incident_summary,
        continuity_recovery_readiness=continuity_recovery_readiness,
        continuity_repair_plan=continuity_repair_plan,
        continuity_repair_observation=continuity_repair_observation,
        post_rebuild_continuity_check=post_rebuild_continuity_check,
        identity_restore_validation=identity_restore_validation,
        supervised_resume_validation=supervised_resume_validation,
        review_handoff_summary=review_handoff_summary,
        drift_review_summary=drift_review_summary,
    )
    confidence_summary = build_confidence_summary(
        self_model_summary=self_model_summary,
        presence_initiative_summary=presence_initiative_summary,
        continuity_recovery_readiness=continuity_recovery_readiness,
        operational_resume_governance_summary=operational_resume_governance_summary,
        operational_resume_checkpoint=operational_resume_checkpoint,
        bounded_autonomy_policy_summary=bounded_autonomy_policy_summary,
        commitment_summary=commitment_summary,
        action_rationale_summary=action_rationale_summary,
        identity_continuity_summary=identity_continuity_summary,
        agency_control_summary=agency_control_summary,
        drift_summary=drift_review_summary,
        mimicry_control_summary=mimicry_control_summary,
        continuity_quality_summary=continuity_quality_summary,
    )
    profile = build_entity_profile(
        {
            "id": entity_id,
            "display_name": entity_id,
            "task_name": task_name,
            "session_target": session_target,
            "operational_session_target": binding.get("operational_session_target"),
            "operational_agent_id": binding.get("operational_agent_id"),
            "fingerprint_id": binding.get("fingerprint_id"),
            "platform": platform,
            "mode": mode,
            "last_activity": last_activity,
            "pending_approvals": review_handoff_summary.get("pending_count") or 0,
            "decisions_count": decisions_count if include_decisions_count else 0,
            "memory_health": {
                "status": "healthy" if identity_continuity_summary.get("status") == "healthy" else "partial" if identity_continuity_summary.get("status") == "partial" else "missing",
                "last_wake_at": identity_continuity_summary.get("last_wake_at"),
                "last_sleep_at": identity_continuity_summary.get("last_sleep_at"),
                "continuity_anchor": identity_continuity_summary.get("continuity_anchor"),
            },
            "identity_continuity_summary": identity_continuity_summary,
            "continuity_incident_summary": continuity_incident_summary,
            "continuity_recovery_ack": continuity_recovery_ack,
            "continuity_repair_observation": continuity_repair_observation,
            "post_rebuild_continuity_check": post_rebuild_continuity_check,
            "identity_restore_validation": identity_restore_validation,
            "continuity_recovery_readiness": continuity_recovery_readiness,
            "continuity_repair_plan": continuity_repair_plan,
            "identity_resume_procedure": identity_resume_procedure,
            "identity_resume_observation": identity_resume_observation,
            "identity_resume_closeout": load_identity_resume_closeout(root=root, binding=binding, session_target=session_target),
            "operational_resume_governance_summary": operational_resume_governance_summary,
            "operational_resume_checkpoint": operational_resume_checkpoint,
            "supervised_resume_validation": supervised_resume_validation,
            "agency_control_summary": agency_control_summary,
            "review_handoff_summary": review_handoff_summary,
            "commitment_summary": commitment_summary,
            "drift_review_summary": drift_review_summary,
            "mimicry_control_summary": mimicry_control_summary,
            "voice_belief_separation_summary": voice_belief_separation_summary,
            "continuity_quality_summary": continuity_quality_summary,
            "self_model_summary": self_model_summary,
            "relationship_memory_summary": relationship_memory_summary,
            "confidence_summary": confidence_summary,
            "action_rationale_summary": action_rationale_summary,
            "presence_initiative_summary": presence_initiative_summary,
        },
        recent_runs=recent_runs or _recent_runs(),
    )
    payload = {
        "id": entity_id,
        "task_name": task_name,
        "source_task_name": task_name,
        "job_id": job_id,
        "session_target": session_target,
        "operational_session_target": binding.get("operational_session_target"),
        "operational_agent_id": binding.get("operational_agent_id"),
        "operational_family": binding.get("operational_family"),
        "fingerprint_id": binding.get("fingerprint_id"),
        "compatible_session_targets": binding.get("compatible_session_targets") or [],
        "compatible_agent_ids": binding.get("compatible_agent_ids") or [],
        "platform": platform,
        "mode": mode,
        "source_platform": source_platform,
        "assigned_social_accounts": assigned_social_accounts,
        "identity_continuity_summary": identity_continuity_summary,
        "identity_resume_procedure": identity_resume_procedure,
        "identity_resume_observation": identity_resume_observation,
        "identity_resume_closeout": load_identity_resume_closeout(root=root, binding=binding, session_target=session_target),
        "continuity_incident_summary": continuity_incident_summary,
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
        "presence_initiative_summary": presence_initiative_summary,
        "agency_control_summary": agency_control_summary,
        "self_model_summary": self_model_summary,
        "relationship_memory_summary": relationship_memory_summary,
        "crew_dynamics_summary": crew_dynamics_summary,
        "commitment_summary": commitment_summary,
        "drift_review_summary": drift_review_summary,
        "mimicry_control_summary": mimicry_control_summary,
        "voice_belief_separation_summary": voice_belief_separation_summary,
        "continuity_quality_summary": continuity_quality_summary,
        "confidence_summary": confidence_summary,
        "affect_action_summary": affect_action_summary,
        "social_posture_summary": build_social_posture_summary(
            agency_control_summary=agency_control_summary,
            self_model_summary=self_model_summary,
            relationship_memory_summary=relationship_memory_summary,
            assigned_social_accounts=assigned_social_accounts,
        ),
        "action_rationale_summary": action_rationale_summary,
        "review_handoff_summary": review_handoff_summary,
        "research_delivery_summary": research_delivery_summary,
        "has_decisions": has_decisions,
        "last_activity": last_activity,
        "profile": profile,
        "wake_context_tokens": _wake_context_tokens(task_name) if include_wake_tokens else None,
    }
    if include_decisions_count:
        payload["decisions_count"] = decisions_count
        payload["persona_dir"] = _persona_dir(source_platform, root) if root and source_platform else None
    return payload


def list_entities() -> list[dict[str, Any]]:
    """List all entities from job_registry with optional has_decisions and last_activity."""
    root = _workspace_root()
    registry = _get_registry()
    if not root or not registry:
        return []
    recent_runs = _recent_runs()
    out = []
    for spec in _visible_entity_specs(root, registry):
        out.append(
            _build_entity_payload(
                entity_id=str(spec.get("entity_id") or ""),
                task_name=str(spec.get("task_name") or ""),
                root=root,
                registry=registry,
                session_target=str(spec.get("session_target") or ""),
                job_id=str(spec.get("job_id") or ""),
                platform=spec.get("platform"),
                mode=spec.get("mode"),
                source_platform=spec.get("source_platform"),
                include_wake_tokens=False,
                include_decisions_count=False,
                recent_runs=recent_runs,
            )
        )
    return out


def get_entity(entity_id: str) -> dict[str, Any] | None:
    """Detail for one entity: registry fields + decisions count, persona_dir."""
    root = _workspace_root()
    registry = _get_registry()
    if not registry:
        return None
    spec = _resolve_entity_spec(entity_id, root, registry)
    if not spec:
        return None
    return _build_entity_payload(
        entity_id=str(spec.get("entity_id") or ""),
        task_name=str(spec.get("task_name") or ""),
        root=root,
        registry=registry,
        session_target=str(spec.get("session_target") or ""),
        job_id=str(spec.get("job_id") or ""),
        platform=spec.get("platform"),
        mode=spec.get("mode"),
        source_platform=spec.get("source_platform"),
        include_wake_tokens=True,
        include_decisions_count=True,
        recent_runs=_recent_runs(),
    )


def get_entity_graph(entity_id: str) -> dict[str, Any] | None:
    """
    Entity graph for one entity from the shared gateway DB.
    Returns None if entity not in registry; otherwise { entities: [], facts: [] }.
    """
    entity = get_entity(entity_id)
    if entity is None:
        return None
    root = _workspace_root()
    if not root:
        return None
    session_target = str(entity.get("session_target") or "")
    if not session_target:
        return {"entities": [], "facts": []}
    db_path = root / "memory" / "automation" / session_target / "agent_memory.db"
    if use_shared_gateway_db(db_path):
        agent_id = session_target.replace("automation-", "", 1) if session_target.startswith("automation-") else session_target
        return get_shared_entity_graph(agent_id)
    return {"entities": [], "facts": []}


def get_entity_persona(entity_id: str) -> dict[str, str] | None:
    """
    Read SOUL.md, HEART.md, IDENTITY.md for entity's platform. Return { soul, heart, identity }.
    None if entity not found or no platform.
    """
    root = _workspace_root()
    registry = _get_registry()
    spec = _resolve_entity_spec(entity_id, root, registry)
    if not root or not registry or not spec:
        return None
    platform = spec.get("source_platform")
    if not platform:
        return None
    try:
        from hg_lib.config import get_persona_dir
        persona_dir = get_persona_dir(platform, "default")
    except Exception:
        persona_dir = root / "skills" / "automation" / "personas" / platform / "default"
    if not persona_dir.exists():
        return None
    out: dict[str, str] = {"soul": "", "heart": "", "identity": ""}
    for key, filename in [("soul", "SOUL.md"), ("heart", "HEART.md"), ("identity", "IDENTITY.md")]:
        path = persona_dir / filename
        if path.exists():
            try:
                out[key] = path.read_text(encoding="utf-8")
            except OSError:
                pass
    return out
