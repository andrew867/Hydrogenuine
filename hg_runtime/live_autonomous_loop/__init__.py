"""ALOOP-LIVE runtime — governed autonomous loop supervisor; leases are not authority."""

from hg_runtime.live_autonomous_loop.adapter import lease_to_fake_sink, supervise_to_fake_sink
from hg_runtime.live_autonomous_loop.evaluator import (
    analyze_aloop_fixtures,
    process_aloop_bundle,
    process_autonomous_loop,
    replay_fixture_stream,
    run_autonomous_loop_fixture,
)
from hg_runtime.live_autonomous_loop.fixtures import (
    ALOOP_FIXTURE_BUNDLES,
    FUTURE_EXPIRY,
    FUTURE_LEASE,
    PAST_EXPIRY,
    PAST_LEASE,
    load_aloop_fixtures,
)
from hg_runtime.live_autonomous_loop.rollback import record_loop_pause, rollback_loop_supervisor
from hg_runtime.live_autonomous_loop.tep_emission import (
    SOURCE_ORGAN,
    emit_fixture_loop_lease,
    fence_live_loop_emission,
    run_aloop_fixture_emission,
)
from hg_runtime.live_autonomous_loop.types import (
    ALOOP_SCHEMA_VERSION,
    FIXTURE_CLOCK,
    AutonomousLoopRequest,
    LoopLease,
    LoopSupervisorReceipt,
    LoopSupervisorState,
    is_bare_operator_ref,
    is_valid_tim_freshness,
    request_from_fixture,
)
from hg_runtime.live_autonomous_loop.validator import refuse_aloop_as_authority, validate_loop_request

__all__ = [
    "ALOOP_FIXTURE_BUNDLES",
    "ALOOP_SCHEMA_VERSION",
    "FIXTURE_CLOCK",
    "FUTURE_EXPIRY",
    "FUTURE_LEASE",
    "PAST_EXPIRY",
    "PAST_LEASE",
    "SOURCE_ORGAN",
    "AutonomousLoopRequest",
    "LoopLease",
    "LoopSupervisorReceipt",
    "LoopSupervisorState",
    "analyze_aloop_fixtures",
    "emit_fixture_loop_lease",
    "fence_live_loop_emission",
    "is_bare_operator_ref",
    "is_valid_tim_freshness",
    "lease_to_fake_sink",
    "load_aloop_fixtures",
    "process_aloop_bundle",
    "process_autonomous_loop",
    "record_loop_pause",
    "refuse_aloop_as_authority",
    "replay_fixture_stream",
    "request_from_fixture",
    "rollback_loop_supervisor",
    "run_aloop_fixture_emission",
    "run_autonomous_loop_fixture",
    "supervise_to_fake_sink",
    "validate_loop_request",
]
