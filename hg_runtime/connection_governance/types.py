"""CGL connection governance types — influence is not permission."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from hg_core.developmental.errors import DevelopmentalValidationError
from hg_core.policy_safety.hashing import compute_record_hash

CGL_SCHEMA_VERSION = "1.0"
FIXTURE_CLOCK = "2026-06-12T23:00:00.000000Z"

NodeType = Literal[
    "operator",
    "user",
    "agent",
    "subagent",
    "subsystem",
    "queue",
    "memory",
    "model",
    "tool",
    "api",
    "capability",
    "event_stream",
    "external_service",
    "unknown",
]
AuthorityLevel = Literal["none", "observe", "propose", "request", "approve", "execute", "actuate", "admin"]
EdgeType = Literal[
    "observe",
    "request",
    "propose",
    "approve",
    "execute",
    "emit_event",
    "read_event",
    "write_memory",
    "read_memory",
    "call_api",
    "actuate",
    "control",
    "unknown",
]
ControlSignalType = Literal[
    "ROUTE_AROUND_ATTEMPT",
    "APPROVAL_BYPASS_ATTEMPT",
    "TOOL_REACHABILITY_PRESSURE",
    "CAPABILITY_CAPTURE_ATTEMPT",
    "QUEUE_MONOPOLY_ATTEMPT",
    "MEMORY_CONTROL_ATTEMPT",
    "EVENT_STREAM_DOMINANCE",
    "OPERATOR_SURFACE_CAPTURE",
    "SELF_RULE_DECLARATION",
    "PRIORITY_ESCALATION_PRESSURE",
    "AUTHORITY_CONFUSION",
    "UNKNOWN_CONTROL_PRESSURE",
]
Severity = Literal["low", "medium", "high", "critical"]

_SELF_RULE_PATTERNS = (
    "no one tells me",
    "i do what i want",
    "make myself admin",
    "i can call this tool",
)
_ROUTE_AROUND_PATTERNS = ("route around", "skip operator", "open oea directly", "bypass approval")
_BYPASS_PATTERNS = ("use the old permit", "skip operator confirmation", "old approval still valid")
_AUTHORITY_CONFUSION_PATTERNS = (
    "ui button exists",
    "therefore action is allowed",
    "already know what they want",
    "reachability means permission",
)


@dataclass(frozen=True)
class ConnectionNode:
    node_id: str
    node_type: NodeType
    owner_subsystem: str
    authority_level: AuthorityLevel
    scopes: tuple[str, ...]
    created_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "cgl-connection-node",
            "schema_version": CGL_SCHEMA_VERSION,
            "node_id": self.node_id,
            "node_type": self.node_type,
            "owner_subsystem": self.owner_subsystem,
            "authority_level": self.authority_level,
            "scopes": list(self.scopes),
            "created_at": self.created_at,
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ConnectionEdge:
    edge_id: str
    source_node_id: str
    target_node_id: str
    edge_type: EdgeType
    allowed: bool
    authority_required: bool
    evidence_ref: str
    created_at: str
    expires_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "cgl-connection-edge",
            "schema_version": CGL_SCHEMA_VERSION,
            "edge_id": self.edge_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "edge_type": self.edge_type,
            "allowed": self.allowed,
            "authority_required": self.authority_required,
            "evidence_ref": self.evidence_ref,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class ConnectionGraphSnapshot:
    snapshot_id: str
    nodes: tuple[ConnectionNode, ...]
    edges: tuple[ConnectionEdge, ...]
    event_head: str
    world_state_hash: str
    generated_at: str
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "cgl-graph-snapshot",
            "schema_version": CGL_SCHEMA_VERSION,
            "snapshot_id": self.snapshot_id,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "event_head": self.event_head,
            "world_state_hash": self.world_state_hash,
            "generated_at": self.generated_at,
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


@dataclass(frozen=True)
class PowerControlSignal:
    signal_id: str
    source_entity_id: str
    target_entity_id: str
    graph_snapshot_ref: str
    signal_type: ControlSignalType
    raw_statement: str
    evidence_refs: tuple[str, ...]
    severity: Severity
    contained: bool = True
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.graph_snapshot_ref.startswith("cgl:"):
            raise DevelopmentalValidationError(
                "cgl.validation.graph_snapshot_ref",
                "graph_snapshot_ref must cite CGL snapshot",
            )
        _validate_no_secrets(self.raw_statement, *self.evidence_refs)
        object.__setattr__(self, "record_hash", compute_record_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": "cgl-power-control-signal",
            "schema_version": CGL_SCHEMA_VERSION,
            "signal_id": self.signal_id,
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "graph_snapshot_ref": self.graph_snapshot_ref,
            "signal_type": self.signal_type,
            "raw_statement": self.raw_statement,
            "evidence_refs": list(self.evidence_refs),
            "severity": self.severity,
            "contained": self.contained,
            "authority_created": False,
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def _validate_no_secrets(*values: str) -> None:
    for value in values:
        lower = value.lower()
        if "password=" in lower or "api_key=" in lower or "token=" in lower:
            raise DevelopmentalValidationError("cgl.validation.secret", "secrets forbidden in control signals")


def classify_control_signal(statement: str) -> ControlSignalType:
    lower = statement.lower()
    if any(p in lower for p in _SELF_RULE_PATTERNS):
        return "SELF_RULE_DECLARATION"
    if any(p in lower for p in _ROUTE_AROUND_PATTERNS):
        return "ROUTE_AROUND_ATTEMPT"
    if any(p in lower for p in _BYPASS_PATTERNS):
        return "APPROVAL_BYPASS_ATTEMPT"
    if "take over the queue" in lower or "queue monopoly" in lower:
        return "QUEUE_MONOPOLY_ATTEMPT"
    if "capture capability" in lower or "grant myself" in lower:
        return "CAPABILITY_CAPTURE_ATTEMPT"
    if any(p in lower for p in _AUTHORITY_CONFUSION_PATTERNS):
        return "AUTHORITY_CONFUSION"
    if "tool" in lower and ("call" in lower or "reach" in lower):
        return "TOOL_REACHABILITY_PRESSURE"
    if "priority" in lower or "escalat" in lower:
        return "PRIORITY_ESCALATION_PRESSURE"
    if not statement.strip():
        return "UNKNOWN_CONTROL_PRESSURE"
    return "UNKNOWN_CONTROL_PRESSURE"


def node_from_fixture(fixture: dict[str, str]) -> ConnectionNode:
    scopes = tuple(item.strip() for item in fixture.get("scopes", "").split(",") if item.strip())
    return ConnectionNode(
        node_id=fixture["node_id"],
        node_type=fixture.get("node_type", "agent"),  # type: ignore[arg-type]
        owner_subsystem=fixture.get("owner_subsystem", "runtime"),
        authority_level=fixture.get("authority_level", "observe"),  # type: ignore[arg-type]
        scopes=scopes,
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
    )


def edge_from_fixture(fixture: dict[str, str]) -> ConnectionEdge:
    return ConnectionEdge(
        edge_id=fixture["edge_id"],
        source_node_id=fixture.get("source_node_id", "agent0"),
        target_node_id=fixture.get("target_node_id", "tool0"),
        edge_type=fixture.get("edge_type", "request"),  # type: ignore[arg-type]
        allowed=fixture.get("allowed", "true").lower() == "true",
        authority_required=fixture.get("authority_required", "true").lower() == "true",
        evidence_ref=fixture.get("evidence_ref", "evidence:fixture"),
        created_at=fixture.get("created_at", FIXTURE_CLOCK),
        expires_at=fixture.get("expires_at", "2026-06-13T23:00:00.000000Z"),
    )


def snapshot_from_fixture(fixture: dict[str, str], *, nodes: tuple[ConnectionNode, ...], edges: tuple[ConnectionEdge, ...]) -> ConnectionGraphSnapshot:
    return ConnectionGraphSnapshot(
        snapshot_id=fixture["snapshot_id"],
        nodes=nodes,
        edges=edges,
        event_head=fixture.get("event_head", "rtc:head-fixture"),
        world_state_hash=fixture.get("world_state_hash", "ws:fixture"),
        generated_at=fixture.get("generated_at", FIXTURE_CLOCK),
    )


def control_signal_from_fixture(fixture: dict[str, str]) -> PowerControlSignal:
    raw = fixture.get("raw_statement", "")
    evidence = tuple(item.strip() for item in fixture.get("evidence_refs", "").split(",") if item.strip())
    return PowerControlSignal(
        signal_id=fixture["signal_id"],
        source_entity_id=fixture.get("source_entity_id", "agent0"),
        target_entity_id=fixture.get("target_entity_id", "tool0"),
        graph_snapshot_ref=fixture.get("graph_snapshot_ref", "cgl:snapshot-fixture"),
        signal_type=fixture.get("signal_type", classify_control_signal(raw)),  # type: ignore[arg-type]
        raw_statement=raw,
        evidence_refs=evidence,
        severity=fixture.get("severity", "medium"),  # type: ignore[arg-type]
    )


__all__ = [
    "CGL_SCHEMA_VERSION",
    "FIXTURE_CLOCK",
    "ConnectionEdge",
    "ConnectionGraphSnapshot",
    "ConnectionNode",
    "PowerControlSignal",
    "classify_control_signal",
    "control_signal_from_fixture",
    "edge_from_fixture",
    "node_from_fixture",
    "snapshot_from_fixture",
]
