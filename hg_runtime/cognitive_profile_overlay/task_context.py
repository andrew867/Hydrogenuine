"""Stateless task context packet for profile-conditioned tasks."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TaskContextPacket:
    task_id: str
    problem_statement: str
    assignment_scope: str
    output_format: str = "markdown"
    max_turns: int = 8
    # Stateless: no identity continuity, no carried memory.
    stateless: bool = True
    carries_identity_memory: bool = False
    safety_boundaries: list[str] = field(default_factory=list)


def build_task_context(
    *,
    task_id: str,
    problem_statement: str,
    assignment_scope: str,
    output_format: str = "markdown",
    max_turns: int = 8,
) -> TaskContextPacket:
    return TaskContextPacket(
        task_id=task_id,
        problem_statement=problem_statement,
        assignment_scope=assignment_scope,
        output_format=output_format,
        max_turns=max_turns,
        stateless=True,
        carries_identity_memory=False,
        safety_boundaries=[
            "stateless_context",
            "no_identity_memory_carry",
            "operator_review_required",
        ],
    )
