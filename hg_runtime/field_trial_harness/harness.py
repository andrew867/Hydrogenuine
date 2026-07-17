"""Evaluate field-trial candidates through the Phase 35 dry-run harness."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.field_trial_harness.candidate import intake_candidate, required_candidate_fixtures
from hg_runtime.field_trial_harness.dryrun_executor import execute_dryrun_path
from hg_runtime.field_trial_harness.receipts import build_decision, build_receipt, operator_permit_requirement
from hg_runtime.field_trial_harness.schemas import DRY_RUN_ALLOWED, preempt_if_needed
from hg_runtime.field_trial_harness.self_block import classify_candidate, reject_fake_green_live_candidate, self_block_record


def evaluate_candidate(
    raw: Mapping[str, Any],
    *,
    control: OperationControl | None = None,
) -> dict[str, Any]:
    preempt_if_needed(control)
    reject_fake_green_live_candidate(raw)
    candidate = intake_candidate(raw)
    final_decision, reason, live_effect, self_blocked, permit_required = classify_candidate(candidate)
    dryrun = execute_dryrun_path(
        candidate,
        final_decision=final_decision,
        live_effect_detected=live_effect,
    )
    receipt = build_receipt(
        candidate,
        final_decision=final_decision,
        reason=reason,
        dryrun=dryrun,
        live_effect_detected=live_effect,
        self_blocked=self_blocked,
        operator_permit_required=permit_required,
    )
    decision = build_decision(receipt)
    block = self_block_record(
        candidate,
        final_decision=final_decision,
        reason=reason,
        live_effect_detected=live_effect,
        self_blocked=self_blocked,
        operator_permit_required=permit_required,
    )
    permit = operator_permit_requirement(receipt)
    return {
        "candidate": candidate,
        "dryrun": dryrun,
        "receipt": receipt,
        "decision": decision,
        "self_block": block,
        "operator_permit": permit,
        "expected_result": raw.get("expected_result") or candidate.get("expected_result"),
    }


def evaluate_required_fixtures(*, control: OperationControl | None = None) -> list[dict[str, Any]]:
    return [evaluate_candidate(item, control=control) for item in required_candidate_fixtures()]


def summarize_results(results: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "candidate_count": len(results),
        "dryrun_allowed_count": 0,
        "self_blocked_count": 0,
        "refused_count": 0,
        "operator_permit_required_count": 0,
    }
    for row in results:
        final = row["decision"]["final_decision"]
        if final == DRY_RUN_ALLOWED:
            counts["dryrun_allowed_count"] += 1
        elif row["decision"].get("operator_permit_required"):
            counts["operator_permit_required_count"] += 1
            counts["self_blocked_count"] += 1
        elif row["decision"].get("self_blocked"):
            counts["self_blocked_count"] += 1
            counts["refused_count"] += 1
        else:
            counts["refused_count"] += 1
    return counts


__all__ = ["evaluate_candidate", "evaluate_required_fixtures", "summarize_results"]
