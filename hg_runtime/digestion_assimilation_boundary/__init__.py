"""DAB Digestion Assimilation Boundary — fixture/static only."""

from hg_runtime.digestion_assimilation_boundary.evaluator import process_dab_bundle, refuse_dab_as_authority
from hg_runtime.digestion_assimilation_boundary.fixtures import analyze_dab_fixtures, load_dab_fixtures
from hg_runtime.digestion_assimilation_boundary.replay import replay_fixture_stream
from hg_runtime.digestion_assimilation_boundary.types import (
    FIXTURE_CLOCK,
    DigestionRequest,
    DigestionReceipt,
    DigestionSignal,
    classify_dab_claim_risk,
    dab_record_from_fixture,
)
from hg_core.dab_cluster.events import planned_dab_event_refs

__all__ = [
    "FIXTURE_CLOCK",
    "DigestionRequest",
    "DigestionReceipt",
    "DigestionSignal",
    "analyze_dab_fixtures",
    "classify_dab_claim_risk",
    "load_dab_fixtures",
    "planned_dab_event_refs",
    "process_dab_bundle",
    "dab_record_from_fixture",
    "refuse_dab_as_authority",
    "replay_fixture_stream",
]

