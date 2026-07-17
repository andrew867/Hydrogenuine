"""AIS Autonomic Inference Substrate — fixture/static only."""

from hg_runtime.autonomic_inference_substrate.evaluator import process_ais_bundle, refuse_ais_as_authority
from hg_runtime.autonomic_inference_substrate.fixtures import analyze_ais_fixtures, load_ais_fixtures
from hg_runtime.autonomic_inference_substrate.replay import replay_fixture_stream
from hg_runtime.autonomic_inference_substrate.types import (
    FIXTURE_CLOCK,
    InferenceRequest,
    InferenceReceipt,
    InferencePressureSignal,
    classify_ais_claim_risk,
    ais_record_from_fixture,
)
from hg_core.ais_cluster.events import planned_ais_event_refs

__all__ = [
    "FIXTURE_CLOCK",
    "InferenceRequest",
    "InferenceReceipt",
    "InferencePressureSignal",
    "analyze_ais_fixtures",
    "classify_ais_claim_risk",
    "load_ais_fixtures",
    "planned_ais_event_refs",
    "process_ais_bundle",
    "ais_record_from_fixture",
    "refuse_ais_as_authority",
    "replay_fixture_stream",
]
