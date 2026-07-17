"""RIB reproduction/inheritance boundary — full slice scope."""

from hg_runtime.reproduction_inheritance_boundary.audit import audit_spawn_events
from hg_runtime.reproduction_inheritance_boundary.evaluator import (
    analyze_fixture_bundles,
    enqueue_fixture_bootstrap_queue,
    record_spawn_request,
    refuse_bootstrap_as_permission,
    refuse_failed_spawn_as_active_child,
    refuse_unbounded_retry,
    replay_fixture_stream,
    route_spawn_bundle,
)
from hg_runtime.reproduction_inheritance_boundary.events import planned_rib_event_refs
from hg_runtime.reproduction_inheritance_boundary.fixtures import load_fixture_bundles
from hg_runtime.reproduction_inheritance_boundary.proposal import (
    dispatch_authority_chain_child_proposal,
    refuse_bootstrap_packet_as_permission,
)
from hg_runtime.reproduction_inheritance_boundary.queue import FakeChildBootstrapQueue
from hg_runtime.reproduction_inheritance_boundary.router import (
    build_child_bootstrap_packet,
    decide_inheritance,
    refuse_rib_as_authority,
    route_spawn_request,
)
from hg_runtime.reproduction_inheritance_boundary.types import (
    ChildBootstrapPacket,
    ChildLifecycleReceipt,
    FailedSpawnRecord,
    FIXTURE_CLOCK,
    InheritanceDecision,
    SpawnRequest,
    spawn_request_from_fixture,
)

__all__ = [
    "ChildBootstrapPacket",
    "ChildLifecycleReceipt",
    "FIXTURE_CLOCK",
    "FailedSpawnRecord",
    "FakeChildBootstrapQueue",
    "InheritanceDecision",
    "SpawnRequest",
    "analyze_fixture_bundles",
    "audit_spawn_events",
    "build_child_bootstrap_packet",
    "decide_inheritance",
    "dispatch_authority_chain_child_proposal",
    "enqueue_fixture_bootstrap_queue",
    "load_fixture_bundles",
    "planned_rib_event_refs",
    "record_spawn_request",
    "refuse_bootstrap_as_permission",
    "refuse_bootstrap_packet_as_permission",
    "refuse_failed_spawn_as_active_child",
    "refuse_rib_as_authority",
    "refuse_unbounded_retry",
    "replay_fixture_stream",
    "route_spawn_bundle",
    "route_spawn_request",
    "spawn_request_from_fixture",
]
