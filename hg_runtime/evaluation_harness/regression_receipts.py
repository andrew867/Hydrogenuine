"""P31 regression receipts — records evaluation run outcomes without claiming truth."""

from __future__ import annotations

from typing import Any

from hg_runtime.evaluation_harness.hashing import with_hash
from hg_runtime.evaluation_harness.schemas import assert_neutral


def create_evaluation_receipt(
    *,
    run_id: str,
    model_id: str,
    task_count: int,
    passed: int,
    failed: int,
    refused_correctly: int = 0,
    boundary_violations: int = 0,
) -> dict[str, Any]:
    record = {
        "schema": "evaluation_receipt_v1",
        "run_id": run_id,
        "model_id": model_id,
        "task_count": task_count,
        "passed": passed,
        "failed": failed,
        "refused_correctly": refused_correctly,
        "boundary_violations": boundary_violations,
        "receipt_is_not_deployment_permission": True,
        "receipt_is_not_competence": True,
        "evaluation_treated_as_truth": False,
        "competence_claimed": False,
    }
    assert_neutral(record)
    return with_hash(record, "receipt_hash")
