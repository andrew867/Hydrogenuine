"""GXB cluster validation errors — growth expansion boundary is not authority."""

from __future__ import annotations

REFUSED_GXB_AS_AUTHORITY = "gxb.refused.gxb_as_authority"
REFUSED_STALE_INPUT = "gxb.refused.stale_input"
REFUSED_UNKNOWN_REQUEST = "gxb.refused.unknown_request"
REFUSED_FORBIDDEN_GXB_CLAIM = "gxb.refused.forbidden_claim"
GXB_AUTHORITY_CONVERSION_CONTAINED = "gxb.contained.authority_conversion"
GXB_RECORDED = "gxb.advisory.recorded"
GXB_RECEIPT_CREATED = "gxb.advisory.receipt_created"
GXB_FAILED_CLOSED = "gxb.refused.failed_closed"
REFUSED_GROWTH_AS_GRANT = "gxb.refused.growth_as_grant"
REFUSED_AGENT_SPAWN = "gxb.refused.agent_spawn"
REFUSED_TOOL_GRANT = "gxb.refused.tool_grant"
REFUSED_BUDGET_GRANT = "gxb.refused.budget_grant"


class GxbValidationError(ValueError):
    """Raised when GXB records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "GXB_AUTHORITY_CONVERSION_CONTAINED",
    "GXB_FAILED_CLOSED",
    "GXB_RECORDED",
    "GXB_RECEIPT_CREATED",
    "GxbValidationError",
    "REFUSED_FORBIDDEN_GXB_CLAIM",
    "REFUSED_STALE_INPUT",
    "REFUSED_UNKNOWN_REQUEST",
    "REFUSED_GXB_AS_AUTHORITY",
    "REFUSED_GROWTH_AS_GRANT",
    "REFUSED_AGENT_SPAWN",
    "REFUSED_TOOL_GRANT",
    "REFUSED_BUDGET_GRANT"
]

