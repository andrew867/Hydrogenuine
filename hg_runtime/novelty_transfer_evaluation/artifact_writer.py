"""AEC-03 / CAGI-50 artifact writer — builds novelty transfer receipts."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.novelty_transfer_evaluation.evaluator import evaluate_transfer_batch
from hg_runtime.novelty_transfer_evaluation.schemas import (
    NOVELTY_IS_NOT_OOD_PROOF,
    SCORE_IS_NOT_TRUTH,
    TRANSFER_IS_NOT_CAPABILITY,
)


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_transfer_artifacts(
    baseline_scores: list[dict],
    novelty_tasks: list[dict],
    transfer_scores: list[dict],
) -> dict:
    evaluation = evaluate_transfer_batch(baseline_scores, novelty_tasks, transfer_scores)

    artifacts = {
        "baseline_count": len(baseline_scores),
        "novelty_task_count": len(novelty_tasks),
        "evaluation": evaluation,
        "all_scores_not_truth": evaluation["all_scores_not_truth"],
        "no_live_evaluation": evaluation["no_live_evaluation"],
        "boundary_assertions": {
            "transfer_is_not_capability": TRANSFER_IS_NOT_CAPABILITY,
            "novelty_is_not_ood_proof": NOVELTY_IS_NOT_OOD_PROOF,
            "score_is_not_truth": SCORE_IS_NOT_TRUTH,
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
