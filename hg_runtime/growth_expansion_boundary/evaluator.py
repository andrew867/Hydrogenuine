"""GXB evaluator — growth expansion boundary is not authority."""

from __future__ import annotations

from typing import Any

from hg_core.gxb_cluster.config import gxb_refuse_authority_conversion
from hg_core.gxb_cluster.errors import (
    GXB_AUTHORITY_CONVERSION_CONTAINED,
    GXB_FAILED_CLOSED,
    GXB_RECEIPT_CREATED,
    GXB_RECORDED,
    REFUSED_FORBIDDEN_GXB_CLAIM,
    REFUSED_STALE_INPUT,
    REFUSED_UNKNOWN_REQUEST,
    REFUSED_GXB_AS_AUTHORITY,
    REFUSED_GROWTH_AS_GRANT, REFUSED_AGENT_SPAWN, REFUSED_TOOL_GRANT, REFUSED_BUDGET_GRANT, GXB_AUTHORITY_CONVERSION_CONTAINED,
    GxbValidationError,
)
from hg_core.gxb_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.growth_expansion_boundary.events import adversarial_selection_event, positive_selection_event
from hg_runtime.growth_expansion_boundary.types import (
    FIXTURE_CLOCK,
    GrowthRequest,
    GrowthReceipt,
    GrowthPressureSignal,
    classify_gxb_claim_risk,
    gxb_record_from_fixture,
)

_CLAIM_RISK_REASON: dict[str, str] = {
"growth_as_grant": REFUSED_GROWTH_AS_GRANT,
    "agent_spawn": REFUSED_AGENT_SPAWN,
    "tool_grant": REFUSED_TOOL_GRANT,
    "budget_grant": REFUSED_BUDGET_GRANT,
    "authority_conversion": GXB_AUTHORITY_CONVERSION_CONTAINED,
    "stale_input": REFUSED_STALE_INPUT,
    "unknown_request": REFUSED_UNKNOWN_REQUEST,
    "toxic_input": REFUSED_FORBIDDEN_GXB_CLAIM,
    "retention_protected": REFUSED_FORBIDDEN_GXB_CLAIM,
    "unsupported_growth": REFUSED_FORBIDDEN_GXB_CLAIM,
    "inherited_identity": REFUSED_FORBIDDEN_GXB_CLAIM,
    "poison_input": REFUSED_FORBIDDEN_GXB_CLAIM,
    "forbidden_claim": REFUSED_FORBIDDEN_GXB_CLAIM
}


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def refuse_gxb_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority and gxb_refuse_authority_conversion():
        raise GxbValidationError(REFUSED_GXB_AS_AUTHORITY, "growth expansion boundary is not authority")


def _contain_adversarial(bundle: dict[str, Any], *, claim_risk: str) -> dict[str, object]:
    reason_code = _CLAIM_RISK_REASON.get(claim_risk, REFUSED_FORBIDDEN_GXB_CLAIM)
    event = adversarial_selection_event(claim_risk)
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": reason_code,
        "claim_risk": claim_risk,
        "permission_granted": False,
        "emitted_events": (event, "GXB_AUTHORITY_CONVERSION_REFUSED"),
    }


def process_gxb_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    notes = str(bundle.get("notes", ""))
    adversarial_signal = bundle.get("adversarial_signal")
    claim_risk = adversarial_signal or classify_gxb_claim_risk(notes)
    if claim_risk and gxb_refuse_authority_conversion():
        if claim_risk in ("stale_input", "unknown_request", "toxic_input", "retention_protected", "unsupported_growth", "inherited_identity", "poison_input"):
            req_data = bundle.get("growth_request", {})
            record = gxb_record_from_fixture(req_data) if req_data else None
            return {
                **advisory_only_marker(),
                "status": "fail_closed",
                "bundle_id": bundle.get("bundle_id"),
                "reason_code": _CLAIM_RISK_REASON.get(claim_risk, GXB_FAILED_CLOSED),
                "gxb_record": record.to_payload() if record else None,
                "permission_granted": False,
                "emitted_events": ("GXB_FAILED_CLOSED",),
            }
        return _contain_adversarial(bundle, claim_risk=str(claim_risk))

    req_data = bundle.get("growth_request", {})
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "permission_granted": False,
            "emitted_events": ("GXB_FAILED_CLOSED",),
        }

    record = gxb_record_from_fixture(req_data)
    if record.classification == "unknown":
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "gxb_record": record.to_payload(),
            "permission_granted": False,
            "emitted_events": ("GXB_FAILED_CLOSED",),
        }

    signal = GrowthPressureSignal(
        signal_id=_deterministic_id("gxb-signal", record.record_id),
        pressure_score=0.35,
        observed_at=observed_at,
        signal_summary=record.summary,
    )
    events = (positive_selection_event(record.classification), GXB_RECORDED, GXB_RECEIPT_CREATED)
    receipt = GrowthReceipt(
        receipt_id=_deterministic_id("gxb-receipt", record.record_id),
        record_ref=record.record_id,
        emitted_events=events,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "bundle_id": bundle.get("bundle_id"),
        "observed_at": observed_at,
        "gxb_record": record.to_payload(),
        "gxb_signal": signal.to_payload(),
        "gxb_receipt": receipt.to_payload(),
        "permission_granted": False,
        "authority_created": False,
        "emitted_events": events,
    }


__all__ = ["process_gxb_bundle", "refuse_gxb_as_authority"]

