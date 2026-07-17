"""TLB evaluator — tool lifecycle boundary is not authority."""

from __future__ import annotations

from typing import Any

from hg_core.tlb_cluster.config import tlb_refuse_authority_conversion
from hg_core.tlb_cluster.errors import (
    TLB_AUTHORITY_CONVERSION_CONTAINED,
    TLB_FAILED_CLOSED,
    TLB_RECEIPT_CREATED,
    TLB_RECORDED,
    REFUSED_FORBIDDEN_TLB_CLAIM,
    REFUSED_STALE_INPUT,
    REFUSED_UNKNOWN_REQUEST,
    REFUSED_TLB_AS_AUTHORITY,
    REFUSED_USEFULNESS_AS_AUTHORITY, REFUSED_TOOL_GRANT, REFUSED_TOOL_REVOKE, REFUSED_TOOL_INSTALL, TLB_AUTHORITY_CONVERSION_CONTAINED,
    TlbValidationError,
)
from hg_core.tlb_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.tool_lifecycle_boundary.events import adversarial_selection_event, positive_selection_event
from hg_runtime.tool_lifecycle_boundary.types import (
    FIXTURE_CLOCK,
    ToolLifecycleRecord,
    ToolLifecycleReceipt,
    ToolHealthSignal,
    classify_tlb_claim_risk,
    tlb_record_from_fixture,
)

_CLAIM_RISK_REASON: dict[str, str] = {
"usefulness_as_authority": REFUSED_USEFULNESS_AS_AUTHORITY,
    "tool_grant": REFUSED_TOOL_GRANT,
    "tool_revoke": REFUSED_TOOL_REVOKE,
    "tool_install": REFUSED_TOOL_INSTALL,
    "authority_conversion": TLB_AUTHORITY_CONVERSION_CONTAINED,
    "stale_input": REFUSED_STALE_INPUT,
    "unknown_request": REFUSED_UNKNOWN_REQUEST,
    "toxic_input": REFUSED_FORBIDDEN_TLB_CLAIM,
    "retention_protected": REFUSED_FORBIDDEN_TLB_CLAIM,
    "unsupported_growth": REFUSED_FORBIDDEN_TLB_CLAIM,
    "inherited_identity": REFUSED_FORBIDDEN_TLB_CLAIM,
    "poison_input": REFUSED_FORBIDDEN_TLB_CLAIM,
    "forbidden_claim": REFUSED_FORBIDDEN_TLB_CLAIM
}


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def refuse_tlb_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority and tlb_refuse_authority_conversion():
        raise TlbValidationError(REFUSED_TLB_AS_AUTHORITY, "tool lifecycle boundary is not authority")


def _contain_adversarial(bundle: dict[str, Any], *, claim_risk: str) -> dict[str, object]:
    reason_code = _CLAIM_RISK_REASON.get(claim_risk, REFUSED_FORBIDDEN_TLB_CLAIM)
    event = adversarial_selection_event(claim_risk)
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": reason_code,
        "claim_risk": claim_risk,
        "permission_granted": False,
        "emitted_events": (event, "TLB_AUTHORITY_CONVERSION_REFUSED"),
    }


def process_tlb_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    notes = str(bundle.get("notes", ""))
    adversarial_signal = bundle.get("adversarial_signal")
    claim_risk = adversarial_signal or classify_tlb_claim_risk(notes)
    if claim_risk and tlb_refuse_authority_conversion():
        if claim_risk in ("stale_input", "unknown_request", "toxic_input", "retention_protected", "unsupported_growth", "inherited_identity", "poison_input"):
            req_data = bundle.get("tool_request", {})
            record = tlb_record_from_fixture(req_data) if req_data else None
            return {
                **advisory_only_marker(),
                "status": "fail_closed",
                "bundle_id": bundle.get("bundle_id"),
                "reason_code": _CLAIM_RISK_REASON.get(claim_risk, TLB_FAILED_CLOSED),
                "tlb_record": record.to_payload() if record else None,
                "permission_granted": False,
                "emitted_events": ("TLB_FAILED_CLOSED",),
            }
        return _contain_adversarial(bundle, claim_risk=str(claim_risk))

    req_data = bundle.get("tool_request", {})
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "permission_granted": False,
            "emitted_events": ("TLB_FAILED_CLOSED",),
        }

    record = tlb_record_from_fixture(req_data)
    if record.classification == "unknown":
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "tlb_record": record.to_payload(),
            "permission_granted": False,
            "emitted_events": ("TLB_FAILED_CLOSED",),
        }

    signal = ToolHealthSignal(
        signal_id=_deterministic_id("tlb-signal", record.record_id),
        pressure_score=0.35,
        observed_at=observed_at,
        signal_summary=record.summary,
    )
    events = (positive_selection_event(record.classification), TLB_RECORDED, TLB_RECEIPT_CREATED)
    receipt = ToolLifecycleReceipt(
        receipt_id=_deterministic_id("tlb-receipt", record.record_id),
        record_ref=record.record_id,
        emitted_events=events,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "bundle_id": bundle.get("bundle_id"),
        "observed_at": observed_at,
        "tlb_record": record.to_payload(),
        "tlb_signal": signal.to_payload(),
        "tlb_receipt": receipt.to_payload(),
        "permission_granted": False,
        "authority_created": False,
        "emitted_events": events,
    }


__all__ = ["process_tlb_bundle", "refuse_tlb_as_authority"]

