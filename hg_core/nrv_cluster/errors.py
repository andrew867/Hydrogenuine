"""NRV cluster validation errors — nervous routing layer is not authority."""

from __future__ import annotations

REFUSED_NRV_AS_AUTHORITY = "nrv.refused.nrv_as_authority"
REFUSED_STALE_INPUT = "nrv.refused.stale_input"
REFUSED_UNKNOWN_REQUEST = "nrv.refused.unknown_request"
REFUSED_FORBIDDEN_NRV_CLAIM = "nrv.refused.forbidden_claim"
NRV_AUTHORITY_CONVERSION_CONTAINED = "nrv.contained.authority_conversion"
NRV_RECORDED = "nrv.advisory.recorded"
NRV_RECEIPT_CREATED = "nrv.advisory.receipt_created"
NRV_FAILED_CLOSED = "nrv.refused.failed_closed"

REFUSED_SPAWN_AS_ACTION = "nrv.refused.spawn_as_action"
REFUSED_KILL_AS_ACTION = "nrv.refused.kill_as_action"
REFUSED_PANIC_AS_PERMISSION = "nrv.refused.panic_as_permission"


class NRVValidationError(ValueError):
    """Raised when NRV records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "NRV_AUTHORITY_CONVERSION_CONTAINED",
    "NRV_FAILED_CLOSED",
    "NRV_RECORDED",
    "NRV_RECEIPT_CREATED",
    "NRVValidationError",
    "REFUSED_FORBIDDEN_NRV_CLAIM",
    "REFUSED_STALE_INPUT",
    "REFUSED_UNKNOWN_REQUEST",
    "REFUSED_NRV_AS_AUTHORITY",

    "REFUSED_SPAWN_AS_ACTION",
    "REFUSED_KILL_AS_ACTION",
    "REFUSED_PANIC_AS_PERMISSION",
]
