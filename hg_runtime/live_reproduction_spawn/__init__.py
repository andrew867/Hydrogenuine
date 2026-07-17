"""RIB-SPAWN-LIVE runtime — governed reproduction spawn; spawn plans are not authority."""

from hg_runtime.live_reproduction_spawn.adapter import commit_to_fake_sink, plan_to_fake_sink
from hg_runtime.live_reproduction_spawn.evaluator import (
    analyze_rib_spawn_fixtures,
    process_reproduction_spawn,
    process_rib_spawn_bundle,
    replay_fixture_stream,
    run_reproduction_spawn_fixture,
)
from hg_runtime.live_reproduction_spawn.fixtures import FUTURE_EXPIRY, PAST_EXPIRY, RIB_SPAWN_FIXTURE_BUNDLES, load_rib_spawn_fixtures
from hg_runtime.live_reproduction_spawn.rollback import rollback_spawn_plan
from hg_runtime.live_reproduction_spawn.tep_emission import (
    SOURCE_ORGAN,
    emit_fixture_spawn_plan,
    fence_live_spawn_emission,
    run_rib_spawn_fixture_emission,
)
from hg_runtime.live_reproduction_spawn.types import (
    FIXTURE_CLOCK,
    RIB_SPAWN_SCHEMA_VERSION,
    ChildIdentityProfile,
    ChildSpawnReceipt,
    ChildSpawnRequest,
    FailedSpawnRecord,
    child_identity_distinct,
    is_bare_operator_ref,
    is_valid_tim_freshness,
    request_from_fixture,
)
from hg_runtime.live_reproduction_spawn.validator import refuse_rib_spawn_as_authority, validate_spawn_request

__all__ = [
    "FIXTURE_CLOCK",
    "FUTURE_EXPIRY",
    "PAST_EXPIRY",
    "RIB_SPAWN_FIXTURE_BUNDLES",
    "RIB_SPAWN_SCHEMA_VERSION",
    "SOURCE_ORGAN",
    "ChildIdentityProfile",
    "ChildSpawnReceipt",
    "ChildSpawnRequest",
    "FailedSpawnRecord",
    "analyze_rib_spawn_fixtures",
    "child_identity_distinct",
    "commit_to_fake_sink",
    "emit_fixture_spawn_plan",
    "fence_live_spawn_emission",
    "is_bare_operator_ref",
    "is_valid_tim_freshness",
    "load_rib_spawn_fixtures",
    "plan_to_fake_sink",
    "process_reproduction_spawn",
    "process_rib_spawn_bundle",
    "refuse_rib_spawn_as_authority",
    "replay_fixture_stream",
    "request_from_fixture",
    "rollback_spawn_plan",
    "run_reproduction_spawn_fixture",
    "run_rib_spawn_fixture_emission",
    "validate_spawn_request",
]
