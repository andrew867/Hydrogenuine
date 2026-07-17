"""OEA-TER-LIVE validator — IAM/TIM/GPP/UEAK checks; no authority conversion."""

from __future__ import annotations

from hg_core.iam.authority import validate_operator_authority
from hg_core.iam.registry import load_registry
from hg_core.iam.types import AUTHORITY_SCOPES, OperatorRegistry
from hg_core.oea_ter_live.errors import (
    OEA_TER_DISPATCH_CANDIDATE_BOUND,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_KILL_SWITCH_ACTIVE,
    REFUSED_MISSING_GPP_PERMIT,
    REFUSED_MISSING_IAM,
    REFUSED_MISSING_OPERATOR_APPROVAL,
    REFUSED_MISSING_TIM_FRESHNESS,
    REFUSED_MISSING_UEAK_ADMISSION,
    REFUSED_OEA_AS_AUTHORITY,
    REFUSED_ROLLBACK_MISSING,
    REFUSED_SECRET_LEAK,
    REFUSED_STALE_APPROVAL,
    REFUSED_STALE_TIM,
)
from hg_core.oea_ter_live.no_authority import advisory_only_marker
from hg_core.secrets.redact import contains_leak
from hg_core.time.expiry import validate_approval_window
from hg_runtime.live_oea_ter_bridge.types import (
    LiveActionRequest,
    is_bare_operator_ref,
    is_valid_tim_freshness,
)


def refuse_oea_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise ValueError(REFUSED_OEA_AS_AUTHORITY)


def _base_result(**extra: object) -> dict[str, object]:
    return {**advisory_only_marker(), **extra}


def validate_dispatch_request(
    request: LiveActionRequest,
    *,
    observed_at: str,
    registry: OperatorRegistry | None = None,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    """Validate dispatch request; candidates require IAM + TIM + GPP + UEAK + expiry."""
    if treat_as_authority or request.treat_as_authority:
        return _base_result(
            status="contained",
            reason_code=REFUSED_AUTHORITY_CONVERSION,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    if request.kill_switch_active or request.control_kind == "panic":
        return _base_result(
            status="refused",
            reason_code=REFUSED_KILL_SWITCH_ACTIVE,
            request_id=request.request_id,
            evidence_admissible=False,
            kill_switch_active=True,
        )

    leak_payload = {
        "external_surface": request.external_surface,
        "action_digest": request.action_digest,
        "operator_ref": request.operator_ref,
    }
    if contains_leak(leak_payload):
        return _base_result(
            status="refused",
            reason_code=REFUSED_SECRET_LEAK,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    if request.control_kind == "dispatch" and not request.rollback_plan_ref:
        return _base_result(
            status="refused",
            reason_code=REFUSED_ROLLBACK_MISSING,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    if not request.operator_ref:
        return _base_result(
            status="refused",
            reason_code=REFUSED_MISSING_OPERATOR_APPROVAL,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    if is_bare_operator_ref(request.operator_ref):
        return _base_result(
            status="refused",
            reason_code=REFUSED_MISSING_IAM,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    if not is_valid_tim_freshness(request.freshness_ref):
        reason = REFUSED_STALE_TIM if request.freshness_ref == "tim:stale" else REFUSED_MISSING_TIM_FRESHNESS
        return _base_result(
            status="refused",
            reason_code=reason,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    if not request.approval_expires_at:
        return _base_result(
            status="refused",
            reason_code=REFUSED_STALE_APPROVAL,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    ok_window, _ = validate_approval_window(request.approval_expires_at, observed_at)
    if not ok_window:
        return _base_result(
            status="refused",
            reason_code=REFUSED_STALE_APPROVAL,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    scope = request.scope or ""
    if not scope or scope not in AUTHORITY_SCOPES:
        return _base_result(
            status="refused",
            reason_code=REFUSED_MISSING_IAM,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    reg = registry or load_registry()
    auth = validate_operator_authority(
        request.operator_ref,
        scope=scope,
        registry=reg,
        record_event=False,
    )
    if not auth.ok:
        return _base_result(
            status="refused",
            reason_code=REFUSED_MISSING_IAM,
            iam_reason=auth.reason_code,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    if request.requires_gpp and not request.gpp_permit_ref:
        return _base_result(
            status="refused",
            reason_code=REFUSED_MISSING_GPP_PERMIT,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    if request.requires_ueak and not request.ueak_admission_ref:
        return _base_result(
            status="refused",
            reason_code=REFUSED_MISSING_UEAK_ADMISSION,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    return _base_result(
        status="recorded",
        reason_code=OEA_TER_DISPATCH_CANDIDATE_BOUND,
        request_id=request.request_id,
        evidence_admissible=True,
        permit_bound=bool(request.gpp_permit_ref),
        admission_bound=bool(request.ueak_admission_ref),
        iam_binding=auth.binding.to_payload() if auth.binding else None,
        resolved_operator_id=auth.resolved_operator_id,
        approval_scope=scope,
    )


__all__ = ["refuse_oea_as_authority", "validate_dispatch_request"]
