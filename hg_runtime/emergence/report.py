"""ELS wake report generation."""

from __future__ import annotations

from typing import Any

from hg_runtime.emergence.types import WakeResult


def build_wake_report(result: WakeResult) -> dict[str, Any]:
    failed = [c.to_payload() for c in result.checks if c.status == "fail"]
    degraded = [c.to_payload() for c in result.checks if c.status == "degraded"]
    return {
        "wake_id": result.wake_id,
        "agent_id": result.agent_id,
        "profile": result.profile,
        "verdict": result.verdict,
        "final_state": result.final_state,
        "posture": result.posture,
        "work_admission_open": result.work_admission_open,
        "states_visited": list(result.states_visited),
        "failed_checks": failed,
        "degraded_checks": degraded,
        "refusal_reason": result.refusal_reason,
        "event_head_seq": result.event_head_seq,
        "world_state_hash": result.world_state_hash,
        "authority_freshened": result.authority_freshened,
        "observation_only": True,
        "ready_honest": result.verdict in ("ready", "degraded_ready") and result.work_admission_open,
    }


__all__ = ["build_wake_report"]
