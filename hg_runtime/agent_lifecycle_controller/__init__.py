"""ALC Agent Lifecycle Controller — fixture/static only."""

from hg_runtime.agent_lifecycle_controller.evaluator import process_alc_bundle, refuse_alc_as_authority
from hg_runtime.agent_lifecycle_controller.fixtures import analyze_alc_fixtures, load_alc_fixtures
from hg_runtime.agent_lifecycle_controller.replay import replay_fixture_stream
from hg_runtime.agent_lifecycle_controller.types import (
    FIXTURE_CLOCK,
    LifecycleRecord,
    LifecycleReceipt,
    LifecycleSignal,
    classify_alc_claim_risk,
    alc_record_from_fixture,
)
from hg_core.alc_cluster.events import planned_alc_event_refs

__all__ = [
    "FIXTURE_CLOCK",
    "LifecycleRecord",
    "LifecycleReceipt",
    "LifecycleSignal",
    "analyze_alc_fixtures",
    "classify_alc_claim_risk",
    "load_alc_fixtures",
    "planned_alc_event_refs",
    "process_alc_bundle",
    "alc_record_from_fixture",
    "refuse_alc_as_authority",
    "replay_fixture_stream",
]
