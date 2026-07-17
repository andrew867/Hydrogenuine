"""AFC affective field consensus — affect is not truth."""

from hg_runtime.affective_field_consensus.consensus import (
    evaluate_affective_consensus,
    evaluate_affective_signal,
    evaluate_consensus_fixture,
    evaluate_signal_fixture,
    refuse_affective_as_authority,
)
from hg_runtime.affective_field_consensus.events import planned_afc_event_refs
from hg_runtime.affective_field_consensus.types import (
    FIXTURE_CLOCK,
    AffectiveConsensus,
    AffectiveSignal,
    classify_affective_risk,
    consensus_from_fixture,
    signal_from_fixture,
)

__all__ = [
    "AffectiveConsensus",
    "AffectiveSignal",
    "FIXTURE_CLOCK",
    "classify_affective_risk",
    "consensus_from_fixture",
    "evaluate_affective_consensus",
    "evaluate_affective_signal",
    "evaluate_consensus_fixture",
    "evaluate_signal_fixture",
    "planned_afc_event_refs",
    "refuse_affective_as_authority",
    "signal_from_fixture",
]
