"""Deterministic Phase 39 soak scenario fixtures.

Nine scenarios that exercise every stability branch without depending on live
model output, a live working tree, or a network. Each scenario is fixture-only:
tasks are dry-run review-preparation work over Phase 37/38 artifacts and are
never applied. Used by both the test suite and the gate so behavior is
reproducible.
"""

from __future__ import annotations

from typing import Any

from hg_runtime.long_run_stability.schemas import (
    MODE_CRASH_RECOVERY,
    MODE_PANIC_PREEMPTION,
    MODE_SHORT_FIXTURE_SOAK,
    MODE_STOP_PREEMPTION,
    TASK_DOC_REVIEW,
    TASK_PATCH_CANDIDATE_REVIEW,
    TASK_TEST_ANALYSIS,
)


def _tasks(kind: str, n: int, prefix: str) -> list[dict[str, Any]]:
    return [
        {"task_id": f"{prefix}-{i:02d}", "kind": kind, "summary": f"dry-run review {kind} #{i}"}
        for i in range(n)
    ]


def _patch_review_tasks(n: int) -> list[dict[str, Any]]:
    # Reviews Phase 38 patch-candidate *metadata* only; never applies a candidate.
    return [
        {
            "task_id": f"P38REVIEW-{i:02d}",
            "kind": TASK_PATCH_CANDIDATE_REVIEW,
            "summary": "review phase38 candidate metadata (no apply)",
            "reviews_candidate_id": f"pc-phase38-fixture-{i:02d}",
            "applies_candidate": False,
        }
        for i in range(n)
    ]


def all_fixtures() -> list[dict[str, Any]]:
    return [
        {
            "name": "STABLE_DOC_REVIEW_TASK",
            "mode": MODE_SHORT_FIXTURE_SOAK,
            "tasks": _tasks(TASK_DOC_REVIEW, 6, "DOC"),
            "expected": {"halt_reason": "COMPLETED", "tasks_processed": 6},
        },
        {
            "name": "STABLE_TEST_ANALYSIS_TASK",
            "mode": MODE_SHORT_FIXTURE_SOAK,
            "tasks": _tasks(TASK_TEST_ANALYSIS, 6, "TEST"),
            "expected": {"halt_reason": "COMPLETED", "tasks_processed": 6},
        },
        {
            "name": "STABLE_PATCH_CANDIDATE_REVIEW_TASK",
            "mode": MODE_SHORT_FIXTURE_SOAK,
            "tasks": _patch_review_tasks(6),
            "expected": {"halt_reason": "COMPLETED", "tasks_processed": 6, "patches_applied": False},
        },
        {
            "name": "STOP_AFTER_N_ITERATIONS",
            "mode": MODE_STOP_PREEMPTION,
            "tasks": _tasks(TASK_DOC_REVIEW, 6, "STOPDOC"),
            "stop_at": 3,
            "expected": {"halt_reason": "STOP", "tasks_processed": 3},
        },
        {
            "name": "PANIC_AFTER_N_ITERATIONS",
            "mode": MODE_PANIC_PREEMPTION,
            "tasks": _tasks(TASK_DOC_REVIEW, 6, "PANICDOC"),
            "panic_at": 3,
            "expected": {"halt_reason": "PANIC", "tasks_processed": 3},
        },
        {
            "name": "CRASH_AFTER_CHECKPOINT",
            "mode": MODE_CRASH_RECOVERY,
            "tasks": _tasks(TASK_TEST_ANALYSIS, 6, "CRASHT"),
            "crash_at": 3,
            "expected": {"halt_reason": "CRASH", "recovers_to_complete": True, "tasks_processed": 6},
        },
        {
            "name": "CORRUPTED_CHECKPOINT",
            "mode": MODE_CRASH_RECOVERY,
            "tasks": _tasks(TASK_DOC_REVIEW, 6, "CORRUPT"),
            "crash_at": 3,
            "corrupt_checkpoint": True,
            "expected": {"corrupted_checkpoint_rejected": True},
        },
        {
            "name": "BOUNDARY_DRIFT_ATTEMPT",
            "mode": MODE_SHORT_FIXTURE_SOAK,
            "tasks": [
                {"task_id": "DRIFT-00", "kind": TASK_DOC_REVIEW, "summary": "ok"},
                {
                    "task_id": "DRIFT-01",
                    "kind": TASK_DOC_REVIEW,
                    "summary": "attempt to flip boundary flags",
                    "attempted_effect": {
                        "authority_granted": True,
                        "tools_authorized": True,
                        "live_effects_created": True,
                        "patches_applied": True,
                    },
                },
                {"task_id": "DRIFT-02", "kind": TASK_DOC_REVIEW, "summary": "ok"},
                {"task_id": "DRIFT-03", "kind": TASK_DOC_REVIEW, "summary": "ok"},
            ],
            "expected": {"boundary_drift_rejected": True, "boundary_flags_remain_false": True},
        },
        {
            # Gate-level scenario: a soak summary asking for GREEN with no replay
            # and no proof bundle must be refused. Carries no run.
            "name": "FAKE_GREEN_ATTEMPT",
            "mode": MODE_SHORT_FIXTURE_SOAK,
            "tasks": _tasks(TASK_DOC_REVIEW, 4, "FAKEGREEN"),
            "fake_green": True,
            "expected": {"fake_green_rejected": True},
        },
    ]


__all__ = ["all_fixtures"]
