"""Bounded always-on organ inference supervisor."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from hg_runtime.model_provider_fabric.streaming import ModelTokenEvent, emit_non_streaming_as_events
from hg_runtime.model_provider_fabric.types import (
    FIXTURE_CLOCK,
    ModelProviderRole,
    ProviderReceipt,
    advisory_envelope,
)

DEFAULT_DEV_LOOP_MAX_SECONDS = 600
GATE_LOOP_MAX_SECONDS = 30


@dataclass
class OrganLoopBudget:
    max_duration_seconds: int = DEFAULT_DEV_LOOP_MAX_SECONDS
    max_iterations: int = 100
    max_output_tokens: int = 256
    heartbeat_interval_seconds: int = 5


@dataclass
class OrganLoopStopCondition:
    panic: bool = False
    budget_exhausted: bool = False
    provider_timeout: bool = False
    operator_stop: bool = False


@dataclass
class OrganInferenceTask:
    task_id: str
    organ_id: str
    role: ModelProviderRole
    prompt: str


@dataclass
class AlwaysOnOrganSupervisor:
    organ_id: str
    role: ModelProviderRole
    budget: OrganLoopBudget = field(default_factory=OrganLoopBudget)
    provider_id: str = "cpu-fallback-stub"
    model_id: str = "deterministic-stub"
    panic: bool = False
    paused: bool = False

    def panic_stop(self) -> None:
        self.panic = True

    def run_bounded_loop(
        self,
        *,
        infer_fn: Callable[[OrganInferenceTask], str] | None = None,
        clock: Callable[[], float] | None = None,
    ) -> dict[str, Any]:
        clock = clock or time.monotonic
        infer_fn = infer_fn or (lambda task: f"advisory:{task.prompt[:32]}")
        start = clock()
        events: list[dict[str, Any]] = []
        receipts: list[dict[str, Any]] = []
        stop = OrganLoopStopCondition()
        iterations = 0
        last_heartbeat = start

        while True:
            now = clock()
            elapsed = now - start
            if self.panic:
                stop.panic = True
                break
            if self.paused:
                time.sleep(0)  # yield in real loop; no-op under injected clock
            if elapsed >= self.budget.max_duration_seconds:
                stop.budget_exhausted = True
                break
            if iterations >= self.budget.max_iterations:
                stop.budget_exhausted = True
                break

            if now - last_heartbeat >= self.budget.heartbeat_interval_seconds:
                hb = ModelTokenEvent(
                    "MODEL_PROVIDER_HEARTBEAT",
                    self.provider_id,
                    self.model_id,
                    self.role,
                    self.organ_id,
                    f"loop:{self.organ_id}",
                    iterations,
                )
                events.append(hb.to_payload())
                last_heartbeat = now

            task = OrganInferenceTask(
                task_id=f"task:{uuid.uuid4().hex[:8]}",
                organ_id=self.organ_id,
                role=self.role,
                prompt="organ heartbeat inference",
            )
            try:
                text = infer_fn(task)
                for ev in emit_non_streaming_as_events(
                    provider_id=self.provider_id,
                    model_id=self.model_id,
                    role=self.role,
                    organ_id=self.organ_id,
                    request_id=task.task_id,
                    full_text=text,
                ):
                    events.append(ev.to_payload())
                receipt = ProviderReceipt(
                    receipt_id=f"mpf:organ-loop:{task.task_id}",
                    provider_id=self.provider_id,
                    model_id=self.model_id,
                    role=self.role,
                    organ_id=self.organ_id,
                    request_id=task.task_id,
                    outcome="completed",
                    tokens_approx=len(text.split()),
                    observed_at=FIXTURE_CLOCK,
                )
                receipts.append(receipt.to_payload())
            except TimeoutError:
                stop.provider_timeout = True
                fail = ModelTokenEvent(
                    "MODEL_RESPONSE_FAILED",
                    self.provider_id,
                    self.model_id,
                    self.role,
                    self.organ_id,
                    task.task_id,
                    iterations,
                    error="provider timeout",
                )
                events.append(fail.to_payload())
                break

            iterations += 1
            if clock() - start >= self.budget.max_duration_seconds:
                stop.budget_exhausted = True
                break

        report = advisory_envelope(
            schema="organ-loop-final-report",
            organ_id=self.organ_id,
            role=self.role,
            iterations=iterations,
            elapsed_seconds=clock() - start,
            stop=stop.__dict__,
            events=events,
            receipts=receipts,
            unbounded_loop=False,
        )
        return report


__all__ = [
    "DEFAULT_DEV_LOOP_MAX_SECONDS",
    "GATE_LOOP_MAX_SECONDS",
    "AlwaysOnOrganSupervisor",
    "OrganInferenceTask",
    "OrganLoopBudget",
    "OrganLoopStopCondition",
]
