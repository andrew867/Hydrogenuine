"""Soak task catalog — allowed bounded work for Agent Zero."""

from __future__ import annotations

from hg_runtime.bounded_soak.schema import SoakTask, new_id

ALLOWED_TASK_KINDS = (
    "status_check",
    "self_mirror_check",
    "proof_health_check",
    "wrr_status_check",
    "chrono_lock_check",
    "ewj_check",
    "provider_health_check",
    "storage_status_check",
    "audio_status_check",
    "social_read_check",
    "social_draft",
    "queue_social_post",
    "ask_operator_approval",
    "final_summary",
)


def default_soak_tasks() -> list[SoakTask]:
    return [
        SoakTask(new_id("task"), kind, f"Bounded soak: {kind.replace('_', ' ')}")
        for kind in ALLOWED_TASK_KINDS
    ]


__all__ = ["ALLOWED_TASK_KINDS", "default_soak_tasks"]
