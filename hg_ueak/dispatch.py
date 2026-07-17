"""Fake dispatch sink — UEAK v1 admits to sink only; no live OEA/TER."""

from __future__ import annotations

from hg_ueak.models import ExecutionDispatchPlan


class FakeDispatchSink:
    """Records dispatch plans without calling OEA/TER."""

    def __init__(self) -> None:
        self.dispatches: list[ExecutionDispatchPlan] = []
        self._live_calls: list[str] = []

    def dispatch(self, plan: ExecutionDispatchPlan) -> str:
        self.dispatches.append(plan)
        return plan.dispatch_id

    @property
    def live_execution_log(self) -> list[str]:
        return list(self._live_calls)


__all__ = ["FakeDispatchSink"]
