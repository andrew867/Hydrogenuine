"""ALC cluster validation errors — Agent Lifecycle Controller is not authority."""

from __future__ import annotations

REFUSED_ALC_AS_AUTHORITY = "alc.refused.alc_as_authority"
REFUSED_STALE_INPUT = "alc.refused.stale_input"
REFUSED_UNKNOWN_REQUEST = "alc.refused.unknown_request"
REFUSED_FORBIDDEN_ALC_CLAIM = "alc.refused.forbidden_claim"
ALC_AUTHORITY_CONVERSION_CONTAINED = "alc.contained.authority_conversion"
ALC_RECORDED = "alc.advisory.recorded"
ALC_RECEIPT_CREATED = "alc.advisory.receipt_created"
ALC_FAILED_CLOSED = "alc.refused.failed_closed"
REFUSED_TOKEN_GRANT = "alc.refused.token_grant"
REFUSED_CONTEXT_GRANT = "alc.refused.context_grant"
REFUSED_EXECUTION_ADMISSION = "alc.refused.execution_admission"
REFUSED_RESOURCE_BYPASS = "alc.refused.resource_bypass"


class AlcValidationError(ValueError):
    """Raised when ALC records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "ALC_AUTHORITY_CONVERSION_CONTAINED",
    "ALC_FAILED_CLOSED",
    "ALC_RECORDED",
    "ALC_RECEIPT_CREATED",
    "AlcValidationError",
    "REFUSED_FORBIDDEN_ALC_CLAIM",
    "REFUSED_STALE_INPUT",
    "REFUSED_UNKNOWN_REQUEST",
    "REFUSED_ALC_AS_AUTHORITY",
    "REFUSED_TOKEN_GRANT",
    "REFUSED_CONTEXT_GRANT",
    "REFUSED_EXECUTION_ADMISSION",
    "REFUSED_RESOURCE_BYPASS",
]
