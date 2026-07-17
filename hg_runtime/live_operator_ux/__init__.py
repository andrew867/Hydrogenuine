"""OUX-LIVE runtime — governed live operator review console; receipts are not authority."""

from hg_runtime.live_operator_ux.adapter import dispatch_to_fake_sink
from hg_runtime.live_operator_ux.audit import audit_operator_ux_events, record_audit_event
from hg_runtime.live_operator_ux.evaluator import (
    analyze_oux_fixtures,
    process_operator_control,
    process_oux_bundle,
    render_review_queue_view,
    replay_fixture_stream,
    run_console_adapter_fixture,
)
from hg_runtime.live_operator_ux.fixtures import FUTURE_EXPIRY, OUX_FIXTURE_BUNDLES, PAST_EXPIRY, load_oux_fixtures
from hg_runtime.live_operator_ux.tep_emission import (
    SOURCE_ORGAN,
    emit_fixture_ux_receipt,
    fence_live_rtc_emission,
    run_oux_fixture_emission,
)
from hg_runtime.live_operator_ux.types import (
    APPROVAL_EVIDENCE_ACTIONS,
    FIXTURE_CLOCK,
    OUX_SCHEMA_VERSION,
    OperatorActionRequest,
    OperatorReviewQueueView,
    OperatorSession,
    OperatorUXAuditRecord,
    OperatorUXReceipt,
    action_request_from_fixture,
    is_bare_operator_ref,
    is_valid_tim_freshness,
    session_from_fixture,
)
from hg_runtime.live_operator_ux.validator import refuse_oux_as_authority, validate_operator_action_request

__all__ = [
    "APPROVAL_EVIDENCE_ACTIONS",
    "FUTURE_EXPIRY",
    "FIXTURE_CLOCK",
    "OUX_FIXTURE_BUNDLES",
    "OUX_SCHEMA_VERSION",
    "PAST_EXPIRY",
    "SOURCE_ORGAN",
    "OperatorActionRequest",
    "OperatorReviewQueueView",
    "OperatorSession",
    "OperatorUXAuditRecord",
    "OperatorUXReceipt",
    "action_request_from_fixture",
    "analyze_oux_fixtures",
    "audit_operator_ux_events",
    "dispatch_to_fake_sink",
    "emit_fixture_ux_receipt",
    "fence_live_rtc_emission",
    "is_bare_operator_ref",
    "is_valid_tim_freshness",
    "load_oux_fixtures",
    "process_operator_control",
    "process_oux_bundle",
    "record_audit_event",
    "refuse_oux_as_authority",
    "render_review_queue_view",
    "replay_fixture_stream",
    "run_console_adapter_fixture",
    "run_oux_fixture_emission",
    "session_from_fixture",
    "validate_operator_action_request",
]
