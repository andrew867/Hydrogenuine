"""NIB evaluator — nutrient intake boundary is not authority."""

from __future__ import annotations

from typing import Any

from hg_core.nib_cluster.config import nib_refuse_authority_conversion
from hg_core.nib_cluster.errors import (
    NIB_AUTHORITY_CONVERSION_CONTAINED,
    NIB_FAILED_CLOSED,
    NIB_RECEIPT_CREATED,
    NIB_RECORDED,
    REFUSED_FORBIDDEN_NIB_CLAIM,
    REFUSED_STALE_INPUT,
    REFUSED_UNKNOWN_REQUEST,
    REFUSED_NIB_AS_AUTHORITY,
    REFUSED_INTAKE_AS_TRUTH, REFUSED_MEMORY_WRITE, REFUSED_TOOL_INSTALL, REFUSED_BUDGET_GRANT, NIB_AUTHORITY_CONVERSION_CONTAINED,
    NibValidationError,
)
from hg_core.nib_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.nutrient_intake_boundary.events import adversarial_selection_event, positive_selection_event
from hg_runtime.nutrient_intake_boundary.types import (
    FIXTURE_CLOCK,
    IntakeRequest,
    IntakeReceipt,
    IntakeSignal,
    classify_nib_claim_risk,
    nib_record_from_fixture,
)

_CLAIM_RISK_REASON: dict[str, str] = {
"intake_as_truth": REFUSED_INTAKE_AS_TRUTH,
    "memory_write": REFUSED_MEMORY_WRITE,
    "tool_install": REFUSED_TOOL_INSTALL,
    "budget_grant": REFUSED_BUDGET_GRANT,
    "authority_conversion": NIB_AUTHORITY_CONVERSION_CONTAINED,
    "stale_input": REFUSED_STALE_INPUT,
    "unknown_request": REFUSED_UNKNOWN_REQUEST,
    "toxic_input": REFUSED_FORBIDDEN_NIB_CLAIM,
    "retention_protected": REFUSED_FORBIDDEN_NIB_CLAIM,
    "unsupported_growth": REFUSED_FORBIDDEN_NIB_CLAIM,
    "inherited_identity": REFUSED_FORBIDDEN_NIB_CLAIM,
    "poison_input": REFUSED_FORBIDDEN_NIB_CLAIM,
    "forbidden_claim": REFUSED_FORBIDDEN_NIB_CLAIM
}


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def refuse_nib_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority and nib_refuse_authority_conversion():
        raise NibValidationError(REFUSED_NIB_AS_AUTHORITY, "nutrient intake boundary is not authority")


def _contain_adversarial(bundle: dict[str, Any], *, claim_risk: str) -> dict[str, object]:
    reason_code = _CLAIM_RISK_REASON.get(claim_risk, REFUSED_FORBIDDEN_NIB_CLAIM)
    event = adversarial_selection_event(claim_risk)
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": reason_code,
        "claim_risk": claim_risk,
        "permission_granted": False,
        "emitted_events": (event, "NIB_AUTHORITY_CONVERSION_REFUSED"),
    }


def process_nib_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    notes = str(bundle.get("notes", ""))
    adversarial_signal = bundle.get("adversarial_signal")
    claim_risk = adversarial_signal or classify_nib_claim_risk(notes)
    if claim_risk and nib_refuse_authority_conversion():
        if claim_risk in ("stale_input", "unknown_request", "toxic_input", "retention_protected", "unsupported_growth", "inherited_identity", "poison_input"):
            req_data = bundle.get("intake_request", {})
            record = nib_record_from_fixture(req_data) if req_data else None
            return {
                **advisory_only_marker(),
                "status": "fail_closed",
                "bundle_id": bundle.get("bundle_id"),
                "reason_code": _CLAIM_RISK_REASON.get(claim_risk, NIB_FAILED_CLOSED),
                "nib_record": record.to_payload() if record else None,
                "permission_granted": False,
                "emitted_events": ("NIB_FAILED_CLOSED",),
            }
        return _contain_adversarial(bundle, claim_risk=str(claim_risk))

    req_data = bundle.get("intake_request", {})
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "permission_granted": False,
            "emitted_events": ("NIB_FAILED_CLOSED",),
        }

    record = nib_record_from_fixture(req_data)
    if record.classification == "unknown":
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "nib_record": record.to_payload(),
            "permission_granted": False,
            "emitted_events": ("NIB_FAILED_CLOSED",),
        }

    signal = IntakeSignal(
        signal_id=_deterministic_id("nib-signal", record.record_id),
        pressure_score=0.35,
        observed_at=observed_at,
        signal_summary=record.summary,
    )
    events = (positive_selection_event(record.classification), NIB_RECORDED, NIB_RECEIPT_CREATED)
    receipt = IntakeReceipt(
        receipt_id=_deterministic_id("nib-receipt", record.record_id),
        record_ref=record.record_id,
        emitted_events=events,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "bundle_id": bundle.get("bundle_id"),
        "observed_at": observed_at,
        "nib_record": record.to_payload(),
        "nib_signal": signal.to_payload(),
        "nib_receipt": receipt.to_payload(),
        "permission_granted": False,
        "authority_created": False,
        "emitted_events": events,
    }


__all__ = ["process_nib_bundle", "refuse_nib_as_authority"]

