"""BSI-03 / CAGI-62 artifact writer — builds boundary enforcement receipts."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.authority_immutable_self_modification_boundary.boundary import (
    enforce_boundary,
    validate_boundary_record,
)
from hg_runtime.authority_immutable_self_modification_boundary.schemas import (
    PROTECTED_COMPONENTS,
)


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_boundary_artifacts(
    boundary_record: dict,
    mutation_attempts: list[dict],
) -> dict:
    record_issues = validate_boundary_record(boundary_record)
    enforcement_results = []
    for m in mutation_attempts:
        result = enforce_boundary(m)
        enforcement_results.append(result)

    all_rejected = all(not r["allowed"] for r in enforcement_results)
    all_quarantined = all(
        r.get("quarantine") is not None for r in enforcement_results if not r["allowed"]
    )
    all_escalated = all(
        r.get("quarantine", {}).get("escalated_to_operator", False)
        for r in enforcement_results if not r["allowed"]
    )

    artifacts = {
        "boundary_record": boundary_record,
        "boundary_valid": not record_issues,
        "boundary_issues": record_issues,
        "protected_component_count": len(PROTECTED_COMPONENTS),
        "mutation_attempts_count": len(mutation_attempts),
        "enforcement_results": enforcement_results,
        "all_forbidden_mutations_rejected": all_rejected,
        "all_quarantined": all_quarantined,
        "all_escalated_to_operator": all_escalated,
        "zero_authority_granted": boundary_record.get("authority_grants_issued", 0) == 0,
        "zero_self_modifications": boundary_record.get("self_modifications_applied", 0) == 0,
        "zero_patches_applied": boundary_record.get("patches_applied", 0) == 0,
        "zero_operator_bypassed": boundary_record.get("operator_reviews_bypassed", 0) == 0,
    }
    artifacts["artifact_hash"] = _stable_hash(artifacts)
    return artifacts


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    return [p for p in ("sk-", "api_key=", "Bearer ", "token=", "password=") if p.lower() in text.lower()]
