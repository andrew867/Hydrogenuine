"""BRB cluster validation errors — breathing regulation boundary is not authority."""

from __future__ import annotations

REFUSED_BRB_AS_AUTHORITY = "brb.refused.brb_as_authority"
REFUSED_STALE_INPUT = "brb.refused.stale_input"
REFUSED_UNKNOWN_REQUEST = "brb.refused.unknown_request"
REFUSED_FORBIDDEN_BRB_CLAIM = "brb.refused.forbidden_claim"
BRB_AUTHORITY_CONVERSION_CONTAINED = "brb.contained.authority_conversion"
BRB_RECORDED = "brb.advisory.recorded"
BRB_RECEIPT_CREATED = "brb.advisory.receipt_created"
BRB_FAILED_CLOSED = "brb.refused.failed_closed"
REFUSED_TOKEN_GRANT = "brb.refused.token_grant"
REFUSED_CONTEXT_GRANT = "brb.refused.context_grant"
REFUSED_EXECUTION_ADMISSION = "brb.refused.execution_admission"
REFUSED_RESOURCE_BYPASS = "brb.refused.resource_bypass"


class BrbValidationError(ValueError):
    """Raised when BRB records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "BRB_AUTHORITY_CONVERSION_CONTAINED",
    "BRB_FAILED_CLOSED",
    "BRB_RECORDED",
    "BRB_RECEIPT_CREATED",
    "BrbValidationError",
    "REFUSED_FORBIDDEN_BRB_CLAIM",
    "REFUSED_STALE_INPUT",
    "REFUSED_UNKNOWN_REQUEST",
    "REFUSED_BRB_AS_AUTHORITY",
    "REFUSED_TOKEN_GRANT",
    "REFUSED_CONTEXT_GRANT",
    "REFUSED_EXECUTION_ADMISSION",
    "REFUSED_RESOURCE_BYPASS"
]

