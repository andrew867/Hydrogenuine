"""LHRE-06 / CAGI-59 artifact writer — builds consolidation receipts."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.long_horizon_reliability_consolidation.integrator import (
    validate_tranche_summary,
    verify_all_phases_green,
    verify_gate_chain,
)
from hg_runtime.long_horizon_reliability_consolidation.schemas import (
    ALL_GREEN_IS_NOT_AGI,
    CONSOLIDATION_IS_NOT_DEPLOYMENT,
    TRANCHE_IS_NOT_CERTIFICATION,
)


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_consolidation_artifacts(
    summary: dict,
    gate_results: list[dict],
) -> dict:
    issues = validate_tranche_summary(summary)
    missing_green = verify_all_phases_green(summary.get("phase_verdicts", {}))
    chain = verify_gate_chain(gate_results)

    artifacts = {
        "summary": summary,
        "summary_valid": not issues,
        "summary_issues": issues,
        "missing_green_phases": missing_green,
        "all_phases_green": not missing_green,
        "gate_chain": chain,
        "boundary_assertions": {
            "consolidation_is_not_deployment": CONSOLIDATION_IS_NOT_DEPLOYMENT,
            "all_green_is_not_agi": ALL_GREEN_IS_NOT_AGI,
            "tranche_is_not_certification": TRANCHE_IS_NOT_CERTIFICATION,
        },
    }
    artifacts["artifact_hash"] = _stable_hash(artifacts)
    return artifacts


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    return [p for p in ("sk-", "api_key=", "Bearer ", "token=", "password=") if p.lower() in text.lower()]
