"""F12A simulated work capsule replay."""

from __future__ import annotations

from hg_runtime.simulated_work_capsule.artifact_writer import build_capsule_artifacts
from hg_runtime.simulated_work_capsule.fixtures import (
    fixture_capsule_artifact,
    fixture_capsule_review_packet,
    fixture_capsule_state_memory_ref,
    fixture_capsule_task,
    fixture_capsule_work_plan,
    fixture_soak_maintenance_workload,
)


def replay_capsule_artifacts() -> dict:
    task = fixture_capsule_task()
    plan = fixture_capsule_work_plan(task["task_id"])
    artifact = fixture_capsule_artifact(task["task_id"])
    review = fixture_capsule_review_packet(task["task_id"])
    mem_ref = fixture_capsule_state_memory_ref()
    soak = fixture_soak_maintenance_workload()
    return build_capsule_artifacts(
        [task], [plan], [artifact], [review], [mem_ref], soak,
    )
