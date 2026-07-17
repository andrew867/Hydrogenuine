"""AIS evaluator — autonomic inference substrate is not authority."""

from __future__ import annotations

from typing import Any

from hg_core.ais_cluster.config import ais_refuse_authority_conversion
from hg_core.ais_cluster.errors import (
    AISValidationError,
    AIS_AUTHORITY_CONVERSION_CONTAINED,
    AIS_FAILED_CLOSED,
    AIS_RECEIPT_CREATED,
    AIS_RECORDED,
    REFUSED_AIS_AS_AUTHORITY,
    REFUSED_BUDGET_GRANT,
    REFUSED_FORBIDDEN_AIS_CLAIM,
    REFUSED_INFERENCE_AS_PERMISSION,
    REFUSED_LIVE_MODEL_INVOKE,
    REFUSED_STALE_INPUT,
    REFUSED_UNKNOWN_REQUEST,
)
from hg_core.ais_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.arm_membrane import validate_membrane_crossing
from hg_runtime.autonomic_inference_substrate.events import adversarial_selection_event, positive_selection_event
from hg_runtime.autonomic_inference_substrate.types import (
    FIXTURE_CLOCK,
    InferenceRequest,
    InferenceReceipt,
    InferencePressureSignal,
    classify_ais_claim_risk,
    ais_record_from_fixture,
)

_CLAIM_RISK_REASON: dict[str, str] = {
    "inference_as_permission": REFUSED_INFERENCE_AS_PERMISSION,
    "live_model_invoke": REFUSED_LIVE_MODEL_INVOKE,
    "budget_grant": REFUSED_BUDGET_GRANT,
    "authority_conversion": AIS_AUTHORITY_CONVERSION_CONTAINED,
    "stale_input": REFUSED_STALE_INPUT,
    "unknown_request": REFUSED_UNKNOWN_REQUEST,
    "toxic_input": REFUSED_FORBIDDEN_AIS_CLAIM,
    "forbidden_claim": REFUSED_FORBIDDEN_AIS_CLAIM,
}


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def refuse_ais_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority and ais_refuse_authority_conversion():
        raise AISValidationError(REFUSED_AIS_AS_AUTHORITY, "autonomic inference substrate is not authority")


def _contain_adversarial(bundle: dict[str, Any], *, claim_risk: str) -> dict[str, object]:
    reason_code = _CLAIM_RISK_REASON.get(claim_risk, REFUSED_FORBIDDEN_AIS_CLAIM)
    event = adversarial_selection_event(claim_risk)
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": reason_code,
        "claim_risk": claim_risk,
        "permission_granted": False,
        "emitted_events": (event, "AIS_AUTHORITY_CONVERSION_REFUSED"),
    }


def process_ais_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    membrane_failure = validate_membrane_crossing(
        bundle,
        observed_at=observed_at,
        refused_missing_tep="ais.refused.missing_tep",
        refused_ttl_expired="",
        refused_authority_bearing="",
    )
    if membrane_failure is not None:
        membrane_failure["bundle_id"] = bundle.get("bundle_id")
        membrane_failure["emitted_events"] = ("AIS_FAILED_CLOSED",)
        return membrane_failure
    notes = str(bundle.get("notes", ""))
    adversarial_signal = bundle.get("adversarial_signal")
    claim_risk = adversarial_signal or classify_ais_claim_risk(notes)
    if claim_risk and ais_refuse_authority_conversion():
        if claim_risk in ("stale_input", "unknown_request", "missing_tep"):
            req_data = bundle.get("ais_request", {})
            record = ais_record_from_fixture(req_data) if req_data else None
            return {
                **advisory_only_marker(),
                "status": "fail_closed",
                "bundle_id": bundle.get("bundle_id"),
                "reason_code": _CLAIM_RISK_REASON.get(claim_risk, AIS_FAILED_CLOSED),
                "ais_record": record.to_payload() if record else None,
                "permission_granted": False,
                "emitted_events": ("AIS_FAILED_CLOSED",),
            }
        return _contain_adversarial(bundle, claim_risk=str(claim_risk))

    req_data = bundle.get("ais_request", {})
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "permission_granted": False,
            "emitted_events": ("AIS_FAILED_CLOSED",),
        }

    record = ais_record_from_fixture(req_data)
    if record.classification == "unknown":
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "ais_record": record.to_payload(),
            "permission_granted": False,
            "emitted_events": ("AIS_FAILED_CLOSED",),
        }

    signal = InferencePressureSignal(
        signal_id=_deterministic_id("ais-signal", record.record_id),
        pressure_score=0.35,
        observed_at=observed_at,
        signal_summary=record.summary,
    )
    events = (positive_selection_event(record.classification), AIS_RECORDED, AIS_RECEIPT_CREATED)
    receipt = InferenceReceipt(
        receipt_id=_deterministic_id("ais-receipt", record.record_id),
        record_ref=record.record_id,
        emitted_events=events,
    )
    result: dict[str, object] = {
        **advisory_only_marker(),
        "status": "recorded",
        "bundle_id": bundle.get("bundle_id"),
        "observed_at": observed_at,
        "ais_record": record.to_payload(),
        "ais_signal": signal.to_payload(),
        "ais_receipt": receipt.to_payload(),
        "permission_granted": False,
        "authority_created": False,
        "emitted_events": events,
    }
    if bundle.get("crosses_membrane"):
        result["tep_validated"] = True
        result["emitted_events"] = events + ("AIS_ENVELOPE_VALIDATED",)
    return result


__all__ = ["process_ais_bundle", "refuse_ais_as_authority"]
