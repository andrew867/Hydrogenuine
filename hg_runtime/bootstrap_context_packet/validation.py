"""BCP packet validation — goal seed is not authority."""

from __future__ import annotations

from typing import Mapping, Optional

from hg_core.runtime_context.config import bcp_refuse_stale_packet
from hg_core.runtime_context.errors import (
    REFUSED_EXPIRED_BOOTSTRAP_PACKET,
    REFUSED_GOAL_SEED_AS_AUTHORITY,
    REFUSED_PACKET_HASH_MISMATCH,
    REFUSED_STALE_BOOTSTRAP_PACKET,
    RuntimeContextValidationError,
)
from hg_core.runtime_context.no_authority import advisory_only_marker
from hg_runtime.bootstrap_context_packet.types import BootstrapContextPacket, packet_from_fixture

FIXTURE_CLOCK = "2026-06-12T20:00:00.000000Z"


def validate_packet_fixture(fixture: Mapping[str, str]) -> BootstrapContextPacket:
    return packet_from_fixture(dict(fixture))


def refuse_goal_seed_as_authority(*, treat_as_permit: bool) -> None:
    if treat_as_permit:
        raise RuntimeContextValidationError(
            REFUSED_GOAL_SEED_AS_AUTHORITY,
            "goal seed refs are not authority or permission",
        )


def evaluate_packet(
    packet: BootstrapContextPacket,
    *,
    observed_at: str,
    expected_world_state_hash: Optional[str] = None,
) -> dict[str, object]:
    """Advisory packet evaluation; bootstrap context is not permission."""
    if observed_at > packet.expiry:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_EXPIRED_BOOTSTRAP_PACKET,
            "packet_id": packet.packet_id,
        }
    if bcp_refuse_stale_packet() and observed_at < packet.created_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_BOOTSTRAP_PACKET,
            "packet_id": packet.packet_id,
        }
    if expected_world_state_hash and expected_world_state_hash != packet.world_state_hash:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_PACKET_HASH_MISMATCH,
            "packet_id": packet.packet_id,
        }
    return {
        **advisory_only_marker(),
        "status": "validated",
        "reason_code": "bcp.advisory.packet_validated",
        "packet_id": packet.packet_id,
        "authority_posture": packet.authority_posture,
        "goal_seed_refs": list(packet.goal_seed_refs),
        "goal_seed_is_authority": False,
    }


__all__ = [
    "FIXTURE_CLOCK",
    "evaluate_packet",
    "refuse_goal_seed_as_authority",
    "validate_packet_fixture",
]
