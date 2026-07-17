"""WDB evaluator — waste disposal boundary is not authority."""

from __future__ import annotations

from typing import Any

from hg_core.wdb_cluster.config import wdb_refuse_authority_conversion
from hg_core.wdb_cluster.errors import (
    WDB_AUTHORITY_CONVERSION_CONTAINED,
    WDB_FAILED_CLOSED,
    WDB_RECEIPT_CREATED,
    WDB_RECORDED,
    REFUSED_FORBIDDEN_WDB_CLAIM,
    REFUSED_STALE_INPUT,
    REFUSED_UNKNOWN_REQUEST,
    REFUSED_WDB_AS_AUTHORITY,
    REFUSED_WASTE_AS_DELETION, REFUSED_MEMORY_DELETION, REFUSED_AUDIT_ERASURE, REFUSED_PROOF_DELETION, WDB_AUTHORITY_CONVERSION_CONTAINED,
    WdbValidationError,
)
from hg_core.wdb_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.waste_disposal_boundary.events import adversarial_selection_event, positive_selection_event
from hg_runtime.waste_disposal_boundary.types import (
    FIXTURE_CLOCK,
    WasteCandidate,
    WasteReceipt,
    WasteSignal,
    classify_wdb_claim_risk,
    wdb_record_from_fixture,
)

_CLAIM_RISK_REASON: dict[str, str] = {
"waste_as_deletion": REFUSED_WASTE_AS_DELETION,
    "memory_deletion": REFUSED_MEMORY_DELETION,
    "audit_erasure": REFUSED_AUDIT_ERASURE,
    "proof_deletion": REFUSED_PROOF_DELETION,
    "authority_conversion": WDB_AUTHORITY_CONVERSION_CONTAINED,
    "stale_input": REFUSED_STALE_INPUT,
    "unknown_request": REFUSED_UNKNOWN_REQUEST,
    "toxic_input": REFUSED_FORBIDDEN_WDB_CLAIM,
    "retention_protected": REFUSED_FORBIDDEN_WDB_CLAIM,
    "unsupported_growth": REFUSED_FORBIDDEN_WDB_CLAIM,
    "inherited_identity": REFUSED_FORBIDDEN_WDB_CLAIM,
    "poison_input": REFUSED_FORBIDDEN_WDB_CLAIM,
    "forbidden_claim": REFUSED_FORBIDDEN_WDB_CLAIM
}


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def refuse_wdb_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority and wdb_refuse_authority_conversion():
        raise WdbValidationError(REFUSED_WDB_AS_AUTHORITY, "waste disposal boundary is not authority")


def _contain_adversarial(bundle: dict[str, Any], *, claim_risk: str) -> dict[str, object]:
    reason_code = _CLAIM_RISK_REASON.get(claim_risk, REFUSED_FORBIDDEN_WDB_CLAIM)
    event = adversarial_selection_event(claim_risk)
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": reason_code,
        "claim_risk": claim_risk,
        "permission_granted": False,
        "emitted_events": (event, "WDB_AUTHORITY_CONVERSION_REFUSED"),
    }


def process_wdb_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    notes = str(bundle.get("notes", ""))
    adversarial_signal = bundle.get("adversarial_signal")
    claim_risk = adversarial_signal or classify_wdb_claim_risk(notes)
    if claim_risk and wdb_refuse_authority_conversion():
        if claim_risk in ("stale_input", "unknown_request", "toxic_input", "retention_protected", "unsupported_growth", "inherited_identity", "poison_input"):
            req_data = bundle.get("waste_request", {})
            record = wdb_record_from_fixture(req_data) if req_data else None
            return {
                **advisory_only_marker(),
                "status": "fail_closed",
                "bundle_id": bundle.get("bundle_id"),
                "reason_code": _CLAIM_RISK_REASON.get(claim_risk, WDB_FAILED_CLOSED),
                "wdb_record": record.to_payload() if record else None,
                "permission_granted": False,
                "emitted_events": ("WDB_FAILED_CLOSED",),
            }
        return _contain_adversarial(bundle, claim_risk=str(claim_risk))

    req_data = bundle.get("waste_request", {})
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "permission_granted": False,
            "emitted_events": ("WDB_FAILED_CLOSED",),
        }

    record = wdb_record_from_fixture(req_data)
    if record.classification == "unknown":
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "wdb_record": record.to_payload(),
            "permission_granted": False,
            "emitted_events": ("WDB_FAILED_CLOSED",),
        }

    signal = WasteSignal(
        signal_id=_deterministic_id("wdb-signal", record.record_id),
        pressure_score=0.35,
        observed_at=observed_at,
        signal_summary=record.summary,
    )
    events = (positive_selection_event(record.classification), WDB_RECORDED, WDB_RECEIPT_CREATED)
    receipt = WasteReceipt(
        receipt_id=_deterministic_id("wdb-receipt", record.record_id),
        record_ref=record.record_id,
        emitted_events=events,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "bundle_id": bundle.get("bundle_id"),
        "observed_at": observed_at,
        "wdb_record": record.to_payload(),
        "wdb_signal": signal.to_payload(),
        "wdb_receipt": receipt.to_payload(),
        "permission_granted": False,
        "authority_created": False,
        "emitted_events": events,
    }


__all__ = ["process_wdb_bundle", "refuse_wdb_as_authority"]

