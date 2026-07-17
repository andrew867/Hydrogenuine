"""EGI packet surface tests — slice 2."""

from __future__ import annotations

from hg_core.egi import (
    create_build_request,
    create_capability_gap,
    create_infrastructure_proposal,
    create_operator_approval_packet,
    detect_repeated_patterns,
)
from hg_runtime.emergent_gap_identifier import (
    render_operator_approval_packet_surface,
    render_packet_surface_fixture,
)
from hg_runtime.emergent_gap_identifier.packet_surface import EGI_PACKET_SURFACE_RECORDED


def _fixture_packet():
    events = [
        {
            "event_id": f"evt_{i}",
            "behavior_label": "manual_csv_export",
            "timestamp": f"2026-06-12T17:0{i}:00.000000Z",
            "source_ref": f"src:{i}",
            "module": "workspace",
        }
        for i in range(3)
    ]
    obs = detect_repeated_patterns(events)[0]
    gap = create_capability_gap(obs)
    proposal = create_infrastructure_proposal(gap)
    build_request = create_build_request(proposal)
    return create_operator_approval_packet(build_request)


def test_packet_surface_plt_exciton_descriptors():
    surface = render_operator_approval_packet_surface(_fixture_packet())
    assert surface["static_surface_only"] is True
    assert surface["packet_is_not_approval"] is True
    assert surface["live_dispatch"] is False
    assert surface["reason_code"] == EGI_PACKET_SURFACE_RECORDED
    descriptors = surface["descriptors"]
    assert len(descriptors) == 2
    kinds = {d["surface_kind"] for d in descriptors}  # type: ignore[index]
    assert kinds == {"plt", "exciton"}
    for descriptor in descriptors:
        assert descriptor["packet_is_not_approval"] is True
        assert descriptor["permission_granted"] is False
        assert descriptor["live_plt_dispatch"] is False
        assert descriptor["live_exciton_dispatch"] is False


def test_packet_surface_fixture_helper():
    surface = render_packet_surface_fixture()
    assert surface["fixture_flow"] is True
    assert surface["descriptor_count"] == 2
    assert surface["permission_granted"] is False
