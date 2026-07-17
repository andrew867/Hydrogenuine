"""NRV Nervous Routing Layer — fixture/static only."""

from hg_runtime.nervous_routing_layer.evaluator import process_nrv_bundle, refuse_nrv_as_authority
from hg_runtime.nervous_routing_layer.fixtures import analyze_nrv_fixtures, load_nrv_fixtures
from hg_runtime.nervous_routing_layer.replay import replay_fixture_stream
from hg_runtime.nervous_routing_layer.types import (
    FIXTURE_CLOCK,
    RoutingRequest,
    RoutingReceipt,
    RoutingPressureSignal,
    classify_nrv_claim_risk,
    nrv_record_from_fixture,
)
from hg_core.nrv_cluster.events import planned_nrv_event_refs

__all__ = [
    "FIXTURE_CLOCK",
    "RoutingRequest",
    "RoutingReceipt",
    "RoutingPressureSignal",
    "analyze_nrv_fixtures",
    "classify_nrv_claim_risk",
    "load_nrv_fixtures",
    "planned_nrv_event_refs",
    "process_nrv_bundle",
    "nrv_record_from_fixture",
    "refuse_nrv_as_authority",
    "replay_fixture_stream",
]
