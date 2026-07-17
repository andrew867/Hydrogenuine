"""MBR refusal reason codes."""

REFUSED_AUTHORITY_CONVERSION = "mbr.refused.authority_conversion"
REFUSED_DIRECT_ACTION = "mbr.refused.direct_action"
REFUSED_PERMIT_MINT = "mbr.refused.permit_mint"
REFUSED_UEAK_APPROVAL = "mbr.refused.ueak_approval"
REFUSED_DURABLE_SINK = "mbr.refused.durable_sink"
REFUSED_SECRET_LEAK = "mbr.refused.secret_leak"

MBR_STATE_RECORDED = "mbr.advisory.state_recorded"
MBR_RECOVERY_RECOMMENDED = "mbr.advisory.recovery_recommended"
MBR_PANIC_RECOMMENDED = "mbr.advisory.panic_recommended"

__all__ = [
    "MBR_PANIC_RECOMMENDED",
    "MBR_RECOVERY_RECOMMENDED",
    "MBR_STATE_RECORDED",
    "REFUSED_AUTHORITY_CONVERSION",
    "REFUSED_DIRECT_ACTION",
    "REFUSED_DURABLE_SINK",
    "REFUSED_PERMIT_MINT",
    "REFUSED_SECRET_LEAK",
    "REFUSED_UEAK_APPROVAL",
]
