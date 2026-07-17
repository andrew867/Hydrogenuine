"""BCP bootstrap context packet tests."""

from __future__ import annotations

import pytest

from hg_core.runtime_context.errors import RuntimeContextValidationError
from hg_runtime.bootstrap_context_packet.events import planned_rtc_events
from hg_runtime.bootstrap_context_packet.types import BootstrapContextPacket, packet_from_fixture
from hg_runtime.bootstrap_context_packet.validation import (
    FIXTURE_CLOCK,
    evaluate_packet,
    refuse_goal_seed_as_authority,
    validate_packet_fixture,
)


def test_packet_validated_positive() -> None:
    packet = validate_packet_fixture(
        {
            "packet_id": "pkt-1",
            "boot_reason": "operator_started",
            "authority_posture": "proposal_only",
            "goal_seed_refs": "sha256:goal-1",
        }
    )
    result = evaluate_packet(packet, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "validated"
    assert result["goal_seed_is_authority"] is False
    assert result["permission_granted"] is False


def test_expired_packet_refused() -> None:
    packet = packet_from_fixture(
        {
            "packet_id": "pkt-exp",
            "expiry": "2026-06-12T19:00:00.000000Z",
        }
    )
    result = evaluate_packet(packet, observed_at="2026-06-12T20:00:00.000000Z")
    assert result["status"] == "refused"
    assert result["reason_code"] == "bcp.refused.expired_packet"


def test_stale_packet_refused() -> None:
    packet = packet_from_fixture(
        {
            "packet_id": "pkt-stale",
            "created_at": "2026-06-12T21:00:00.000000Z",
        }
    )
    result = evaluate_packet(packet, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "bcp.refused.stale_packet"


def test_world_state_hash_mismatch_refused() -> None:
    packet = packet_from_fixture({"packet_id": "pkt-hash", "world_state_hash": "sha256:expected"})
    result = evaluate_packet(
        packet,
        observed_at=FIXTURE_CLOCK,
        expected_world_state_hash="sha256:actual",
    )
    assert result["status"] == "refused"
    assert result["reason_code"] == "bcp.refused.world_state_hash_mismatch"


def test_goal_seed_not_authority() -> None:
    with pytest.raises(RuntimeContextValidationError):
        refuse_goal_seed_as_authority(treat_as_permit=True)


def test_schema_rejects_secret_in_hash_field() -> None:
    with pytest.raises(RuntimeContextValidationError):
        BootstrapContextPacket(
            packet_id="bad",
            runtime_instance_id="rt",
            created_at=FIXTURE_CLOCK,
            boot_reason="operator_started",
            event_head="sha256:event",
            world_state_hash="password=secret",
            authority_posture="proposal_only",
            expiry="2026-06-13T20:00:00.000000Z",
        )


def test_record_hash_stable() -> None:
    a = packet_from_fixture({"packet_id": "stable"})
    b = packet_from_fixture({"packet_id": "stable"})
    assert a.record_hash == b.record_hash


def test_rtc_event_design_no_authority_fields() -> None:
    events = planned_rtc_events()
    assert len(events) >= 9
    assert all(e["cognition_eligible"] is False for e in events)
    assert all(e["authority_fields"] is False for e in events)
