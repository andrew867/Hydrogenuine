"""REB re-entry boundary — all slices, no live resume."""

from hg_runtime.reentry_boundary.audit import audit_discontinuity_events
from hg_runtime.reentry_boundary.evaluator import (
    analyze_fixture_bundles,
    enqueue_fixture_queue,
    record_reentry_request,
    refuse_reentry_packet_as_permission,
    replay_fixture_stream,
    route_reentry_bundle,
)
from hg_runtime.reentry_boundary.events import planned_reb_event_refs
from hg_runtime.reentry_boundary.fixtures import load_fixture_bundles
from hg_runtime.reentry_boundary.proposal import dispatch_authority_chain_proposal
from hg_runtime.reentry_boundary.queue import FakeReEntryQueue
from hg_runtime.reentry_boundary.router import (
    assess_temporal_continuity,
    build_long_gap_policy,
    build_reentry_packet,
    decide_reentry,
    refuse_reb_as_authority,
    route_reentry_request,
)
from hg_runtime.reentry_boundary.types import (
    DiscontinuityEvent,
    FIXTURE_CLOCK,
    LongGapPolicy,
    ReEntryDecision,
    ReEntryPacket,
    ReEntryRequest,
    TemporalContinuityAssessment,
    discontinuity_from_fixture,
    reentry_request_from_fixture,
)

__all__ = [
    "DiscontinuityEvent",
    "FIXTURE_CLOCK",
    "FakeReEntryQueue",
    "LongGapPolicy",
    "ReEntryDecision",
    "ReEntryPacket",
    "ReEntryRequest",
    "TemporalContinuityAssessment",
    "analyze_fixture_bundles",
    "assess_temporal_continuity",
    "audit_discontinuity_events",
    "build_long_gap_policy",
    "build_reentry_packet",
    "decide_reentry",
    "discontinuity_from_fixture",
    "dispatch_authority_chain_proposal",
    "enqueue_fixture_queue",
    "load_fixture_bundles",
    "planned_reb_event_refs",
    "record_reentry_request",
    "refuse_reb_as_authority",
    "refuse_reentry_packet_as_permission",
    "replay_fixture_stream",
    "reentry_request_from_fixture",
    "route_reentry_bundle",
    "route_reentry_request",
]
