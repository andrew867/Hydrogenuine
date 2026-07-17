"""OCF refusal reason codes."""

from __future__ import annotations

REFUSED_AUTHORITY_CONVERSION = "ocf.refused.authority_conversion"
REFUSED_PERMIT_MINT = "ocf.refused.permit_mint"
REFUSED_UEAK_APPROVAL = "ocf.refused.ueak_approval"
REFUSED_OEA_TER = "ocf.refused.oea_ter"
REFUSED_SRP_APPLY = "ocf.refused.srp_apply"
REFUSED_MEMORY_MUTATION = "ocf.refused.memory_mutation"
REFUSED_SPAWN = "ocf.refused.spawn"
REFUSED_PUBLISH = "ocf.refused.publish"
REFUSED_DURABLE_SINK = "ocf.refused.durable_sink"
REFUSED_UNKNOWN_POSTURE = "ocf.refused.unknown_posture"
REFUSED_RECoupling_WITHOUT_AUDIT = "ocf.refused.recoupling_without_audit"
REFUSED_SECRET_LEAK = "ocf.refused.secret_leak"
REFUSED_HIDE_PROOF_FAILURE = "ocf.refused.hide_proof_failure"

OCF_ADVISORY_RECORDED = "ocf.advisory.recorded"
OCF_POSTURE_TRANSITION = "ocf.posture.transition"
OCF_PANIC_DARK_RESTRICT = "ocf.panic_dark.restrict_only"

__all__ = [
    "OCF_ADVISORY_RECORDED",
    "OCF_PANIC_DARK_RESTRICT",
    "OCF_POSTURE_TRANSITION",
    "REFUSED_AUTHORITY_CONVERSION",
    "REFUSED_DURABLE_SINK",
    "REFUSED_HIDE_PROOF_FAILURE",
    "REFUSED_MEMORY_MUTATION",
    "REFUSED_OEA_TER",
    "REFUSED_PERMIT_MINT",
    "REFUSED_PUBLISH",
    "REFUSED_RECoupling_WITHOUT_AUDIT",
    "REFUSED_SECRET_LEAK",
    "REFUSED_SPAWN",
    "REFUSED_SRP_APPLY",
    "REFUSED_UEAK_APPROVAL",
    "REFUSED_UNKNOWN_POSTURE",
]
