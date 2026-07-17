"""IMS cluster validation errors — inference model scheduler is not authority."""

from __future__ import annotations

REFUSED_IMS_AS_AUTHORITY = "ims.refused.ims_as_authority"
REFUSED_STALE_INPUT = "ims.refused.stale_input"
REFUSED_UNKNOWN_REQUEST = "ims.refused.unknown_request"
REFUSED_FORBIDDEN_IMS_CLAIM = "ims.refused.forbidden_claim"
IMS_AUTHORITY_CONVERSION_CONTAINED = "ims.contained.authority_conversion"
IMS_RECORDED = "ims.advisory.recorded"
IMS_RECEIPT_CREATED = "ims.advisory.receipt_created"
IMS_FAILED_CLOSED = "ims.refused.failed_closed"

REFUSED_SCHEDULER_AS_PERMISSION = "ims.refused.scheduler_as_permission"
REFUSED_ESCALATION_AS_GRANT = "ims.refused.escalation_as_grant"
REFUSED_CONTEXT_GRANT = "ims.refused.context_grant"


class IMSValidationError(ValueError):
    """Raised when IMS records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "IMS_AUTHORITY_CONVERSION_CONTAINED",
    "IMS_FAILED_CLOSED",
    "IMS_RECORDED",
    "IMS_RECEIPT_CREATED",
    "IMSValidationError",
    "REFUSED_FORBIDDEN_IMS_CLAIM",
    "REFUSED_STALE_INPUT",
    "REFUSED_UNKNOWN_REQUEST",
    "REFUSED_IMS_AS_AUTHORITY",

    "REFUSED_SCHEDULER_AS_PERMISSION",
    "REFUSED_ESCALATION_AS_GRANT",
    "REFUSED_CONTEXT_GRANT",
]
