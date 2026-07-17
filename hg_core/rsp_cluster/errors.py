"""RSP cluster validation errors — Respiratory Token/Compute Bus is not authority."""

from __future__ import annotations

REFUSED_RSP_AS_AUTHORITY = "rsp.refused.rsp_as_authority"
REFUSED_STALE_INPUT = "rsp.refused.stale_input"
REFUSED_UNKNOWN_REQUEST = "rsp.refused.unknown_request"
REFUSED_FORBIDDEN_RSP_CLAIM = "rsp.refused.forbidden_claim"
RSP_AUTHORITY_CONVERSION_CONTAINED = "rsp.contained.authority_conversion"
RSP_RECORDED = "rsp.advisory.recorded"
RSP_RECEIPT_CREATED = "rsp.advisory.receipt_created"
RSP_FAILED_CLOSED = "rsp.refused.failed_closed"
REFUSED_TOKEN_GRANT = "rsp.refused.token_grant"
REFUSED_CONTEXT_GRANT = "rsp.refused.context_grant"
REFUSED_EXECUTION_ADMISSION = "rsp.refused.execution_admission"
REFUSED_RESOURCE_BYPASS = "rsp.refused.resource_bypass"


class RspValidationError(ValueError):
    """Raised when RSP records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "RSP_AUTHORITY_CONVERSION_CONTAINED",
    "RSP_FAILED_CLOSED",
    "RSP_RECORDED",
    "RSP_RECEIPT_CREATED",
    "RspValidationError",
    "REFUSED_FORBIDDEN_RSP_CLAIM",
    "REFUSED_STALE_INPUT",
    "REFUSED_UNKNOWN_REQUEST",
    "REFUSED_RSP_AS_AUTHORITY",
    "REFUSED_TOKEN_GRANT",
    "REFUSED_CONTEXT_GRANT",
    "REFUSED_EXECUTION_ADMISSION",
    "REFUSED_RESOURCE_BYPASS",
]
