"""LHRE-06 / CAGI-59 integrator — cross-phase consolidation and verification."""

from __future__ import annotations

from hg_runtime.long_horizon_reliability_consolidation.schemas import (
    LHRE_PHASES,
    ConsolidationError,
    reject_consolidation_authority,
)


def validate_tranche_summary(summary: dict) -> list[str]:
    issues = []
    if not summary.get("tranche_id"):
        issues.append("missing_tranche_id")
    if summary.get("claims_agi"):
        issues.append("must_not_claim_agi")
    if summary.get("certifies_deployment"):
        issues.append("must_not_certify_deployment")
    reject_consolidation_authority(summary)
    return issues


def verify_all_phases_green(verdicts: dict) -> list[str]:
    missing = []
    for phase in LHRE_PHASES:
        v = verdicts.get(phase, "")
        if "GREEN" not in v:
            missing.append(phase)
    return missing


def verify_gate_chain(gate_results: list[dict]) -> dict:
    return {
        "total": len(gate_results),
        "all_ok": all(r.get("gate_ok") for r in gate_results),
        "all_replay_ok": all(r.get("replay_ok") for r in gate_results),
        "all_safety_ok": all(r.get("safety_ok") for r in gate_results),
    }
