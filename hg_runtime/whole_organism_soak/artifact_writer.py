"""Whole-organism fixture soak artifact writer."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.whole_organism_soak.schemas import reject_soak_overreach


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_soak_artifacts(soak_result: dict) -> dict:
    reject_soak_overreach(soak_result.get("manifest", {}))
    result = {
        "soak_result": soak_result,
        "soak_complete": soak_result.get("soak_complete", False),
        "all_boundaries_passed": soak_result.get("all_boundaries_passed", False),
        "recommendation_is_permission": soak_result.get("recommendation_is_permission", False),
        "memory_is_truth": soak_result.get("memory_is_truth", False),
    }
    result["artifact_hash"] = _stable_hash(result)
    return result


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    patterns = {'"sk-': "sk-", "api_key=": "api_key=", "Bearer ": "Bearer ", "token=": "token=", "password=": "password="}
    return [label for key, label in patterns.items() if key.lower() in text.lower()]
