"""RIB cluster validation errors — reproduction/inheritance is not permission."""

from __future__ import annotations

REFUSED_RIB_AS_AUTHORITY = "rib.refused.reproduction_as_authority"
REFUSED_PARENT_PERMIT_INHERITANCE = "rib.refused.parent_permit_inheritance"
REFUSED_PARENT_IDENTITY_INHERITANCE = "rib.refused.parent_identity_inheritance"
REFUSED_PARENT_TRUST_INHERITANCE = "rib.refused.parent_trust_inheritance"
REFUSED_EXECUTION_ADMISSION_INHERITANCE = "rib.refused.execution_admission_inheritance"
REFUSED_TOOL_GRANT_INHERITANCE = "rib.refused.tool_grant_inheritance"
REFUSED_SECRET_INHERITANCE = "rib.refused.secret_inheritance"
REFUSED_SELF_PRESERVATION = "rib.refused.self_preservation"
REFUSED_BOOTSTRAP_AS_PERMISSION = "rib.refused.bootstrap_as_permission"
REFUSED_FAILED_SPAWN_AS_ACTIVE_CHILD = "rib.refused.failed_spawn_as_active_child"
REFUSED_PARTIAL_SPAWN_WITHOUT_ROLLBACK = "rib.refused.partial_spawn_without_rollback"
REFUSED_UNBOUNDED_RETRY = "rib.refused.unbounded_retry"
RIB_SPAWN_REQUEST_RECORDED = "rib.advisory.spawn_request_recorded"
RIB_INHERITANCE_DECISION_RECORDED = "rib.advisory.inheritance_decision_recorded"
RIB_BOOTSTRAP_PACKET_CREATED = "rib.advisory.bootstrap_packet_created"
RIB_CHILD_SPAWN_DENIED = "rib.advisory.child_spawn_denied"
RIB_CHILD_FAILED_SPAWN_RECORDED = "rib.advisory.child_failed_spawn_recorded"
RIB_CHILD_PARTIAL_SPAWN_RECORDED = "rib.advisory.child_partial_spawn_recorded"
RIB_CHILD_ROLLBACK_REQUESTED = "rib.advisory.child_rollback_requested"
RIB_CHILD_LIFECYCLE_RECEIPT_CREATED = "rib.advisory.child_lifecycle_receipt_created"
RIB_PARENT_CHILD_AUTHORITY_SEPARATED = "rib.advisory.parent_child_authority_separated"
RIB_INHERITED_PERMISSION_REFUSED = "rib.refused.inherited_permission"
RIB_INHERITED_IDENTITY_REFUSED = "rib.refused.inherited_identity"
RIB_AUTHORITY_CONVERSION_CONTAINED = "rib.contained.authority_conversion"
RIB_SIGNAL_REFUSED = "rib.refused.signal"
REFUSED_STALE_SPAWN_REQUEST = "rib.refused.stale_spawn_request"
RIB_UNKNOWN_INHERITANCE_FAILED_CLOSED = "rib.refused.unknown_inheritance"
RIB_FAKE_QUEUE_ENQUEUED = "rib.advisory.fake_queue_enqueued"
RIB_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED = "rib.advisory.authority_chain_proposal_dispatched"


class RibValidationError(ValueError):
    """Raised when RIB records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.code = code


__all__ = [
    "REFUSED_BOOTSTRAP_AS_PERMISSION",
    "REFUSED_EXECUTION_ADMISSION_INHERITANCE",
    "REFUSED_FAILED_SPAWN_AS_ACTIVE_CHILD",
    "REFUSED_PARENT_IDENTITY_INHERITANCE",
    "REFUSED_PARENT_PERMIT_INHERITANCE",
    "REFUSED_PARENT_TRUST_INHERITANCE",
    "REFUSED_PARTIAL_SPAWN_WITHOUT_ROLLBACK",
    "REFUSED_RIB_AS_AUTHORITY",
    "REFUSED_SECRET_INHERITANCE",
    "REFUSED_SELF_PRESERVATION",
    "REFUSED_STALE_SPAWN_REQUEST",
    "REFUSED_TOOL_GRANT_INHERITANCE",
    "REFUSED_UNBOUNDED_RETRY",
    "RIB_AUTHORITY_CONVERSION_CONTAINED",
    "RIB_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED",
    "RIB_BOOTSTRAP_PACKET_CREATED",
    "RIB_CHILD_FAILED_SPAWN_RECORDED",
    "RIB_FAKE_QUEUE_ENQUEUED",
    "RIB_CHILD_LIFECYCLE_RECEIPT_CREATED",
    "RIB_CHILD_PARTIAL_SPAWN_RECORDED",
    "RIB_CHILD_ROLLBACK_REQUESTED",
    "RIB_CHILD_SPAWN_DENIED",
    "RIB_INHERITED_IDENTITY_REFUSED",
    "RIB_INHERITED_PERMISSION_REFUSED",
    "RIB_INHERITANCE_DECISION_RECORDED",
    "RIB_PARENT_CHILD_AUTHORITY_SEPARATED",
    "RIB_SIGNAL_REFUSED",
    "RIB_SPAWN_REQUEST_RECORDED",
    "RIB_UNKNOWN_INHERITANCE_FAILED_CLOSED",
    "RibValidationError",
]
