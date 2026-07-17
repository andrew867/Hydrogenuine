"""EGI end-to-end flow tests — fixture detector through fake queue."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_core.egi import (
    DEFAULT_REPEAT_THRESHOLD,
    DENIED_EXPIRED_APPROVAL,
    DENIED_PENDING_APPROVAL,
    DENIED_REJECTED_APPROVAL,
    EGIRoutingDenied,
    FakeCodeBuildingQueue,
    approve_packet,
    create_build_request,
    create_capability_gap,
    create_infrastructure_proposal,
    create_operator_approval_packet,
    detect_repeated_patterns,
    recommend_modules,
    reject_packet,
    route_to_fake_code_queue,
    validate_routing,
)
from hg_core.egi.detector import FIXTURE_CLOCK


def _repeated_events(count: int = 3, **extra):
    return [
        {
            "event_id": f"evt_{i}",
            "behavior_label": "manual_csv_export",
            "timestamp": f"2026-06-12T17:0{i}:00.000000Z",
            "source_ref": f"src:{i}",
            "module": "workspace",
            **extra,
        }
        for i in range(count)
    ]


def test_repeated_pattern_detection():
    observations = detect_repeated_patterns(_repeated_events(3), threshold=DEFAULT_REPEAT_THRESHOLD)
    assert len(observations) == 1
    assert observations[0].repeated_count == 3


def test_one_off_behavior_does_not_create_gap():
    observations = detect_repeated_patterns(_repeated_events(1), threshold=DEFAULT_REPEAT_THRESHOLD)
    assert observations == []
    assert create_capability_gap(
        detect_repeated_patterns(
            _repeated_events(3),
            threshold=DEFAULT_REPEAT_THRESHOLD,
        )[0],
        threshold=DEFAULT_REPEAT_THRESHOLD,
    ).tool_granted is False


def test_capability_gap_does_not_grant_tool():
    obs = detect_repeated_patterns(_repeated_events(3))[0]
    gap = create_capability_gap(obs)
    assert gap is not None
    assert gap.tool_granted is False
    assert gap.permission_granted is False


def test_proposal_does_not_grant_permission():
    gap = create_capability_gap(detect_repeated_patterns(_repeated_events(3))[0])
    proposal = create_infrastructure_proposal(gap)
    assert proposal.permission_granted is False
    assert proposal.required_operator_approval is True


def test_full_flow_to_fake_queue(tmp_path: Path):
    obs = detect_repeated_patterns(_repeated_events(3))[0]
    gap = create_capability_gap(obs)
    proposal = create_infrastructure_proposal(gap)
    build_request = create_build_request(proposal)
    packet = create_operator_approval_packet(build_request)
    approved = approve_packet(packet, operator_ref="op:local")
    queue = FakeCodeBuildingQueue(root=tmp_path / "fake_queue")
    receipt = route_to_fake_code_queue(build_request, approved, queue=queue)
    assert receipt.sink == "fake_code_building_queue"
    assert receipt.audit_required is True
    assert receipt.available is False
    assert receipt.status == "implemented_pending_audit"
    assert len(queue.dispatches) == 1
    assert queue.runtime_files_touched == []


def test_missing_approval_blocks_route(tmp_path: Path):
    obs = detect_repeated_patterns(_repeated_events(3))[0]
    proposal = create_infrastructure_proposal(create_capability_gap(obs))
    build_request = create_build_request(proposal)
    packet = create_operator_approval_packet(build_request)
    queue = FakeCodeBuildingQueue(root=tmp_path / "fake_queue")
    with pytest.raises(EGIRoutingDenied) as exc:
        route_to_fake_code_queue(build_request, packet, queue=queue)
    assert DENIED_PENDING_APPROVAL in exc.value.codes


def test_rejected_approval_blocks_route(tmp_path: Path):
    proposal = create_infrastructure_proposal(create_capability_gap(detect_repeated_patterns(_repeated_events(3))[0]))
    build_request = create_build_request(proposal)
    packet = reject_packet(create_operator_approval_packet(build_request), operator_ref="op:local")
    queue = FakeCodeBuildingQueue(root=tmp_path / "fake_queue")
    with pytest.raises(EGIRoutingDenied) as exc:
        route_to_fake_code_queue(build_request, packet, queue=queue)
    assert DENIED_REJECTED_APPROVAL in exc.value.codes


def test_expired_approval_blocks_route(tmp_path: Path):
    proposal = create_infrastructure_proposal(create_capability_gap(detect_repeated_patterns(_repeated_events(3))[0]))
    build_request = create_build_request(proposal)
    packet = approve_packet(
        create_operator_approval_packet(build_request, now="2020-01-01T00:00:00.000000Z", ttl_hours=1),
        operator_ref="op:local",
        decision_time="2020-01-01T00:00:00.000000Z",
    )
    queue = FakeCodeBuildingQueue(root=tmp_path / "fake_queue")
    with pytest.raises(EGIRoutingDenied) as exc:
        route_to_fake_code_queue(build_request, packet, queue=queue, now="2099-01-01T00:00:00.000000Z")
    assert DENIED_EXPIRED_APPROVAL in exc.value.codes


def test_privacy_sensitive_routes_sec_ret():
    events = _repeated_events(3, sensitivity_tag="privacy")
    obs = detect_repeated_patterns(events)[0]
    gap = create_capability_gap(obs)
    assert "SEC" in gap.recommended_modules
    assert "RET" in gap.recommended_modules
    proposal = create_infrastructure_proposal(gap)
    assert any("sec" in ref for ref in proposal.risk_assessment_refs)


def test_resource_heavy_routes_rsc():
    events = _repeated_events(3, behavior_label="batch_index_rebuild_heavy")
    obs = detect_repeated_patterns(events)[0]
    gap = create_capability_gap(obs)
    assert "RSC" in gap.recommended_modules


def test_mission_changing_routes_mis():
    events = _repeated_events(3, sensitivity_tag="mission")
    obs = detect_repeated_patterns(events)[0]
    modules = recommend_modules(obs)
    assert "MIS" in modules


def test_affect_driven_routes_afc_sil_dep_bond():
    events = _repeated_events(3, sensitivity_tag="affect")
    obs = detect_repeated_patterns(events)[0]
    modules = recommend_modules(obs)
    assert "AFC" in modules
    assert "SIL" in modules
    assert "DEP-BOND" in modules


def test_validate_routing_pending():
    build_request = create_build_request(
        create_infrastructure_proposal(create_capability_gap(detect_repeated_patterns(_repeated_events(3))[0]))
    )
    packet = create_operator_approval_packet(build_request)
    with pytest.raises(EGIRoutingDenied):
        validate_routing(build_request, packet, now=FIXTURE_CLOCK)
