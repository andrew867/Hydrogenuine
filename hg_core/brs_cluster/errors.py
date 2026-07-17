"""BRS cluster validation errors — Bus Rate Supervisor is not authority."""

from __future__ import annotations

REFUSED_BRS_AS_AUTHORITY = "brs.refused.brs_as_authority"
REFUSED_STALE_INPUT = "brs.refused.stale_input"
REFUSED_UNKNOWN_REQUEST = "brs.refused.unknown_request"
REFUSED_FORBIDDEN_BRS_CLAIM = "brs.refused.forbidden_claim"
BRS_AUTHORITY_CONVERSION_CONTAINED = "brs.contained.authority_conversion"
BRS_RECORDED = "brs.advisory.recorded"
BRS_RECEIPT_CREATED = "brs.advisory.receipt_created"
BRS_FAILED_CLOSED = "brs.refused.failed_closed"
REFUSED_TOKEN_GRANT = "brs.refused.token_grant"
REFUSED_CONTEXT_GRANT = "brs.refused.context_grant"
REFUSED_EXECUTION_ADMISSION = "brs.refused.execution_admission"
REFUSED_RESOURCE_BYPASS = "brs.refused.resource_bypass"


class BrsValidationError(ValueError):
    """Raised when BRS records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "BRS_AUTHORITY_CONVERSION_CONTAINED",
    "BRS_FAILED_CLOSED",
    "BRS_RECORDED",
    "BRS_RECEIPT_CREATED",
    "BrsValidationError",
    "REFUSED_FORBIDDEN_BRS_CLAIM",
    "REFUSED_STALE_INPUT",
    "REFUSED_UNKNOWN_REQUEST",
    "REFUSED_BRS_AS_AUTHORITY",
    "REFUSED_TOKEN_GRANT",
    "REFUSED_CONTEXT_GRANT",
    "REFUSED_EXECUTION_ADMISSION",
    "REFUSED_RESOURCE_BYPASS",
]
