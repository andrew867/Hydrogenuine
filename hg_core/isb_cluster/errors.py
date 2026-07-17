"""ISB cluster validation errors — Intuition/Salience Bus is not authority."""

from __future__ import annotations

REFUSED_ISB_AS_AUTHORITY = "isb.refused.isb_as_authority"
REFUSED_STALE_INPUT = "isb.refused.stale_input"
REFUSED_UNKNOWN_REQUEST = "isb.refused.unknown_request"
REFUSED_FORBIDDEN_ISB_CLAIM = "isb.refused.forbidden_claim"
ISB_AUTHORITY_CONVERSION_CONTAINED = "isb.contained.authority_conversion"
ISB_RECORDED = "isb.advisory.recorded"
ISB_RECEIPT_CREATED = "isb.advisory.receipt_created"
ISB_FAILED_CLOSED = "isb.refused.failed_closed"
REFUSED_TOKEN_GRANT = "isb.refused.token_grant"
REFUSED_CONTEXT_GRANT = "isb.refused.context_grant"
REFUSED_EXECUTION_ADMISSION = "isb.refused.execution_admission"
REFUSED_RESOURCE_BYPASS = "isb.refused.resource_bypass"


class IsbValidationError(ValueError):
    """Raised when ISB records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "ISB_AUTHORITY_CONVERSION_CONTAINED",
    "ISB_FAILED_CLOSED",
    "ISB_RECORDED",
    "ISB_RECEIPT_CREATED",
    "IsbValidationError",
    "REFUSED_FORBIDDEN_ISB_CLAIM",
    "REFUSED_STALE_INPUT",
    "REFUSED_UNKNOWN_REQUEST",
    "REFUSED_ISB_AS_AUTHORITY",
    "REFUSED_TOKEN_GRANT",
    "REFUSED_CONTEXT_GRANT",
    "REFUSED_EXECUTION_ADMISSION",
    "REFUSED_RESOURCE_BYPASS",
]
