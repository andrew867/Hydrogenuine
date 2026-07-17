"""TLB cluster validation errors — tool lifecycle boundary is not authority."""

from __future__ import annotations

REFUSED_TLB_AS_AUTHORITY = "tlb.refused.tlb_as_authority"
REFUSED_STALE_INPUT = "tlb.refused.stale_input"
REFUSED_UNKNOWN_REQUEST = "tlb.refused.unknown_request"
REFUSED_FORBIDDEN_TLB_CLAIM = "tlb.refused.forbidden_claim"
TLB_AUTHORITY_CONVERSION_CONTAINED = "tlb.contained.authority_conversion"
TLB_RECORDED = "tlb.advisory.recorded"
TLB_RECEIPT_CREATED = "tlb.advisory.receipt_created"
TLB_FAILED_CLOSED = "tlb.refused.failed_closed"
REFUSED_USEFULNESS_AS_AUTHORITY = "tlb.refused.usefulness_as_authority"
REFUSED_TOOL_GRANT = "tlb.refused.tool_grant"
REFUSED_TOOL_REVOKE = "tlb.refused.tool_revoke"
REFUSED_TOOL_INSTALL = "tlb.refused.tool_install"


class TlbValidationError(ValueError):
    """Raised when TLB records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "TLB_AUTHORITY_CONVERSION_CONTAINED",
    "TLB_FAILED_CLOSED",
    "TLB_RECORDED",
    "TLB_RECEIPT_CREATED",
    "TlbValidationError",
    "REFUSED_FORBIDDEN_TLB_CLAIM",
    "REFUSED_STALE_INPUT",
    "REFUSED_UNKNOWN_REQUEST",
    "REFUSED_TLB_AS_AUTHORITY",
    "REFUSED_USEFULNESS_AS_AUTHORITY",
    "REFUSED_TOOL_GRANT",
    "REFUSED_TOOL_REVOKE",
    "REFUSED_TOOL_INSTALL"
]

