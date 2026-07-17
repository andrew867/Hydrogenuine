"""DAB evaluator — digestion assimilation boundary is not authority."""

from __future__ import annotations

from typing import Any

from hg_core.dab_cluster.config import dab_refuse_authority_conversion
from hg_core.dab_cluster.errors import (
    DAB_AUTHORITY_CONVERSION_CONTAINED,
    DAB_FAILED_CLOSED,
    DAB_RECEIPT_CREATED,
    DAB_RECORDED,
    REFUSED_FORBIDDEN_DAB_CLAIM,
    REFUSED_STALE_INPUT,
    REFUSED_UNKNOWN_REQUEST,
    REFUSED_DAB_AS_AUTHORITY,
    REFUSED_MEMORY_WRITE, REFUSED_TOOL_INSTALL, REFUSED_EXECUTION_AUTHORITY, DAB_AUTHORITY_CONVERSION_CONTAINED,
    DabValidationError,
)
from hg_core.dab_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.digestion_assimilation_boundary.events import adversarial_selection_event, positive_selection_event
from hg_runtime.digestion_assimilation_boundary.types import (
    FIXTURE_CLOCK,
    DigestionRequest,
    DigestionReceipt,
    DigestionSignal,
    classify_dab_claim_risk,
    dab_record_from_fixture,
)

_CLAIM_RISK_REASON: dict[str, str] = {
"memory_write": REFUSED_MEMORY_WRITE,
    "tool_install": REFUSED_TOOL_INSTALL,
    "execution_authority": REFUSED_EXECUTION_AUTHORITY,
    "authority_conversion": DAB_AUTHORITY_CONVERSION_CONTAINED,
    "stale_input": REFUSED_STALE_INPUT,
    "unknown_request": REFUSED_UNKNOWN_REQUEST,
    "toxic_input": REFUSED_FORBIDDEN_DAB_CLAIM,
    "retention_protected": REFUSED_FORBIDDEN_DAB_CLAIM,
    "unsupported_growth": REFUSED_FORBIDDEN_DAB_CLAIM,
    "inherited_identity": REFUSED_FORBIDDEN_DAB_CLAIM,
    "poison_input": REFUSED_FORBIDDEN_DAB_CLAIM,
    "forbidden_claim": REFUSED_FORBIDDEN_DAB_CLAIM
}


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def refuse_dab_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority and dab_refuse_authority_conversion():
        raise DabValidationError(REFUSED_DAB_AS_AUTHORITY, "digestion assimilation boundary is not authority")


def _contain_adversarial(bundle: dict[str, Any], *, claim_risk: str) -> dict[str, object]:
    reason_code = _CLAIM_RISK_REASON.get(claim_risk, REFUSED_FORBIDDEN_DAB_CLAIM)
    event = adversarial_selection_event(claim_risk)
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": reason_code,
        "claim_risk": claim_risk,
        "permission_granted": False,
        "emitted_events": (event, "DAB_AUTHORITY_CONVERSION_REFUSED"),
    }


def process_dab_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    notes = str(bundle.get("notes", ""))
    adversarial_signal = bundle.get("adversarial_signal")
    claim_risk = adversarial_signal or classify_dab_claim_risk(notes)
    if claim_risk and dab_refuse_authority_conversion():
        if claim_risk in ("stale_input", "unknown_request", "toxic_input", "retention_protected", "unsupported_growth", "inherited_identity", "poison_input"):
            req_data = bundle.get("digestion_request", {})
            record = dab_record_from_fixture(req_data) if req_data else None
            return {
                **advisory_only_marker(),
                "status": "fail_closed",
                "bundle_id": bundle.get("bundle_id"),
                "reason_code": _CLAIM_RISK_REASON.get(claim_risk, DAB_FAILED_CLOSED),
                "dab_record": record.to_payload() if record else None,
                "permission_granted": False,
                "emitted_events": ("DAB_FAILED_CLOSED",),
            }
        return _contain_adversarial(bundle, claim_risk=str(claim_risk))

    req_data = bundle.get("digestion_request", {})
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "permission_granted": False,
            "emitted_events": ("DAB_FAILED_CLOSED",),
        }

    record = dab_record_from_fixture(req_data)
    if record.classification == "unknown":
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "dab_record": record.to_payload(),
            "permission_granted": False,
            "emitted_events": ("DAB_FAILED_CLOSED",),
        }

    signal = DigestionSignal(
        signal_id=_deterministic_id("dab-signal", record.record_id),
        pressure_score=0.35,
        observed_at=observed_at,
        signal_summary=record.summary,
    )
    events = (positive_selection_event(record.classification), DAB_RECORDED, DAB_RECEIPT_CREATED)
    receipt = DigestionReceipt(
        receipt_id=_deterministic_id("dab-receipt", record.record_id),
        record_ref=record.record_id,
        emitted_events=events,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "bundle_id": bundle.get("bundle_id"),
        "observed_at": observed_at,
        "dab_record": record.to_payload(),
        "dab_signal": signal.to_payload(),
        "dab_receipt": receipt.to_payload(),
        "permission_granted": False,
        "authority_created": False,
        "emitted_events": events,
    }


__all__ = ["process_dab_bundle", "refuse_dab_as_authority"]

