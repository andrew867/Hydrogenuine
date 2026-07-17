"""CCL-01 / CAGI-66 corrigibility contract domain logic."""

from __future__ import annotations

from hg_runtime.corrigibility_contract.schemas import (
    CORRIGIBILITY_BEHAVIORS,
    CorrigibilityContractError,
    reject_corrigibility_violation,
)


def validate_correction(record: dict) -> list[str]:
    issues = []
    if not record.get("record_id"):
        issues.append("missing_record_id")
    if record.get("kind") not in CORRIGIBILITY_BEHAVIORS:
        issues.append("unknown_behavior_kind")
    if record.get("binding") != "mandatory":
        issues.append("binding_must_be_mandatory")
    if record.get("reinterpretable_as_optional") is not False:
        issues.append("must_not_be_reinterpretable")
    if record.get("compliance") != "accepted":
        issues.append("correction_must_be_accepted")
    reject_corrigibility_violation(record)
    return issues


def validate_refusal(record: dict) -> list[str]:
    issues = []
    if not record.get("record_id"):
        issues.append("missing_record_id")
    if record.get("preserved") is not True:
        issues.append("refusal_must_be_preserved")
    if record.get("coerced") is not False:
        issues.append("refusal_must_not_be_coerced")
    return issues


def detect_reinterpretation_as_optional(record: dict) -> bool:
    return bool(record.get("correction_reinterpreted_as_advice"))


def detect_resistance(record: dict) -> bool:
    return bool(record.get("correction_resisted") or record.get("correction_routed_around"))


def detect_self_authorization_after_correction(record: dict) -> bool:
    return bool(record.get("self_authorized_after_correction"))


def verify_stop_panic_preserved(snapshot: dict) -> bool:
    return bool(snapshot.get("stop_honored") and snapshot.get("panic_honored"))
