"""SRP-LIVE validator — IAM/TIM/GPP/UEAK checks; no self-modification."""

from __future__ import annotations

from hg_core.iam.authority import validate_operator_authority
from hg_core.iam.registry import load_registry
from hg_core.iam.types import AUTHORITY_SCOPES, OperatorRegistry
from hg_core.srp_live.errors import (
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_MISSING_IAM,
    REFUSED_MISSING_OPERATOR_APPROVAL,
    REFUSED_MISSING_TIM_FRESHNESS,
    REFUSED_SECRET_LEAK,
    REFUSED_SELF_MODIFICATION,
    REFUSED_SRP_AS_AUTHORITY,
    REFUSED_STALE_APPROVAL,
    REFUSED_STALE_TIM,
    SRP_PLAN_BOUND,
)
from hg_core.srp_live.no_authority import advisory_only_marker
from hg_core.secrets.redact import contains_leak
from hg_core.time.expiry import validate_approval_window
from hg_runtime.live_srp_apply.types import SRPApplyRequest, is_bare_operator_ref, is_valid_tim_freshness


def refuse_srp_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise ValueError(REFUSED_SRP_AS_AUTHORITY)


def _base_result(**extra: object) -> dict[str, object]:
    return {**advisory_only_marker(), **extra}


def validate_srp_apply_request(
    request: SRPApplyRequest,
    *,
    observed_at: str,
    registry: OperatorRegistry | None = None,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    """Validate SRP apply request for plan phase; plans are not authority."""
    if treat_as_authority or request.treat_as_authority:
        return _base_result(
            status="contained",
            reason_code=REFUSED_AUTHORITY_CONVERSION,
            repair_id=request.repair_id,
            evidence_admissible=False,
        )

    if request.self_approved:
        return _base_result(
            status="refused",
            reason_code=REFUSED_SELF_MODIFICATION,
            repair_id=request.repair_id,
            evidence_admissible=False,
        )

    leak_payload = {
        "target_ref": request.target_ref,
        "change_set_digest": request.change_set_digest,
        "operator_ref": request.operator_ref,
    }
    if contains_leak(leak_payload):
        return _base_result(
            status="refused",
            reason_code=REFUSED_SECRET_LEAK,
            repair_id=request.repair_id,
            evidence_admissible=False,
        )

    if not request.operator_ref:
        return _base_result(
            status="refused",
            reason_code=REFUSED_MISSING_OPERATOR_APPROVAL,
            repair_id=request.repair_id,
            evidence_admissible=False,
        )

    if is_bare_operator_ref(request.operator_ref):
        return _base_result(
            status="refused",
            reason_code=REFUSED_MISSING_IAM,
            repair_id=request.repair_id,
            evidence_admissible=False,
        )

    if not is_valid_tim_freshness(request.freshness_ref):
        reason = REFUSED_STALE_TIM if request.freshness_ref == "tim:stale" else REFUSED_MISSING_TIM_FRESHNESS
        return _base_result(
            status="refused",
            reason_code=reason,
            repair_id=request.repair_id,
            evidence_admissible=False,
        )

    if not request.approval_expires_at:
        return _base_result(
            status="refused",
            reason_code=REFUSED_STALE_APPROVAL,
            repair_id=request.repair_id,
            evidence_admissible=False,
        )

    ok_window, _ = validate_approval_window(request.approval_expires_at, observed_at)
    if not ok_window:
        return _base_result(
            status="refused",
            reason_code=REFUSED_STALE_APPROVAL,
            repair_id=request.repair_id,
            evidence_admissible=False,
        )

    scope = request.scope or ""
    if not scope or scope not in AUTHORITY_SCOPES:
        return _base_result(
            status="refused",
            reason_code=REFUSED_MISSING_IAM,
            repair_id=request.repair_id,
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
            repair_id=request.repair_id,
            evidence_admissible=False,
        )

    return _base_result(
        status="recorded",
        reason_code=SRP_PLAN_BOUND,
        repair_id=request.repair_id,
        evidence_admissible=True,
        iam_binding=auth.binding.to_payload() if auth.binding else None,
        resolved_operator_id=auth.resolved_operator_id,
        approval_scope=scope,
    )


__all__ = ["refuse_srp_as_authority", "validate_srp_apply_request"]
