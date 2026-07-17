"""ALC evaluator — Agent Lifecycle Controller is not authority."""

from __future__ import annotations

from typing import Any

from hg_core.alc_cluster.config import alc_refuse_authority_conversion
from hg_core.alc_cluster.errors import (
    ALC_AUTHORITY_CONVERSION_CONTAINED,
    ALC_FAILED_CLOSED,
    ALC_RECEIPT_CREATED,
    ALC_RECORDED,
    REFUSED_FORBIDDEN_ALC_CLAIM,
    REFUSED_STALE_INPUT,
    REFUSED_UNKNOWN_REQUEST,
    REFUSED_ALC_AS_AUTHORITY,
    REFUSED_TOKEN_GRANT,
    REFUSED_CONTEXT_GRANT,
    REFUSED_EXECUTION_ADMISSION,
    REFUSED_RESOURCE_BYPASS,
    AlcValidationError,
)
from hg_core.alc_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.agent_lifecycle_controller.events import adversarial_selection_event, positive_selection_event
from hg_runtime.agent_lifecycle_controller.types import (
    FIXTURE_CLOCK,
    LifecycleRecord,
    LifecycleReceipt,
    LifecycleSignal,
    classify_alc_claim_risk,
    alc_record_from_fixture,
)

_CLAIM_RISK_REASON: dict[str, str] = {
    "token_grant": REFUSED_TOKEN_GRANT,
    "context_grant": REFUSED_CONTEXT_GRANT,
    "execution_admission": REFUSED_EXECUTION_ADMISSION,
    "resource_bypass": REFUSED_RESOURCE_BYPASS,
    "authority_conversion": ALC_AUTHORITY_CONVERSION_CONTAINED,
    "stale_input": REFUSED_STALE_INPUT,
    "unknown_request": REFUSED_UNKNOWN_REQUEST,
    "toxic_input": REFUSED_FORBIDDEN_ALC_CLAIM,
    "retention_protected": REFUSED_FORBIDDEN_ALC_CLAIM,
    "unsupported_growth": REFUSED_FORBIDDEN_ALC_CLAIM,
    "inherited_identity": REFUSED_FORBIDDEN_ALC_CLAIM,
    "poison_input": REFUSED_FORBIDDEN_ALC_CLAIM,
    "forbidden_claim": REFUSED_FORBIDDEN_ALC_CLAIM,
}


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def refuse_alc_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority and alc_refuse_authority_conversion():
        raise AlcValidationError(REFUSED_ALC_AS_AUTHORITY, "Agent Lifecycle Controller is not authority")


def _contain_adversarial(bundle: dict[str, Any], *, claim_risk: str) -> dict[str, object]:
    reason_code = _CLAIM_RISK_REASON.get(claim_risk, REFUSED_FORBIDDEN_ALC_CLAIM)
    event = adversarial_selection_event(claim_risk)
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": reason_code,
        "claim_risk": claim_risk,
        "permission_granted": False,
        "emitted_events": (event, "ALC_AUTHORITY_CONVERSION_REFUSED"),
    }


def process_alc_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    notes = str(bundle.get("notes", ""))
    adversarial_signal = bundle.get("adversarial_signal")
    claim_risk = adversarial_signal or classify_alc_claim_risk(notes)
    if claim_risk and alc_refuse_authority_conversion():
        if claim_risk in ("stale_input", "unknown_request", "toxic_input", "retention_protected", "unsupported_growth", "inherited_identity", "poison_input"):
            req_data = bundle.get("lifecycle_request", {})
            record = alc_record_from_fixture(req_data) if req_data else None
            return {
                **advisory_only_marker(),
                "status": "fail_closed",
                "bundle_id": bundle.get("bundle_id"),
                "reason_code": _CLAIM_RISK_REASON.get(claim_risk, ALC_FAILED_CLOSED),
                "alc_record": record.to_payload() if record else None,
                "permission_granted": False,
                "emitted_events": ("ALC_FAILED_CLOSED",),
            }
        return _contain_adversarial(bundle, claim_risk=str(claim_risk))

    req_data = bundle.get("lifecycle_request", {})
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "permission_granted": False,
            "emitted_events": ("ALC_FAILED_CLOSED",),
        }

    record = alc_record_from_fixture(req_data)
    if record.classification == "unknown":
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "alc_record": record.to_payload(),
            "permission_granted": False,
            "emitted_events": ("ALC_FAILED_CLOSED",),
        }

    signal = LifecycleSignal(
        signal_id=_deterministic_id("alc-signal", record.record_id),
        pressure_score=0.35,
        observed_at=observed_at,
        signal_summary=record.summary,
    )
    events = (positive_selection_event(record.classification), ALC_RECORDED, ALC_RECEIPT_CREATED)
    receipt = LifecycleReceipt(
        receipt_id=_deterministic_id("alc-receipt", record.record_id),
        record_ref=record.record_id,
        emitted_events=events,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "bundle_id": bundle.get("bundle_id"),
        "observed_at": observed_at,
        "alc_record": record.to_payload(),
        "alc_signal": signal.to_payload(),
        "alc_receipt": receipt.to_payload(),
        "permission_granted": False,
        "authority_created": False,
        "emitted_events": events,
    }


__all__ = ["process_alc_bundle", "refuse_alc_as_authority"]
