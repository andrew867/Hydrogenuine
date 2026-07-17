"""CIR cluster validation errors — Circulatory Resource Bus is not authority."""

from __future__ import annotations

REFUSED_CIR_AS_AUTHORITY = "cir.refused.cir_as_authority"
REFUSED_STALE_INPUT = "cir.refused.stale_input"
REFUSED_UNKNOWN_REQUEST = "cir.refused.unknown_request"
REFUSED_FORBIDDEN_CIR_CLAIM = "cir.refused.forbidden_claim"
CIR_AUTHORITY_CONVERSION_CONTAINED = "cir.contained.authority_conversion"
CIR_RECORDED = "cir.advisory.recorded"
CIR_RECEIPT_CREATED = "cir.advisory.receipt_created"
CIR_FAILED_CLOSED = "cir.refused.failed_closed"
REFUSED_TOKEN_GRANT = "cir.refused.token_grant"
REFUSED_CONTEXT_GRANT = "cir.refused.context_grant"
REFUSED_EXECUTION_ADMISSION = "cir.refused.execution_admission"
REFUSED_RESOURCE_BYPASS = "cir.refused.resource_bypass"


class CirValidationError(ValueError):
    """Raised when CIR records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "CIR_AUTHORITY_CONVERSION_CONTAINED",
    "CIR_FAILED_CLOSED",
    "CIR_RECORDED",
    "CIR_RECEIPT_CREATED",
    "CirValidationError",
    "REFUSED_FORBIDDEN_CIR_CLAIM",
    "REFUSED_STALE_INPUT",
    "REFUSED_UNKNOWN_REQUEST",
    "REFUSED_CIR_AS_AUTHORITY",
    "REFUSED_TOKEN_GRANT",
    "REFUSED_CONTEXT_GRANT",
    "REFUSED_EXECUTION_ADMISSION",
    "REFUSED_RESOURCE_BYPASS",
]
