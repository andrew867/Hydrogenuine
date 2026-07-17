"""MSC state model — observation only, no authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

MSC_CYCLE_STATES = (
    "IDLE",
    "MEDITATION_REQUESTED",
    "LISTENING",
    "SUMMARIZING",
    "SETTLED",
    "SKIPPED",
    "FAILED",
)

MSC_REFUSAL_REASONS = (
    "REFUSED_PANIC",
    "REFUSED_RECOVERY_ACTIVE",
    "REFUSED_BUSY",
    "REFUSED_NO_CONTEXT",
    "REFUSED_POLICY",
)

MSC_RESULT_STATUSES = MSC_CYCLE_STATES + MSC_REFUSAL_REASONS

SummaryMode = Literal["deterministic", "model_assisted"]


@dataclass(frozen=True)
class SubAgentIdentity:
    """Sub-agent identity — not operator IAM, not authority."""

    agent_id: str
    role: str = "observer"
    allowed_observation_scopes: tuple[str, ...] = ("rtc", "aep", "crr")
    meditation_enabled: bool = True
    max_window_events: int = 50
    can_use_model_summary: bool = False


@dataclass
class MeditationCycleRecord:
    agent_id: str
    cycle_id: str
    started_at: str
    completed_at: str | None = None
    event_window_start: int | None = None
    event_window_end: int | None = None
    observed_event_count: int = 0
    observed_subsystems: list[str] = field(default_factory=list)
    pressure_snapshot: dict[str, Any] = field(default_factory=dict)
    recovery_snapshot: dict[str, Any] = field(default_factory=dict)
    summary_hash: str | None = None
    result_status: str = "IDLE"
    reason_code: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "cycle_id": self.cycle_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "event_window_start": self.event_window_start,
            "event_window_end": self.event_window_end,
            "observed_event_count": self.observed_event_count,
            "observed_subsystems": list(self.observed_subsystems),
            "pressure_snapshot": dict(self.pressure_snapshot),
            "recovery_snapshot": dict(self.recovery_snapshot),
            "summary_hash": self.summary_hash,
            "result_status": self.result_status,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True)
class MeditationSummary:
    summary_id: str
    agent_id: str
    cycle_id: str
    input_event_hashes: tuple[str, ...]
    input_world_state_hash: str
    generated_by: SummaryMode
    summary: dict[str, Any]
    summary_hash: str
    redaction_report_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "summary_id": self.summary_id,
            "agent_id": self.agent_id,
            "cycle_id": self.cycle_id,
            "input_event_hashes": list(self.input_event_hashes),
            "input_world_state_hash": self.input_world_state_hash,
            "generated_by": self.generated_by,
            "summary": self.summary,
            "summary_hash": self.summary_hash,
            "redaction_report_ref": self.redaction_report_ref,
        }


__all__ = [
    "MSC_CYCLE_STATES",
    "MSC_REFUSAL_REASONS",
    "MSC_RESULT_STATUSES",
    "MeditationCycleRecord",
    "MeditationSummary",
    "SubAgentIdentity",
    "SummaryMode",
]
