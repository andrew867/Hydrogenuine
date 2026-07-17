"""
Control Surface Pack 10: Multi-swarm overseer API — fleet rollups, routing, global controls, impact.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.fleet import (
    get_fleet_swarms_with_rollups,
    suggest_routing,
    apply_routing,
    preflight_global_control,
    apply_global_control,
    list_active_global_controls,
    explore_impact,
)


def api_fleet_swarms(workspace_root: Path, state: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """GET /api/fleet/swarms — list swarms with rollup metrics."""
    return get_fleet_swarms_with_rollups(workspace_root, state=state, limit=limit)


def api_fleet_controls_preflight(
    workspace_root: Path,
    kind: str,
    scope: Dict[str, str],
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """POST /api/fleet/controls/preflight."""
    return preflight_global_control(workspace_root, kind, scope, params=params)


def api_fleet_controls_apply(
    kind: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    expiry_hours: int = 1,
    rationale_artifact_id: str = "",
    params: Optional[Dict[str, Any]] = None,
    quorum_approved: bool = True,
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """POST /api/fleet/controls/apply."""
    return apply_global_control(
        kind=kind,
        scope=scope,
        actor=actor,
        expiry_hours=expiry_hours,
        rationale_artifact_id=rationale_artifact_id,
        params=params,
        quorum_approved=quorum_approved,
        workspace_root=workspace_root,
    )


def api_fleet_routing_suggest(
    workspace_root: Path,
    work_item_id: str,
    from_swarm: str,
    constraints: Optional[List[str]] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    """POST /api/fleet/routing/suggest."""
    return suggest_routing(workspace_root, work_item_id, from_swarm, constraints=constraints, limit=limit)


def api_fleet_routing_apply(
    work_item_id: str,
    from_swarm: str,
    to_swarm: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    rationale_artifact_id: str = "",
    constraints_checked: Optional[List[str]] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """POST /api/fleet/routing/apply. Returns routing_id."""
    return apply_routing(
        work_item_id=work_item_id,
        from_swarm=from_swarm,
        to_swarm=to_swarm,
        scope=scope,
        actor=actor,
        rationale_artifact_id=rationale_artifact_id,
        constraints_checked=constraints_checked,
        workspace_root=workspace_root,
    )


def api_fleet_impact_explore(
    workspace_root: Path,
    swarm_ids: Optional[List[str]] = None,
    include_incidents: bool = True,
    include_work_items: bool = True,
    limit: int = 100,
) -> Dict[str, Any]:
    """GET /api/fleet/impact/explore."""
    return explore_impact(
        workspace_root,
        swarm_ids=swarm_ids,
        include_incidents=include_incidents,
        include_work_items=include_work_items,
        limit=limit,
    )
