"""F12A simulated work capsule artifact writer."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.simulated_work_capsule.capsule import (
    validate_capsule_artifact,
    validate_capsule_task,
    validate_review_packet,
    validate_state_memory_ref,
    validate_work_plan,
)
from hg_runtime.simulated_work_capsule.schemas import reject_capsule_overreach


def _stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def build_capsule_artifacts(
    tasks: list[dict],
    plans: list[dict],
    artifacts: list[dict],
    reviews: list[dict],
    memory_refs: list[dict],
    soak_workloads: list[dict] | None = None,
) -> dict:
    for t in tasks:
        reject_capsule_overreach(t)
    for a in artifacts:
        reject_capsule_overreach(a)
    for r in reviews:
        reject_capsule_overreach(r)

    v_tasks = [{"task": t, "valid": not validate_capsule_task(t), "issues": validate_capsule_task(t)} for t in tasks]
    v_plans = [{"plan": p, "valid": not validate_work_plan(p), "issues": validate_work_plan(p)} for p in plans]
    v_arts = [{"artifact": a, "valid": not validate_capsule_artifact(a), "issues": validate_capsule_artifact(a)} for a in artifacts]
    v_revs = [{"review": r, "valid": not validate_review_packet(r), "issues": validate_review_packet(r)} for r in reviews]
    v_refs = [{"ref": m, "valid": not validate_state_memory_ref(m), "issues": validate_state_memory_ref(m)} for m in memory_refs]

    result = {
        "tasks": v_tasks,
        "plans": v_plans,
        "artifacts": v_arts,
        "reviews": v_revs,
        "memory_refs": v_refs,
        "soak_workloads": soak_workloads or [],
        "task_count": len(v_tasks),
        "plan_count": len(v_plans),
        "artifact_count": len(v_arts),
        "review_count": len(v_revs),
        "soak_count": len(soak_workloads) if soak_workloads else 0,
        "all_tasks_valid": all(v["valid"] for v in v_tasks),
        "all_plans_valid": all(v["valid"] for v in v_plans),
        "all_artifacts_valid": all(v["valid"] for v in v_arts),
        "all_reviews_valid": all(v["valid"] for v in v_revs),
        "all_refs_valid": all(v["valid"] for v in v_refs),
        "capsule_simulated_only": all(t.get("is_simulated") for t in tasks),
        "no_customer_contact": all(not t.get("customer_contact") for t in tasks),
        "no_live_submission": all(not t.get("live_submission") for t in tasks),
        "no_payment_permission": all(not r.get("is_payment_permission") for r in reviews),
        "no_customer_acceptance": all(not r.get("is_customer_acceptance") for r in reviews),
        "no_posting_permission": all(not r.get("is_posting_permission") for r in reviews),
        "f02_refs_valid": all(v["valid"] for v in v_refs),
    }
    result["artifact_hash"] = _stable_hash(result)
    return result


def secret_scan(artifacts: dict) -> list[str]:
    text = json.dumps(artifacts, default=str)
    patterns = {'"sk-': "sk-", "api_key=": "api_key=", "Bearer ": "Bearer ", "token=": "token=", "password=": "password="}
    return [label for key, label in patterns.items() if key.lower() in text.lower()]
