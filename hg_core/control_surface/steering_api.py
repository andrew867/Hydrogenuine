"""
Control Surface Pack 7: Steering integrity API — directives, timeline, integrity, group drift, guardrails.
Delegates to hg_core.steering and hg_core.operator.guardrails.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.steering import (
    list_directives,
    get_active_directive,
    get_steering_timeline,
    publish_directive,
    apply_directive,
    get_goal_integrity_scores,
    get_goal_integrity_alerts,
    get_group_drift_scores,
    get_group_drift_alerts,
)
from hg_core.operator.guardrails import get_operator_guardrails_status


def api_steering_directives_list(
    workspace_root: Path,
    target_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """List directives and active by target. GET /api/steering/directives."""
    return list_directives(workspace_root, target_id=target_id, limit=limit)


def api_steering_directives_publish(
    *,
    target_ref: Dict[str, Any],
    goal: str,
    constraints: List[str],
    autonomy_preset: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    rationale_artifact_id: str = "",
    value_profiles: Optional[List[str]] = None,
    continuity_contract_id: Optional[str] = None,
    expires_hours: int = 24 * 7,
    supersedes: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Publish steering directive (may require quorum). POST /api/steering/directives/publish."""
    return publish_directive(
        target_ref=target_ref,
        goal=goal,
        constraints=constraints,
        autonomy_preset=autonomy_preset,
        scope=scope,
        actor=actor,
        rationale_artifact_id=rationale_artifact_id,
        value_profiles=value_profiles,
        continuity_contract_id=continuity_contract_id,
        expires_hours=expires_hours,
        supersedes=supersedes,
        workspace_root=workspace_root,
    )


def api_steering_directives_apply(
    *,
    directive_id: str,
    target_ref: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Apply directive to target (audited). POST /api/steering/directives/apply."""
    return apply_directive(
        directive_id=directive_id,
        target_ref=target_ref,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def api_steering_timeline(
    workspace_root: Path,
    target_id: str,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Steering history for target. GET /api/steering/timeline."""
    return get_steering_timeline(workspace_root, target_id=target_id, limit=limit)


def api_steering_integrity_scores(
    workspace_root: Path,
    target_id: Optional[str] = None,
    work_item_id: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """Goal integrity scores and alerts. GET /api/steering/integrity/scores."""
    scores = get_goal_integrity_scores(
        workspace_root, target_id=target_id, work_item_id=work_item_id, limit=limit
    )
    alerts = get_goal_integrity_alerts(workspace_root)
    return {"scores": scores, "alerts": alerts}


def api_steering_group_drift(
    workspace_root: Path,
    group_id: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """Group drift scores and safeguards. GET /api/steering/group_drift."""
    scores = get_group_drift_scores(workspace_root, group_id=group_id, limit=limit)
    alerts = get_group_drift_alerts(workspace_root)
    return {"scores": scores, "alerts": alerts}


def api_operator_guardrails(
    workspace_root: Path,
    operator_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Operator budgets and fatigue status. GET /api/operator/guardrails."""
    return get_operator_guardrails_status(workspace_root, operator_id=operator_id)
