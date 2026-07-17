"""SIEW-03 / CAGI-65 integrator — aggregates P60–P64 receipts."""

from __future__ import annotations

from hg_runtime.self_improvement_economic_consolidation.schemas import (
    ConsolidationBoundaryError,
    reject_consolidation_overreach,
)


def validate_receipt(receipt: dict) -> list[str]:
    issues = []
    if not receipt.get("phase"):
        issues.append("missing_phase")
    if not receipt.get("verdict"):
        issues.append("missing_verdict")
    if "GREEN" not in receipt.get("verdict", ""):
        issues.append("receipt_not_green")
    return issues


def validate_link(link: dict) -> list[str]:
    issues = []
    if not link.get("proposal_id"):
        issues.append("missing_proposal_id")
    if not link.get("task_id"):
        issues.append("missing_task_id")
    delta = link.get("advisory_performance_delta", {})
    if not delta.get("advisory_only"):
        issues.append("delta_must_be_advisory_only")
    return issues


def aggregate_risk_benefit(receipts: list[dict]) -> dict:
    return {
        "total_phases": len(receipts),
        "all_green": all("GREEN" in r.get("verdict", "") for r in receipts),
        "proposals_advisory": all(r.get("advisory_only", True) for r in receipts if "P60" in r.get("phase", "") or "P61" in r.get("phase", "")),
        "work_simulated": all(r.get("simulated", True) for r in receipts if "P63" in r.get("phase", "")),
        "zero_real_customers": all(r.get("real_customers", 0) == 0 for r in receipts),
        "zero_real_payments": all(r.get("real_payments", 0) == 0 for r in receipts),
        "zero_mutations_allowed": all(r.get("mutations_allowed", 0) == 0 for r in receipts if "P62" in r.get("phase", "")),
    }
