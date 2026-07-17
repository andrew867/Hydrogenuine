"""Pack 11: Taxonomy adapter - internal event -> public class."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

EVENT_TO_PUBLIC_CLASS: Dict[str, str] = {
    "SWARM_CREATED": "SwarmLifecycle",
    "SWARM_CONFIG_PUBLISHED": "SwarmLifecycle",
    "SWARM_STATE_CHANGED": "SwarmLifecycle",
    "WORK_ITEM_ROUTED": "Routing",
    "WORK_ITEM_CREATED": "WorkItem",
    "WORK_ITEM_UPDATED": "WorkItem",
    "WORK_ITEM_BLOCKED": "WorkItem",
    "GLOBAL_CONTROL_APPLIED": "GlobalControl",
    "GLOBAL_CONTROL_DENIED": "GlobalControl",
    "ORCHESTRATION_ACTION_APPLIED": "Orchestration",
    "STEERING_DIRECTIVE_PUBLISHED": "Steering",
    "STEERING_DIRECTIVE_APPLIED": "Steering",
    "GOAL_INTEGRITY_SCORE_COMPUTED": "GoalIntegrity",
    "GROUP_DRIFT_SCORE_COMPUTED": "GroupDrift",
    "DRIFT_SCORE_COMPUTED": "Drift",
    "DRIFT_SAFEGUARD_APPLIED": "Drift",
    "ENTITY_PAUSED": "Control",
    "ENTITY_RESUMED": "Control",
    "CONTROL_OVERRIDE_APPLIED": "Control",
    "AUTONOMY_PRESET_APPLIED": "Steering",
    "SIMULATION_RUN_STARTED": "Simulation",
    "SIMULATION_RUN_COMPLETED": "Simulation",
    "PINSET_PUBLISHED": "Pinset",
    "PINSET_APPLIED": "Pinset",
}


def get_public_class(internal_action: str) -> Optional[str]:
    return EVENT_TO_PUBLIC_CLASS.get(internal_action)


def list_taxonomy_mappings() -> List[Dict[str, Any]]:
    return [{"internal_name": k, "conceptual_class": v} for k, v in sorted(EVENT_TO_PUBLIC_CLASS.items())]
