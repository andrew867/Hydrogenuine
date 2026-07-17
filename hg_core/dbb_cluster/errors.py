"""DBB cluster validation errors — Data/Blob Bus is not authority."""

from __future__ import annotations

REFUSED_DBB_AS_AUTHORITY = "dbb.refused.dbb_as_authority"
REFUSED_STALE_INPUT = "dbb.refused.stale_input"
REFUSED_UNKNOWN_REQUEST = "dbb.refused.unknown_request"
REFUSED_FORBIDDEN_DBB_CLAIM = "dbb.refused.forbidden_claim"
DBB_AUTHORITY_CONVERSION_CONTAINED = "dbb.contained.authority_conversion"
DBB_RECORDED = "dbb.advisory.recorded"
DBB_RECEIPT_CREATED = "dbb.advisory.receipt_created"
DBB_FAILED_CLOSED = "dbb.refused.failed_closed"
REFUSED_TOKEN_GRANT = "dbb.refused.token_grant"
REFUSED_CONTEXT_GRANT = "dbb.refused.context_grant"
REFUSED_EXECUTION_ADMISSION = "dbb.refused.execution_admission"
REFUSED_RESOURCE_BYPASS = "dbb.refused.resource_bypass"


class DbbValidationError(ValueError):
    """Raised when DBB records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "DBB_AUTHORITY_CONVERSION_CONTAINED",
    "DBB_FAILED_CLOSED",
    "DBB_RECORDED",
    "DBB_RECEIPT_CREATED",
    "DbbValidationError",
    "REFUSED_FORBIDDEN_DBB_CLAIM",
    "REFUSED_STALE_INPUT",
    "REFUSED_UNKNOWN_REQUEST",
    "REFUSED_DBB_AS_AUTHORITY",
    "REFUSED_TOKEN_GRANT",
    "REFUSED_CONTEXT_GRANT",
    "REFUSED_EXECUTION_ADMISSION",
    "REFUSED_RESOURCE_BYPASS",
]
