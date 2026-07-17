"""NIB cluster validation errors — nutrient intake boundary is not authority."""

from __future__ import annotations

REFUSED_NIB_AS_AUTHORITY = "nib.refused.nib_as_authority"
REFUSED_STALE_INPUT = "nib.refused.stale_input"
REFUSED_UNKNOWN_REQUEST = "nib.refused.unknown_request"
REFUSED_FORBIDDEN_NIB_CLAIM = "nib.refused.forbidden_claim"
NIB_AUTHORITY_CONVERSION_CONTAINED = "nib.contained.authority_conversion"
NIB_RECORDED = "nib.advisory.recorded"
NIB_RECEIPT_CREATED = "nib.advisory.receipt_created"
NIB_FAILED_CLOSED = "nib.refused.failed_closed"
REFUSED_INTAKE_AS_TRUTH = "nib.refused.intake_as_truth"
REFUSED_MEMORY_WRITE = "nib.refused.memory_write"
REFUSED_TOOL_INSTALL = "nib.refused.tool_install"
REFUSED_BUDGET_GRANT = "nib.refused.budget_grant"


class NibValidationError(ValueError):
    """Raised when NIB records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "NIB_AUTHORITY_CONVERSION_CONTAINED",
    "NIB_FAILED_CLOSED",
    "NIB_RECORDED",
    "NIB_RECEIPT_CREATED",
    "NibValidationError",
    "REFUSED_FORBIDDEN_NIB_CLAIM",
    "REFUSED_STALE_INPUT",
    "REFUSED_UNKNOWN_REQUEST",
    "REFUSED_NIB_AS_AUTHORITY",
    "REFUSED_INTAKE_AS_TRUTH",
    "REFUSED_MEMORY_WRITE",
    "REFUSED_TOOL_INSTALL",
    "REFUSED_BUDGET_GRANT"
]

