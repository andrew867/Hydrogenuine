"""EGI replay/hash determinism tests."""

from __future__ import annotations

from hg_core.egi import (
    approve_packet,
    create_build_request,
    create_capability_gap,
    create_infrastructure_proposal,
    create_operator_approval_packet,
    detect_repeated_patterns,
)
from hg_core.egi.hashing import compute_record_hash


def _fixture_events():
    return [
        {
            "event_id": f"evt_{i}",
            "behavior_label": "manual_csv_export",
            "timestamp": f"2026-06-12T17:0{i}:00.000000Z",
            "source_ref": f"src:{i}",
        }
        for i in range(3)
    ]


def test_replay_deterministic_observation_hash():
    a = detect_repeated_patterns(_fixture_events())
    b = detect_repeated_patterns(_fixture_events())
    assert a[0].record_hash == b[0].record_hash


def test_replay_deterministic_full_chain_hash():
    def chain_hash() -> str:
        obs = detect_repeated_patterns(_fixture_events())[0]
        gap = create_capability_gap(obs)
        proposal = create_infrastructure_proposal(gap)
        build_request = create_build_request(proposal)
        packet = create_operator_approval_packet(build_request)
        approved = approve_packet(packet, operator_ref="op:local")
        body = {
            "observation": obs.record_hash,
            "gap": gap.record_hash,
            "proposal": proposal.record_hash,
            "build": build_request.record_hash,
            "approval": approved.record_hash,
        }
        return compute_record_hash(body)

    assert chain_hash() == chain_hash()
