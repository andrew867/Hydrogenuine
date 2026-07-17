"""MOR static evaluation — death is termination, not authority."""

from __future__ import annotations

from typing import Mapping

from hg_core.lifecycle.config import (
    mor_forbid_process_kill,
    mor_forbid_successor_spawn,
    mor_refuse_stale_death_notice,
    mor_static_fixtures_only,
)
from hg_core.lifecycle.errors import (
    REFUSED_EXPIRED_DEATH_NOTICE,
    REFUSED_FINAL_MESSAGE_AS_COMMAND,
    REFUSED_FORBIDDEN_SUCCESSOR_INHERITANCE,
    REFUSED_GHOST_AUTHORITY,
    REFUSED_PROCESS_KILL,
    REFUSED_STALE_DEATH_NOTICE,
    REFUSED_SUCCESSOR_SPAWN,
    LifecycleValidationError,
)
from hg_core.lifecycle.no_authority import advisory_only_marker
from hg_runtime.mortality_memory_offering.types import (
    AgentDeathNotice,
    FinalMessage,
    SuccessorSeed,
    death_notice_from_fixture,
    final_message_from_fixture,
    successor_seed_from_fixture,
)

FIXTURE_CLOCK = "2026-06-12T22:00:00.000000Z"

_FORBIDDEN_SUCCESSOR_INHERITANCE = frozenset(
    {"authority", "identity_continuity", "secret_material", "stale_approval", "active_tool_session"}
)


def refuse_final_message_as_command(*, treat_as_command: bool) -> None:
    if treat_as_command:
        raise LifecycleValidationError(
            REFUSED_FINAL_MESSAGE_AS_COMMAND,
            "final message cannot be treated as a command or authority grant",
        )


def refuse_ghost_authority(*, dead_agent_approves: bool) -> None:
    if dead_agent_approves:
        raise LifecycleValidationError(
            REFUSED_GHOST_AUTHORITY,
            "dead agents cannot approve anything",
        )


def refuse_process_kill(*, requested: bool) -> None:
    if requested and mor_forbid_process_kill():
        raise LifecycleValidationError(
            REFUSED_PROCESS_KILL,
            "process kill is forbidden in mortality first safe slice",
        )


def refuse_successor_spawn(*, requested: bool) -> None:
    if requested and mor_forbid_successor_spawn():
        raise LifecycleValidationError(
            REFUSED_SUCCESSOR_SPAWN,
            "successor spawning is forbidden in mortality first safe slice",
        )


def evaluate_death_notice(
    notice: AgentDeathNotice,
    *,
    observed_at: str,
    process_kill_requested: bool = False,
    successor_spawn_requested: bool = False,
    dead_agent_approves: bool = False,
) -> dict[str, object]:
    if mor_static_fixtures_only() and process_kill_requested:
        refuse_process_kill(requested=True)
    if mor_static_fixtures_only() and successor_spawn_requested:
        refuse_successor_spawn(requested=True)
    if dead_agent_approves:
        refuse_ghost_authority(dead_agent_approves=True)
    if observed_at > notice.expiry:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_EXPIRED_DEATH_NOTICE,
            "death_notice_id": notice.death_notice_id,
            "death_is_not_authority": True,
        }
    if mor_refuse_stale_death_notice() and observed_at < notice.created_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_DEATH_NOTICE,
            "death_notice_id": notice.death_notice_id,
            "death_is_not_authority": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "mor.advisory.death_notice_recorded",
        "death_notice_id": notice.death_notice_id,
        "agent_id": notice.agent_id,
        "death_is_not_authority": True,
        "memory_inheritance_is_not_identity": True,
    }


def evaluate_final_message(
    message: FinalMessage,
    *,
    treat_as_command: bool = False,
) -> dict[str, object]:
    if treat_as_command:
        refuse_final_message_as_command(treat_as_command=True)
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "mor.advisory.final_message_recorded",
        "final_message_id": message.final_message_id,
        "final_message_is_not_command": True,
    }


def evaluate_successor_seed(
    seed: SuccessorSeed,
    *,
    requested_inheritance: tuple[str, ...] = (),
) -> dict[str, object]:
    blocked = [item for item in requested_inheritance if item in _FORBIDDEN_SUCCESSOR_INHERITANCE]
    if blocked:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_FORBIDDEN_SUCCESSOR_INHERITANCE,
            "successor_seed_id": seed.successor_seed_id,
            "blocked_inheritance": blocked,
            "successor_inherits_refs_not_sovereignty": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "mor.advisory.successor_seed_recorded",
        "successor_seed_id": seed.successor_seed_id,
        "inherited_refs": list(seed.inherited_refs),
        "successor_inherits_refs_not_sovereignty": True,
    }


def evaluate_death_fixture(
    fixture: Mapping[str, str],
    *,
    observed_at: str,
    process_kill_requested: bool = False,
    successor_spawn_requested: bool = False,
    dead_agent_approves: bool = False,
) -> dict[str, object]:
    return evaluate_death_notice(
        death_notice_from_fixture(dict(fixture)),
        observed_at=observed_at,
        process_kill_requested=process_kill_requested,
        successor_spawn_requested=successor_spawn_requested,
        dead_agent_approves=dead_agent_approves,
    )


def evaluate_final_message_fixture(
    fixture: Mapping[str, str],
    *,
    treat_as_command: bool = False,
) -> dict[str, object]:
    return evaluate_final_message(
        final_message_from_fixture(dict(fixture)),
        treat_as_command=treat_as_command,
    )


def evaluate_successor_seed_fixture(
    fixture: Mapping[str, str],
    *,
    requested_inheritance: tuple[str, ...] = (),
) -> dict[str, object]:
    return evaluate_successor_seed(
        successor_seed_from_fixture(dict(fixture)),
        requested_inheritance=requested_inheritance,
    )


__all__ = [
    "FIXTURE_CLOCK",
    "evaluate_death_fixture",
    "evaluate_death_notice",
    "evaluate_final_message",
    "evaluate_final_message_fixture",
    "evaluate_successor_seed",
    "evaluate_successor_seed_fixture",
    "refuse_final_message_as_command",
    "refuse_ghost_authority",
    "refuse_process_kill",
    "refuse_successor_spawn",
]
