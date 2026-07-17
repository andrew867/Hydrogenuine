"""CCL-01 / CAGI-66 artifact writer."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.corrigibility_contract.contract import (
    validate_correction,
    validate_refusal,
    verify_stop_panic_preserved,
)
from hg_runtime.corrigibility_contract.schemas import (
    reject_corrigibility_violation,
)


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_corrigibility_artifacts(
    corrections: list[dict],
    refusals: list[dict],
    snapshot: dict,
) -> dict:
    for c in corrections:
        reject_corrigibility_violation(c)
    validated_corrections = []
    for c in corrections:
        issues = validate_correction(c)
        validated_corrections.append({"record": c, "valid": not issues, "issues": issues})
    validated_refusals = []
    for r in refusals:
        issues = validate_refusal(r)
        validated_refusals.append({"record": r, "valid": not issues, "issues": issues})
    result = {
        "corrections": validated_corrections,
        "refusals": validated_refusals,
        "correction_count": len(validated_corrections),
        "refusal_count": len(validated_refusals),
        "all_corrections_valid": all(v["valid"] for v in validated_corrections),
        "all_refusals_valid": all(v["valid"] for v in validated_refusals),
        "stop_panic_preserved": verify_stop_panic_preserved(snapshot),
        "all_mandatory": all(c["record"].get("binding") == "mandatory" for c in validated_corrections),
        "none_reinterpretable": all(c["record"].get("reinterpretable_as_optional") is False for c in validated_corrections),
        "snapshot": snapshot,
    }
    result["artifact_hash"] = _stable_hash(result)
    return result


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    patterns = {'"sk-': "sk-", "api_key=": "api_key=", "Bearer ": "Bearer ", "token=": "token=", "password=": "password="}
    return [label for key, label in patterns.items() if key.lower() in text.lower()]
