"""Resource Scarcity Controller — static fixture first slice."""

from hg_runtime.resource_scarcity_controller.controller import (
    evaluate_overrun_risk,
    evaluate_resource_posture,
    refuse_rsc_as_authority,
)
from hg_runtime.resource_scarcity_controller.events import planned_rsc_event_refs
from hg_runtime.resource_scarcity_controller.types import (
    ResourceOverrunRisk,
    ResourcePosture,
    posture_from_fixture,
    risk_from_fixture,
)

__all__ = [
    "ResourceOverrunRisk",
    "ResourcePosture",
    "evaluate_overrun_risk",
    "evaluate_resource_posture",
    "planned_rsc_event_refs",
    "posture_from_fixture",
    "refuse_rsc_as_authority",
    "risk_from_fixture",
]
