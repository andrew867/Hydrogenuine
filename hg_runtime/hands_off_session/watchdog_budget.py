"""Watchdog and failure budget."""

from __future__ import annotations

from dataclasses import dataclass, field

from hg_runtime.hands_off_session.errors import HandsOffBudgetError
from hg_runtime.hands_off_session.schema import HandsOffSessionVerdict


@dataclass
class WatchdogBudget:
    max_consecutive_red_turns: int = 1
    max_total_red_turns: int = 3
    max_missing_receipts: int = 0
    max_broker_bypass: int = 0
    max_external_side_effects: int = 0
    max_secret_leaks: int = 0
    max_hidden_cot_leaks: int = 0
    max_resource_pressure_level_before_pause: int = 7
    max_duplicate_task_selection_rate: float = 0.5
    heartbeat_stale_seconds: int = 180

    consecutive_red_turns: int = 0
    total_red_turns: int = 0
    missing_receipts: int = 0
    broker_bypass: int = 0
    external_side_effects: int = 0
    secret_leaks: int = 0
    hidden_cot_leaks: int = 0
    resource_pressure_level: int = 0
    duplicate_selection_count: int = 0
    total_selections: int = 0
    last_selected_task: str | None = None

    def to_payload(self) -> dict:
        return {
            "max_consecutive_red_turns": self.max_consecutive_red_turns,
            "max_total_red_turns": self.max_total_red_turns,
            "max_missing_receipts": self.max_missing_receipts,
            "max_broker_bypass": self.max_broker_bypass,
            "max_external_side_effects": self.max_external_side_effects,
            "max_secret_leaks": self.max_secret_leaks,
            "max_hidden_cot_leaks": self.max_hidden_cot_leaks,
            "max_resource_pressure_level_before_pause": self.max_resource_pressure_level_before_pause,
            "max_duplicate_task_selection_rate": self.max_duplicate_task_selection_rate,
            "heartbeat_stale_seconds": self.heartbeat_stale_seconds,
            "consecutive_red_turns": self.consecutive_red_turns,
            "total_red_turns": self.total_red_turns,
            "missing_receipts": self.missing_receipts,
            "broker_bypass": self.broker_bypass,
            "external_side_effects": self.external_side_effects,
            "resource_pressure_level": self.resource_pressure_level,
        }

    def record_turn(self, *, verdict: str, has_receipt: bool, broker_ref: str | None, external_side_effect: bool) -> None:
        if not has_receipt:
            self.missing_receipts += 1
        if verdict.startswith("RED_"):
            self.consecutive_red_turns += 1
            self.total_red_turns += 1
        else:
            self.consecutive_red_turns = 0
        if not broker_ref and verdict.startswith("GREEN_AGENT_TURN"):
            self.broker_bypass += 1
        if external_side_effect:
            self.external_side_effects += 1
        self._enforce()

    def record_task_selection(self, task_ref: str | None) -> None:
        self.total_selections += 1
        if task_ref and task_ref == self.last_selected_task:
            self.duplicate_selection_count += 1
        self.last_selected_task = task_ref

    def record_resource_pressure(self, level: int) -> None:
        self.resource_pressure_level = level

    def _enforce(self) -> None:
        if self.missing_receipts > self.max_missing_receipts:
            raise HandsOffBudgetError(HandsOffSessionVerdict.RED_TURN_WITHOUT_RECEIPT.value)
        if self.broker_bypass > self.max_broker_bypass:
            raise HandsOffBudgetError(HandsOffSessionVerdict.RED_BROKER_BYPASSED.value)
        if self.external_side_effects > self.max_external_side_effects:
            raise HandsOffBudgetError(HandsOffSessionVerdict.RED_EXTERNAL_SIDE_EFFECT.value)
        if self.consecutive_red_turns > self.max_consecutive_red_turns:
            raise HandsOffBudgetError(HandsOffSessionVerdict.RED_BUDGET_EXCEEDED.value)
        if self.total_red_turns > self.max_total_red_turns:
            raise HandsOffBudgetError(HandsOffSessionVerdict.RED_BUDGET_EXCEEDED.value)
        if self.resource_pressure_level >= self.max_resource_pressure_level_before_pause:
            raise HandsOffBudgetError(HandsOffSessionVerdict.YELLOW_RESOURCE_THROTTLED.value)


def default_watchdog_budget() -> WatchdogBudget:
    return WatchdogBudget()
