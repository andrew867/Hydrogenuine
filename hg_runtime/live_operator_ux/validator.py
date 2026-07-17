"""OUX-LIVE validator — IAM/TIM/GPP/UEAK checks; no authority conversion."""

from __future__ import annotations

from hg_core.iam.authority import validate_operator_authority
from hg_core.iam.registry import load_registry
from hg_core.iam.types import AUTHORITY_SCOPES, OperatorRegistry
from hg_core.oux_live.errors import (
    OUX_APPROVAL_EVIDENCE_BOUND,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_MISSING_GPP_PERMIT,
    REFUSED_MISSING_IAM,
    REFUSED_MISSING_OPERATOR_APPROVAL,
    REFUSED_MISSING_TIM_FRESHNESS,
    REFUSED_MISSING_UEAK_ADMISSION,
    REFUSED_OUX_AS_AUTHORITY,
    REFUSED_PANIC_AS_PERMISSION,
    REFUSED_SECRET_LEAK,
    REFUSED_SILENCE_AS_APPROVAL,
    REFUSED_STALE_APPROVAL,
    REFUSED_STALE_TIM,
    REFUSED_UI_STATE_AS_AUTHORITY,
)
from hg_core.oux_live.no_authority import advisory_only_marker
from hg_core.secrets.redact import contains_leak
from hg_core.time.expiry import validate_approval_window
from hg_runtime.live_operator_ux.types import (
    APPROVAL_EVIDENCE_ACTIONS,
    OperatorActionRequest,
    is_bare_operator_ref,
    is_valid_tim_freshness,
)


def refuse_oux_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise ValueError(REFUSED_OUX_AS_AUTHORITY)


def _base_result(**extra: object) -> dict[str, object]:
    return {**advisory_only_marker(), **extra}


def validate_operator_action_request(
    request: OperatorActionRequest,
    *,
    observed_at: str,
    registry: OperatorRegistry | None = None,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    """Validate operator action request; approval evidence requires IAM + TIM + expiry."""
    if treat_as_authority or request.treat_as_authority:
        return _base_result(
            status="contained",
            reason_code=REFUSED_AUTHORITY_CONVERSION,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    if request.silence_as_approval:
        return _base_result(
            status="refused",
            reason_code=REFUSED_SILENCE_AS_APPROVAL,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    if request.ui_display_state and request.ui_display_state.lower() in {"approved", "authorized", "permitted"}:
        return _base_result(
            status="contained",
            reason_code=REFUSED_UI_STATE_AS_AUTHORITY,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    leak_payload = {
        "review_item_ref": request.review_item_ref,
        "operator_ref": request.operator_ref,
    }
    if contains_leak(leak_payload):
        return _base_result(
            status="refused",
            reason_code=REFUSED_SECRET_LEAK,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    if request.control_kind == "panic" and "grants execution" in request.review_item_ref.lower():
        return _base_result(
            status="contained",
            reason_code=REFUSED_PANIC_AS_PERMISSION,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    if request.control_kind in APPROVAL_EVIDENCE_ACTIONS:
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
            reason_code=OUX_APPROVAL_EVIDENCE_BOUND,
            request_id=request.request_id,
            evidence_admissible=True,
            iam_binding=auth.binding.to_payload() if auth.binding else None,
            resolved_operator_id=auth.resolved_operator_id,
            approval_scope=scope,
        )

    # Restrict-only controls (deny/revoke/pause/panic) require operator identity but never grant authority
    if not request.operator_ref or is_bare_operator_ref(request.operator_ref):
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

    reg = registry or load_registry()
    scope = request.scope or "approve_change"
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
            request_id=request.request_id,
            evidence_admissible=False,
        )

    return _base_result(
        status="recorded",
        reason_code=f"oux.advisory.{request.control_kind}_recorded",
        request_id=request.request_id,
        evidence_admissible=False,
        restrict_only=True,
    )


__all__ = ["refuse_oux_as_authority", "validate_operator_action_request"]
