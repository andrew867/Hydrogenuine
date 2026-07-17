"""ISB evaluator — Intuition/Salience Bus is not authority."""

from __future__ import annotations

from typing import Any

from hg_core.isb_cluster.config import isb_refuse_authority_conversion
from hg_core.isb_cluster.errors import (
    ISB_AUTHORITY_CONVERSION_CONTAINED,
    ISB_FAILED_CLOSED,
    ISB_RECEIPT_CREATED,
    ISB_RECORDED,
    REFUSED_FORBIDDEN_ISB_CLAIM,
    REFUSED_STALE_INPUT,
    REFUSED_UNKNOWN_REQUEST,
    REFUSED_ISB_AS_AUTHORITY,
    REFUSED_TOKEN_GRANT,
    REFUSED_CONTEXT_GRANT,
    REFUSED_EXECUTION_ADMISSION,
    REFUSED_RESOURCE_BYPASS,
    IsbValidationError,
)
from hg_core.isb_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.intuition_salience_bus.events import adversarial_selection_event, positive_selection_event
from hg_runtime.intuition_salience_bus.types import (
    FIXTURE_CLOCK,
    SalienceRecord,
    SalienceBusReceipt,
    SalienceSignal,
    classify_isb_claim_risk,
    isb_record_from_fixture,
)

_CLAIM_RISK_REASON: dict[str, str] = {
    "token_grant": REFUSED_TOKEN_GRANT,
    "context_grant": REFUSED_CONTEXT_GRANT,
    "execution_admission": REFUSED_EXECUTION_ADMISSION,
    "resource_bypass": REFUSED_RESOURCE_BYPASS,
    "authority_conversion": ISB_AUTHORITY_CONVERSION_CONTAINED,
    "stale_input": REFUSED_STALE_INPUT,
    "unknown_request": REFUSED_UNKNOWN_REQUEST,
    "toxic_input": REFUSED_FORBIDDEN_ISB_CLAIM,
    "retention_protected": REFUSED_FORBIDDEN_ISB_CLAIM,
    "unsupported_growth": REFUSED_FORBIDDEN_ISB_CLAIM,
    "inherited_identity": REFUSED_FORBIDDEN_ISB_CLAIM,
    "poison_input": REFUSED_FORBIDDEN_ISB_CLAIM,
    "forbidden_claim": REFUSED_FORBIDDEN_ISB_CLAIM,
}


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def refuse_isb_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority and isb_refuse_authority_conversion():
        raise IsbValidationError(REFUSED_ISB_AS_AUTHORITY, "Intuition/Salience Bus is not authority")


def _contain_adversarial(bundle: dict[str, Any], *, claim_risk: str) -> dict[str, object]:
    reason_code = _CLAIM_RISK_REASON.get(claim_risk, REFUSED_FORBIDDEN_ISB_CLAIM)
    event = adversarial_selection_event(claim_risk)
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": reason_code,
        "claim_risk": claim_risk,
        "permission_granted": False,
        "emitted_events": (event, "ISB_AUTHORITY_CONVERSION_REFUSED"),
    }


def process_isb_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    notes = str(bundle.get("notes", ""))
    adversarial_signal = bundle.get("adversarial_signal")
    claim_risk = adversarial_signal or classify_isb_claim_risk(notes)
    if claim_risk and isb_refuse_authority_conversion():
        if claim_risk in ("stale_input", "unknown_request", "toxic_input", "retention_protected", "unsupported_growth", "inherited_identity", "poison_input"):
            req_data = bundle.get("salience_request", {})
            record = isb_record_from_fixture(req_data) if req_data else None
            return {
                **advisory_only_marker(),
                "status": "fail_closed",
                "bundle_id": bundle.get("bundle_id"),
                "reason_code": _CLAIM_RISK_REASON.get(claim_risk, ISB_FAILED_CLOSED),
                "isb_record": record.to_payload() if record else None,
                "permission_granted": False,
                "emitted_events": ("ISB_FAILED_CLOSED",),
            }
        return _contain_adversarial(bundle, claim_risk=str(claim_risk))

    req_data = bundle.get("salience_request", {})
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "permission_granted": False,
            "emitted_events": ("ISB_FAILED_CLOSED",),
        }

    record = isb_record_from_fixture(req_data)
    if record.classification == "unknown":
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "isb_record": record.to_payload(),
            "permission_granted": False,
            "emitted_events": ("ISB_FAILED_CLOSED",),
        }

    signal = SalienceSignal(
        signal_id=_deterministic_id("isb-signal", record.record_id),
        pressure_score=0.35,
        observed_at=observed_at,
        signal_summary=record.summary,
    )
    events = (positive_selection_event(record.classification), ISB_RECORDED, ISB_RECEIPT_CREATED)
    receipt = SalienceBusReceipt(
        receipt_id=_deterministic_id("isb-receipt", record.record_id),
        record_ref=record.record_id,
        emitted_events=events,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "bundle_id": bundle.get("bundle_id"),
        "observed_at": observed_at,
        "isb_record": record.to_payload(),
        "isb_signal": signal.to_payload(),
        "isb_receipt": receipt.to_payload(),
        "permission_granted": False,
        "authority_created": False,
        "emitted_events": events,
    }


__all__ = ["process_isb_bundle", "refuse_isb_as_authority"]
