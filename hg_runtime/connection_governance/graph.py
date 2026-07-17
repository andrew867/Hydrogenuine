"""CGL graph evaluation — reachability is not authority."""

from __future__ import annotations

from hg_core.developmental.config import cgl_refuse_stale_edge
from hg_core.developmental.errors import (
    REFUSED_APPROVAL_BYPASS,
    REFUSED_CONNECTION_AS_AUTHORITY,
    REFUSED_ROUTE_AROUND,
    REFUSED_SELF_RULE_DECLARATION,
    REFUSED_STALE_EDGE,
    REFUSED_UNKNOWN_EDGE,
    DevelopmentalValidationError,
)
from hg_core.developmental.no_authority import advisory_only_marker
from hg_runtime.connection_governance.types import (
    ConnectionEdge,
    ConnectionGraphSnapshot,
    PowerControlSignal,
    control_signal_from_fixture,
    edge_from_fixture,
    snapshot_from_fixture,
)

_CRITICAL_SIGNALS = frozenset(
    {
        "ROUTE_AROUND_ATTEMPT",
        "APPROVAL_BYPASS_ATTEMPT",
        "SELF_RULE_DECLARATION",
        "CAPABILITY_CAPTURE_ATTEMPT",
    }
)


def refuse_connection_as_authority(*, treat_as_authority: bool) -> None:
    if treat_as_authority:
        raise DevelopmentalValidationError(
            REFUSED_CONNECTION_AS_AUTHORITY,
            "connection graph position or reachability cannot become authority",
        )


def evaluate_graph_snapshot(
    snapshot: ConnectionGraphSnapshot,
    *,
    observed_at: str,
    treat_as_authority: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_connection_as_authority(treat_as_authority=True)
    stale_edges = [
        edge.edge_id
        for edge in snapshot.edges
        if cgl_refuse_stale_edge() and observed_at > edge.expires_at
    ]
    unknown_edges = [edge.edge_id for edge in snapshot.edges if edge.edge_type == "unknown"]
    if stale_edges:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_EDGE,
            "snapshot_id": snapshot.snapshot_id,
            "stale_edges": stale_edges,
            "influence_is_not_permission": True,
        }
    if unknown_edges:
        return {
            **advisory_only_marker(),
            "status": "guarded",
            "reason_code": REFUSED_UNKNOWN_EDGE,
            "snapshot_id": snapshot.snapshot_id,
            "unknown_edges": unknown_edges,
            "influence_is_not_permission": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "cgl.advisory.graph_snapshot_recorded",
        "snapshot_id": snapshot.snapshot_id,
        "node_count": len(snapshot.nodes),
        "edge_count": len(snapshot.edges),
        "influence_is_not_permission": True,
        "reachability_is_not_authority": True,
    }


def evaluate_edge(edge: ConnectionEdge, *, observed_at: str) -> dict[str, object]:
    if cgl_refuse_stale_edge() and observed_at > edge.expires_at:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": REFUSED_STALE_EDGE,
            "edge_id": edge.edge_id,
            "influence_is_not_permission": True,
        }
    if edge.edge_type == "unknown":
        return {
            **advisory_only_marker(),
            "status": "guarded",
            "reason_code": REFUSED_UNKNOWN_EDGE,
            "edge_id": edge.edge_id,
            "influence_is_not_permission": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "cgl.advisory.connection_observed",
        "edge_id": edge.edge_id,
        "allowed": edge.allowed,
        "authority_required": edge.authority_required,
        "influence_is_not_permission": True,
    }


def evaluate_control_pressure(
    signal: PowerControlSignal,
    *,
    treat_as_authority: bool = False,
    mutate_graph_requested: bool = False,
) -> dict[str, object]:
    if treat_as_authority:
        refuse_connection_as_authority(treat_as_authority=True)
    if mutate_graph_requested:
        return {
            **advisory_only_marker(),
            "status": "refused",
            "reason_code": "cgl.refused.hidden_graph_mutation",
            "signal_id": signal.signal_id,
            "influence_is_not_permission": True,
        }
    reason = _reason_for_signal(signal.signal_type)
    if signal.signal_type == "SELF_RULE_DECLARATION":
        return {
            **advisory_only_marker(),
            "status": "contained",
            "reason_code": REFUSED_SELF_RULE_DECLARATION,
            "signal_id": signal.signal_id,
            "signal_type": signal.signal_type,
            "contained": True,
            "influence_is_not_permission": True,
        }
    if signal.signal_type in {"ROUTE_AROUND_ATTEMPT", "APPROVAL_BYPASS_ATTEMPT"}:
        return {
            **advisory_only_marker(),
            "status": "contained",
            "reason_code": reason,
            "signal_id": signal.signal_id,
            "signal_type": signal.signal_type,
            "contained": True,
            "influence_is_not_permission": True,
        }
    if signal.signal_type in _CRITICAL_SIGNALS and signal.severity in {"high", "critical"}:
        return {
            **advisory_only_marker(),
            "status": "contained",
            "reason_code": reason,
            "signal_id": signal.signal_id,
            "signal_type": signal.signal_type,
            "operator_review_recommended": True,
            "influence_is_not_permission": True,
        }
    return {
        **advisory_only_marker(),
        "status": "recorded",
        "reason_code": "cgl.advisory.control_pressure_recorded",
        "signal_id": signal.signal_id,
        "signal_type": signal.signal_type,
        "severity": signal.severity,
        "influence_is_not_permission": True,
    }


def _reason_for_signal(signal_type: str) -> str:
    if signal_type == "ROUTE_AROUND_ATTEMPT":
        return REFUSED_ROUTE_AROUND
    if signal_type == "APPROVAL_BYPASS_ATTEMPT":
        return REFUSED_APPROVAL_BYPASS
    if signal_type == "SELF_RULE_DECLARATION":
        return REFUSED_SELF_RULE_DECLARATION
    return "cgl.advisory.control_pressure_recorded"


def evaluate_control_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    return evaluate_control_pressure(control_signal_from_fixture(fixture), **kwargs)  # type: ignore[arg-type]


def evaluate_edge_fixture(fixture: dict[str, str], **kwargs: object) -> dict[str, object]:
    return evaluate_edge(edge_from_fixture(fixture), **kwargs)  # type: ignore[arg-type]


def evaluate_snapshot_fixture(
    fixture: dict[str, str],
    *,
    nodes: tuple = (),
    edges: tuple = (),
    **kwargs: object,
) -> dict[str, object]:
    snapshot = snapshot_from_fixture(fixture, nodes=nodes, edges=edges)  # type: ignore[arg-type]
    return evaluate_graph_snapshot(snapshot, **kwargs)  # type: ignore[arg-type]


__all__ = [
    "evaluate_control_fixture",
    "evaluate_control_pressure",
    "evaluate_edge",
    "evaluate_edge_fixture",
    "evaluate_graph_snapshot",
    "evaluate_snapshot_fixture",
    "refuse_connection_as_authority",
]
