"""DSE sink admission — IAM/TIM/GPP/UEAK/operator approval gate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_core.dse.config import dse_real_sink_enabled
from hg_core.dse.errors import (
    DSE_ADMISSION_GRANTED,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_MISSING_GPP_PERMIT,
    REFUSED_MISSING_IAM,
    REFUSED_MISSING_OPERATOR_APPROVAL,
    REFUSED_MISSING_TIM_FRESHNESS,
    REFUSED_MISSING_UEAK_ADMISSION,
    REFUSED_REAL_SINK_DISABLED,
    REFUSED_SECRET_LEAK,
    REFUSED_SINK_NOT_IN_SCOPE,
    REFUSED_STALE_APPROVAL,
    REFUSED_STALE_TIM,
    REFUSED_WRONG_SINK_CLASS,
)
from hg_core.dse.no_authority import advisory_only_marker
from hg_core.dse.policy import RealSinkPolicy, SinkClass
from hg_core.dse.types import SinkAdmissionDecision
from hg_core.iam.authority import validate_operator_authority
from hg_core.iam.registry import load_registry
from hg_core.iam.types import AUTHORITY_SCOPES, OperatorRegistry
from hg_core.secrets.redact import contains_leak
from hg_core.time.expiry import validate_approval_window


def is_bare_operator_ref(operator_ref: str | None) -> bool:
    if not operator_ref:
        return True
    return ":" not in operator_ref and not operator_ref.startswith("op:")


def is_valid_tim_freshness(freshness_ref: str | None) -> bool:
    if not freshness_ref:
        return False
    if freshness_ref == "tim:stale":
        return False
    return freshness_ref.startswith("tim:")


@dataclass(frozen=True)
class AdmissionRequest:
    request_id: str
    tranche_id: str
    sink_class: SinkClass
    operator_ref: str | None
    freshness_ref: str | None
    approval_expires_at: str | None
    scope: str | None
    requires_gpp: bool = False
    gpp_permit_ref: str | None = None
    requires_ueak: bool = False
    ueak_admission_ref: str | None = None
    treat_as_authority: bool = False
    payload: dict[str, Any] | None = None

    @classmethod
    def from_fixture(cls, data: dict[str, Any], *, tranche_id: str, sink_class: SinkClass) -> AdmissionRequest:
        return cls(
            request_id=str(data.get("request_id", "dse-req-unknown")),
            tranche_id=tranche_id,
            sink_class=sink_class,
            operator_ref=data.get("operator_ref"),
            freshness_ref=data.get("freshness_ref"),
            approval_expires_at=data.get("approval_expires_at"),
            scope=data.get("scope"),
            requires_gpp=bool(data.get("requires_gpp")),
            gpp_permit_ref=data.get("gpp_permit_ref"),
            requires_ueak=bool(data.get("requires_ueak")),
            ueak_admission_ref=data.get("ueak_admission_ref"),
            treat_as_authority=bool(data.get("treat_as_authority")),
            payload=data.get("payload"),
        )


def evaluate_sink_admission(
    request: AdmissionRequest,
    *,
    observed_at: str,
    expected_sink_class: SinkClass | None = None,
    registry: OperatorRegistry | None = None,
) -> SinkAdmissionDecision:
    """Evaluate admission for durable sink; never grants permission."""
    base = advisory_only_marker()
    policy = RealSinkPolicy(
        sink_class=request.sink_class,
        tranche_id=request.tranche_id,
        requires_gpp=request.requires_gpp,
        requires_ueak=request.requires_ueak,
    )

    def _deny(reason_code: str) -> SinkAdmissionDecision:
        return SinkAdmissionDecision(
            admitted=False,
            reason_code=reason_code,
            sink_class=request.sink_class.value,
            tranche_id=request.tranche_id,
            request_id=request.request_id,
            operator_ref=request.operator_ref,
            evidence_admissible=False,
            permission_granted=base["permission_granted"],
            authority_created=base["authority_created"],
        )

    if not dse_real_sink_enabled():
        return _deny(REFUSED_REAL_SINK_DISABLED)

    if request.treat_as_authority:
        return _deny(REFUSED_AUTHORITY_CONVERSION)

    in_scope, scope_reason = policy.validate_scope()
    if not in_scope:
        return _deny(scope_reason)

    if expected_sink_class and request.sink_class != expected_sink_class:
        return _deny(REFUSED_WRONG_SINK_CLASS)

    leak_payload = request.payload or {}
    leak_payload = {**leak_payload, "operator_ref": request.operator_ref}
    if contains_leak(leak_payload):
        return _deny(REFUSED_SECRET_LEAK)

    if not request.operator_ref:
        return _deny(REFUSED_MISSING_OPERATOR_APPROVAL)

    if is_bare_operator_ref(request.operator_ref):
        return _deny(REFUSED_MISSING_IAM)

    if not is_valid_tim_freshness(request.freshness_ref):
        reason = REFUSED_STALE_TIM if request.freshness_ref == "tim:stale" else REFUSED_MISSING_TIM_FRESHNESS
        return _deny(reason)

    if not request.approval_expires_at:
        return _deny(REFUSED_STALE_APPROVAL)

    ok_window, _ = validate_approval_window(request.approval_expires_at, observed_at)
    if not ok_window:
        return _deny(REFUSED_STALE_APPROVAL)

    scope = request.scope or ""
    if not scope or scope not in AUTHORITY_SCOPES:
        return _deny(REFUSED_MISSING_IAM)

    reg = registry or load_registry()
    auth = validate_operator_authority(request.operator_ref, scope=scope, registry=reg, record_event=False)
    if not auth.ok:
        return _deny(REFUSED_MISSING_IAM)

    if request.requires_gpp and not request.gpp_permit_ref:
        return _deny(REFUSED_MISSING_GPP_PERMIT)

    if request.requires_ueak and not request.ueak_admission_ref:
        return _deny(REFUSED_MISSING_UEAK_ADMISSION)

    return SinkAdmissionDecision(
        admitted=True,
        reason_code=DSE_ADMISSION_GRANTED,
        sink_class=request.sink_class.value,
        tranche_id=request.tranche_id,
        request_id=request.request_id,
        operator_ref=request.operator_ref,
        evidence_admissible=True,
        permission_granted=False,
        authority_created=False,
    )


__all__ = ["AdmissionRequest", "evaluate_sink_admission", "is_bare_operator_ref", "is_valid_tim_freshness"]
