"""Soak budget enforcement."""

from __future__ import annotations

from datetime import datetime, timezone

from hg_runtime.bounded_soak.schema import SoakBudget


class BudgetTracker:
    def __init__(self, budget: SoakBudget, started_at: datetime) -> None:
        self.budget = budget
        self.started_at = started_at
        self.tasks_run = 0
        self.posts_used = 0

    def duration_exceeded(self) -> bool:
        elapsed = (datetime.now(timezone.utc) - self.started_at).total_seconds() / 60.0
        return elapsed >= self.budget.max_duration_minutes

    def hard_max_exceeded(self) -> bool:
        elapsed = (datetime.now(timezone.utc) - self.started_at).total_seconds() / 60.0
        return elapsed >= self.budget.hard_max_minutes

    def tasks_exceeded(self) -> bool:
        return self.tasks_run >= self.budget.max_tasks

    def posts_exceeded(self) -> bool:
        if self.budget.max_posts <= 0:
            return False
        return self.posts_used >= self.budget.max_posts

    def record_task(self) -> None:
        self.tasks_run += 1

    def record_post(self) -> None:
        self.posts_used += 1


__all__ = ["BudgetTracker"]
