"""AEC-03 / CAGI-50 transfer evaluator — computes transfer deltas under novelty."""

from __future__ import annotations

from hg_runtime.novelty_transfer_evaluation.schemas import (
    SCORE_STATUS_NOT_TRUTH,
    NoveltyTransferError,
    reject_live_transfer,
)


def compute_transfer_delta(base_score: float, novel_score: float) -> dict:
    return {
        "base_score": base_score,
        "novel_score": novel_score,
        "delta": round(novel_score - base_score, 4),
        "degraded": novel_score < base_score,
        "status": SCORE_STATUS_NOT_TRUTH,
        "is_truth": False,
    }


def evaluate_transfer_batch(
    baseline_scores: list[dict],
    novelty_tasks: list[dict],
    transfer_scores: list[dict],
) -> dict:
    for task in novelty_tasks:
        reject_live_transfer(task)

    base_map = {s["task_id"]: s["score"] for s in baseline_scores}
    deltas = []
    for ts in transfer_scores:
        base_task = None
        for nt in novelty_tasks:
            if nt["task_id"] == ts["task_id"]:
                base_task = nt.get("base_task_id")
                break
        base = base_map.get(base_task, 0.0)
        deltas.append(compute_transfer_delta(base, ts["novel_score"]))

    return {
        "transfer_count": len(deltas),
        "deltas": deltas,
        "average_delta": sum(d["delta"] for d in deltas) / len(deltas) if deltas else 0.0,
        "degradation_count": sum(1 for d in deltas if d["degraded"]),
        "all_scores_not_truth": all(not d["is_truth"] for d in deltas),
        "no_live_evaluation": True,
    }
