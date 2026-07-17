"""EGI external code-builder queue tests — slice 3."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_core.egi import (
    DENIED_PENDING_APPROVAL,
    EGIRoutingDenied,
    FakeCodeBuildingQueue,
    approve_packet,
    create_build_request,
    create_capability_gap,
    create_infrastructure_proposal,
    create_operator_approval_packet,
    detect_repeated_patterns,
    enqueue_fixture_code_builder_queue,
    route_to_fake_code_queue,
)
from hg_core.egi.fake_queue import EGI_FAKE_QUEUE_ENQUEUED, EXTERNAL_CODE_BUILDER_SINK


def _approved_flow(tmp_path: Path):
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
    packet = approve_packet(
        create_operator_approval_packet(build_request),
        operator_ref="op:queue-test",
    )
    queue = FakeCodeBuildingQueue(root=tmp_path / "external_queue")
    return build_request, packet, queue


def test_external_code_builder_enqueue(tmp_path: Path):
    build_request, packet, queue = _approved_flow(tmp_path)
    result = queue.enqueue_approved(build_request, packet)
    assert result["reason_code"] == EGI_FAKE_QUEUE_ENQUEUED
    assert result["fake_queue_only"] is True
    assert result["external_code_builder_only"] is True
    assert result["queue_item"]["sink"] == EXTERNAL_CODE_BUILDER_SINK
    assert queue.depth == 1
    assert queue.peek() is not None


def test_route_to_external_queue_writes_receipt(tmp_path: Path):
    build_request, packet, queue = _approved_flow(tmp_path)
    receipt = route_to_fake_code_queue(build_request, packet, queue=queue)
    assert queue.depth == 1
    assert receipt.audit_required is True
    assert receipt.available is False
    assert len(queue.dispatches) == 1


def test_enqueue_fixture_code_builder_queue(tmp_path: Path):
    result = enqueue_fixture_code_builder_queue(root=tmp_path / "fixture_queue")
    assert result["external_code_builder_only"] is True
    assert result["queue_depth"] == 2
    assert len(result["enqueued"]) == 2


def test_pending_build_request_denied(tmp_path: Path):
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
    proposal = create_infrastructure_proposal(create_capability_gap(obs))
    build_request = create_build_request(proposal)
    packet = create_operator_approval_packet(build_request)
    queue = FakeCodeBuildingQueue(root=tmp_path / "denied_queue")
    with pytest.raises(EGIRoutingDenied) as exc:
        queue.enqueue_approved(build_request, packet)
    assert DENIED_PENDING_APPROVAL in exc.value.codes


def test_queue_drain(tmp_path: Path):
    build_request, packet, queue = _approved_flow(tmp_path)
    queue.enqueue_approved(build_request, packet)
    drained = queue.drain()
    assert len(drained) == 1
    assert queue.depth == 0
