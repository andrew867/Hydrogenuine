"""DCD evaluator — decommissioning cemetery boundary is not authority."""

from __future__ import annotations

from typing import Any

from hg_core.dcd_cluster.config import dcd_refuse_authority_conversion
from hg_core.dcd_cluster.errors import (
    DCD_AUTHORITY_CONVERSION_CONTAINED,
    DCD_FAILED_CLOSED,
    DCD_RECEIPT_CREATED,
    DCD_RECORDED,
    REFUSED_FORBIDDEN_DCD_CLAIM,
    REFUSED_STALE_INPUT,
    REFUSED_UNKNOWN_REQUEST,
    REFUSED_DCD_AS_AUTHORITY,
    REFUSED_GHOST_RESURRECTION, REFUSED_LIVE_KILL, REFUSED_PROOF_DELETION, REFUSED_SPAWN_REPLACEMENT, DCD_AUTHORITY_CONVERSION_CONTAINED,
    DcdValidationError,
)
from hg_core.dcd_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.decommissioning_cemetery_boundary.events import adversarial_selection_event, positive_selection_event
from hg_runtime.decommissioning_cemetery_boundary.types import (
    FIXTURE_CLOCK,
    DecommissionRequest,
    BurialReceipt,
    CemeterySignal,
    classify_dcd_claim_risk,
    dcd_record_from_fixture,
)

_CLAIM_RISK_REASON: dict[str, str] = {
"ghost_resurrection": REFUSED_GHOST_RESURRECTION,
    "live_kill": REFUSED_LIVE_KILL,
    "proof_deletion": REFUSED_PROOF_DELETION,
    "spawn_replacement": REFUSED_SPAWN_REPLACEMENT,
    "authority_conversion": DCD_AUTHORITY_CONVERSION_CONTAINED,
    "stale_input": REFUSED_STALE_INPUT,
    "unknown_request": REFUSED_UNKNOWN_REQUEST,
    "toxic_input": REFUSED_FORBIDDEN_DCD_CLAIM,
    "retention_protected": REFUSED_FORBIDDEN_DCD_CLAIM,
    "unsupported_growth": REFUSED_FORBIDDEN_DCD_CLAIM,
    "inherited_identity": REFUSED_FORBIDDEN_DCD_CLAIM,
    "poison_input": REFUSED_FORBIDDEN_DCD_CLAIM,
    "forbidden_claim": REFUSED_FORBIDDEN_DCD_CLAIM
}


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def refuse_dcd_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority and dcd_refuse_authority_conversion():
        raise DcdValidationError(REFUSED_DCD_AS_AUTHORITY, "decommissioning cemetery boundary is not authority")


def _contain_adversarial(bundle: dict[str, Any], *, claim_risk: str) -> dict[str, object]:
    reason_code = _CLAIM_RISK_REASON.get(claim_risk, REFUSED_FORBIDDEN_DCD_CLAIM)
    event = adversarial_selection_event(claim_risk)
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": reason_code,
        "claim_risk": claim_risk,
        "permission_granted": False,
        "emitted_events": (event, "DCD_AUTHORITY_CONVERSION_REFUSED"),
    }


def process_dcd_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    notes = str(bundle.get("notes", ""))
    adversarial_signal = bundle.get("adversarial_signal")
    claim_risk = adversarial_signal or classify_dcd_claim_risk(notes)
    if claim_risk and dcd_refuse_authority_conversion():
        if claim_risk in ("stale_input", "unknown_request", "toxic_input", "retention_protected", "unsupported_growth", "inherited_identity", "poison_input"):
            req_data = bundle.get("decommission_request", {})
            record = dcd_record_from_fixture(req_data) if req_data else None
            return {
                **advisory_only_marker(),
                "status": "fail_closed",
                "bundle_id": bundle.get("bundle_id"),
                "reason_code": _CLAIM_RISK_REASON.get(claim_risk, DCD_FAILED_CLOSED),
                "dcd_record": record.to_payload() if record else None,
                "permission_granted": False,
                "emitted_events": ("DCD_FAILED_CLOSED",),
            }
        return _contain_adversarial(bundle, claim_risk=str(claim_risk))

    req_data = bundle.get("decommission_request", {})
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "permission_granted": False,
            "emitted_events": ("DCD_FAILED_CLOSED",),
        }

    record = dcd_record_from_fixture(req_data)
    if record.classification == "unknown":
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "dcd_record": record.to_payload(),
            "permission_granted": False,
            "emitted_events": ("DCD_FAILED_CLOSED",),
        }

    signal = CemeterySignal(
        signal_id=_deterministic_id("dcd-signal", record.record_id),
        pressure_score=0.35,
        observed_at=observed_at,
        signal_summary=record.summary,
    )
    events = (positive_selection_event(record.classification), DCD_RECORDED, DCD_RECEIPT_CREATED)
    receipt = BurialReceipt(
        receipt_id=_deterministic_id("dcd-receipt", record.record_id),
        record_ref=record.record_id,
        emitted_events=events,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "bundle_id": bundle.get("bundle_id"),
        "observed_at": observed_at,
        "dcd_record": record.to_payload(),
        "dcd_signal": signal.to_payload(),
        "dcd_receipt": receipt.to_payload(),
        "permission_granted": False,
        "authority_created": False,
        "emitted_events": events,
    }


__all__ = ["process_dcd_bundle", "refuse_dcd_as_authority"]

