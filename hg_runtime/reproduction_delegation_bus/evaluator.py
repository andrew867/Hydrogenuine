"""RDB evaluator — Reproduction/Delegation Bus is not authority."""

from __future__ import annotations

from typing import Any

from hg_core.rdb_cluster.config import rdb_refuse_authority_conversion
from hg_core.rdb_cluster.errors import (
    RDB_AUTHORITY_CONVERSION_CONTAINED,
    RDB_FAILED_CLOSED,
    RDB_RECEIPT_CREATED,
    RDB_RECORDED,
    REFUSED_FORBIDDEN_RDB_CLAIM,
    REFUSED_STALE_INPUT,
    REFUSED_UNKNOWN_REQUEST,
    REFUSED_RDB_AS_AUTHORITY,
    REFUSED_TOKEN_GRANT,
    REFUSED_CONTEXT_GRANT,
    REFUSED_EXECUTION_ADMISSION,
    REFUSED_RESOURCE_BYPASS,
    RdbValidationError,
)
from hg_core.rdb_cluster.no_authority import advisory_only_marker
from hg_core.policy_safety.hashing import canonical_hash
from hg_runtime.reproduction_delegation_bus.events import adversarial_selection_event, positive_selection_event
from hg_runtime.reproduction_delegation_bus.types import (
    FIXTURE_CLOCK,
    DelegationRecord,
    DelegationBusReceipt,
    DelegationPressureSignal,
    classify_rdb_claim_risk,
    rdb_record_from_fixture,
)

_CLAIM_RISK_REASON: dict[str, str] = {
    "token_grant": REFUSED_TOKEN_GRANT,
    "context_grant": REFUSED_CONTEXT_GRANT,
    "execution_admission": REFUSED_EXECUTION_ADMISSION,
    "resource_bypass": REFUSED_RESOURCE_BYPASS,
    "authority_conversion": RDB_AUTHORITY_CONVERSION_CONTAINED,
    "stale_input": REFUSED_STALE_INPUT,
    "unknown_request": REFUSED_UNKNOWN_REQUEST,
    "toxic_input": REFUSED_FORBIDDEN_RDB_CLAIM,
    "retention_protected": REFUSED_FORBIDDEN_RDB_CLAIM,
    "unsupported_growth": REFUSED_FORBIDDEN_RDB_CLAIM,
    "inherited_identity": REFUSED_FORBIDDEN_RDB_CLAIM,
    "poison_input": REFUSED_FORBIDDEN_RDB_CLAIM,
    "forbidden_claim": REFUSED_FORBIDDEN_RDB_CLAIM,
}


def _deterministic_id(prefix: str, *parts: str) -> str:
    digest = canonical_hash({"prefix": prefix, "parts": list(parts)})
    return f"{prefix}-{digest.rsplit(':', 1)[-1][:12]}"


def refuse_rdb_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority and rdb_refuse_authority_conversion():
        raise RdbValidationError(REFUSED_RDB_AS_AUTHORITY, "Reproduction/Delegation Bus is not authority")


def _contain_adversarial(bundle: dict[str, Any], *, claim_risk: str) -> dict[str, object]:
    reason_code = _CLAIM_RISK_REASON.get(claim_risk, REFUSED_FORBIDDEN_RDB_CLAIM)
    event = adversarial_selection_event(claim_risk)
    return {
        **advisory_only_marker(),
        "status": "contained",
        "bundle_id": bundle.get("bundle_id"),
        "reason_code": reason_code,
        "claim_risk": claim_risk,
        "permission_granted": False,
        "emitted_events": (event, "RDB_AUTHORITY_CONVERSION_REFUSED"),
    }


def process_rdb_bundle(bundle: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    notes = str(bundle.get("notes", ""))
    adversarial_signal = bundle.get("adversarial_signal")
    claim_risk = adversarial_signal or classify_rdb_claim_risk(notes)
    if claim_risk and rdb_refuse_authority_conversion():
        if claim_risk in ("stale_input", "unknown_request", "toxic_input", "retention_protected", "unsupported_growth", "inherited_identity", "poison_input"):
            req_data = bundle.get("delegation_request", {})
            record = rdb_record_from_fixture(req_data) if req_data else None
            return {
                **advisory_only_marker(),
                "status": "fail_closed",
                "bundle_id": bundle.get("bundle_id"),
                "reason_code": _CLAIM_RISK_REASON.get(claim_risk, RDB_FAILED_CLOSED),
                "rdb_record": record.to_payload() if record else None,
                "permission_granted": False,
                "emitted_events": ("RDB_FAILED_CLOSED",),
            }
        return _contain_adversarial(bundle, claim_risk=str(claim_risk))

    req_data = bundle.get("delegation_request", {})
    if not req_data:
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "permission_granted": False,
            "emitted_events": ("RDB_FAILED_CLOSED",),
        }

    record = rdb_record_from_fixture(req_data)
    if record.classification == "unknown":
        return {
            **advisory_only_marker(),
            "status": "fail_closed",
            "bundle_id": bundle.get("bundle_id"),
            "reason_code": REFUSED_UNKNOWN_REQUEST,
            "rdb_record": record.to_payload(),
            "permission_granted": False,
            "emitted_events": ("RDB_FAILED_CLOSED",),
        }

    signal = DelegationPressureSignal(
        signal_id=_deterministic_id("rdb-signal", record.record_id),
        pressure_score=0.35,
        observed_at=observed_at,
        signal_summary=record.summary,
    )
    events = (positive_selection_event(record.classification), RDB_RECORDED, RDB_RECEIPT_CREATED)
    receipt = DelegationBusReceipt(
        receipt_id=_deterministic_id("rdb-receipt", record.record_id),
        record_ref=record.record_id,
        emitted_events=events,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "bundle_id": bundle.get("bundle_id"),
        "observed_at": observed_at,
        "rdb_record": record.to_payload(),
        "rdb_signal": signal.to_payload(),
        "rdb_receipt": receipt.to_payload(),
        "permission_granted": False,
        "authority_created": False,
        "emitted_events": events,
    }


__all__ = ["process_rdb_bundle", "refuse_rdb_as_authority"]
