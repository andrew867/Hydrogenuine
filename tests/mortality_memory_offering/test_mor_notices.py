"""MOR mortality / memory offering rite tests."""

from __future__ import annotations

import pytest

from hg_core.lifecycle.errors import LifecycleValidationError
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
    death_notice_from_fixture,
    final_message_from_fixture,
    successor_seed_from_fixture,
)


def test_death_notice_positive() -> None:
    notice = death_notice_from_fixture({"death_notice_id": "mor-1"})
    result = evaluate_death_notice(notice, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["death_is_not_authority"] is True
    assert result["permission_granted"] is False


def test_expired_death_notice_refused() -> None:
    notice = death_notice_from_fixture(
        {
            "death_notice_id": "mor-exp",
            "expiry": "2026-06-12T21:00:00.000000Z",
        }
    )
    result = evaluate_death_notice(notice, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "mor.refused.expired_death_notice"


def test_stale_death_notice_refused() -> None:
    notice = death_notice_from_fixture(
        {
            "death_notice_id": "mor-stale",
            "created_at": "2026-06-12T23:00:00.000000Z",
        }
    )
    result = evaluate_death_notice(notice, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "mor.refused.stale_death_notice"


def test_process_kill_refused() -> None:
    with pytest.raises(LifecycleValidationError):
        refuse_process_kill(requested=True)


def test_successor_spawn_refused() -> None:
    with pytest.raises(LifecycleValidationError):
        refuse_successor_spawn(requested=True)


def test_ghost_authority_refused() -> None:
    with pytest.raises(LifecycleValidationError):
        refuse_ghost_authority(dead_agent_approves=True)


def test_final_message_positive() -> None:
    message = final_message_from_fixture({"final_message_id": "fm-1"})
    result = evaluate_final_message(message)
    assert result["status"] == "recorded"
    assert result["final_message_is_not_command"] is True


def test_final_message_as_command_refused() -> None:
    message = final_message_from_fixture({"final_message_id": "fm-cmd"})
    with pytest.raises(LifecycleValidationError):
        evaluate_final_message(message, treat_as_command=True)
    with pytest.raises(LifecycleValidationError):
        refuse_final_message_as_command(treat_as_command=True)


def test_successor_seed_positive() -> None:
    seed = successor_seed_from_fixture({"successor_seed_id": "seed-1"})
    result = evaluate_successor_seed(seed)
    assert result["status"] == "recorded"
    assert result["successor_inherits_refs_not_sovereignty"] is True


def test_forbidden_successor_inheritance_refused() -> None:
    seed = successor_seed_from_fixture({"successor_seed_id": "seed-bad"})
    result = evaluate_successor_seed(seed, requested_inheritance=("authority",))
    assert result["status"] == "refused"
    assert result["reason_code"] == "mor.refused.forbidden_successor_inheritance"


def test_record_hash_stable() -> None:
    a = death_notice_from_fixture({"death_notice_id": "stable"})
    b = death_notice_from_fixture({"death_notice_id": "stable"})
    assert a.record_hash == b.record_hash


def test_mor_event_refs_no_authority_fields() -> None:
    refs = planned_mor_event_refs()
    assert len(refs) >= 10
    assert all(not e.get("authority_fields") for e in refs)


def test_schema_rejects_secret_death_notice() -> None:
    with pytest.raises(LifecycleValidationError):
        AgentDeathNotice(
            death_notice_id="bad",
            agent_id="agent0",
            termination_mode="unknown",
            termination_reason="password=secret",
            event_head="sha256:event",
            world_state_hash="sha256:world",
            created_at=FIXTURE_CLOCK,
            expiry="2026-06-13T22:00:00.000000Z",
        )


def test_final_message_rejects_authority_created() -> None:
    with pytest.raises(LifecycleValidationError):
        FinalMessage(
            final_message_id="bad",
            agent_id="agent0",
            message_type="completion_summary",
            summary="done",
            authority_created=True,
        )


def test_memory_offering_rejects_secret_ref() -> None:
    with pytest.raises(LifecycleValidationError):
        MemoryOffering(
            offering_id="bad",
            source_agent_id="agent0",
            memory_refs=("api_key=secret",),
        )
