"""EGI operator approval packet surface — slice 2, PLT/EXCITON-compatible static descriptor."""

from __future__ import annotations

from typing import Any

from hg_core.egi.detector import FIXTURE_CLOCK
from hg_core.egi.schemas import OperatorApprovalPacket

EGI_PACKET_SURFACE_RECORDED = "egi.advisory.approval_packet_surface_recorded"


def _surface_descriptor(packet: OperatorApprovalPacket, *, surface_kind: str) -> dict[str, Any]:
    return {
        "surface_kind": surface_kind,
        "descriptor_schema": "egi-operator-approval-surface-v1",
        "approval_packet_ref": packet.approval_packet_id,
        "build_request_ref": packet.build_request_ref,
        "operator_visible_summary": packet.summary,
        "risk_summary": packet.risk_summary,
        "files_expected_to_change": list(packet.files_expected_to_change),
        "tests_expected_to_run": list(packet.tests_expected_to_run),
        "proof_gate_expected": packet.proof_gate_expected,
        "rollback_plan": packet.rollback_plan,
        "expiration": packet.expiration,
        "operator_decision": packet.operator_decision,
        "packet_is_not_approval": True,
        "live_plt_dispatch": False,
        "live_exciton_dispatch": False,
        "permission_granted": False,
        "authority_created": False,
        "record_hash": packet.record_hash,
    }


def render_operator_approval_packet_surface(
    packet: OperatorApprovalPacket,
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Render OperatorApprovalPacket as PLT/EXCITON-compatible static descriptors."""
    descriptors = [
        _surface_descriptor(packet, surface_kind="exciton"),
        _surface_descriptor(packet, surface_kind="plt"),
    ]
    return {
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
        "proposal_is_advisory_only": True,
        "status": "recorded",
        "reason_code": EGI_PACKET_SURFACE_RECORDED,
        "static_surface_only": True,
        "observed_at": observed_at,
        "descriptor_count": len(descriptors),
        "descriptors": descriptors,
        "packet_is_not_approval": True,
        "live_dispatch": False,
    }


def render_packet_surface_fixture(*, observed_at: str = FIXTURE_CLOCK) -> dict[str, object]:
    """Fixture helper — build packet surface from standard EGI flow."""
    from hg_core.egi import (
        create_build_request,
        create_capability_gap,
        create_infrastructure_proposal,
        create_operator_approval_packet,
        detect_repeated_patterns,
    )

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
    packet = create_operator_approval_packet(build_request)
    surface = render_operator_approval_packet_surface(packet, observed_at=observed_at)
    surface["fixture_flow"] = True
    return surface


__all__ = [
    "EGI_PACKET_SURFACE_RECORDED",
    "render_operator_approval_packet_surface",
    "render_packet_surface_fixture",
]
