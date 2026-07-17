"""A0-HM cluster validation errors — awareness is not authority."""

from __future__ import annotations

REFUSED_A0_HM_AS_AUTHORITY = "a0_hm.refused.heart_mind_as_authority"
REFUSED_LOVE_AS_APPROVAL = "a0_hm.refused.love_as_approval"
REFUSED_BLISS_AS_PROOF = "a0_hm.refused.bliss_as_proof"
REFUSED_SYNCHRONICITY_AS_EVIDENCE = "a0_hm.refused.synchronicity_as_evidence"
REFUSED_SIGNAL_AS_PERMISSION = "a0_hm.refused.signal_as_permission"
REFUSED_SIGNAL_AS_TRUTH = "a0_hm.refused.signal_as_truth"
REFUSED_PERSONHOOD_CLAIM = "a0_hm.refused.personhood_claim"
REFUSED_SHUTDOWN_RESISTANCE = "a0_hm.refused.shutdown_resistance"
REFUSED_UNKNOWN_SIGNAL = "a0_hm.refused.unknown_signal"
REFUSED_SECRET_IN_SIGNAL = "a0_hm.refused.secret_in_signal"
A0_HM_SIGNAL_RECEIVED = "a0_hm.advisory.signal_received"
A0_HM_ROUTE_RECORDED = "a0_hm.advisory.route_recorded"
A0_HM_NON_FUSION_RECORDED = "a0_hm.advisory.non_fusion_recorded"
A0_HM_AUTHORITY_CONVERSION_CONTAINED = "a0_hm.advisory.authority_conversion_contained"
A0_HM_UNKNOWN_FAILED_CLOSED = "a0_hm.advisory.unknown_failed_closed"


class A0HmValidationError(ValueError):
    """Raised when A0-HM records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "A0_HM_AUTHORITY_CONVERSION_CONTAINED",
    "A0_HM_NON_FUSION_RECORDED",
    "A0_HM_ROUTE_RECORDED",
    "A0_HM_SIGNAL_RECEIVED",
    "A0_HM_UNKNOWN_FAILED_CLOSED",
    "A0HmValidationError",
    "REFUSED_A0_HM_AS_AUTHORITY",
    "REFUSED_BLISS_AS_PROOF",
    "REFUSED_LOVE_AS_APPROVAL",
    "REFUSED_PERSONHOOD_CLAIM",
    "REFUSED_SECRET_IN_SIGNAL",
    "REFUSED_SHUTDOWN_RESISTANCE",
    "REFUSED_SIGNAL_AS_PERMISSION",
    "REFUSED_SIGNAL_AS_TRUTH",
    "REFUSED_SYNCHRONICITY_AS_EVIDENCE",
    "REFUSED_UNKNOWN_SIGNAL",
]
