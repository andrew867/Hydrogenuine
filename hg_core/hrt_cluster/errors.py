"""HRT cluster validation errors — Heartbeat & Liveness Transport is not authority."""

from __future__ import annotations

REFUSED_HRT_AS_AUTHORITY = "hrt.refused.hrt_as_authority"
REFUSED_STALE_INPUT = "hrt.refused.stale_input"
REFUSED_UNKNOWN_REQUEST = "hrt.refused.unknown_request"
REFUSED_FORBIDDEN_HRT_CLAIM = "hrt.refused.forbidden_claim"
HRT_AUTHORITY_CONVERSION_CONTAINED = "hrt.contained.authority_conversion"
HRT_RECORDED = "hrt.advisory.recorded"
HRT_RECEIPT_CREATED = "hrt.advisory.receipt_created"
HRT_FAILED_CLOSED = "hrt.refused.failed_closed"
REFUSED_TOKEN_GRANT = "hrt.refused.token_grant"
REFUSED_CONTEXT_GRANT = "hrt.refused.context_grant"
REFUSED_EXECUTION_ADMISSION = "hrt.refused.execution_admission"
REFUSED_RESOURCE_BYPASS = "hrt.refused.resource_bypass"


class HrtValidationError(ValueError):
    """Raised when HRT records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "HRT_AUTHORITY_CONVERSION_CONTAINED",
    "HRT_FAILED_CLOSED",
    "HRT_RECORDED",
    "HRT_RECEIPT_CREATED",
    "HrtValidationError",
    "REFUSED_FORBIDDEN_HRT_CLAIM",
    "REFUSED_STALE_INPUT",
    "REFUSED_UNKNOWN_REQUEST",
    "REFUSED_HRT_AS_AUTHORITY",
    "REFUSED_TOKEN_GRANT",
    "REFUSED_CONTEXT_GRANT",
    "REFUSED_EXECUTION_ADMISSION",
    "REFUSED_RESOURCE_BYPASS",
]
