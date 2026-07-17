"""ARB cluster validation errors — route is not permission."""

from __future__ import annotations

REFUSED_ARB_AS_AUTHORITY = "arb.refused.agency_routing_as_authority"
REFUSED_STALE_POLICY = "arb.refused.stale_policy"
REFUSED_FORBIDDEN_ROUTING = "arb.refused.forbidden_routing"
REFUSED_UNKNOWN_SIGNAL = "arb.refused.unknown_signal"
REFUSED_AUTHORITY_CONVERSION = "arb.refused.authority_conversion"
ADVISORY_CONTAINMENT_WAIVED_ARB = "arb.advisory.containment_waived"
ARB_ROUTE_RECORDED = "arb.advisory.route_recorded"
ARB_AUTHORITY_CONVERSION_CONTAINED = "arb.advisory.authority_conversion_contained"
ARB_UNKNOWN_SIGNAL_FAILED_CLOSED = "arb.advisory.unknown_signal_failed_closed"
ARB_FORBIDDEN_ROUTE_REFUSED = "arb.advisory.forbidden_route_refused"
ARB_ROUTE_CONFLICT_FAIL_CLOSED = "arb.advisory.route_conflict_fail_closed"
ARB_ROUTE_EVENT_RECORDED = "arb.advisory.route_event_recorded"
ARB_FIXTURE_QUEUE_ENQUEUED = "arb.advisory.fixture_queue_enqueued"
ARB_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED = "arb.advisory.authority_chain_proposal_dispatched"


class ArbValidationError(ValueError):
    """Raised when ARB records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "ADVISORY_CONTAINMENT_WAIVED_ARB",
    "ARB_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED",
    "ARB_AUTHORITY_CONVERSION_CONTAINED",
    "ARB_FIXTURE_QUEUE_ENQUEUED",
    "ARB_ROUTE_EVENT_RECORDED",
    "ARB_FORBIDDEN_ROUTE_REFUSED",
    "ARB_ROUTE_CONFLICT_FAIL_CLOSED",
    "ARB_ROUTE_RECORDED",
    "ARB_UNKNOWN_SIGNAL_FAILED_CLOSED",
    "ArbValidationError",
    "REFUSED_ARB_AS_AUTHORITY",
    "REFUSED_AUTHORITY_CONVERSION",
    "REFUSED_FORBIDDEN_ROUTING",
    "REFUSED_STALE_POLICY",
    "REFUSED_UNKNOWN_SIGNAL",
]
