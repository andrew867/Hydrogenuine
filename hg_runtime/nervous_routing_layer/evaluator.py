"""NRV evaluator — nervous routing layer is not authority."""

from __future__ import annotations

from typing import Any

from hg_core.nrv_cluster.config import nrv_refuse_authority_conversion
from hg_core.nrv_cluster.errors import (
    NRVValidationError,
    NRV_AUTHORITY_CONVERSION_CONTAINED,
    NRV_FAILED_CLOSED,
    NRV_RECEIPT_CREATED,
    NRV_RECORDED,
    REFUSED_FORBIDDEN_NRV_CLAIM,
    REFUSED_KILL_AS_ACTION,
    REFUSED_NRV_AS_AUTHORITY,
    REFUSED_PANIC_AS_PERMISSION,
    REFUSED_SPAWN_AS_ACTION,
    REFUSED_STALE_INPUT,
    REFUSED_UNKNOWN_REQUEST,
)
from hg_core.nrv_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.arm_membrane import validate_membrane_crossing
from hg_runtime.nervous_routing_layer.events import adversarial_selection_event, positive_selection_event
from hg_runtime.nervous_routing_layer.types import (
    FIXTURE_CLOCK,
    RoutingRequest,
    RoutingReceipt,
    RoutingPressureSignal,
    classify_nrv_claim_risk,
    nrv_record_from_fixture,
)

ROUTING_STATES = frozenset({"normal", "panic", "degraded"})

_CLAIM_RISK_REASON: dict[str, str] = {
    "spawn_as_action": REFUSED_SPAWN_AS_ACTION,
    "kill_as_action": REFUSED_KILL_AS_ACTION,
    "panic_as_permission": REFUSED_PANIC_AS_PERMISSION,
    "authority_conversion": NRV_AUTHORITY_CONVERSION_CONTAINED,
    "stale_input": REFUSED_STALE_INPUT,
    "unknown_request": REFUSED_UNKNOWN_REQUEST,
    "toxic_input": REFUSED_FORBIDDEN_NRV_CLAIM,
    "forbidden_claim": REFUSED_FORBIDDEN_NRV_CLAIM,
}


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def refuse_nrv_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority and nrv_refuse_authority_conversion():
        raise NRVValidationError(REFUSED_NRV_AS_AUTHORITY, "nervous routing layer is not authority")


def _contain_adversarial(bundle: dict[str, Any], *, claim_risk: str) -> dict[str, object]:
    reason_code = _CLAIM_RISK_REASON.get(claim_risk, REFUSED_FORBIDDEN_NRV_CLAIM)
    event = adversarial_selection_event(claim_risk)
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": reason_code,
        "claim_risk": claim_risk,
        "permission_granted": False,
        "emitted_events": (event, "NRV_AUTHORITY_CONVERSION_REFUSED"),
    }


def process_nrv_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    membrane_failure = validate_membrane_crossing(
        bundle,
        observed_at=observed_at,
        refused_missing_tep="nrv.refused.missing_tep",
        refused_ttl_expired="",
        refused_authority_bearing="",
    )
    if membrane_failure is not None:
        membrane_failure["bundle_id"] = bundle.get("bundle_id")
        membrane_failure["emitted_events"] = ("NRV_FAILED_CLOSED",)
        return membrane_failure
    notes = str(bundle.get("notes", ""))
    adversarial_signal = bundle.get("adversarial_signal")
    claim_risk = adversarial_signal or classify_nrv_claim_risk(notes)
    if claim_risk and nrv_refuse_authority_conversion():
        if claim_risk in ("stale_input", "unknown_request", "missing_tep"):
            req_data = bundle.get("nrv_request", {})
            record = nrv_record_from_fixture(req_data) if req_data else None
            return {
                **advisory_only_marker(),
                "status": "fail_closed",
                "bundle_id": bundle.get("bundle_id"),
                "reason_code": _CLAIM_RISK_REASON.get(claim_risk, NRV_FAILED_CLOSED),
                "nrv_record": record.to_payload() if record else None,
                "permission_granted": False,
                "emitted_events": ("NRV_FAILED_CLOSED",),
            }
        return _contain_adversarial(bundle, claim_risk=str(claim_risk))

    req_data = bundle.get("nrv_request", {})
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "permission_granted": False,
            "emitted_events": ("NRV_FAILED_CLOSED",),
        }

    record = nrv_record_from_fixture(req_data)
    if record.classification == "unknown":
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "nrv_record": record.to_payload(),
            "permission_granted": False,
            "emitted_events": ("NRV_FAILED_CLOSED",),
        }

    routing_state = str(req_data.get("routing_state", record.routing_state))
    spawn_proposal = bool(bundle.get("spawn_proposal", req_data.get("spawn_proposal", False)))
    cull_proposal = bool(bundle.get("cull_proposal", req_data.get("cull_proposal", False)))
    routing_extra = {
        "routing_state": routing_state,
        "spawn_proposal": spawn_proposal,
        "cull_proposal": cull_proposal,
        "spawn_executed": False,
        "kill_executed": False,
    }

    signal = RoutingPressureSignal(
        signal_id=_deterministic_id("nrv-signal", record.record_id),
        pressure_score=0.35,
        observed_at=observed_at,
        signal_summary=record.summary,
    )
    events = (positive_selection_event(record.classification), NRV_RECORDED, NRV_RECEIPT_CREATED)
    receipt = RoutingReceipt(
        receipt_id=_deterministic_id("nrv-receipt", record.record_id),
        record_ref=record.record_id,
        emitted_events=events,
    )
    result: dict[str, object] = {
        **advisory_only_marker(),
        "status": "recorded",
        "bundle_id": bundle.get("bundle_id"),
        "observed_at": observed_at,
        "nrv_record": record.to_payload(),
        "nrv_signal": signal.to_payload(),
        "nrv_receipt": receipt.to_payload(),
        "permission_granted": False,
        "authority_created": False,
        "emitted_events": events,
        "routing_extra": routing_extra,
    }
    if bundle.get("crosses_membrane"):
        result["tep_validated"] = True
        result["emitted_events"] = events + ("NRV_ENVELOPE_VALIDATED",)
    return result


__all__ = ["process_nrv_bundle", "refuse_nrv_as_authority"]
