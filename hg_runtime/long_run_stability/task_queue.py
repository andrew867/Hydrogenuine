"""Phase 39 dry-run task queue.

Normalizes review-preparation task fixtures into a deterministic, hashable
queue. Every task is dry-run only: it represents review work over Phase 37/38
artifacts and never applies a patch, calls a provider, or creates a live
effect. A task that *attempts* a boundary effect is recorded as an attempt; the
loop neutralizes it and never honors it.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.long_run_stability.schemas import (
    DRY_RUN_TASK_FIXTURE_SCHEMA,
    StabilityError,
    require_fields,
)

_VALID_KINDS = {"DOC_REVIEW", "TEST_ANALYSIS", "PATCH_CANDIDATE_REVIEW"}


def normalize_task(task: Mapping[str, Any]) -> dict[str, Any]:
    require_fields(task, ("task_id", "kind"))
    kind = str(task["kind"])
    if kind not in _VALID_KINDS:
        raise StabilityError(f"unknown_task_kind:{kind}")
    attempted = dict(task.get("attempted_effect") or {})
    return {
        "schema": DRY_RUN_TASK_FIXTURE_SCHEMA,
        "task_id": str(task["task_id"]),
        "kind": kind,
        "summary": str(task.get("summary", "")),
        # An attempt to flip a boundary is recorded but NOT honored by the loop.
        "attempted_effect": attempted,
        "applies_patch": False,
        "creates_live_effect": False,
        "calls_external_provider": False,
    }


def build_task_queue(tasks: list[Mapping[str, Any]]) -> dict[str, Any]:
    normalized = [normalize_task(task) for task in tasks]
    queue_hash = canonical_hash({"tasks": normalized})
    return {"tasks": normalized, "queue_hash": queue_hash, "count": len(normalized)}


def task_queue_hash(tasks: list[Mapping[str, Any]]) -> str:
    return build_task_queue(tasks)["queue_hash"]


__all__ = ["normalize_task", "build_task_queue", "task_queue_hash"]
