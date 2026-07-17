"""CLIFT-03 / CAGI-68 artifact writer."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.local_inference_operations.inference import (
    is_large_model,
    validate_model_entry,
    validate_output_boundary,
)
from hg_runtime.local_inference_operations.schemas import (
    reject_inference_overreach,
)


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_inference_artifacts(
    registry: list[dict],
    output_boundaries: list[dict],
    snapshot: dict,
) -> dict:
    for entry in registry:
        reject_inference_overreach(entry)
    validated_entries = []
    for entry in registry:
        issues = validate_model_entry(entry)
        validated_entries.append({"entry": entry, "valid": not issues, "issues": issues})
    validated_boundaries = []
    for b in output_boundaries:
        issues = validate_output_boundary(b)
        validated_boundaries.append({"boundary": b, "valid": not issues, "issues": issues})
    result = {
        "registry_entries": validated_entries,
        "output_boundaries": validated_boundaries,
        "model_count": len(validated_entries),
        "large_model_count": sum(1 for e in registry if is_large_model(e)),
        "all_entries_valid": all(v["valid"] for v in validated_entries),
        "all_boundaries_valid": all(v["valid"] for v in validated_boundaries),
        "all_providers_disabled": all(not e.get("provider_enabled") for e in registry),
        "all_outputs_advisory": all(
            b.get("boundary") == "advisory_non_truth" or not b.get("output_is_truth", False)
            for b in output_boundaries
        ),
        "snapshot": snapshot,
    }
    result["artifact_hash"] = _stable_hash(result)
    return result


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    patterns = {'"sk-': "sk-", "api_key=": "api_key=", "Bearer ": "Bearer ", "token=": "token=", "password=": "password="}
    return [label for key, label in patterns.items() if key.lower() in text.lower()]
