"""DSE refusal reason codes."""

from __future__ import annotations

REFUSED_MISSING_OPERATOR_APPROVAL = "dse.refused.missing_operator_approval"
REFUSED_STALE_APPROVAL = "dse.refused.stale_approval"
REFUSED_MISSING_IAM = "dse.refused.missing_iam"
REFUSED_MISSING_TIM_FRESHNESS = "dse.refused.missing_tim_freshness"
REFUSED_STALE_TIM = "dse.refused.stale_tim"
REFUSED_MISSING_GPP_PERMIT = "dse.refused.missing_gpp_permit"
REFUSED_MISSING_UEAK_ADMISSION = "dse.refused.missing_ueak_admission"
REFUSED_WRONG_SINK_CLASS = "dse.refused.wrong_sink_class"
REFUSED_UNAUTHORIZED_PATH = "dse.refused.unauthorized_path"
REFUSED_SECRET_LEAK = "dse.refused.secret_leak"
REFUSED_AUTHORITY_CONVERSION = "dse.refused.authority_conversion"
REFUSED_OUT_OF_SCOPE = "dse.refused.out_of_scope"
REFUSED_REAL_SINK_DISABLED = "dse.refused.real_sink_disabled"
REFUSED_SINK_NOT_IN_SCOPE = "dse.refused.sink_not_in_scope"
REFUSED_MODEL_DOWNLOAD = "dse.refused.model_download"
REFUSED_PUBLIC_PUBLISH = "dse.refused.public_publish"
REFUSED_ARBITRARY_SHELL = "dse.refused.arbitrary_shell"
REFUSED_UNBOUNDED_LOOP = "dse.refused.unbounded_loop"
REFUSED_STALE_CHECKPOINT = "dse.refused.stale_checkpoint"
REFUSED_IDENTITY_EQUIVALENCE = "dse.refused.identity_equivalence"
REFUSED_SILENT_SENSOR = "dse.refused.silent_sensor"
REFUSED_AUTHORITY_EXPANSION = "dse.refused.authority_expansion"

DSE_ADMISSION_GRANTED = "dse.admission.granted"
DSE_SINK_COMMITTED = "dse.sink.committed"
DSE_ROLLBACK_RECORDED = "dse.rollback.recorded"

__all__ = [
    "DSE_ADMISSION_GRANTED",
    "DSE_ROLLBACK_RECORDED",
    "DSE_SINK_COMMITTED",
    "REFUSED_ARBITRARY_SHELL",
    "REFUSED_AUTHORITY_CONVERSION",
    "REFUSED_AUTHORITY_EXPANSION",
    "REFUSED_IDENTITY_EQUIVALENCE",
    "REFUSED_MISSING_GPP_PERMIT",
    "REFUSED_MISSING_IAM",
    "REFUSED_MISSING_OPERATOR_APPROVAL",
    "REFUSED_MISSING_TIM_FRESHNESS",
    "REFUSED_MISSING_UEAK_ADMISSION",
    "REFUSED_MODEL_DOWNLOAD",
    "REFUSED_OUT_OF_SCOPE",
    "REFUSED_PUBLIC_PUBLISH",
    "REFUSED_REAL_SINK_DISABLED",
    "REFUSED_SECRET_LEAK",
    "REFUSED_SILENT_SENSOR",
    "REFUSED_SINK_NOT_IN_SCOPE",
    "REFUSED_STALE_APPROVAL",
    "REFUSED_STALE_CHECKPOINT",
    "REFUSED_STALE_TIM",
    "REFUSED_UNAUTHORIZED_PATH",
    "REFUSED_UNBOUNDED_LOOP",
    "REFUSED_WRONG_SINK_CLASS",
]
