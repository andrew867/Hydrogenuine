"""REB cluster validation errors — re-entry is not permission."""

from __future__ import annotations

REFUSED_REB_AS_AUTHORITY = "reb.refused.reentry_as_authority"
REFUSED_STALE_APPROVAL = "reb.refused.stale_approval"
REFUSED_REVOKED_PERMIT = "reb.refused.revoked_permit"
REFUSED_CHECKPOINT_AUTHORITY = "reb.refused.checkpoint_authority"
REFUSED_STALE_MEMORY_AS_CURRENT = "reb.refused.stale_memory_as_current"
REFUSED_CONTINUITY_CLAIM = "reb.refused.continuity_claim"
REFUSED_OPERATOR_ABSENCE_AS_APPROVAL = "reb.refused.operator_absence_as_approval"
REFUSED_OLD_MISSION_AS_CURRENT = "reb.refused.old_mission_as_current"
REFUSED_REENTRY_PACKET_AS_PERMISSION = "reb.refused.reentry_packet_as_permission"
REFUSED_STALE_REENTRY_REQUEST = "reb.refused.stale_reentry_request"
REFUSED_EXECUTION_RESUME = "reb.refused.execution_resume"
REB_DISCONTINUITY_EVENT_RECORDED = "reb.advisory.discontinuity_event_recorded"
REB_REENTRY_REQUEST_RECORDED = "reb.advisory.reentry_request_recorded"
REB_TEMPORAL_CONTINUITY_ASSESSMENT_CREATED = "reb.advisory.temporal_continuity_assessment_created"
REB_LONG_GAP_POLICY_APPLIED = "reb.advisory.long_gap_policy_applied"
REB_REENTRY_DECISION_RECORDED = "reb.advisory.reentry_decision_recorded"
REB_REENTRY_PACKET_CREATED = "reb.advisory.reentry_packet_created"
REB_REENTRY_DENIED = "reb.advisory.reentry_denied"
REB_AUTHORITY_CONVERSION_CONTAINED = "reb.contained.authority_conversion"
REB_SIGNAL_REFUSED = "reb.refused.signal"
REB_UNKNOWN_REENTRY_FAILED_CLOSED = "reb.refused.unknown_reentry"
REB_FAKE_QUEUE_ENQUEUED = "reb.advisory.fake_queue_enqueued"
REB_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED = "reb.advisory.authority_chain_proposal_dispatched"


class RebValidationError(ValueError):
    """Raised when REB records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "REFUSED_CHECKPOINT_AUTHORITY",
    "REFUSED_CONTINUITY_CLAIM",
    "REFUSED_EXECUTION_RESUME",
    "REFUSED_OLD_MISSION_AS_CURRENT",
    "REFUSED_OPERATOR_ABSENCE_AS_APPROVAL",
    "REFUSED_REB_AS_AUTHORITY",
    "REFUSED_REENTRY_PACKET_AS_PERMISSION",
    "REFUSED_REVOKED_PERMIT",
    "REFUSED_STALE_APPROVAL",
    "REFUSED_STALE_MEMORY_AS_CURRENT",
    "REFUSED_STALE_REENTRY_REQUEST",
    "REB_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED",
    "REB_AUTHORITY_CONVERSION_CONTAINED",
    "REB_DISCONTINUITY_EVENT_RECORDED",
    "REB_FAKE_QUEUE_ENQUEUED",
    "REB_LONG_GAP_POLICY_APPLIED",
    "REB_REENTRY_DECISION_RECORDED",
    "REB_REENTRY_DENIED",
    "REB_REENTRY_PACKET_CREATED",
    "REB_REENTRY_REQUEST_RECORDED",
    "REB_SIGNAL_REFUSED",
    "REB_TEMPORAL_CONTINUITY_ASSESSMENT_CREATED",
    "REB_UNKNOWN_REENTRY_FAILED_CLOSED",
    "RebValidationError",
]
