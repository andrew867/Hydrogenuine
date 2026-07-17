"""OEF cluster validation errors — organ edge filter is not authority."""

from __future__ import annotations

REFUSED_OEF_AS_AUTHORITY = "oef.refused.oef_as_authority"
REFUSED_STALE_INPUT = "oef.refused.stale_input"
REFUSED_UNKNOWN_REQUEST = "oef.refused.unknown_request"
REFUSED_FORBIDDEN_OEF_CLAIM = "oef.refused.forbidden_claim"
OEF_AUTHORITY_CONVERSION_CONTAINED = "oef.contained.authority_conversion"
OEF_RECORDED = "oef.advisory.recorded"
OEF_RECEIPT_CREATED = "oef.advisory.receipt_created"
OEF_FAILED_CLOSED = "oef.refused.failed_closed"

REFUSED_FILTER_AS_PERMISSION = "oef.refused.filter_as_permission"
REFUSED_MISSING_TEP = "oef.refused.missing_tep"
REFUSED_TTL_EXPIRED = "oef.refused.ttl_expired"
REFUSED_RATE_EXCEEDED = "oef.refused.rate_exceeded"
REFUSED_AUTHORITY_BEARING = "oef.refused.authority_bearing"


class OEFValidationError(ValueError):
    """Raised when OEF records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "OEF_AUTHORITY_CONVERSION_CONTAINED",
    "OEF_FAILED_CLOSED",
    "OEF_RECORDED",
    "OEF_RECEIPT_CREATED",
    "OEFValidationError",
    "REFUSED_FORBIDDEN_OEF_CLAIM",
    "REFUSED_STALE_INPUT",
    "REFUSED_UNKNOWN_REQUEST",
    "REFUSED_OEF_AS_AUTHORITY",

    "REFUSED_FILTER_AS_PERMISSION",
    "REFUSED_MISSING_TEP",
    "REFUSED_TTL_EXPIRED",
    "REFUSED_RATE_EXCEEDED",
    "REFUSED_AUTHORITY_BEARING",
]
