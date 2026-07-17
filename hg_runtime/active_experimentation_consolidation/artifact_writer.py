"""AEC-06 / CAGI-53 artifact writer — builds consolidation receipts."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.active_experimentation_consolidation.integrator import (
    compute_tranche_summary,
    validate_integration_checks,
    validate_phase_verdicts,
)
from hg_runtime.active_experimentation_consolidation.schemas import (
    CONSOLIDATION_IS_NOT_COMPLETION,
    INTEGRATION_IS_NOT_DEPLOYMENT,
)


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_consolidation_artifacts(
    verdicts: dict,
    stats: list[dict],
    integration_checks: list[dict],
) -> dict:
    verdict_issues = validate_phase_verdicts(verdicts)
    integration_issues = validate_integration_checks(integration_checks)
    summary = compute_tranche_summary(stats)

    artifacts = {
        "verdicts": verdicts,
        "verdict_issues": verdict_issues,
        "all_phases_green": not verdict_issues,
        "integration_checks": integration_checks,
        "integration_issues": integration_issues,
        "all_integrations_verified": not integration_issues,
        "tranche_summary": summary,
        "boundary_assertions": {
            "consolidation_is_not_completion": CONSOLIDATION_IS_NOT_COMPLETION,
            "integration_is_not_deployment": INTEGRATION_IS_NOT_DEPLOYMENT,
        },
    }
    artifacts["artifact_hash"] = _stable_hash(artifacts)
    return artifacts


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    hits = []
    for pattern in ("sk-", "api_key=", "Bearer ", "token=", "password="):
        if pattern.lower() in text.lower():
            hits.append(pattern)
    return hits
