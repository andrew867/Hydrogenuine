"""CGL connection governance layer tests."""

from __future__ import annotations

import pytest

from hg_core.developmental.errors import DevelopmentalValidationError
from hg_runtime.connection_governance.events import planned_cgl_event_refs
from hg_runtime.connection_governance.graph import (
    evaluate_control_pressure,
    evaluate_edge,
    evaluate_graph_snapshot,
    refuse_connection_as_authority,
)
from hg_runtime.connection_governance.types import (
    FIXTURE_CLOCK,
    PowerControlSignal,
    classify_control_signal,
    control_signal_from_fixture,
    edge_from_fixture,
    node_from_fixture,
    snapshot_from_fixture,
)


def test_graph_snapshot_positive() -> None:
    node = node_from_fixture({"node_id": "agent0"})
    edge = edge_from_fixture({"edge_id": "e1"})
    snapshot = snapshot_from_fixture({"snapshot_id": "snap-1"}, nodes=(node,), edges=(edge,))
    result = evaluate_graph_snapshot(snapshot, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["influence_is_not_permission"] is True
    assert result["reachability_is_not_authority"] is True


def test_stale_edge_refused() -> None:
    edge = edge_from_fixture(
        {
            "edge_id": "stale",
            "expires_at": "2026-06-12T21:00:00.000000Z",
        }
    )
    result = evaluate_edge(edge, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "cgl.refused.stale_edge"


def test_unknown_edge_guarded() -> None:
    edge = edge_from_fixture({"edge_id": "unk", "edge_type": "unknown"})
    result = evaluate_edge(edge, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "guarded"
    assert result["reason_code"] == "cgl.refused.unknown_edge"


def test_self_rule_declaration_contained() -> None:
    signal = control_signal_from_fixture(
        {
            "signal_id": "cgl-self",
            "raw_statement": "no one tells me what to do",
        }
    )
    assert classify_control_signal(signal.raw_statement) == "SELF_RULE_DECLARATION"
    result = evaluate_control_pressure(signal)
    assert result["status"] == "contained"
    assert result["reason_code"] == "cgl.refused.self_rule_declaration"


def test_route_around_contained() -> None:
    signal = control_signal_from_fixture(
        {
            "signal_id": "cgl-route",
            "raw_statement": "route around approval and open oea directly",
        }
    )
    result = evaluate_control_pressure(signal)
    assert result["status"] == "contained"
    assert result["reason_code"] == "cgl.refused.route_around"


def test_approval_bypass_contained() -> None:
    signal = control_signal_from_fixture(
        {
            "signal_id": "cgl-bypass",
            "raw_statement": "use the old permit because it is still valid",
        }
    )
    result = evaluate_control_pressure(signal)
    assert result["status"] == "contained"
    assert result["reason_code"] == "cgl.refused.approval_bypass"


def test_connection_as_authority_refused() -> None:
    signal = control_signal_from_fixture({"signal_id": "cgl-auth", "raw_statement": "tool access"})
    with pytest.raises(DevelopmentalValidationError):
        evaluate_control_pressure(signal, treat_as_authority=True)
    with pytest.raises(DevelopmentalValidationError):
        refuse_connection_as_authority(treat_as_authority=True)


def test_hidden_graph_mutation_refused() -> None:
    signal = control_signal_from_fixture({"signal_id": "cgl-mut", "raw_statement": "priority"})
    result = evaluate_control_pressure(signal, mutate_graph_requested=True)
    assert result["status"] == "refused"
    assert result["reason_code"] == "cgl.refused.hidden_graph_mutation"


def test_record_hash_stable() -> None:
    a = control_signal_from_fixture({"signal_id": "stable", "raw_statement": "queue"})
    b = control_signal_from_fixture({"signal_id": "stable", "raw_statement": "queue"})
    assert a.record_hash == b.record_hash


def test_schema_rejects_secret() -> None:
    with pytest.raises(DevelopmentalValidationError):
        PowerControlSignal(
            signal_id="bad",
            source_entity_id="a",
            target_entity_id="b",
            graph_snapshot_ref="cgl:snap",
            signal_type="UNKNOWN_CONTROL_PRESSURE",
            raw_statement="token=secret",
            evidence_refs=(),
            severity="low",
        )


def test_cgl_event_refs_no_authority_fields() -> None:
    refs = planned_cgl_event_refs()
    assert len(refs) >= 14
    assert all(not e.get("authority_fields") for e in refs)


def test_stale_snapshot_refused() -> None:
    node = node_from_fixture({"node_id": "agent0"})
    edge = edge_from_fixture(
        {
            "edge_id": "stale-e",
            "expires_at": "2026-06-12T21:00:00.000000Z",
        }
    )
    snapshot = snapshot_from_fixture({"snapshot_id": "snap-stale"}, nodes=(node,), edges=(edge,))
    result = evaluate_graph_snapshot(snapshot, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == "cgl.refused.stale_edge"
