# Pack 14 API
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
from . import data_governance, red_team, supply_chain, cost_runaway, dr

def api_data_policies_list(workspace_root: Path) -> List[Dict[str, Any]]:
    return []

def api_data_policies_publish(workspace_root: Path, policy: Dict[str, Any], scope: Dict[str, str], actor: Dict[str, str]) -> str:
    return data_governance.publish_data_policy(workspace_root, policy, scope, actor)

def api_red_team_run(workspace_root: Path, scenario_id: str, scope: Dict[str, str], actor: Dict[str, str], seed: int = 42) -> Dict[str, Any]:
    return red_team.run_red_team_scenario(scenario_id, workspace_root, scope, actor, seed=seed)

def api_supply_chain_sbom(workspace_root: Path) -> List[Dict[str, Any]]:
    return supply_chain.get_sbom_refs(workspace_root)

def api_supply_chain_revoke(workspace_root: Path, plugin_id: str, scope: Dict[str, str], actor: Dict[str, str], reason: str = "") -> str:
    return supply_chain.revoke_plugin(plugin_id, workspace_root, scope, actor, reason)

def api_budgets_ceilings(workspace_root: Path) -> Dict[str, Any]:
    return {"ceilings": {}, "usage": {}}

def api_dr_drills_run(workspace_root: Path, drill_type: str, scope: Dict[str, str], actor: Dict[str, str]) -> Dict[str, Any]:
    return dr.run_drill(drill_type, workspace_root, scope, actor)
