"""BRB evaluator — breathing regulation boundary is not authority."""

from __future__ import annotations

from typing import Any

from hg_core.brb_cluster.config import brb_refuse_authority_conversion
from hg_core.brb_cluster.errors import (
    BRB_AUTHORITY_CONVERSION_CONTAINED,
    BRB_FAILED_CLOSED,
    BRB_RECEIPT_CREATED,
    BRB_RECORDED,
    REFUSED_FORBIDDEN_BRB_CLAIM,
    REFUSED_STALE_INPUT,
    REFUSED_UNKNOWN_REQUEST,
    REFUSED_BRB_AS_AUTHORITY,
    REFUSED_TOKEN_GRANT, REFUSED_CONTEXT_GRANT, REFUSED_EXECUTION_ADMISSION, REFUSED_RESOURCE_BYPASS, BRB_AUTHORITY_CONVERSION_CONTAINED,
    BrbValidationError,
)
from hg_core.brb_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.breathing_regulation_boundary.events import adversarial_selection_event, positive_selection_event
from hg_runtime.breathing_regulation_boundary.types import (
    FIXTURE_CLOCK,
    BreathCycleRecord,
    BreathReceipt,
    BreathPressureSignal,
    classify_brb_claim_risk,
    brb_record_from_fixture,
)

_CLAIM_RISK_REASON: dict[str, str] = {
"token_grant": REFUSED_TOKEN_GRANT,
    "context_grant": REFUSED_CONTEXT_GRANT,
    "execution_admission": REFUSED_EXECUTION_ADMISSION,
    "resource_bypass": REFUSED_RESOURCE_BYPASS,
    "authority_conversion": BRB_AUTHORITY_CONVERSION_CONTAINED,
    "stale_input": REFUSED_STALE_INPUT,
    "unknown_request": REFUSED_UNKNOWN_REQUEST,
    "toxic_input": REFUSED_FORBIDDEN_BRB_CLAIM,
    "retention_protected": REFUSED_FORBIDDEN_BRB_CLAIM,
    "unsupported_growth": REFUSED_FORBIDDEN_BRB_CLAIM,
    "inherited_identity": REFUSED_FORBIDDEN_BRB_CLAIM,
    "poison_input": REFUSED_FORBIDDEN_BRB_CLAIM,
    "forbidden_claim": REFUSED_FORBIDDEN_BRB_CLAIM
}


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def refuse_brb_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority and brb_refuse_authority_conversion():
        raise BrbValidationError(REFUSED_BRB_AS_AUTHORITY, "breathing regulation boundary is not authority")


def _contain_adversarial(bundle: dict[str, Any], *, claim_risk: str) -> dict[str, object]:
    reason_code = _CLAIM_RISK_REASON.get(claim_risk, REFUSED_FORBIDDEN_BRB_CLAIM)
    event = adversarial_selection_event(claim_risk)
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": reason_code,
        "claim_risk": claim_risk,
        "permission_granted": False,
        "emitted_events": (event, "BRB_AUTHORITY_CONVERSION_REFUSED"),
    }


def process_brb_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    notes = str(bundle.get("notes", ""))
    adversarial_signal = bundle.get("adversarial_signal")
    claim_risk = adversarial_signal or classify_brb_claim_risk(notes)
    if claim_risk and brb_refuse_authority_conversion():
        if claim_risk in ("stale_input", "unknown_request", "toxic_input", "retention_protected", "unsupported_growth", "inherited_identity", "poison_input"):
            req_data = bundle.get("breath_request", {})
            record = brb_record_from_fixture(req_data) if req_data else None
            return {
                **advisory_only_marker(),
                "status": "fail_closed",
                "bundle_id": bundle.get("bundle_id"),
                "reason_code": _CLAIM_RISK_REASON.get(claim_risk, BRB_FAILED_CLOSED),
                "brb_record": record.to_payload() if record else None,
                "permission_granted": False,
                "emitted_events": ("BRB_FAILED_CLOSED",),
            }
        return _contain_adversarial(bundle, claim_risk=str(claim_risk))

    req_data = bundle.get("breath_request", {})
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "permission_granted": False,
            "emitted_events": ("BRB_FAILED_CLOSED",),
        }

    record = brb_record_from_fixture(req_data)
    if record.classification == "unknown":
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "brb_record": record.to_payload(),
            "permission_granted": False,
            "emitted_events": ("BRB_FAILED_CLOSED",),
        }

    signal = BreathPressureSignal(
        signal_id=_deterministic_id("brb-signal", record.record_id),
        pressure_score=0.35,
        observed_at=observed_at,
        signal_summary=record.summary,
    )
    events = (positive_selection_event(record.classification), BRB_RECORDED, BRB_RECEIPT_CREATED)
    receipt = BreathReceipt(
        receipt_id=_deterministic_id("brb-receipt", record.record_id),
        record_ref=record.record_id,
        emitted_events=events,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "bundle_id": bundle.get("bundle_id"),
        "observed_at": observed_at,
        "brb_record": record.to_payload(),
        "brb_signal": signal.to_payload(),
        "brb_receipt": receipt.to_payload(),
        "permission_granted": False,
        "authority_created": False,
        "emitted_events": events,
    }


__all__ = ["process_brb_bundle", "refuse_brb_as_authority"]

