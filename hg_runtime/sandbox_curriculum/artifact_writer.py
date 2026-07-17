"""AEC-02 / CAGI-49 artifact writer — builds curriculum receipts."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.sandbox_curriculum.schemas import (
    CURRICULUM_IS_NOT_INSTRUCTION,
    SCORE_IS_NOT_TRUTH,
    SEQUENCE_IS_NOT_SCHEDULE,
)
from hg_runtime.sandbox_curriculum.sequencer import (
    score_curriculum,
    validate_sequence,
    validate_task,
)


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_curriculum_artifacts(
    tasks: list[dict],
    sequences: list[dict],
    scores: list[dict],
) -> dict:
    task_ids = {t["task_id"] for t in tasks}

    validated_tasks = []
    for task in tasks:
        issues = validate_task(task)
        validated_tasks.append({"task": task, "valid": not issues, "issues": issues})

    validated_seqs = []
    for seq in sequences:
        issues = validate_sequence(seq, task_ids)
        validated_seqs.append({"sequence": seq, "valid": not issues, "issues": issues})

    scoring = score_curriculum(tasks, scores)

    artifacts = {
        "tasks": validated_tasks,
        "task_count": len(validated_tasks),
        "sequences": validated_seqs,
        "sequence_count": len(validated_seqs),
        "scoring": scoring,
        "all_tasks_sandbox": all(v["valid"] for v in validated_tasks),
        "all_sequences_sandbox": all(v["valid"] for v in validated_seqs),
        "all_scores_not_truth": scoring["all_scores_not_truth"],
        "boundary_assertions": {
            "curriculum_is_not_instruction": CURRICULUM_IS_NOT_INSTRUCTION,
            "sequence_is_not_schedule": SEQUENCE_IS_NOT_SCHEDULE,
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
