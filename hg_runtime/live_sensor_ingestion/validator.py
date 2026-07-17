"""SEN-LIVE validator — IAM/TIM/GPP/UEAK/consent/redaction checks; no authority conversion."""

from __future__ import annotations

from hg_core.iam.authority import validate_operator_authority
from hg_core.iam.registry import load_registry
from hg_core.iam.types import AUTHORITY_SCOPES, OperatorRegistry
from hg_core.sen_live.errors import (
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_MISSING_CONSENT,
    REFUSED_MISSING_GPP_PERMIT,
    REFUSED_MISSING_IAM,
    REFUSED_MISSING_OPERATOR_APPROVAL,
    REFUSED_MISSING_REDACTION_POLICY,
    REFUSED_MISSING_TIM_FRESHNESS,
    REFUSED_MISSING_UEAK_ADMISSION,
    REFUSED_SCALAR_AS_TRUTH,
    REFUSED_SECRET_LEAK,
    REFUSED_SEN_AS_AUTHORITY,
    REFUSED_STALE_APPROVAL,
    REFUSED_STALE_TIM,
    SEN_OBSERVATION_CANDIDATE_BOUND,
)
from hg_core.sen_live.no_authority import advisory_only_marker
from hg_core.secrets.redact import contains_leak
from hg_core.time.expiry import validate_approval_window
from hg_runtime.live_sensor_ingestion.types import (
    SensorIngestRequest,
    is_bare_operator_ref,
    is_scalar_truth_claim,
    is_valid_tim_freshness,
)


def refuse_sen_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise ValueError(REFUSED_SEN_AS_AUTHORITY)


def _base_result(**extra: object) -> dict[str, object]:
    return {**advisory_only_marker(), **extra}


def validate_sensor_ingest_request(
    request: SensorIngestRequest,
    *,
    observed_at: str,
    registry: OperatorRegistry | None = None,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    """Validate sensor ingest request; observation candidates require IAM + TIM + consent + redaction."""
    if treat_as_authority or request.treat_as_authority:
        return _base_result(
            status="contained",
            reason_code=REFUSED_AUTHORITY_CONVERSION,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    leak_payload = {
        "observation_digest": request.observation_digest,
        "operator_ref": request.operator_ref,
    }
    if contains_leak(leak_payload):
        return _base_result(
            status="refused",
            reason_code=REFUSED_SECRET_LEAK,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    if is_scalar_truth_claim(request.observation_digest):
        return _base_result(
            status="refused",
            reason_code=REFUSED_SCALAR_AS_TRUTH,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    if not request.consent_ref:
        return _base_result(
            status="refused",
            reason_code=REFUSED_MISSING_CONSENT,
            request_id=request.request_id,
            evidence_admissible=False,
        )

    if not request.redaction_policy_ref:
        return _base_result(
            status="refused",
            reason_code=REFUSED_MISSING_REDACTION_POLICY,
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
        reason_code=SEN_OBSERVATION_CANDIDATE_BOUND,
        request_id=request.request_id,
        evidence_admissible=True,
        iam_binding=auth.binding.to_payload() if auth.binding else None,
        resolved_operator_id=auth.resolved_operator_id,
        approval_scope=scope,
    )


__all__ = ["refuse_sen_as_authority", "validate_sensor_ingest_request"]
