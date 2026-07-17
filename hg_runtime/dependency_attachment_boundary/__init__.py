"""DEP-BOND dependency attachment boundary — text fixture observations only."""

from hg_runtime.dependency_attachment_boundary.events import planned_rtc_events
from hg_runtime.dependency_attachment_boundary.observations import (
    evaluate_fixture,
    evaluate_observation,
    refuse_dependency_as_optimization,
)
from hg_runtime.dependency_attachment_boundary.types import (
    DEP_BOND_SCHEMA_VERSION,
    AllowedResponse,
    DependencyRiskObservation,
    RiskType,
    observation_from_fixture,
)

__all__ = [
    "AllowedResponse",
    "DEP_BOND_SCHEMA_VERSION",
    "DependencyRiskObservation",
    "RiskType",
    "evaluate_fixture",
    "evaluate_observation",
    "observation_from_fixture",
    "planned_rtc_events",
    "refuse_dependency_as_optimization",
]
