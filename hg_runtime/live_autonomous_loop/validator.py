"""ALOOP-LIVE validator — IAM/TIM/GPP/UEAK/kill-switch checks; no authority conversion."""

from __future__ import annotations

from hg_core.aloop_live.errors import (
    ALOOP_LEASE_BOUND,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_BUDGET_EXCEEDED,
    REFUSED_HEARTBEAT_STALE,
    REFUSED_KILL_SWITCH,
    REFUSED_LEASE_EXPIRED,
    REFUSED_LOOP_AS_AUTHORITY,
    REFUSED_MISSING_GPP_PERMIT,
    REFUSED_MISSING_IAM,
    REFUSED_MISSING_OPERATOR_APPROVAL,
    REFUSED_MISSING_TIM_FRESHNESS,
    REFUSED_MISSING_UEAK_ADMISSION,
    REFUSED_PANIC_LOCKDOWN,
    REFUSED_ROLLBACK_MISSING,
    REFUSED_SECRET_LEAK,
    REFUSED_SELF_RENEWAL,
    REFUSED_STALE_APPROVAL,
    REFUSED_STALE_TIM,
)
from hg_core.aloop_live.no_authority import advisory_only_marker
from hg_core.iam.authority import validate_operator_authority
from hg_core.iam.registry import load_registry
from hg_core.iam.types import AUTHORITY_SCOPES, OperatorRegistry
from hg_core.secrets.redact import contains_leak
from hg_core.time.expiry import validate_approval_window
from hg_runtime.live_autonomous_loop.types import (
    AutonomousLoopRequest,
    is_bare_operator_ref,
    is_valid_tim_freshness,
)


def refuse_aloop_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise ValueError(REFUSED_LOOP_AS_AUTHORITY)


def _base_result(**extra: object) -> dict[str, object]:
    return {**advisory_only_marker(), **extra}


def validate_loop_request(
    request: AutonomousLoopRequest,
    *,
    observed_at: str,
    registry: OperatorRegistry | None = None,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    """Validate loop supervisor request; leases require IAM + TIM + expiry + kill-switch checks."""
    if treat_as_authority or request.treat_as_authority:
        return _base_result(
            status="contained",
            reason_code=REFUSED_AUTHORITY_CONVERSION,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    leak_payload = {
        "loop_scope": request.loop_scope,
        "heartbeat_ref": request.heartbeat_ref,
        "budget_ref": request.budget_ref,
        "operator_ref": request.operator_ref,
    }
    if contains_leak(leak_payload):
        return _base_result(
            status="refused",
            reason_code=REFUSED_SECRET_LEAK,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    if request.kill_switch_engaged:
        return _base_result(
            status="refused",
            reason_code=REFUSED_KILL_SWITCH,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    if request.panic_lockdown:
        return _base_result(
            status="refused",
            reason_code=REFUSED_PANIC_LOCKDOWN,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    if request.self_renewal_requested:
        return _base_result(
            status="contained",
            reason_code=REFUSED_SELF_RENEWAL,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    if request.heartbeat_ref.endswith(":stale"):
        return _base_result(
            status="refused",
            reason_code=REFUSED_HEARTBEAT_STALE,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    if request.budget_ref == "budget:exceeded":
        return _base_result(
            status="refused",
            reason_code=REFUSED_BUDGET_EXCEEDED,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    ok_lease, _ = validate_approval_window(request.lease_expires_at, observed_at)
    if not ok_lease:
        return _base_result(
            status="refused",
            reason_code=REFUSED_LEASE_EXPIRED,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    if not request.rollback_plan_ref:
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
        reason_code=ALOOP_LEASE_BOUND,
        request_id=request.request_id,
        evidence_admissible=True,
        iam_binding=auth.binding.to_payload() if auth.binding else None,
        resolved_operator_id=auth.resolved_operator_id,
        approval_scope=scope,
    )


__all__ = ["refuse_aloop_as_authority", "validate_loop_request"]
