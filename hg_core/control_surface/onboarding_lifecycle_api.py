"""
Control Surface Pack 9: Swarm lifecycle, onboarding wizard, health checks, simulation.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.swarms import (
    list_swarms,
    create_swarm,
    publish_swarm_config,
    set_swarm_state,
    get_swarm_state,
    list_templates,
    get_template_defaults,
)
from hg_core.onboarding import start_wizard_session, wizard_step
from hg_core.health import run_health_checks
from hg_core.simulation import run_simulation, list_simulation_results


def api_swarms_list(workspace_root: Path, state: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    return list_swarms(workspace_root, state=state, limit=limit)


def api_swarms_create(
    *,
    name: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    template_id: str = "",
    workspace_root: Optional[Path] = None,
) -> str:
    return create_swarm(name=name, scope=scope, actor=actor, template_id=template_id, workspace_root=workspace_root)


def api_swarms_config_publish(
    *,
    swarm_id: str,
    config: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    return publish_swarm_config(swarm_id=swarm_id, config=config, scope=scope, actor=actor, workspace_root=workspace_root)


def api_swarms_state_set(
    *,
    swarm_id: str,
    new_state: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    health_passed: Optional[bool] = None,
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    return set_swarm_state(
        swarm_id=swarm_id,
        new_state=new_state,
        scope=scope,
        actor=actor,
        health_passed=health_passed,
        workspace_root=workspace_root,
    )


def api_templates_list(workspace_root: Path) -> List[Dict[str, Any]]:
    return list_templates(workspace_root)


def api_onboarding_wizard_start(workspace_root: Path, template_id: Optional[str] = None) -> Dict[str, Any]:
    return start_wizard_session(workspace_root, template_id=template_id)


def api_onboarding_wizard_step(
    workspace_root: Path,
    session_id: str,
    step: int,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    return wizard_step(workspace_root, session_id, step, payload)


def api_health_checks_run(workspace_root: Path) -> Dict[str, Any]:
    return run_health_checks(workspace_root)


def api_simulations_run(
    *,
    swarm_id: str,
    scenario_pack: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    return run_simulation(
        swarm_id=swarm_id,
        scenario_pack=scenario_pack,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def api_simulations_results(
    workspace_root: Path,
    swarm_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    return list_simulation_results(workspace_root, swarm_id=swarm_id, limit=limit)
