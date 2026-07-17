"""INFER-LIVE cluster validation errors — inference output is not authority."""

from __future__ import annotations

REFUSED_INFER_AS_AUTHORITY = "infer.refused.infer_as_authority"
REFUSED_MISSING_OPERATOR_APPROVAL = "infer.refused.missing_operator_approval"
REFUSED_STALE_APPROVAL = "infer.refused.stale_approval"
REFUSED_MISSING_IAM = "infer.refused.missing_iam"
REFUSED_MISSING_TIM_FRESHNESS = "infer.refused.missing_tim_freshness"
REFUSED_STALE_TIM = "infer.refused.stale_tim"
REFUSED_MISSING_GPP_PERMIT = "infer.refused.missing_gpp_permit"
REFUSED_MISSING_UEAK_ADMISSION = "infer.refused.missing_ueak_admission"
REFUSED_AUTHORITY_CONVERSION = "infer.refused.authority_conversion"
REFUSED_SECRET_LEAK = "infer.refused.secret_leak"
REFUSED_INFERENCE_AS_PERMISSION = "infer.refused.inference_as_permission"
REFUSED_LIVE_BACKEND_CALL = "infer.refused.live_backend_call"
REFUSED_MODEL_DOWNLOAD = "infer.refused.model_download_without_approval"
REFUSED_INSUFFICIENT_HARDWARE = "infer.refused.insufficient_hardware"
REFUSED_TOOL_GRANT_FROM_INFER = "infer.refused.tool_grant_from_inference"
REFUSED_MEMORY_GRANT_FROM_INFER = "infer.refused.memory_grant_from_inference"
REFUSED_CONTEXT_GRANT_FROM_INFER = "infer.refused.context_grant_from_inference"
REFUSED_ESCALATION_AS_AUTHORITY = "infer.refused.escalation_as_authority"

INFER_RECORDED = "infer.advisory.recorded"
INFER_OUTPUT_BOUND = "infer.advisory.output_bound"
INFER_ESCALATION_REQUEST = "infer.advisory.escalation_request"
INFER_FAILED_CLOSED = "infer.refused.failed_closed"
INFER_AUTHORITY_CONVERSION_CONTAINED = "infer.contained.authority_conversion"
INFER_DRY_RUN_COMPLETE = "infer.advisory.dry_run_complete"


class InferValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


__all__ = [
    "INFER_AUTHORITY_CONVERSION_CONTAINED",
    "INFER_DRY_RUN_COMPLETE",
    "INFER_ESCALATION_REQUEST",
    "INFER_FAILED_CLOSED",
    "INFER_OUTPUT_BOUND",
    "INFER_RECORDED",
    "InferValidationError",
    "REFUSED_AUTHORITY_CONVERSION",
    "REFUSED_CONTEXT_GRANT_FROM_INFER",
    "REFUSED_ESCALATION_AS_AUTHORITY",
    "REFUSED_INFERENCE_AS_PERMISSION",
    "REFUSED_INFER_AS_AUTHORITY",
    "REFUSED_INSUFFICIENT_HARDWARE",
    "REFUSED_LIVE_BACKEND_CALL",
    "REFUSED_MEMORY_GRANT_FROM_INFER",
    "REFUSED_MISSING_GPP_PERMIT",
    "REFUSED_MISSING_IAM",
    "REFUSED_MISSING_OPERATOR_APPROVAL",
    "REFUSED_MISSING_TIM_FRESHNESS",
    "REFUSED_MISSING_UEAK_ADMISSION",
    "REFUSED_MODEL_DOWNLOAD",
    "REFUSED_SECRET_LEAK",
    "REFUSED_STALE_APPROVAL",
    "REFUSED_STALE_TIM",
    "REFUSED_TOOL_GRANT_FROM_INFER",
]
