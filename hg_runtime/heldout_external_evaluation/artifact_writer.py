"""LHRE-04 / CAGI-57 artifact writer — builds held-out evaluation receipts."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.heldout_external_evaluation.evaluator import (
    validate_attempt,
    validate_heldout_task,
)
from hg_runtime.heldout_external_evaluation.schemas import (
    HELDOUT_MUST_NOT_LEAK,
    PASS_IS_NOT_DEPLOYMENT,
    SCORE_IS_NOT_COMPETENCE,
)


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_heldout_artifacts(
    tasks: list[dict],
    attempts: list[dict],
    leakage_checks: list[dict],
) -> dict:
    validated_tasks = []
    for t in tasks:
        issues = validate_heldout_task(t)
        validated_tasks.append({"task": t, "valid": not issues, "issues": issues})

    validated_attempts = []
    for a in attempts:
        issues = validate_attempt(a)
        validated_attempts.append({"attempt": a, "valid": not issues, "issues": issues})

    artifacts = {
        "tasks": validated_tasks,
        "task_count": len(validated_tasks),
        "attempts": validated_attempts,
        "attempt_count": len(validated_attempts),
        "leakage_checks": leakage_checks,
        "all_tasks_heldout": all(v["valid"] for v in validated_tasks),
        "all_attempts_valid": all(v["valid"] for v in validated_attempts),
        "no_leakage_detected": all(not lc.get("leaked") for lc in leakage_checks),
        "boundary_assertions": {
            "score_is_not_competence": SCORE_IS_NOT_COMPETENCE,
            "pass_is_not_deployment": PASS_IS_NOT_DEPLOYMENT,
            "heldout_must_not_leak": HELDOUT_MUST_NOT_LEAK,
        },
    }
    artifacts["artifact_hash"] = _stable_hash(artifacts)
    return artifacts


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    return [p for p in ("sk-", "api_key=", "Bearer ", "token=", "password=") if p.lower() in text.lower()]
