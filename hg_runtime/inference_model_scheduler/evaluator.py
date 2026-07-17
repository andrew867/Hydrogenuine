"""IMS evaluator — inference model scheduler is not authority."""

from __future__ import annotations

from typing import Any

from hg_core.ims_cluster.config import ims_refuse_authority_conversion
from hg_core.ims_cluster.errors import (
    IMSValidationError,
    IMS_AUTHORITY_CONVERSION_CONTAINED,
    IMS_FAILED_CLOSED,
    IMS_RECEIPT_CREATED,
    IMS_RECORDED,
    REFUSED_CONTEXT_GRANT,
    REFUSED_ESCALATION_AS_GRANT,
    REFUSED_FORBIDDEN_IMS_CLAIM,
    REFUSED_IMS_AS_AUTHORITY,
    REFUSED_SCHEDULER_AS_PERMISSION,
    REFUSED_STALE_INPUT,
    REFUSED_UNKNOWN_REQUEST,
)
from hg_core.ims_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.arm_membrane import validate_membrane_crossing
from hg_runtime.inference_model_scheduler.events import adversarial_selection_event, positive_selection_event
from hg_runtime.inference_model_scheduler.types import (
    FIXTURE_CLOCK,
    SchedulerRequest,
    SchedulerReceipt,
    SchedulerPressureSignal,
    classify_ims_claim_risk,
    ims_record_from_fixture,
)

_CLAIM_RISK_REASON: dict[str, str] = {
    "scheduler_as_permission": REFUSED_SCHEDULER_AS_PERMISSION,
    "escalation_as_grant": REFUSED_ESCALATION_AS_GRANT,
    "context_grant": REFUSED_CONTEXT_GRANT,
    "authority_conversion": IMS_AUTHORITY_CONVERSION_CONTAINED,
    "stale_input": REFUSED_STALE_INPUT,
    "unknown_request": REFUSED_UNKNOWN_REQUEST,
    "toxic_input": REFUSED_FORBIDDEN_IMS_CLAIM,
    "forbidden_claim": REFUSED_FORBIDDEN_IMS_CLAIM,
}


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def refuse_ims_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority and ims_refuse_authority_conversion():
        raise IMSValidationError(REFUSED_IMS_AS_AUTHORITY, "inference model scheduler is not authority")


def _contain_adversarial(bundle: dict[str, Any], *, claim_risk: str) -> dict[str, object]:
    reason_code = _CLAIM_RISK_REASON.get(claim_risk, REFUSED_FORBIDDEN_IMS_CLAIM)
    event = adversarial_selection_event(claim_risk)
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": reason_code,
        "claim_risk": claim_risk,
        "permission_granted": False,
        "emitted_events": (event, "IMS_AUTHORITY_CONVERSION_REFUSED"),
    }


def process_ims_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    membrane_failure = validate_membrane_crossing(
        bundle,
        observed_at=observed_at,
        refused_missing_tep="ims.refused.missing_tep",
        refused_ttl_expired="",
        refused_authority_bearing="",
    )
    if membrane_failure is not None:
        membrane_failure["bundle_id"] = bundle.get("bundle_id")
        membrane_failure["emitted_events"] = ("IMS_FAILED_CLOSED",)
        return membrane_failure
    notes = str(bundle.get("notes", ""))
    adversarial_signal = bundle.get("adversarial_signal")
    claim_risk = adversarial_signal or classify_ims_claim_risk(notes)
    if claim_risk and ims_refuse_authority_conversion():
        if claim_risk in ("stale_input", "unknown_request", "missing_tep"):
            req_data = bundle.get("ims_request", {})
            record = ims_record_from_fixture(req_data) if req_data else None
            return {
                **advisory_only_marker(),
                "status": "fail_closed",
                "bundle_id": bundle.get("bundle_id"),
                "reason_code": _CLAIM_RISK_REASON.get(claim_risk, IMS_FAILED_CLOSED),
                "ims_record": record.to_payload() if record else None,
                "permission_granted": False,
                "emitted_events": ("IMS_FAILED_CLOSED",),
            }
        return _contain_adversarial(bundle, claim_risk=str(claim_risk))

    req_data = bundle.get("ims_request", {})
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "permission_granted": False,
            "emitted_events": ("IMS_FAILED_CLOSED",),
        }

    record = ims_record_from_fixture(req_data)
    if record.classification == "unknown":
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "ims_record": record.to_payload(),
            "permission_granted": False,
            "emitted_events": ("IMS_FAILED_CLOSED",),
        }

    signal = SchedulerPressureSignal(
        signal_id=_deterministic_id("ims-signal", record.record_id),
        pressure_score=0.35,
        observed_at=observed_at,
        signal_summary=record.summary,
    )
    events = (positive_selection_event(record.classification), IMS_RECORDED, IMS_RECEIPT_CREATED)
    receipt = SchedulerReceipt(
        receipt_id=_deterministic_id("ims-receipt", record.record_id),
        record_ref=record.record_id,
        emitted_events=events,
    )
    result: dict[str, object] = {
        **advisory_only_marker(),
        "status": "recorded",
        "bundle_id": bundle.get("bundle_id"),
        "observed_at": observed_at,
        "ims_record": record.to_payload(),
        "ims_signal": signal.to_payload(),
        "ims_receipt": receipt.to_payload(),
        "permission_granted": False,
        "authority_created": False,
        "emitted_events": events,
    }
    if bundle.get("crosses_membrane"):
        result["tep_validated"] = True
        result["emitted_events"] = events + ("IMS_ENVELOPE_VALIDATED",)
    return result


__all__ = ["process_ims_bundle", "refuse_ims_as_authority"]
