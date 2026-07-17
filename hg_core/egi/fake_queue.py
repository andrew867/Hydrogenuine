"""EGI fake code-building queue — fixture path only; audit required."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hg_core.egi.approval import validate_routing
from hg_core.egi.detector import FIXTURE_CLOCK
from hg_core.egi.errors import DENIED_AUTHORITY_CONVERSION, EGIRoutingDenied
from hg_core.egi.schemas import BuildRequest, BuildRequestStatus, OperatorApprovalPacket

FAKE_QUEUE_SINK = "fake_code_building_queue"
EXTERNAL_CODE_BUILDER_SINK = "external_code_builder_queue"
EGI_FAKE_QUEUE_ENQUEUED = "egi.advisory.fake_queue_enqueued"


@dataclass
class FakeQueueReceipt:
    receipt_id: str
    build_request_id: str
    approval_packet_id: str
    sink: str
    status: BuildRequestStatus
    audit_required: bool
    available: bool
    artifact_path: str
    receipt_hash: str
    detail: str = "implemented_pending_audit"

    def to_payload(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "build_request_id": self.build_request_id,
            "approval_packet_id": self.approval_packet_id,
            "sink": self.sink,
            "status": self.status,
            "audit_required": self.audit_required,
            "available": self.available,
            "artifact_path": self.artifact_path,
            "receipt_hash": self.receipt_hash,
            "detail": self.detail,
        }


@dataclass
class FakeCodeBuildingQueue:
    """In-memory external code-builder queue; writes receipt JSON only under fixture root."""

    root: Path
    dispatches: list[FakeQueueReceipt] = field(default_factory=list)
    tool_grants: list[str] = field(default_factory=list)
    authority_calls: list[str] = field(default_factory=list)
    runtime_files_touched: list[str] = field(default_factory=list)
    _pending: list[dict[str, Any]] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    @property
    def depth(self) -> int:
        return len(self._pending)

    def peek(self) -> dict[str, Any] | None:
        if not self._pending:
            return None
        return dict(self._pending[0])

    def drain(self) -> list[dict[str, Any]]:
        items = list(self._pending)
        self._pending.clear()
        return items

    def enqueue_approved(
        self,
        build_request: BuildRequest,
        approval_packet: OperatorApprovalPacket,
        *,
        now: str | None = None,
    ) -> dict[str, object]:
        """Enqueue an approved build request on the in-memory external code-builder queue."""
        if build_request.status in {"rejected", "superseded"}:
            raise EGIRoutingDenied((DENIED_AUTHORITY_CONVERSION,), detail="build request not routable")
        validate_routing(build_request, approval_packet, now=now)
        item = {
            "queue_id": f"egi-queue-{len(self._pending) + 1}",
            "build_request_id": build_request.build_request_id,
            "approval_packet_id": approval_packet.approval_packet_id,
            "sink": EXTERNAL_CODE_BUILDER_SINK,
            "enqueued_at": now or FIXTURE_CLOCK,
            "status": "queued",
            "audit_required": True,
            "available": False,
            "permission_granted": False,
            "live_external_build": False,
        }
        self._pending.append(item)
        return {
            "status": "enqueued",
            "reason_code": EGI_FAKE_QUEUE_ENQUEUED,
            "queue_item": item,
            "queue_depth": self.depth,
            "fake_queue_only": True,
            "external_code_builder_only": True,
            "permission_granted": False,
        }

    def route(
        self,
        build_request: BuildRequest,
        approval_packet: OperatorApprovalPacket,
        *,
        now: str | None = None,
    ) -> FakeQueueReceipt:
        validate_routing(build_request, approval_packet, now=now)
        receipt_id = f"egi_fake_{build_request.build_request_id}"
        artifact = self.root / f"{receipt_id}.json"
        receipt = FakeQueueReceipt(
            receipt_id=receipt_id,
            build_request_id=build_request.build_request_id,
            approval_packet_id=approval_packet.approval_packet_id,
            sink=FAKE_QUEUE_SINK,
            status="implemented_pending_audit",
            audit_required=True,
            available=False,
            artifact_path=str(artifact),
            receipt_hash=receipt_id,
        )
        artifact.write_text(json.dumps(receipt.to_payload(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.dispatches.append(receipt)
        return receipt


def route_to_fake_code_queue(
    build_request: BuildRequest,
    approval_packet: OperatorApprovalPacket,
    *,
    queue: FakeCodeBuildingQueue,
    now: str | None = None,
) -> FakeQueueReceipt:
    """Route an approved build request to the external code-builder queue only."""
    if build_request.status in {"rejected", "superseded"}:
        raise EGIRoutingDenied((DENIED_AUTHORITY_CONVERSION,), detail="build request not routable")
    queue.enqueue_approved(build_request, approval_packet, now=now)
    return queue.route(build_request, approval_packet, now=now or FIXTURE_CLOCK)


def enqueue_fixture_code_builder_queue(
    *,
    queue: FakeCodeBuildingQueue | None = None,
    root: Path | None = None,
) -> dict[str, object]:
    """Enqueue fixture-approved build requests on the in-memory external code-builder queue."""
    from hg_core.egi.approval import approve_packet, create_build_request, create_operator_approval_packet
    from hg_core.egi.proposal import create_capability_gap, create_infrastructure_proposal

    from hg_core.egi.detector import detect_repeated_patterns

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
    active_queue = queue
    if active_queue is None:
        if root is None:
            raise ValueError("queue or root required")
        active_queue = FakeCodeBuildingQueue(root=root)
    enqueued: list[dict[str, object]] = []
    for idx in range(2):
        obs = detect_repeated_patterns(events, threshold=3)[0]
        gap = create_capability_gap(obs)
        proposal = create_infrastructure_proposal(gap)
        build_request = create_build_request(proposal)
        packet = approve_packet(
            create_operator_approval_packet(build_request),
            operator_ref=f"op:fixture-{idx}",
        )
        enqueued.append(active_queue.enqueue_approved(build_request, packet))
    return {
        "status": "queued",
        "fake_queue_only": True,
        "external_code_builder_only": True,
        "queue_depth": active_queue.depth,
        "enqueued": enqueued,
        "permission_granted": False,
    }


__all__ = [
    "EGI_FAKE_QUEUE_ENQUEUED",
    "EXTERNAL_CODE_BUILDER_SINK",
    "FAKE_QUEUE_SINK",
    "FakeCodeBuildingQueue",
    "FakeQueueReceipt",
    "enqueue_fixture_code_builder_queue",
    "route_to_fake_code_queue",
]
