"""MBS cluster validation errors — multi-bus substrate is not authority."""

from __future__ import annotations

REFUSED_MBS_AS_AUTHORITY = "mbs.refused.mbs_as_authority"
REFUSED_STALE_INPUT = "mbs.refused.stale_input"
REFUSED_UNKNOWN_REQUEST = "mbs.refused.unknown_request"
REFUSED_FORBIDDEN_MBS_CLAIM = "mbs.refused.forbidden_claim"
MBS_AUTHORITY_CONVERSION_CONTAINED = "mbs.contained.authority_conversion"
MBS_RECORDED = "mbs.advisory.recorded"
MBS_RECEIPT_CREATED = "mbs.advisory.receipt_created"
MBS_FAILED_CLOSED = "mbs.refused.failed_closed"

REFUSED_BUS_AS_PERMISSION = "mbs.refused.bus_as_permission"
REFUSED_LANE_BYPASS = "mbs.refused.lane_bypass"
REFUSED_SATURATION_IGNORE = "mbs.refused.saturation_ignore"
REFUSED_INVALID_LANE = "mbs.refused.invalid_lane"


class MBSValidationError(ValueError):
    """Raised when MBS records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "MBS_AUTHORITY_CONVERSION_CONTAINED",
    "MBS_FAILED_CLOSED",
    "MBS_RECORDED",
    "MBS_RECEIPT_CREATED",
    "MBSValidationError",
    "REFUSED_FORBIDDEN_MBS_CLAIM",
    "REFUSED_STALE_INPUT",
    "REFUSED_UNKNOWN_REQUEST",
    "REFUSED_MBS_AS_AUTHORITY",

    "REFUSED_BUS_AS_PERMISSION",
    "REFUSED_LANE_BYPASS",
    "REFUSED_SATURATION_IGNORE",
    "REFUSED_INVALID_LANE",
]
