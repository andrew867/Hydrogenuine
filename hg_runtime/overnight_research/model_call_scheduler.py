"""Model call scheduler with wall-clock budget and call intents.

Orders calls by priority. Skips optional calls when budget is low.
All decisions receipted. No promotion. Operator review required.
Timeout is not failure if honestly receipted.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone


CALL_INTENTS = {
    "source_summary": {"priority": 1, "required": True, "timeout_s": 45},
    "skeptical_review": {"priority": 2, "required": True, "timeout_s": 45},
    "formalism_audit": {"priority": 3, "required": False, "timeout_s": 45},
    "high_risk_boundary": {"priority": 4, "required": False, "timeout_s": 45},
    "backlog_mini_summary": {"priority": 5, "required": True, "timeout_s": 30},
    "backlog_gap_scan": {"priority": 6, "required": False, "timeout_s": 30},
    "public_safe_summary": {"priority": 7, "required": False, "timeout_s": 30},
    "synthesis": {"priority": 8, "required": False, "timeout_s": 30},
}


@dataclass
class PlannedCall:
    call_id: str
    intent: str
    prompt_key: str
    source_index: int
    priority: int
    required: bool
    timeout_s: int
    status: str = "planned"
    elapsed_s: float = 0.0
    output_chars: int = 0
    error: str = ""


@dataclass
class WallClockBudget:
    total_seconds: float = 600.0
    reserve_final_report_seconds: float = 30.0
    per_call_timeout_seconds: float = 45.0
    per_topic_wall_clock_seconds: float = 180.0
    stop_new_calls_when_remaining_below: float = 15.0

    _start_time: float = 0.0
    _topic_start_time: float = 0.0

    def start(self):
        self._start_time = time.monotonic()
        self._topic_start_time = self._start_time

    def start_topic(self):
        self._topic_start_time = time.monotonic()

    def elapsed(self) -> float:
        if self._start_time == 0:
            return 0.0
        return time.monotonic() - self._start_time

    def topic_elapsed(self) -> float:
        if self._topic_start_time == 0:
            return 0.0
        return time.monotonic() - self._topic_start_time

    def remaining(self) -> float:
        return max(0.0, self.total_seconds - self.elapsed())

    def topic_remaining(self) -> float:
        return max(0.0, self.per_topic_wall_clock_seconds - self.topic_elapsed())

    def available_for_call(self) -> float:
        return max(0.0, self.remaining() - self.reserve_final_report_seconds)

    def can_start_call(self, timeout_s: float) -> bool:
        avail = self.available_for_call()
        if avail < self.stop_new_calls_when_remaining_below:
            return False
        if avail < timeout_s:
            return False
        if self.topic_remaining() < timeout_s:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "total_seconds": self.total_seconds,
            "reserve_final_report_seconds": self.reserve_final_report_seconds,
            "per_call_timeout_seconds": self.per_call_timeout_seconds,
            "per_topic_wall_clock_seconds": self.per_topic_wall_clock_seconds,
            "stop_new_calls_when_remaining_below": self.stop_new_calls_when_remaining_below,
            "elapsed": round(self.elapsed(), 2),
            "remaining": round(self.remaining(), 2),
        }


class ModelCallScheduler:
    def __init__(self, *, wall_clock: WallClockBudget | None = None):
        self.wall_clock = wall_clock or WallClockBudget()
        self.plan: list[PlannedCall] = []
        self.receipts: list[dict] = []
        self.calls_succeeded = 0
        self.calls_timed_out = 0
        self.calls_skipped = 0
        self.total_model_seconds = 0.0
        self.consecutive_timeouts: int = 0
        self.timeout_cooldown_threshold: int = 3

    def build_plan(
        self,
        prompt_keys: list[str],
        source_count: int,
        *,
        run_id: str = "",
        is_backlog: bool = False,
    ) -> list[PlannedCall]:
        self.plan = []
        for src_idx in range(source_count):
            for pkey in prompt_keys:
                intent_name = self._intent_for_prompt(pkey, is_backlog=is_backlog)
                intent = CALL_INTENTS.get(intent_name, CALL_INTENTS["source_summary"])
                call = PlannedCall(
                    call_id=f"{run_id}_{pkey}_{src_idx}",
                    intent=intent_name,
                    prompt_key=pkey,
                    source_index=src_idx,
                    priority=intent["priority"],
                    required=intent["required"],
                    timeout_s=min(intent["timeout_s"], int(self.wall_clock.per_call_timeout_seconds)),
                )
                self.plan.append(call)

        self.plan.sort(key=lambda c: (not c.required, c.priority, c.source_index))
        for call in self.plan:
            self.receipts.append(self._receipt("call_planned", call))
        return self.plan

    def should_execute(self, call: PlannedCall) -> tuple[bool, str]:
        if not self.wall_clock.can_start_call(call.timeout_s):
            if call.required:
                return False, "skipped_budget_time"
            return False, "skipped_optional_low_budget"
        if (self.consecutive_timeouts >= self.timeout_cooldown_threshold
                and not call.required):
            return False, "skipped_timeout_cooldown"
        return True, ""

    def record_success(self, call: PlannedCall, elapsed_s: float, output_chars: int):
        call.status = "succeeded"
        call.elapsed_s = elapsed_s
        call.output_chars = output_chars
        self.calls_succeeded += 1
        self.total_model_seconds += elapsed_s
        self.consecutive_timeouts = 0
        self.receipts.append(self._receipt("call_succeeded", call))

    def record_timeout(self, call: PlannedCall, elapsed_s: float):
        call.status = "timed_out"
        call.elapsed_s = elapsed_s
        self.calls_timed_out += 1
        self.total_model_seconds += elapsed_s
        self.consecutive_timeouts += 1
        self.receipts.append(self._receipt("call_timed_out", call))

    def record_error(self, call: PlannedCall, elapsed_s: float, error: str):
        call.status = "error"
        call.elapsed_s = elapsed_s
        call.error = error[:200]
        self.total_model_seconds += elapsed_s
        self.receipts.append(self._receipt("call_error", call))

    def record_skip(self, call: PlannedCall, reason: str):
        call.status = reason
        self.calls_skipped += 1
        self.receipts.append(self._receipt(reason, call))

    def summary(self) -> dict:
        return {
            "total_planned": len(self.plan),
            "calls_succeeded": self.calls_succeeded,
            "calls_timed_out": self.calls_timed_out,
            "calls_skipped": self.calls_skipped,
            "total_model_seconds": round(self.total_model_seconds, 2),
            "wall_clock": self.wall_clock.to_dict(),
            "promotion_allowed": False,
            "operator_review_required": True,
        }

    def _receipt(self, event: str, call: PlannedCall) -> dict:
        return {
            "schema_version": "model_call_receipt_v1",
            "event_type": event,
            "call_id": call.call_id,
            "intent": call.intent,
            "prompt_key": call.prompt_key,
            "source_index": call.source_index,
            "required": call.required,
            "timeout_s": call.timeout_s,
            "elapsed_s": round(call.elapsed_s, 3),
            "output_chars": call.output_chars,
            "status": call.status,
            "error": call.error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "promotion_allowed": False,
            "operator_review_required": True,
        }

    @staticmethod
    def _intent_for_prompt(prompt_key: str, *, is_backlog: bool = False) -> str:
        mapping = {
            "source_summary_v1": "source_summary",
            "tiny_source_summary_v1": "source_summary",
            "skeptical_review_v1": "skeptical_review",
            "tiny_skeptical_scan_v1": "skeptical_review",
            "formalism_audit_v1": "formalism_audit",
            "tiny_formalism_scan_v1": "formalism_audit",
            "high_risk_speculative_boundary_v1": "high_risk_boundary",
            "backlog_mini_packet_v1": "backlog_mini_summary",
            "public_safe_summary_v1": "public_safe_summary",
        }
        return mapping.get(prompt_key, "source_summary")
