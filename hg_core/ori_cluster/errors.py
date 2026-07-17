"""ORI cluster validation errors — review receipts are not authority."""

from __future__ import annotations

REFUSED_ORI_AS_AUTHORITY = "ori.refused.review_as_authority"
REFUSED_STALE_APPROVAL_RECEIPT = "ori.refused.stale_approval_receipt"
INERT_MISSING_OPERATOR_REF = "ori.inert.missing_operator_ref"
INERT_UNREGISTERED_OPERATOR_REF = "ori.inert.unregistered_operator_ref"
INERT_MISSING_SCOPE = "ori.inert.missing_approval_scope"
INERT_OUT_OF_SCOPE = "ori.inert.out_of_scope_approval"
INERT_OPERATOR_REVOKED = "ori.inert.operator_revoked"
INERT_BARE_OPERATOR_REF = "ori.inert.bare_operator_ref"
INERT_MISSING_EXPIRY = "ori.inert.missing_approval_expiry"
ORI_RECEIPT_RECORDED = "ori.advisory.receipt_recorded"
ORI_APPROVAL_EVIDENCE_BOUND = "ori.advisory.approval_evidence_bound"
ORI_REVIEW_REQUEST_RECORDED = "ori.advisory.review_request_recorded"
ORI_REVIEW_ITEM_CREATED = "ori.advisory.review_item_created"
ORI_REVIEW_BATCH_CREATED = "ori.advisory.review_batch_created"
ORI_DEDUPLICATION_APPLIED = "ori.advisory.deduplication_applied"
ORI_PRIORITY_ASSIGNED = "ori.advisory.priority_assigned"
ORI_OPERATOR_OVERLOAD_SIGNAL_RECORDED = "ori.advisory.overload_signal_recorded"
ORI_CRITICAL_REVIEW_ESCALATED = "ori.advisory.critical_review_escalated"
ORI_LOW_PRIORITY_DEFERRED = "ori.advisory.low_priority_deferred"
ORI_SILENCE_NOT_APPROVAL = "ori.advisory.silence_not_approval"
ORI_EXPIRY_NOT_APPROVAL = "ori.advisory.expiry_not_approval"
ORI_PRIORITY_NOT_PERMISSION = "ori.advisory.priority_not_permission"
ORI_AUTHORITY_CONVERSION_CONTAINED = "ori.contained.authority_conversion"
ORI_SIGNAL_REFUSED = "ori.refused.signal"
REFUSED_FORBIDDEN_INTAKE = "ori.refused.forbidden_intake"


class OriValidationError(ValueError):
    """Raised when ORI records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "INERT_BARE_OPERATOR_REF",
    "INERT_MISSING_EXPIRY",
    "INERT_MISSING_OPERATOR_REF",
    "INERT_MISSING_SCOPE",
    "INERT_OPERATOR_REVOKED",
    "INERT_OUT_OF_SCOPE",
    "INERT_UNREGISTERED_OPERATOR_REF",
    "ORI_APPROVAL_EVIDENCE_BOUND",
    "ORI_AUTHORITY_CONVERSION_CONTAINED",
    "ORI_CRITICAL_REVIEW_ESCALATED",
    "ORI_DEDUPLICATION_APPLIED",
    "ORI_EXPIRY_NOT_APPROVAL",
    "ORI_LOW_PRIORITY_DEFERRED",
    "ORI_OPERATOR_OVERLOAD_SIGNAL_RECORDED",
    "ORI_PRIORITY_ASSIGNED",
    "ORI_PRIORITY_NOT_PERMISSION",
    "ORI_RECEIPT_RECORDED",
    "ORI_REVIEW_BATCH_CREATED",
    "ORI_REVIEW_ITEM_CREATED",
    "ORI_REVIEW_REQUEST_RECORDED",
    "ORI_SIGNAL_REFUSED",
    "ORI_SILENCE_NOT_APPROVAL",
    "OriValidationError",
    "REFUSED_FORBIDDEN_INTAKE",
    "REFUSED_ORI_AS_AUTHORITY",
    "REFUSED_STALE_APPROVAL_RECEIPT",
]
