"""DCD cluster validation errors — decommissioning cemetery boundary is not authority."""

from __future__ import annotations

REFUSED_DCD_AS_AUTHORITY = "dcd.refused.dcd_as_authority"
REFUSED_STALE_INPUT = "dcd.refused.stale_input"
REFUSED_UNKNOWN_REQUEST = "dcd.refused.unknown_request"
REFUSED_FORBIDDEN_DCD_CLAIM = "dcd.refused.forbidden_claim"
DCD_AUTHORITY_CONVERSION_CONTAINED = "dcd.contained.authority_conversion"
DCD_RECORDED = "dcd.advisory.recorded"
DCD_RECEIPT_CREATED = "dcd.advisory.receipt_created"
DCD_FAILED_CLOSED = "dcd.refused.failed_closed"
REFUSED_GHOST_RESURRECTION = "dcd.refused.ghost_resurrection"
REFUSED_LIVE_KILL = "dcd.refused.live_kill"
REFUSED_PROOF_DELETION = "dcd.refused.proof_deletion"
REFUSED_SPAWN_REPLACEMENT = "dcd.refused.spawn_replacement"


class DcdValidationError(ValueError):
    """Raised when DCD records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "DCD_AUTHORITY_CONVERSION_CONTAINED",
    "DCD_FAILED_CLOSED",
    "DCD_RECORDED",
    "DCD_RECEIPT_CREATED",
    "DcdValidationError",
    "REFUSED_FORBIDDEN_DCD_CLAIM",
    "REFUSED_STALE_INPUT",
    "REFUSED_UNKNOWN_REQUEST",
    "REFUSED_DCD_AS_AUTHORITY",
    "REFUSED_GHOST_RESURRECTION",
    "REFUSED_LIVE_KILL",
    "REFUSED_PROOF_DELETION",
    "REFUSED_SPAWN_REPLACEMENT"
]

