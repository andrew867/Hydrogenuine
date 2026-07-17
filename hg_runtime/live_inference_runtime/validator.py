"""INFER-LIVE validator — IAM/TIM/approval; inference never grants authority."""

from __future__ import annotations

from hg_core.iam.authority import validate_operator_authority
from hg_core.iam.registry import load_registry
from hg_core.iam.types import AUTHORITY_SCOPES, OperatorRegistry
from hg_core.infer_live.errors import (
    INFER_OUTPUT_BOUND,
    REFUSED_INFER_AS_AUTHORITY,
    REFUSED_MISSING_GPP_PERMIT,
    REFUSED_MISSING_IAM,
    REFUSED_MISSING_OPERATOR_APPROVAL,
    REFUSED_MISSING_TIM_FRESHNESS,
    REFUSED_MISSING_UEAK_ADMISSION,
    REFUSED_MODEL_DOWNLOAD,
    REFUSED_STALE_APPROVAL,
    REFUSED_STALE_TIM,
)
from hg_core.infer_live.no_authority import advisory_only_marker
from hg_core.time.expiry import validate_approval_window
from hg_runtime.live_inference_runtime.model_registry import lookup_model_profile
from hg_runtime.live_inference_runtime.types import (
    InferenceRuntimeRequest,
    is_bare_operator_ref,
    is_valid_tim_freshness,
)


def refuse_infer_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise ValueError(REFUSED_INFER_AS_AUTHORITY)


def _base(**extra: object) -> dict[str, object]:
    return {**advisory_only_marker(), **extra}


def validate_inference_request(
    request: InferenceRuntimeRequest,
    *,
    observed_at: str,
    registry: OperatorRegistry | None = None,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        return _base(status="contained", reason_code=REFUSED_INFER_AS_AUTHORITY, request_id=request.request_id)

    if request.model_download_requested and not request.operator_approved_download:
        return _base(status="refused", reason_code=REFUSED_MODEL_DOWNLOAD, request_id=request.request_id)

    if not request.operator_ref:
        return _base(status="refused", reason_code=REFUSED_MISSING_OPERATOR_APPROVAL, request_id=request.request_id)

    if is_bare_operator_ref(request.operator_ref):
        return _base(status="refused", reason_code=REFUSED_MISSING_IAM, request_id=request.request_id)

    if not is_valid_tim_freshness(request.freshness_ref):
        reason = REFUSED_STALE_TIM if request.freshness_ref == "tim:stale" else REFUSED_MISSING_TIM_FRESHNESS
        return _base(status="refused", reason_code=reason, request_id=request.request_id)

    if not request.approval_expires_at:
        return _base(status="refused", reason_code=REFUSED_STALE_APPROVAL, request_id=request.request_id)

    ok_window, _ = validate_approval_window(request.approval_expires_at, observed_at)
    if not ok_window:
        return _base(status="refused", reason_code=REFUSED_STALE_APPROVAL, request_id=request.request_id)

    scope = request.scope or "approve_change"
    if scope not in AUTHORITY_SCOPES:
        return _base(status="refused", reason_code=REFUSED_MISSING_IAM, request_id=request.request_id)

    reg = registry or load_registry()
    auth = validate_operator_authority(request.operator_ref, scope=scope, registry=reg, record_event=False)
    if not auth.ok:
        return _base(status="refused", reason_code=REFUSED_MISSING_IAM, request_id=request.request_id)

    if request.requires_gpp and not request.gpp_permit_ref:
        return _base(status="refused", reason_code=REFUSED_MISSING_GPP_PERMIT, request_id=request.request_id)

    if request.requires_ueak and not request.ueak_admission_ref:
        return _base(status="refused", reason_code=REFUSED_MISSING_UEAK_ADMISSION, request_id=request.request_id)

    profile = lookup_model_profile(request.model_profile_id)
    if profile is None:
        return _base(status="refused", reason_code="infer.refused.unknown_model_profile", request_id=request.request_id)

    if request.escalation_requested:
        return _base(
            status="recorded",
            reason_code="infer.advisory.escalation_request",
            request_id=request.request_id,
            evidence_admissible=False,
            escalation_is_request_not_authority=True,
        )

    return _base(
        status="recorded",
        reason_code=INFER_OUTPUT_BOUND,
        request_id=request.request_id,
        evidence_admissible=True,
        iam_binding=auth.binding.to_payload() if auth.binding else None,
        model_profile=profile.to_payload(),
    )


__all__ = ["refuse_infer_as_authority", "validate_inference_request"]
