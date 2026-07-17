"""GMG-LIVE runtime — governed tool/memory/context grants; candidates are not authority."""

from hg_runtime.grant_authority_live.adapter import commit_to_fake_sink, request_to_fake_sink
from hg_runtime.grant_authority_live.evaluator import (
    analyze_gmg_fixtures,
    process_gmg_bundle,
    process_grant_authority,
    replay_fixture_stream,
    run_grant_authority_fixture,
)
from hg_runtime.grant_authority_live.fixtures import (
    FUTURE_EXPIRY,
    GMG_FIXTURE_BUNDLES,
    PAST_EXPIRY,
    PAST_GRANT_EXPIRY,
    load_gmg_fixtures,
)
from hg_runtime.grant_authority_live.revocation import record_grant_expiry, revoke_grant
from hg_runtime.grant_authority_live.tep_emission import (
    SOURCE_ORGAN,
    emit_fixture_grant_candidate,
    fence_live_grant_emission,
    run_gmg_fixture_emission,
)
from hg_runtime.grant_authority_live.types import (
    FIXTURE_CLOCK,
    GMG_SCHEMA_VERSION,
    GrantAuditRecord,
    GrantCandidate,
    GrantControlKind,
    GrantExpiryRecord,
    GrantReceipt,
    GrantRequest,
    GrantRevocation,
    GrantType,
    is_ambient_grant_scope,
    is_bare_operator_ref,
    is_valid_tim_freshness,
    request_from_fixture,
)
from hg_runtime.grant_authority_live.validator import refuse_grant_as_authority, validate_grant_request

__all__ = [
    "FIXTURE_CLOCK",
    "FUTURE_EXPIRY",
    "GMG_FIXTURE_BUNDLES",
    "GMG_SCHEMA_VERSION",
    "PAST_EXPIRY",
    "PAST_GRANT_EXPIRY",
    "SOURCE_ORGAN",
    "GrantAuditRecord",
    "GrantCandidate",
    "GrantControlKind",
    "GrantExpiryRecord",
    "GrantReceipt",
    "GrantRequest",
    "GrantRevocation",
    "GrantType",
    "analyze_gmg_fixtures",
    "commit_to_fake_sink",
    "emit_fixture_grant_candidate",
    "fence_live_grant_emission",
    "is_ambient_grant_scope",
    "is_bare_operator_ref",
    "is_valid_tim_freshness",
    "load_gmg_fixtures",
    "process_gmg_bundle",
    "process_grant_authority",
    "record_grant_expiry",
    "refuse_grant_as_authority",
    "replay_fixture_stream",
    "request_from_fixture",
    "request_to_fake_sink",
    "revoke_grant",
    "run_gmg_fixture_emission",
    "run_grant_authority_fixture",
    "validate_grant_request",
]
