"""DAB cluster validation errors — digestion assimilation boundary is not authority."""

from __future__ import annotations

REFUSED_DAB_AS_AUTHORITY = "dab.refused.dab_as_authority"
REFUSED_STALE_INPUT = "dab.refused.stale_input"
REFUSED_UNKNOWN_REQUEST = "dab.refused.unknown_request"
REFUSED_FORBIDDEN_DAB_CLAIM = "dab.refused.forbidden_claim"
DAB_AUTHORITY_CONVERSION_CONTAINED = "dab.contained.authority_conversion"
DAB_RECORDED = "dab.advisory.recorded"
DAB_RECEIPT_CREATED = "dab.advisory.receipt_created"
DAB_FAILED_CLOSED = "dab.refused.failed_closed"
REFUSED_MEMORY_WRITE = "dab.refused.memory_write"
REFUSED_TOOL_INSTALL = "dab.refused.tool_install"
REFUSED_EXECUTION_AUTHORITY = "dab.refused.execution_authority"


class DabValidationError(ValueError):
    """Raised when DAB records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "DAB_AUTHORITY_CONVERSION_CONTAINED",
    "DAB_FAILED_CLOSED",
    "DAB_RECORDED",
    "DAB_RECEIPT_CREATED",
    "DabValidationError",
    "REFUSED_FORBIDDEN_DAB_CLAIM",
    "REFUSED_STALE_INPUT",
    "REFUSED_UNKNOWN_REQUEST",
    "REFUSED_DAB_AS_AUTHORITY",
    "REFUSED_MEMORY_WRITE",
    "REFUSED_TOOL_INSTALL",
    "REFUSED_EXECUTION_AUTHORITY"
]

