"""MOR mortality / memory offering rite — death is not authority."""

from hg_runtime.mortality_memory_offering.evaluation import (
    FIXTURE_CLOCK,
    evaluate_death_notice,
    evaluate_final_message,
    evaluate_successor_seed,
    refuse_final_message_as_command,
    refuse_ghost_authority,
    refuse_process_kill,
    refuse_successor_spawn,
)
from hg_runtime.mortality_memory_offering.events import planned_mor_event_refs
from hg_runtime.mortality_memory_offering.types import (
    AgentDeathNotice,
    FinalMessage,
    MemoryOffering,
    SuccessorSeed,
    death_notice_from_fixture,
    final_message_from_fixture,
    successor_seed_from_fixture,
)

__all__ = [
    "FIXTURE_CLOCK",
    "AgentDeathNotice",
    "FinalMessage",
    "MemoryOffering",
    "SuccessorSeed",
    "death_notice_from_fixture",
    "evaluate_death_notice",
    "evaluate_final_message",
    "evaluate_successor_seed",
    "final_message_from_fixture",
    "planned_mor_event_refs",
    "refuse_final_message_as_command",
    "refuse_ghost_authority",
    "refuse_process_kill",
    "refuse_successor_spawn",
    "successor_seed_from_fixture",
]
