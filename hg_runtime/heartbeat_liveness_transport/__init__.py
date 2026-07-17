"""HRT Heartbeat & Liveness Transport — fixture/static only."""

from hg_runtime.heartbeat_liveness_transport.evaluator import process_hrt_bundle, refuse_hrt_as_authority
from hg_runtime.heartbeat_liveness_transport.fixtures import analyze_hrt_fixtures, load_hrt_fixtures
from hg_runtime.heartbeat_liveness_transport.replay import replay_fixture_stream
from hg_runtime.heartbeat_liveness_transport.types import (
    FIXTURE_CLOCK,
    HeartbeatRecord,
    HeartbeatReceipt,
    LivenessSignal,
    classify_hrt_claim_risk,
    hrt_record_from_fixture,
)
from hg_core.hrt_cluster.events import planned_hrt_event_refs

__all__ = [
    "FIXTURE_CLOCK",
    "HeartbeatRecord",
    "HeartbeatReceipt",
    "LivenessSignal",
    "analyze_hrt_fixtures",
    "classify_hrt_claim_risk",
    "load_hrt_fixtures",
    "planned_hrt_event_refs",
    "process_hrt_bundle",
    "hrt_record_from_fixture",
    "refuse_hrt_as_authority",
    "replay_fixture_stream",
]
