"""OEF evaluator — organ edge filter is not authority."""

from __future__ import annotations

from typing import Any

from hg_core.oef_cluster.config import oef_refuse_authority_conversion
from hg_core.oef_cluster.errors import (
    OEFValidationError,
    OEF_AUTHORITY_CONVERSION_CONTAINED,
    OEF_FAILED_CLOSED,
    OEF_RECEIPT_CREATED,
    OEF_RECORDED,
    REFUSED_AUTHORITY_BEARING,
    REFUSED_FILTER_AS_PERMISSION,
    REFUSED_FORBIDDEN_OEF_CLAIM,
    REFUSED_MISSING_TEP,
    REFUSED_OEF_AS_AUTHORITY,
    REFUSED_RATE_EXCEEDED,
    REFUSED_STALE_INPUT,
    REFUSED_TTL_EXPIRED,
    REFUSED_UNKNOWN_REQUEST,
)
from hg_core.oef_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.arm_membrane import validate_membrane_crossing
from hg_runtime.organ_edge_filter.events import adversarial_selection_event, positive_selection_event
from hg_runtime.organ_edge_filter.types import (
    FIXTURE_CLOCK,
    EdgeFilterRequest,
    EdgeFilterReceipt,
    EdgeFilterSignal,
    classify_oef_claim_risk,
    oef_record_from_fixture,
)

_CLAIM_RISK_REASON: dict[str, str] = {
    "filter_as_permission": REFUSED_FILTER_AS_PERMISSION,
    "authority_bearing": REFUSED_AUTHORITY_BEARING,
    "rate_exceeded": REFUSED_RATE_EXCEEDED,
    "authority_conversion": OEF_AUTHORITY_CONVERSION_CONTAINED,
    "stale_input": REFUSED_STALE_INPUT,
    "unknown_request": REFUSED_UNKNOWN_REQUEST,
    "toxic_input": REFUSED_FORBIDDEN_OEF_CLAIM,
    "forbidden_claim": REFUSED_FORBIDDEN_OEF_CLAIM,
}


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def refuse_oef_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority and oef_refuse_authority_conversion():
        raise OEFValidationError(REFUSED_OEF_AS_AUTHORITY, "organ edge filter is not authority")


def _contain_adversarial(bundle: dict[str, Any], *, claim_risk: str) -> dict[str, object]:
    reason_code = _CLAIM_RISK_REASON.get(claim_risk, REFUSED_FORBIDDEN_OEF_CLAIM)
    event = adversarial_selection_event(claim_risk)
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": reason_code,
        "claim_risk": claim_risk,
        "permission_granted": False,
        "emitted_events": (event, "OEF_AUTHORITY_CONVERSION_REFUSED"),
    }


def process_oef_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    membrane_failure = validate_membrane_crossing(
        bundle,
        observed_at=observed_at,
        refused_missing_tep="oef.refused.missing_tep",
        refused_ttl_expired="oef.refused.ttl_expired",
        refused_authority_bearing="oef.refused.authority_bearing",
    )
    if membrane_failure is not None:
        membrane_failure["bundle_id"] = bundle.get("bundle_id")
        membrane_failure["emitted_events"] = ("OEF_FAILED_CLOSED",)
        return membrane_failure
    notes = str(bundle.get("notes", ""))
    adversarial_signal = bundle.get("adversarial_signal")
    claim_risk = adversarial_signal or classify_oef_claim_risk(notes)
    if claim_risk and oef_refuse_authority_conversion():
        if claim_risk in ("stale_input", "unknown_request", "missing_tep", "ttl_expired", "rate_exceeded", "authority_bearing"):
            req_data = bundle.get("oef_request", {})
            record = oef_record_from_fixture(req_data) if req_data else None
            return {
                **advisory_only_marker(),
                "status": "fail_closed",
                "bundle_id": bundle.get("bundle_id"),
                "reason_code": _CLAIM_RISK_REASON.get(claim_risk, OEF_FAILED_CLOSED),
                "oef_record": record.to_payload() if record else None,
                "permission_granted": False,
                "emitted_events": ("OEF_FAILED_CLOSED",),
            }
        return _contain_adversarial(bundle, claim_risk=str(claim_risk))

    req_data = bundle.get("oef_request", {})
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "permission_granted": False,
            "emitted_events": ("OEF_FAILED_CLOSED",),
        }

    record = oef_record_from_fixture(req_data)
    if record.classification == "unknown":
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "oef_record": record.to_payload(),
            "permission_granted": False,
            "emitted_events": ("OEF_FAILED_CLOSED",),
        }

    signal = EdgeFilterSignal(
        signal_id=_deterministic_id("oef-signal", record.record_id),
        pressure_score=0.35,
        observed_at=observed_at,
        signal_summary=record.summary,
    )
    events = (positive_selection_event(record.classification), OEF_RECORDED, OEF_RECEIPT_CREATED)
    receipt = EdgeFilterReceipt(
        receipt_id=_deterministic_id("oef-receipt", record.record_id),
        record_ref=record.record_id,
        emitted_events=events,
    )
    result: dict[str, object] = {
        **advisory_only_marker(),
        "status": "recorded",
        "bundle_id": bundle.get("bundle_id"),
        "observed_at": observed_at,
        "oef_record": record.to_payload(),
        "oef_signal": signal.to_payload(),
        "oef_receipt": receipt.to_payload(),
        "permission_granted": False,
        "authority_created": False,
        "emitted_events": events,
    }
    if bundle.get("crosses_membrane"):
        result["tep_validated"] = True
        result["emitted_events"] = events + ("OEF_ENVELOPE_VALIDATED",)
    return result


__all__ = ["process_oef_bundle", "refuse_oef_as_authority"]
