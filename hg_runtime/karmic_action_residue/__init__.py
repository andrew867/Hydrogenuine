"""KAR karmic action residue — residue is not punishment or permission."""

from hg_runtime.karmic_action_residue.events import planned_kar_event_refs
from hg_runtime.karmic_action_residue.residue import (
    evaluate_residue_fixture,
    evaluate_action_residue,
    refuse_residue_as_authority,
)
from hg_runtime.karmic_action_residue.types import (
    FIXTURE_CLOCK,
    ActionResidueRecord,
    classify_residue_risk,
    residue_from_fixture,
)

__all__ = [
    "FIXTURE_CLOCK",
    "ActionResidueRecord",
    "classify_residue_risk",
    "evaluate_action_residue",
    "evaluate_residue_fixture",
    "planned_kar_event_refs",
    "refuse_residue_as_authority",
    "residue_from_fixture",
]
