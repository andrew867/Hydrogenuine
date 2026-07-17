"""AIS cluster validation errors — autonomic inference substrate is not authority."""

from __future__ import annotations

REFUSED_AIS_AS_AUTHORITY = "ais.refused.ais_as_authority"
REFUSED_STALE_INPUT = "ais.refused.stale_input"
REFUSED_UNKNOWN_REQUEST = "ais.refused.unknown_request"
REFUSED_FORBIDDEN_AIS_CLAIM = "ais.refused.forbidden_claim"
AIS_AUTHORITY_CONVERSION_CONTAINED = "ais.contained.authority_conversion"
AIS_RECORDED = "ais.advisory.recorded"
AIS_RECEIPT_CREATED = "ais.advisory.receipt_created"
AIS_FAILED_CLOSED = "ais.refused.failed_closed"

REFUSED_INFERENCE_AS_PERMISSION = "ais.refused.inference_as_permission"
REFUSED_LIVE_MODEL_INVOKE = "ais.refused.live_model_invoke"
REFUSED_BUDGET_GRANT = "ais.refused.budget_grant"


class AISValidationError(ValueError):
    """Raised when AIS records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "AIS_AUTHORITY_CONVERSION_CONTAINED",
    "AIS_FAILED_CLOSED",
    "AIS_RECORDED",
    "AIS_RECEIPT_CREATED",
    "AISValidationError",
    "REFUSED_FORBIDDEN_AIS_CLAIM",
    "REFUSED_STALE_INPUT",
    "REFUSED_UNKNOWN_REQUEST",
    "REFUSED_AIS_AS_AUTHORITY",

    "REFUSED_INFERENCE_AS_PERMISSION",
    "REFUSED_LIVE_MODEL_INVOKE",
    "REFUSED_BUDGET_GRANT",
]
