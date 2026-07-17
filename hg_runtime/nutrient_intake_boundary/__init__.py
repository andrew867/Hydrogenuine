"""NIB Nutrient Intake Boundary — fixture/static only."""

from hg_runtime.nutrient_intake_boundary.evaluator import process_nib_bundle, refuse_nib_as_authority
from hg_runtime.nutrient_intake_boundary.fixtures import analyze_nib_fixtures, load_nib_fixtures
from hg_runtime.nutrient_intake_boundary.replay import replay_fixture_stream
from hg_runtime.nutrient_intake_boundary.types import (
    FIXTURE_CLOCK,
    IntakeRequest,
    IntakeReceipt,
    IntakeSignal,
    classify_nib_claim_risk,
    nib_record_from_fixture,
)
from hg_core.nib_cluster.events import planned_nib_event_refs

__all__ = [
    "FIXTURE_CLOCK",
    "IntakeRequest",
    "IntakeReceipt",
    "IntakeSignal",
    "analyze_nib_fixtures",
    "classify_nib_claim_risk",
    "load_nib_fixtures",
    "planned_nib_event_refs",
    "process_nib_bundle",
    "nib_record_from_fixture",
    "refuse_nib_as_authority",
    "replay_fixture_stream",
]

