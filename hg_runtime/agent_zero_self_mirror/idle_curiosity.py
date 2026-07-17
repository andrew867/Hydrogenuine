"""Bounded idle self-inspection — disabled by default."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from hg_runtime.agent_zero_self_mirror.agent0_context import answer_self_inspection
from hg_runtime.agent_zero_self_mirror.receipts import new_receipt
from hg_runtime.agent_zero_self_mirror.schema import IdleCuriosityTask
from hg_runtime.agent_zero_self_mirror.trust_boundary import refuse_mutation

DEFAULT_IDLE_QUESTIONS = [
    "Which capabilities are full-stop?",
    "Which docs describe my current WILL?",
    "What was my latest proof bundle?",
    "Which organs are attached?",
]


@dataclass
class IdleCuriosityConfig:
    enabled: bool = False
    max_tasks: int = 3
    max_duration_seconds: int = 30
    allow_network: bool = False


@dataclass
class IdleCuriosityResult:
    started: bool
    stopped_reason: str
    tasks_run: int
    answers: list[dict[str, Any]] = field(default_factory=list)
    receipts: list[dict[str, Any]] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "idle-curiosity-result",
            "started": self.started,
            "stopped_reason": self.stopped_reason,
            "tasks_run": self.tasks_run,
            "answers": self.answers,
            "receipts": self.receipts,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


def run_idle_self_check(
    config: IdleCuriosityConfig | None = None,
    *,
    panic: bool = False,
    questions: list[str] | None = None,
) -> IdleCuriosityResult:
    cfg = config or IdleCuriosityConfig()
    receipts: list[dict[str, Any]] = []
    answers: list[dict[str, Any]] = []

    if not cfg.enabled:
        return IdleCuriosityResult(
            started=False,
            stopped_reason="YELLOW_SELF_MIRROR_IDLE_DISABLED",
            tasks_run=0,
            receipts=[new_receipt("IDLE_SELF_CHECK_STOPPED", detail="disabled").to_payload()],
        )

    receipts.append(new_receipt("IDLE_SELF_CHECK_STARTED").to_payload())
    started = time.monotonic()
    qs = questions or DEFAULT_IDLE_QUESTIONS
    tasks_run = 0

    for q in qs[: cfg.max_tasks]:
        if panic:
            receipts.append(new_receipt("IDLE_SELF_CHECK_STOPPED", detail="panic").to_payload())
            return IdleCuriosityResult(True, "panic", tasks_run, answers, receipts)
        if time.monotonic() - started > cfg.max_duration_seconds:
            receipts.append(new_receipt("IDLE_SELF_CHECK_STOPPED", detail="duration_budget").to_payload())
            return IdleCuriosityResult(True, "RED_IDLE_LOOP_UNBOUNDED" if tasks_run > cfg.max_tasks else "duration_budget", tasks_run, answers, receipts)

        if any(x in q.lower() for x in ("modify", "commit", "delete", "mutate")):
            receipts.append(new_receipt("IDLE_SELF_CHECK_BLOCKED_MUTATION", detail=q).to_payload())
            answers.append(refuse_mutation(q))
            continue

        task = IdleCuriosityTask(task_id=f"idle-{uuid.uuid4().hex[:8]}", question=q, category="idle")
        receipts.append(new_receipt("IDLE_SELF_CHECK_QUESTION_SELECTED", detail=q).to_payload())
        ans, bundle, ans_receipts = answer_self_inspection(q)
        receipts.extend(ans_receipts)
        receipts.append(new_receipt("IDLE_SELF_CHECK_ANSWERED", question_id=ans.question_id).to_payload())
        answers.append({"task": task.to_payload(), "answer": ans.to_payload()})
        tasks_run += 1

    receipts.append(new_receipt("IDLE_SELF_CHECK_STOPPED", detail="complete").to_payload())
    return IdleCuriosityResult(True, "complete", tasks_run, answers, receipts)


__all__ = ["IdleCuriosityConfig", "IdleCuriosityResult", "run_idle_self_check"]
