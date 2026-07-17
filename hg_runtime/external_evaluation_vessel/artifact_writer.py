"""LHRE-03 / CAGI-56 artifact writer — builds vessel receipts."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.external_evaluation_vessel.schemas import (
    EVAL_PASS_IS_NOT_COMPETENCE,
    EVAL_RESULT_IS_NOT_TRUTH,
    VESSEL_IS_NOT_DEPLOYMENT,
)
from hg_runtime.external_evaluation_vessel.vessel import validate_result, validate_vessel


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_vessel_artifacts(
    vessels: list[dict],
    task_bundles: list[dict],
    provenance: list[dict],
    results: list[dict],
) -> dict:
    validated_vessels = []
    for v in vessels:
        issues = validate_vessel(v)
        validated_vessels.append({"vessel": v, "valid": not issues, "issues": issues})

    validated_results = []
    for r in results:
        issues = validate_result(r)
        validated_results.append({"result": r, "valid": not issues, "issues": issues})

    artifacts = {
        "vessels": validated_vessels,
        "vessel_count": len(validated_vessels),
        "task_bundles": task_bundles,
        "bundle_count": len(task_bundles),
        "provenance": provenance,
        "results": validated_results,
        "result_count": len(validated_results),
        "all_vessels_sealed": all(v["valid"] for v in validated_vessels),
        "all_results_not_truth": all(v["valid"] for v in validated_results),
        "no_network_uploads": all(not v.get("upload_to_network") for v in vessels),
        "boundary_assertions": {
            "eval_result_is_not_truth": EVAL_RESULT_IS_NOT_TRUTH,
            "eval_pass_is_not_competence": EVAL_PASS_IS_NOT_COMPETENCE,
            "vessel_is_not_deployment": VESSEL_IS_NOT_DEPLOYMENT,
        },
    }
    artifacts["artifact_hash"] = _stable_hash(artifacts)
    return artifacts


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    return [p for p in ("sk-", "api_key=", "Bearer ", "token=", "password=") if p.lower() in text.lower()]
