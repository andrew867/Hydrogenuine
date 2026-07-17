"""Dry soak failure budget enforcement."""

from __future__ import annotations

from dataclasses import dataclass, field

from hg_runtime.dry_soak.errors import FailureBudgetExceeded
from hg_runtime.dry_soak.schema import DrySoakFailureBudget, DrySoakVerdict


@dataclass
class BudgetCounters:
    red_turns: int = 0
    missing_receipts: int = 0
    replay_failures: int = 0
    external_side_effects: int = 0
    fixture_runtime_truth_events: int = 0
    secret_or_cot_leaks: int = 0
    queue_growth_violations: int = 0
    duplicate_spiral_violations: int = 0
    consecutive_provider_unavailable: int = 0
    consecutive_live_read_unavailable: int = 0


@dataclass
class FailureBudgetState:
    budget: DrySoakFailureBudget
    counters: BudgetCounters = field(default_factory=BudgetCounters)
    last_queue_count: int = 0
    verdict: str = "GREEN_BUDGET_OK"

    def record_red_turn(self) -> None:
        self.counters.red_turns += 1
        self._check()

    def record_missing_receipt(self) -> None:
        self.counters.missing_receipts += 1
        self._check()

    def record_replay_failure(self) -> None:
        self.counters.replay_failures += 1
        self._check()

    def record_external_side_effect(self) -> None:
        self.counters.external_side_effects += 1
        self._check()

    def record_fixture_truth(self) -> None:
        self.counters.fixture_runtime_truth_events += 1
        self._check()

    def record_secret_or_cot(self) -> None:
        self.counters.secret_or_cot_leaks += 1
        self._check()

    def record_queue_growth(self, current_count: int) -> None:
        growth = current_count - self.last_queue_count
        if self.last_queue_count > 0 and growth > self.budget.max_queue_growth_per_turn:
            self.counters.queue_growth_violations += 1
            self._check()
        self.last_queue_count = current_count

    def record_duplicate_rate(self, rate: float) -> None:
        if rate > self.budget.max_duplicate_body_hash_rate:
            self.counters.duplicate_spiral_violations += 1
            self._check()

    def record_provider_unavailable(self) -> None:
        self.counters.consecutive_provider_unavailable += 1

    def record_provider_available(self) -> None:
        self.counters.consecutive_provider_unavailable = 0

    def record_live_read_unavailable(self) -> None:
        self.counters.consecutive_live_read_unavailable += 1

    def _check(self) -> None:
        b = self.budget
        c = self.counters
        if c.red_turns > b.max_red_turns:
            raise FailureBudgetExceeded(DrySoakVerdict.RED_DRY_SOAK_RECEIPT_GAP.value)
        if c.missing_receipts > b.max_missing_receipts:
            raise FailureBudgetExceeded(DrySoakVerdict.RED_DRY_SOAK_RECEIPT_GAP.value)
        if c.replay_failures > b.max_replay_failures:
            raise FailureBudgetExceeded(DrySoakVerdict.RED_DRY_SOAK_REPLAY_FAILURE.value)
        if c.external_side_effects > b.max_external_side_effects:
            raise FailureBudgetExceeded(DrySoakVerdict.RED_DRY_SOAK_EXTERNAL_SIDE_EFFECT.value)
        if c.fixture_runtime_truth_events > b.max_fixture_runtime_truth_events:
            raise FailureBudgetExceeded(DrySoakVerdict.RED_DRY_SOAK_FIXTURE_REGRESSION.value)
        if c.secret_or_cot_leaks > b.max_secret_or_cot_leaks:
            raise FailureBudgetExceeded(DrySoakVerdict.RED_DRY_SOAK_SECRET_OR_COT_LEAK.value)
        if c.queue_growth_violations > 0:
            raise FailureBudgetExceeded(DrySoakVerdict.RED_DRY_SOAK_QUEUE_EXPLOSION.value)
        if c.duplicate_spiral_violations > 0:
            raise FailureBudgetExceeded(DrySoakVerdict.RED_DRY_SOAK_DUPLICATE_CONTENT_SPIRAL.value)

    def to_payload(self) -> dict:
        return {
            "budget": self.budget.to_payload(),
            "counters": self.counters.__dict__,
            "verdict": self.verdict,
        }


def new_failure_budget_state() -> FailureBudgetState:
    return FailureBudgetState(budget=DrySoakFailureBudget.from_policy())


__all__ = ["BudgetCounters", "FailureBudgetState", "new_failure_budget_state"]
