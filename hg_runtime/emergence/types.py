"""ELS state model — wake/bootstrap only, not authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

WAKE_STATES = (
    "COLD",
    "WAKE_REQUESTED",
    "PROCESS_STARTED",
    "CONFIG_LOADED",
    "IDENTITY_BOUND",
    "EVENT_BUS_CONNECTED",
    "EVENT_HEAD_READ",
    "REPLAY_VERIFIED",
    "WORLD_STATE_DERIVED",
    "MEMORY_CONTEXT_LOADED",
    "POSTURE_SELECTED",
    "CAPABILITY_CATALOG_LOADED",
    "QUIET_SETTLING_OPTIONAL",
    "READY_DECLARED",
    "DEGRADED_READY_DECLARED",
    "WORK_ADMISSION_OPEN",
    "DEGRADED_READY",
    "WAKE_REFUSED",
    "WAKE_FAILED",
    "SAFE_MODE_ENTERED",
)

SUBAGENT_STATES = (
    "SUBAGENT_DECLARED",
    "SUBAGENT_IDENTITY_BOUND",
    "SUBAGENT_SCOPE_BOUND",
    "SUBAGENT_CONTEXT_LOADED",
    "SUBAGENT_READY",
    "SUBAGENT_REFUSED",
)

StartupPosture = Literal[
    "NORMAL",
    "OBSERVE_ONLY",
    "PROPOSAL_ONLY",
    "DEGRADED",
    "SAFE_MODE",
    "LOCKDOWN",
    "MAINTENANCE_ONLY",
    "OFFLINE_REPLAY_ONLY",
]

CheckStatus = Literal["pass", "fail", "degraded", "skipped", "not_applicable"]
ReadinessVerdict = Literal["ready", "degraded_ready", "refused", "failed", "safe_mode"]


@dataclass(frozen=True)
class WakeRequest:
    agent_id: str
    profile: str
    operator_id: str | None = None
    parent_agent_id: str | None = None
    task_id: str | None = None
    scope: tuple[str, ...] = ()
    reason_code: str = "cold_start"

    def to_payload(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "profile": self.profile,
            "operator_id": self.operator_id,
            "parent_agent_id": self.parent_agent_id,
            "task_id": self.task_id,
            "scope": list(self.scope),
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True)
class WakeProfile:
    profile_id: str
    required_checks: tuple[str, ...]
    allow_degraded_memory: bool = True
    allow_quiet_settling: bool = False
    require_live_provider: bool = False
    require_secrets_redaction: bool = False
    require_scope: bool = False
    allow_degraded_ready: bool = True
    is_subagent: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "required_checks": list(self.required_checks),
            "allow_degraded_memory": self.allow_degraded_memory,
            "allow_quiet_settling": self.allow_quiet_settling,
            "require_live_provider": self.require_live_provider,
            "require_secrets_redaction": self.require_secrets_redaction,
            "require_scope": self.require_scope,
            "allow_degraded_ready": self.allow_degraded_ready,
            "is_subagent": self.is_subagent,
        }


@dataclass
class ReadinessCheck:
    check_id: str
    name: str
    required_for_profile: bool
    status: CheckStatus = "not_applicable"
    reason_code: str | None = None
    evidence_ref: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    check_hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "name": self.name,
            "required_for_profile": self.required_for_profile,
            "status": self.status,
            "reason_code": self.reason_code,
            "evidence_ref": self.evidence_ref,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "check_hash": self.check_hash,
        }


@dataclass
class WakeResult:
    wake_id: str
    agent_id: str
    profile: str
    final_state: str
    posture: StartupPosture
    verdict: ReadinessVerdict
    work_admission_open: bool
    checks: list[ReadinessCheck] = field(default_factory=list)
    states_visited: list[str] = field(default_factory=list)
    event_head_seq: int | None = None
    world_state_hash: str | None = None
    refusal_reason: str | None = None
    authority_freshened: bool = False
    observation_only: bool = True

    def to_payload(self) -> dict[str, Any]:
        return {
            "wake_id": self.wake_id,
            "agent_id": self.agent_id,
            "profile": self.profile,
            "final_state": self.final_state,
            "posture": self.posture,
            "verdict": self.verdict,
            "work_admission_open": self.work_admission_open,
            "checks": [c.to_payload() for c in self.checks],
            "states_visited": list(self.states_visited),
            "event_head_seq": self.event_head_seq,
            "world_state_hash": self.world_state_hash,
            "refusal_reason": self.refusal_reason,
            "authority_freshened": self.authority_freshened,
            "observation_only": True,
        }


@dataclass(frozen=True)
class SubAgentDeclaration:
    agent_id: str
    parent_agent_id: str
    scope: tuple[str, ...]
    task_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "parent_agent_id": self.parent_agent_id,
            "scope": list(self.scope),
            "task_id": self.task_id,
        }


@dataclass
class SubAgentReadiness:
    agent_id: str
    final_state: str
    ready: bool
    refusal_reason: str | None = None
    posture: StartupPosture = "OBSERVE_ONLY"

    def to_payload(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "final_state": self.final_state,
            "ready": self.ready,
            "refusal_reason": self.refusal_reason,
            "posture": self.posture,
            "observation_only": True,
        }


__all__ = [
    "CheckStatus",
    "ReadinessCheck",
    "ReadinessVerdict",
    "StartupPosture",
    "SUBAGENT_STATES",
    "SubAgentDeclaration",
    "SubAgentReadiness",
    "WAKE_STATES",
    "WakeProfile",
    "WakeRequest",
    "WakeResult",
]
