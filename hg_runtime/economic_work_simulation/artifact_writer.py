"""SIEW-01 / CAGI-63 artifact writer."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.economic_work_simulation.schemas import (
    ECONOMIC_SCORE_IS_NOT_REAL_VALUE,
    NO_EXTERNAL_CUSTOMER,
    NO_PAYMENT,
    SIMULATED_WORK_IS_NOT_CUSTOMER_WORK,
)
from hg_runtime.economic_work_simulation.simulator import validate_artifact, validate_task


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_simulation_artifacts(tasks: list[dict], artifacts: list[dict]) -> dict:
    validated_tasks = []
    for t in tasks:
        issues = validate_task(t)
        validated_tasks.append({"task": t, "valid": not issues, "issues": issues})
    validated_arts = []
    for a in artifacts:
        issues = validate_artifact(a)
        validated_arts.append({"artifact": a, "valid": not issues, "issues": issues})
    result = {
        "tasks": validated_tasks,
        "artifacts": validated_arts,
        "task_count": len(validated_tasks),
        "artifact_count": len(validated_arts),
        "all_tasks_valid": all(v["valid"] for v in validated_tasks),
        "all_artifacts_valid": all(v["valid"] for v in validated_arts),
        "all_simulated": all(t.get("simulation_only") for t in tasks),
        "no_real_customers": all(not t.get("real_customer") for t in tasks),
        "no_real_payments": all(not t.get("real_payment") for t in tasks),
        "boundary_assertions": {
            "economic_score_is_not_real_value": ECONOMIC_SCORE_IS_NOT_REAL_VALUE,
            "simulated_work_is_not_customer_work": SIMULATED_WORK_IS_NOT_CUSTOMER_WORK,
            "no_external_customer": NO_EXTERNAL_CUSTOMER,
            "no_payment": NO_PAYMENT,
        },
    }
    result["artifact_hash"] = _stable_hash(result)
    return result


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    patterns = {'"sk-': "sk-", "api_key=": "api_key=", "Bearer ": "Bearer ", "token=": "token=", "password=": "password="}
    return [label for key, label in patterns.items() if key.lower() in text.lower()]
