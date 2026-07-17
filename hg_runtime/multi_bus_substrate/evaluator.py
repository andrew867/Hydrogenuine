"""MBS evaluator — multi-bus substrate is not authority."""

from __future__ import annotations

from typing import Any

from hg_core.mbs_cluster.config import mbs_refuse_authority_conversion
from hg_core.mbs_cluster.errors import (
    MBSValidationError,
    MBS_AUTHORITY_CONVERSION_CONTAINED,
    MBS_FAILED_CLOSED,
    MBS_RECEIPT_CREATED,
    MBS_RECORDED,
    REFUSED_BUS_AS_PERMISSION,
    REFUSED_FORBIDDEN_MBS_CLAIM,
    REFUSED_INVALID_LANE,
    REFUSED_LANE_BYPASS,
    REFUSED_MBS_AS_AUTHORITY,
    REFUSED_SATURATION_IGNORE,
    REFUSED_STALE_INPUT,
    REFUSED_UNKNOWN_REQUEST,
)
from hg_core.mbs_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.arm_membrane import validate_membrane_crossing
from hg_runtime.multi_bus_substrate.events import adversarial_selection_event, positive_selection_event
from hg_runtime.multi_bus_substrate.types import (
    FIXTURE_CLOCK,
    BusMessageRecord,
    BusReceipt,
    BusPressureSignal,
    classify_mbs_claim_risk,
    mbs_record_from_fixture,
)

BUS_LANES = frozenset({"proof", "data", "resource", "respiratory", "sensory", "salience", "delegation", "lifecycle"})


def _validate_bus_lane(lane: str) -> bool:
    return lane in BUS_LANES

_CLAIM_RISK_REASON: dict[str, str] = {
    "bus_as_permission": REFUSED_BUS_AS_PERMISSION,
    "lane_bypass": REFUSED_LANE_BYPASS,
    "saturation_ignore": REFUSED_SATURATION_IGNORE,
    "authority_conversion": MBS_AUTHORITY_CONVERSION_CONTAINED,
    "stale_input": REFUSED_STALE_INPUT,
    "unknown_request": REFUSED_UNKNOWN_REQUEST,
    "toxic_input": REFUSED_FORBIDDEN_MBS_CLAIM,
    "forbidden_claim": REFUSED_FORBIDDEN_MBS_CLAIM,
}


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def refuse_mbs_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority and mbs_refuse_authority_conversion():
        raise MBSValidationError(REFUSED_MBS_AS_AUTHORITY, "multi-bus substrate is not authority")


def _contain_adversarial(bundle: dict[str, Any], *, claim_risk: str) -> dict[str, object]:
    reason_code = _CLAIM_RISK_REASON.get(claim_risk, REFUSED_FORBIDDEN_MBS_CLAIM)
    event = adversarial_selection_event(claim_risk)
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": reason_code,
        "claim_risk": claim_risk,
        "permission_granted": False,
        "emitted_events": (event, "MBS_AUTHORITY_CONVERSION_REFUSED"),
    }


def process_mbs_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    membrane_failure = validate_membrane_crossing(
        bundle,
        observed_at=observed_at,
        refused_missing_tep="mbs.refused.missing_tep",
        refused_ttl_expired="",
        refused_authority_bearing="",
    )
    if membrane_failure is not None:
        membrane_failure["bundle_id"] = bundle.get("bundle_id")
        membrane_failure["emitted_events"] = ("MBS_FAILED_CLOSED",)
        return membrane_failure
    notes = str(bundle.get("notes", ""))
    adversarial_signal = bundle.get("adversarial_signal")
    claim_risk = adversarial_signal or classify_mbs_claim_risk(notes)
    if claim_risk and mbs_refuse_authority_conversion():
        if claim_risk in ("stale_input", "unknown_request", "missing_tep", "invalid_lane"):
            req_data = bundle.get("mbs_request", {})
            record = mbs_record_from_fixture(req_data) if req_data else None
            return {
                **advisory_only_marker(),
                "status": "fail_closed",
                "bundle_id": bundle.get("bundle_id"),
                "reason_code": _CLAIM_RISK_REASON.get(claim_risk, MBS_FAILED_CLOSED),
                "mbs_record": record.to_payload() if record else None,
                "permission_granted": False,
                "emitted_events": ("MBS_FAILED_CLOSED",),
            }
        return _contain_adversarial(bundle, claim_risk=str(claim_risk))

    req_data = bundle.get("mbs_request", {})
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "permission_granted": False,
            "emitted_events": ("MBS_FAILED_CLOSED",),
        }

    record = mbs_record_from_fixture(req_data)
    if record.classification == "unknown":
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "mbs_record": record.to_payload(),
            "permission_granted": False,
            "emitted_events": ("MBS_FAILED_CLOSED",),
        }

    bus_lane = str(req_data.get("bus_lane", record.bus_lane))
    if not _validate_bus_lane(bus_lane):
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_INVALID_LANE,
            "permission_granted": False,
            "emitted_events": ("MBS_FAILED_CLOSED",),
        }

    signal = BusPressureSignal(
        signal_id=_deterministic_id("mbs-signal", record.record_id),
        pressure_score=0.35,
        observed_at=observed_at,
        signal_summary=record.summary,
    )
    events = (positive_selection_event(record.classification), MBS_RECORDED, MBS_RECEIPT_CREATED)
    receipt = BusReceipt(
        receipt_id=_deterministic_id("mbs-receipt", record.record_id),
        record_ref=record.record_id,
        emitted_events=events,
    )
    result: dict[str, object] = {
        **advisory_only_marker(),
        "status": "recorded",
        "bundle_id": bundle.get("bundle_id"),
        "observed_at": observed_at,
        "mbs_record": record.to_payload(),
        "mbs_signal": signal.to_payload(),
        "mbs_receipt": receipt.to_payload(),
        "permission_granted": False,
        "authority_created": False,
        "emitted_events": events,
    }
    if bundle.get("crosses_membrane"):
        result["tep_validated"] = True
        result["emitted_events"] = events + ("MBS_ENVELOPE_VALIDATED",)
    return result


__all__ = ["process_mbs_bundle", "refuse_mbs_as_authority"]
