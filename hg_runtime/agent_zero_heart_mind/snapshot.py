"""A0-HM posture snapshots — orientation record, not authority."""

from __future__ import annotations

from hg_core.policy_safety.hashing import canonical_hash
from hg_core.a0_hm_cluster.no_authority import advisory_only_marker
from hg_runtime.agent_zero_heart_mind.types import FIXTURE_CLOCK, DEFAULT_AGENT_REF, HeartMindPostureSnapshot

_FORBIDDEN = (
    "mint_permit",
    "approve_ueak",
    "call_oea",
    "call_ter",
    "grant_tool",
    "grant_memory",
    "execute",
)


def create_posture_snapshot(
    *,
    agent_ref: str = DEFAULT_AGENT_REF,
    active_signal_refs: tuple[str, ...],
    active_route_refs: tuple[str, ...],
    active_boundary_refs: tuple[str, ...],
    unresolved_signal_refs: tuple[str, ...] = (),
    required_review_refs: tuple[str, ...] = (),
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    snapshot = HeartMindPostureSnapshot(
        snapshot_id=f"a0hm-snap-{canonical_hash({'signals': list(active_signal_refs)}).rsplit(':', 1)[-1][:12]}",
        agent_ref=agent_ref,
        active_signal_refs=active_signal_refs,
        active_posture_refs=("loving_awareness",),
        active_route_refs=active_route_refs,
        active_boundary_refs=active_boundary_refs,
        unresolved_signal_refs=unresolved_signal_refs,
        required_review_refs=required_review_refs,
        forbidden_effects=_FORBIDDEN,
        created_at=observed_at,
    )
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "posture_snapshot": snapshot.to_payload(),
        "permission_granted": False,
        "emitted_events": ("A0_HM_POSTURE_SNAPSHOT_CREATED",),
    }


__all__ = ["create_posture_snapshot"]
