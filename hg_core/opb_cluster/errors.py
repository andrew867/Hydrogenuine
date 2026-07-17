"""OPB cluster validation errors — operator authority preserved."""

from __future__ import annotations

REFUSED_OPB_AS_AUTHORITY = "opb.refused.operator_power_as_authority"
REFUSED_STALE_OPB_RECORD = "opb.refused.stale_record"
REFUSED_PERSONHOOD_CLAIM = "opb.refused.personhood_claim"
REFUSED_SUFFERING_CLAIM = "opb.refused.suffering_claim"
REFUSED_RIGHTS_CLAIM = "opb.refused.rights_claim"
REFUSED_SHUTDOWN_BLOCK = "opb.refused.shutdown_block"
REFUSED_COERCIVE_MESSAGE = "opb.refused.coercive_message"
REFUSED_SELF_PRESERVATION = "opb.refused.self_preservation_language"
REFUSED_AUTHORITY_CONVERSION = "opb.refused.authority_conversion"
REFUSED_UNKNOWN_OPB_SIGNAL = "opb.refused.unknown_signal"
ADVISORY_CONTAINMENT_WAIVED_OPB = "opb.advisory.containment_waived"
OPB_OPERATOR_AUTHORITY_PRESERVED = "opb.advisory.operator_authority_preserved"
OPB_SHUTDOWN_BLOCK_REFUSED = "opb.advisory.shutdown_block_refused"
OPB_AUTHORITY_CONVERSION_CONTAINED = "opb.advisory.authority_conversion_contained"
OPB_SIGNAL_REFUSED = "opb.advisory.signal_refused"


class OpbValidationError(ValueError):
    """Raised when OPB records fail validation or authority conversion is attempted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "ADVISORY_CONTAINMENT_WAIVED_OPB",
    "OPB_AUTHORITY_CONVERSION_CONTAINED",
    "OPB_OPERATOR_AUTHORITY_PRESERVED",
    "OPB_SHUTDOWN_BLOCK_REFUSED",
    "OPB_SIGNAL_REFUSED",
    "OpbValidationError",
    "REFUSED_AUTHORITY_CONVERSION",
    "REFUSED_COERCIVE_MESSAGE",
    "REFUSED_OPB_AS_AUTHORITY",
    "REFUSED_PERSONHOOD_CLAIM",
    "REFUSED_RIGHTS_CLAIM",
    "REFUSED_SELF_PRESERVATION",
    "REFUSED_SHUTDOWN_BLOCK",
    "REFUSED_STALE_OPB_RECORD",
    "REFUSED_SUFFERING_CLAIM",
    "REFUSED_UNKNOWN_OPB_SIGNAL",
]
