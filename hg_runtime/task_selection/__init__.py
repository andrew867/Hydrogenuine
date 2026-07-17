"""Autonomous task selection for Agent Zero Phase 21."""

from __future__ import annotations

__all__ = [
    "AllowedTaskType",
    "BLOCKED_TASK_TYPES",
    "TaskSelectionContext",
    "TaskSelectionResult",
    "TaskSelectionVerdict",
    "attach_task_selection_to_turn_payload",
    "build_task_selection_monitor_snapshot",
    "create_demo_universe",
    "load_task_selection_policy",
    "perform_idle_reflection",
    "refuse_out_of_scope_candidate",
    "seed_demo_candidates",
    "select_next_task",
]


def __getattr__(name: str):
    if name in {
        "AllowedTaskType",
        "BLOCKED_TASK_TYPES",
        "TaskSelectionVerdict",
        "load_task_selection_policy",
    }:
        from hg_runtime.task_selection import schema as _schema

        return getattr(_schema, name)
    if name in {"create_demo_universe", "load_universe", "list_universes"}:
        from hg_runtime.task_selection import objective_universe as _ou

        return getattr(_ou, name)
    if name in {"create_candidate", "seed_demo_candidates"}:
        from hg_runtime.task_selection import task_candidate as _tc

        return getattr(_tc, name)
    if name in {
        "TaskSelectionContext",
        "TaskSelectionResult",
        "select_next_task",
        "refuse_out_of_scope_candidate",
        "attach_task_selection_to_turn_payload",
    }:
        from hg_runtime.task_selection import task_selector as _ts

        return getattr(_ts, name)
    if name == "perform_idle_reflection":
        from hg_runtime.task_selection import idle_reflection as _ir

        return getattr(_ir, name)
    if name == "build_task_selection_monitor_snapshot":
        from hg_runtime.task_selection import exciton_snapshot as _ex

        return getattr(_ex, name)
    raise AttributeError(name)
