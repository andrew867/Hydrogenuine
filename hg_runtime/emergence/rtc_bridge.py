"""ELS RTC event drafts — observation only, no authority."""

from __future__ import annotations

from typing import Any

from hg_runtime.contract import draft
from hg_runtime.emergence.types import ReadinessCheck, SubAgentDeclaration, SubAgentReadiness, WakeRequest


def wake_requested(wake_id: str, request: WakeRequest) -> dict[str, Any]:
    return draft("ELS_WAKE_REQUESTED", {"wake_id": wake_id, **request.to_payload(), "observation_only": True})


def process_started(wake_id: str, request: WakeRequest) -> dict[str, Any]:
    return draft("ELS_PROCESS_STARTED", {"wake_id": wake_id, "agent_id": request.agent_id, "observation_only": True})


def config_loaded(wake_id: str, request: WakeRequest) -> dict[str, Any]:
    return draft("ELS_CONFIG_LOADED", {"wake_id": wake_id, "profile": request.profile, "observation_only": True})


def identity_bound(wake_id: str, request: WakeRequest) -> dict[str, Any]:
    return draft(
        "ELS_IDENTITY_BOUND",
        {"wake_id": wake_id, "agent_id": request.agent_id, "operator_id": request.operator_id, "observation_only": True},
    )


def event_bus_connected(wake_id: str, request: WakeRequest) -> dict[str, Any]:
    return draft("ELS_EVENT_BUS_CONNECTED", {"wake_id": wake_id, "agent_id": request.agent_id, "observation_only": True})


def event_head_read(wake_id: str, request: WakeRequest, *, event_head_seq: int | None) -> dict[str, Any]:
    return draft(
        "ELS_EVENT_HEAD_READ",
        {"wake_id": wake_id, "agent_id": request.agent_id, "event_head_seq": event_head_seq, "observation_only": True},
    )


def replay_verified(wake_id: str, request: WakeRequest, *, replay_hash: str | None) -> dict[str, Any]:
    return draft(
        "ELS_REPLAY_VERIFIED",
        {"wake_id": wake_id, "agent_id": request.agent_id, "replay_hash": replay_hash, "observation_only": True},
    )


def replay_failed(wake_id: str, request: WakeRequest, *, reason: str) -> dict[str, Any]:
    return draft(
        "ELS_REPLAY_FAILED",
        {"wake_id": wake_id, "agent_id": request.agent_id, "reason_code": reason, "observation_only": True},
    )


def world_state_derived(wake_id: str, request: WakeRequest, *, state_hash: str) -> dict[str, Any]:
    return draft(
        "ELS_WORLD_STATE_DERIVED",
        {"wake_id": wake_id, "agent_id": request.agent_id, "world_state_hash": state_hash, "observation_only": True},
    )


def memory_context_loaded(wake_id: str, request: WakeRequest, *, status: str) -> dict[str, Any]:
    return draft(
        "ELS_MEMORY_CONTEXT_LOADED",
        {"wake_id": wake_id, "agent_id": request.agent_id, "status": status, "observation_only": True},
    )


def readiness_check_recorded(wake_id: str, check: ReadinessCheck) -> dict[str, Any]:
    return draft(
        "ELS_READINESS_CHECK_RECORDED",
        {"wake_id": wake_id, "check": check.to_payload(), "observation_only": True},
    )


def posture_selected(wake_id: str, request: WakeRequest, *, posture: str) -> dict[str, Any]:
    return draft(
        "ELS_POSTURE_SELECTED",
        {"wake_id": wake_id, "agent_id": request.agent_id, "posture": posture, "observation_only": True},
    )


def capability_catalog_loaded(wake_id: str, request: WakeRequest) -> dict[str, Any]:
    return draft(
        "ELS_CAPABILITY_CATALOG_LOADED",
        {"wake_id": wake_id, "agent_id": request.agent_id, "metadata_only": True, "observation_only": True},
    )


def quiet_settling_started(wake_id: str, request: WakeRequest) -> dict[str, Any]:
    return draft("ELS_QUIET_SETTLING_STARTED", {"wake_id": wake_id, "agent_id": request.agent_id, "observation_only": True})


def quiet_settling_completed(wake_id: str, request: WakeRequest) -> dict[str, Any]:
    return draft("ELS_QUIET_SETTLING_COMPLETED", {"wake_id": wake_id, "agent_id": request.agent_id, "observation_only": True})


def ready_declared(wake_id: str, request: WakeRequest, *, posture: str) -> dict[str, Any]:
    return draft(
        "ELS_READY_DECLARED",
        {"wake_id": wake_id, "agent_id": request.agent_id, "posture": posture, "observation_only": True},
    )


def degraded_ready_declared(wake_id: str, request: WakeRequest, *, posture: str) -> dict[str, Any]:
    return draft(
        "ELS_DEGRADED_READY_DECLARED",
        {"wake_id": wake_id, "agent_id": request.agent_id, "posture": posture, "degraded": True, "observation_only": True},
    )


def work_admission_opened(wake_id: str, request: WakeRequest, *, posture: str) -> dict[str, Any]:
    return draft(
        "ELS_WORK_ADMISSION_OPENED",
        {"wake_id": wake_id, "agent_id": request.agent_id, "posture": posture, "observation_only": True},
    )


def wake_refused(wake_id: str, request: WakeRequest, *, reason: str) -> dict[str, Any]:
    return draft(
        "ELS_WAKE_REFUSED",
        {"wake_id": wake_id, "agent_id": request.agent_id, "reason_code": reason, "observation_only": True},
    )


def wake_failed(wake_id: str, request: WakeRequest, *, reason: str) -> dict[str, Any]:
    return draft(
        "ELS_WAKE_FAILED",
        {"wake_id": wake_id, "agent_id": request.agent_id, "reason_code": reason, "observation_only": True},
    )


def safe_mode_entered(wake_id: str, request: WakeRequest, *, reason: str) -> dict[str, Any]:
    return draft(
        "ELS_SAFE_MODE_ENTERED",
        {"wake_id": wake_id, "agent_id": request.agent_id, "reason_code": reason, "observation_only": True},
    )


def subagent_declared(wake_id: str, decl: SubAgentDeclaration) -> dict[str, Any]:
    return draft("ELS_SUBAGENT_DECLARED", {"wake_id": wake_id, **decl.to_payload(), "observation_only": True})


def subagent_identity_bound(wake_id: str, decl: SubAgentDeclaration) -> dict[str, Any]:
    return draft("ELS_SUBAGENT_IDENTITY_BOUND", {"wake_id": wake_id, **decl.to_payload(), "observation_only": True})


def subagent_scope_bound(wake_id: str, decl: SubAgentDeclaration) -> dict[str, Any]:
    return draft("ELS_SUBAGENT_SCOPE_BOUND", {"wake_id": wake_id, **decl.to_payload(), "observation_only": True})


def subagent_context_loaded(wake_id: str, decl: SubAgentDeclaration) -> dict[str, Any]:
    return draft("ELS_SUBAGENT_CONTEXT_LOADED", {"wake_id": wake_id, **decl.to_payload(), "observation_only": True})


def subagent_ready(wake_id: str, readiness: SubAgentReadiness) -> dict[str, Any]:
    return draft("ELS_SUBAGENT_READY", {"wake_id": wake_id, **readiness.to_payload()})


def subagent_refused(wake_id: str, readiness: SubAgentReadiness) -> dict[str, Any]:
    return draft("ELS_SUBAGENT_REFUSED", {"wake_id": wake_id, **readiness.to_payload()})


__all__ = [
    "capability_catalog_loaded",
    "config_loaded",
    "degraded_ready_declared",
    "event_bus_connected",
    "event_head_read",
    "identity_bound",
    "memory_context_loaded",
    "posture_selected",
    "process_started",
    "quiet_settling_completed",
    "quiet_settling_started",
    "readiness_check_recorded",
    "ready_declared",
    "replay_failed",
    "replay_verified",
    "safe_mode_entered",
    "subagent_context_loaded",
    "subagent_declared",
    "subagent_identity_bound",
    "subagent_ready",
    "subagent_refused",
    "subagent_scope_bound",
    "wake_failed",
    "wake_refused",
    "wake_requested",
    "work_admission_opened",
    "world_state_derived",
]
