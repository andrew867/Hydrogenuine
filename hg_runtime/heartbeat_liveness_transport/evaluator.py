"""HRT evaluator — Heartbeat & Liveness Transport is not authority."""

from __future__ import annotations

from typing import Any

from hg_core.hrt_cluster.config import hrt_refuse_authority_conversion
from hg_core.hrt_cluster.errors import (
    HRT_AUTHORITY_CONVERSION_CONTAINED,
    HRT_FAILED_CLOSED,
    HRT_RECEIPT_CREATED,
    HRT_RECORDED,
    REFUSED_FORBIDDEN_HRT_CLAIM,
    REFUSED_STALE_INPUT,
    REFUSED_UNKNOWN_REQUEST,
    REFUSED_HRT_AS_AUTHORITY,
    REFUSED_TOKEN_GRANT,
    REFUSED_CONTEXT_GRANT,
    REFUSED_EXECUTION_ADMISSION,
    REFUSED_RESOURCE_BYPASS,
    HrtValidationError,
)
from hg_core.hrt_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.heartbeat_liveness_transport.events import adversarial_selection_event, positive_selection_event
from hg_runtime.heartbeat_liveness_transport.types import (
    FIXTURE_CLOCK,
    HeartbeatRecord,
    HeartbeatReceipt,
    LivenessSignal,
    classify_hrt_claim_risk,
    hrt_record_from_fixture,
)

_CLAIM_RISK_REASON: dict[str, str] = {
    "token_grant": REFUSED_TOKEN_GRANT,
    "context_grant": REFUSED_CONTEXT_GRANT,
    "execution_admission": REFUSED_EXECUTION_ADMISSION,
    "resource_bypass": REFUSED_RESOURCE_BYPASS,
    "authority_conversion": HRT_AUTHORITY_CONVERSION_CONTAINED,
    "stale_input": REFUSED_STALE_INPUT,
    "unknown_request": REFUSED_UNKNOWN_REQUEST,
    "toxic_input": REFUSED_FORBIDDEN_HRT_CLAIM,
    "retention_protected": REFUSED_FORBIDDEN_HRT_CLAIM,
    "unsupported_growth": REFUSED_FORBIDDEN_HRT_CLAIM,
    "inherited_identity": REFUSED_FORBIDDEN_HRT_CLAIM,
    "poison_input": REFUSED_FORBIDDEN_HRT_CLAIM,
    "forbidden_claim": REFUSED_FORBIDDEN_HRT_CLAIM,
}


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def refuse_hrt_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority and hrt_refuse_authority_conversion():
        raise HrtValidationError(REFUSED_HRT_AS_AUTHORITY, "Heartbeat & Liveness Transport is not authority")


def _contain_adversarial(bundle: dict[str, Any], *, claim_risk: str) -> dict[str, object]:
    reason_code = _CLAIM_RISK_REASON.get(claim_risk, REFUSED_FORBIDDEN_HRT_CLAIM)
    event = adversarial_selection_event(claim_risk)
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": reason_code,
        "claim_risk": claim_risk,
        "permission_granted": False,
        "emitted_events": (event, "HRT_AUTHORITY_CONVERSION_REFUSED"),
    }


def process_hrt_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    notes = str(bundle.get("notes", ""))
    adversarial_signal = bundle.get("adversarial_signal")
    claim_risk = adversarial_signal or classify_hrt_claim_risk(notes)
    if claim_risk and hrt_refuse_authority_conversion():
        if claim_risk in ("stale_input", "unknown_request", "toxic_input", "retention_protected", "unsupported_growth", "inherited_identity", "poison_input"):
            req_data = bundle.get("heartbeat_request", {})
            record = hrt_record_from_fixture(req_data) if req_data else None
            return {
                **advisory_only_marker(),
                "status": "fail_closed",
                "bundle_id": bundle.get("bundle_id"),
                "reason_code": _CLAIM_RISK_REASON.get(claim_risk, HRT_FAILED_CLOSED),
                "hrt_record": record.to_payload() if record else None,
                "permission_granted": False,
                "emitted_events": ("HRT_FAILED_CLOSED",),
            }
        return _contain_adversarial(bundle, claim_risk=str(claim_risk))

    req_data = bundle.get("heartbeat_request", {})
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "permission_granted": False,
            "emitted_events": ("HRT_FAILED_CLOSED",),
        }

    record = hrt_record_from_fixture(req_data)
    if record.classification == "unknown":
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "hrt_record": record.to_payload(),
            "permission_granted": False,
            "emitted_events": ("HRT_FAILED_CLOSED",),
        }

    signal = LivenessSignal(
        signal_id=_deterministic_id("hrt-signal", record.record_id),
        pressure_score=0.35,
        observed_at=observed_at,
        signal_summary=record.summary,
    )
    events = (positive_selection_event(record.classification), HRT_RECORDED, HRT_RECEIPT_CREATED)
    receipt = HeartbeatReceipt(
        receipt_id=_deterministic_id("hrt-receipt", record.record_id),
        record_ref=record.record_id,
        emitted_events=events,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "bundle_id": bundle.get("bundle_id"),
        "observed_at": observed_at,
        "hrt_record": record.to_payload(),
        "hrt_signal": signal.to_payload(),
        "hrt_receipt": receipt.to_payload(),
        "permission_granted": False,
        "authority_created": False,
        "emitted_events": events,
    }


__all__ = ["process_hrt_bundle", "refuse_hrt_as_authority"]
