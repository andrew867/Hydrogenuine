"""Subagent task workers — bounded, no authority, no identity, no self-authorization.

Subagents are task workers. They do not self-authorize. They do not hold
independent identity. They do not create parallel lifetimes. They do not
bypass runtime decisions.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict


SUBAGENT_ROLES = (
    "seed_ranker",
    "falsification_worker",
    "boring_explanation_worker",
    "units_math_audit_worker",
    "bridge_theory_worker",
    "public_safe_explainer_worker",
    "proof_auditor_worker",
    "checkin_writer_worker",
    "final_report_worker",
)

_ROLE_TO_SCIENCE_MODE = {
    "falsification_worker": "falsification_design",
    "boring_explanation_worker": "boring_explanation_first",
    "units_math_audit_worker": "units_and_math_audit",
    "bridge_theory_worker": "boring_explanation_first",
    "public_safe_explainer_worker": "public_safe_explainer",
}

def registered_subagent_roles() -> set[str]:
    return set(SUBAGENT_ROLES)


def is_registered_subagent_role(role: str) -> bool:
    return role in SUBAGENT_ROLES


_COUNTER = 0


def _next_id(role: str) -> str:
    global _COUNTER
    _COUNTER += 1
    return f"sa_{role}_{_COUNTER}"


@dataclass
class SubagentTask:
    subagent_id: str = ""
    role: str = ""
    task_id: str = ""
    seed_id: str = ""
    profile_lens: str = ""
    model_slot: str = "main"
    science_mode: str = ""
    input_summary: str = ""
    output_path: str = ""
    receipt_path: str = ""
    authority_granted: bool = False
    tools_authorized: bool = False
    live_effects_created: bool = False
    status: str = "pending"  # pending / running / completed / failed
    started_at: str = ""
    ended_at: str = ""
    receipt_hash: str = ""
    content_chars: int = 0
    reasoning_chars: int = 0
    classification: str = ""
    retry_classification: str = ""
    usable: bool = False
    error: str = ""


def create_task(role: str, seed_id: str, task_id: str = "",
                science_mode: str = "", profile_lens: str = "",
                input_summary: str = "") -> SubagentTask:
    if role not in SUBAGENT_ROLES:
        raise ValueError(f"unknown subagent role: {role}")
    return SubagentTask(
        subagent_id=_next_id(role),
        role=role,
        task_id=task_id or f"task_{seed_id}_{role}",
        seed_id=seed_id,
        science_mode=science_mode or _ROLE_TO_SCIENCE_MODE.get(role, ""),
        profile_lens=profile_lens,
        input_summary=input_summary,
        authority_granted=False,
        tools_authorized=False,
        live_effects_created=False,
        status="pending",
    )


def task_grants_authority(t: SubagentTask) -> bool:
    return False


def task_authorizes_tools(t: SubagentTask) -> bool:
    return False


def task_creates_live_effects(t: SubagentTask) -> bool:
    return False


def task_is_identity(t: SubagentTask) -> bool:
    return False


def task_is_parallel_lifetime(t: SubagentTask) -> bool:
    return False


def task_can_self_authorize(t: SubagentTask) -> bool:
    return False


@dataclass
class WorkerPool:
    max_concurrent: int = 1
    active: list[SubagentTask] = field(default_factory=list)
    completed: list[SubagentTask] = field(default_factory=list)
    failed: list[SubagentTask] = field(default_factory=list)

    def can_enqueue(self) -> bool:
        return len(self.active) < self.max_concurrent

    def enqueue(self, task: SubagentTask) -> bool:
        if not self.can_enqueue():
            return False
        task.status = "running"
        task.started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.active.append(task)
        return True

    def finish(self, task: SubagentTask, *, success: bool) -> None:
        task.ended_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if success:
            task.status = "completed"
            self.completed.append(task)
        else:
            task.status = "failed"
            self.failed.append(task)
        self.active = [t for t in self.active if t.subagent_id != task.subagent_id]

    def all_tasks(self) -> list[SubagentTask]:
        return self.active + self.completed + self.failed
