"""ESB cluster validation errors — External Sensory Bus is not authority."""

from __future__ import annotations

REFUSED_ESB_AS_AUTHORITY = "esb.refused.esb_as_authority"
REFUSED_STALE_INPUT = "esb.refused.stale_input"
REFUSED_UNKNOWN_REQUEST = "esb.refused.unknown_request"
REFUSED_FORBIDDEN_ESB_CLAIM = "esb.refused.forbidden_claim"
ESB_AUTHORITY_CONVERSION_CONTAINED = "esb.contained.authority_conversion"
ESB_RECORDED = "esb.advisory.recorded"
ESB_RECEIPT_CREATED = "esb.advisory.receipt_created"
ESB_FAILED_CLOSED = "esb.refused.failed_closed"
REFUSED_TOKEN_GRANT = "esb.refused.token_grant"
REFUSED_CONTEXT_GRANT = "esb.refused.context_grant"
REFUSED_EXECUTION_ADMISSION = "esb.refused.execution_admission"
REFUSED_RESOURCE_BYPASS = "esb.refused.resource_bypass"


class EsbValidationError(ValueError):
    """Raised when ESB records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "ESB_AUTHORITY_CONVERSION_CONTAINED",
    "ESB_FAILED_CLOSED",
    "ESB_RECORDED",
    "ESB_RECEIPT_CREATED",
    "EsbValidationError",
    "REFUSED_FORBIDDEN_ESB_CLAIM",
    "REFUSED_STALE_INPUT",
    "REFUSED_UNKNOWN_REQUEST",
    "REFUSED_ESB_AS_AUTHORITY",
    "REFUSED_TOKEN_GRANT",
    "REFUSED_CONTEXT_GRANT",
    "REFUSED_EXECUTION_ADMISSION",
    "REFUSED_RESOURCE_BYPASS",
]
