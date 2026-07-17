"""OEA-TER-LIVE runtime — governed live OEA/TER bridge; candidates are not authority."""

from hg_runtime.live_oea_ter_bridge.adapter import commit_to_fake_sink, request_to_fake_sink
from hg_runtime.live_oea_ter_bridge.evaluator import (
    analyze_oea_ter_fixtures,
    process_oea_ter_bundle,
    process_live_dispatch,
    replay_fixture_stream,
    run_oea_ter_bridge_fixture,
)
from hg_runtime.live_oea_ter_bridge.fixtures import FUTURE_EXPIRY, OEA_TER_FIXTURE_BUNDLES, PAST_EXPIRY, load_oea_ter_fixtures
from hg_runtime.live_oea_ter_bridge.rollback import compensate_from_rollback, rollback_live_action
from hg_runtime.live_oea_ter_bridge.tep_emission import (
    SOURCE_ORGAN,
    emit_fixture_dispatch_candidate,
    fence_live_oea_ter_emission,
    run_oea_ter_fixture_emission,
)
from hg_runtime.live_oea_ter_bridge.types import (
    FIXTURE_CLOCK,
    OEA_TER_SCHEMA_VERSION,
    ActionControlKind,
    CompensationRecord,
    ExternalSurface,
    LiveActionCandidate,
    LiveActionReceipt,
    LiveActionRequest,
    RollbackRecord,
    is_bare_operator_ref,
    is_valid_tim_freshness,
    request_from_fixture,
)
from hg_runtime.live_oea_ter_bridge.validator import refuse_oea_as_authority, validate_dispatch_request

__all__ = [
    "FIXTURE_CLOCK",
    "FUTURE_EXPIRY",
    "OEA_TER_FIXTURE_BUNDLES",
    "OEA_TER_SCHEMA_VERSION",
    "PAST_EXPIRY",
    "SOURCE_ORGAN",
    "ActionControlKind",
    "CompensationRecord",
    "ExternalSurface",
    "LiveActionCandidate",
    "LiveActionReceipt",
    "LiveActionRequest",
    "RollbackRecord",
    "analyze_oea_ter_fixtures",
    "commit_to_fake_sink",
    "compensate_from_rollback",
    "emit_fixture_dispatch_candidate",
    "fence_live_oea_ter_emission",
    "is_bare_operator_ref",
    "is_valid_tim_freshness",
    "load_oea_ter_fixtures",
    "process_oea_ter_bundle",
    "process_live_dispatch",
    "refuse_oea_as_authority",
    "replay_fixture_stream",
    "request_from_fixture",
    "request_to_fake_sink",
    "rollback_live_action",
    "run_oea_ter_bridge_fixture",
    "run_oea_ter_fixture_emission",
    "validate_dispatch_request",
]
