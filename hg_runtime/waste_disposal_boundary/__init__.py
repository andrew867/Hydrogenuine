"""WDB Waste Disposal Boundary — fixture/static only."""

from hg_runtime.waste_disposal_boundary.evaluator import process_wdb_bundle, refuse_wdb_as_authority
from hg_runtime.waste_disposal_boundary.fixtures import analyze_wdb_fixtures, load_wdb_fixtures
from hg_runtime.waste_disposal_boundary.replay import replay_fixture_stream
from hg_runtime.waste_disposal_boundary.types import (
    FIXTURE_CLOCK,
    WasteCandidate,
    WasteReceipt,
    WasteSignal,
    classify_wdb_claim_risk,
    wdb_record_from_fixture,
)
from hg_core.wdb_cluster.events import planned_wdb_event_refs

__all__ = [
    "FIXTURE_CLOCK",
    "WasteCandidate",
    "WasteReceipt",
    "WasteSignal",
    "analyze_wdb_fixtures",
    "classify_wdb_claim_risk",
    "load_wdb_fixtures",
    "planned_wdb_event_refs",
    "process_wdb_bundle",
    "wdb_record_from_fixture",
    "refuse_wdb_as_authority",
    "replay_fixture_stream",
]

