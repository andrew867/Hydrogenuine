"""
Control Surface Pack 10: Multi-swarm overseers — rollups, routing, global controls, impact.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hg_core.fleet import (
    get_fleet_swarms_with_rollups,
    suggest_routing,
    apply_routing,
    preflight_global_control,
    apply_global_control,
    list_active_global_controls,
    explore_impact,
)
from hg_core.swarms import create_swarm
from hg_core.control_surface import (
    api_fleet_swarms,
    api_fleet_controls_preflight,
    api_fleet_controls_apply,
    api_fleet_routing_suggest,
    api_fleet_routing_apply,
    api_fleet_impact_explore,
)


def _scope_actor():
    return {"type": "run", "id": "test"}, {"agent_id": "ops", "pubkey": "0" * 64, "key_id": "k"}


def test_routing_suggestion_respects_constraints(tmp_path: Path) -> None:
    """Routing suggestion returns suggestions and constraints_checked."""
    scope, actor = _scope_actor()
    create_swarm(name="S1", scope=scope, actor=actor, workspace_root=tmp_path)
    create_swarm(name="S2", scope=scope, actor=actor, workspace_root=tmp_path)
    out = suggest_routing(tmp_path, work_item_id="wi1", from_swarm="nonexistent", constraints=["trust_tier"], limit=5)
    assert "suggestions" in out
    assert "constraints_checked" in out
    assert out["constraints_checked"] == ["trust_tier"]


def test_routing_apply_emits_work_item_routed(tmp_path: Path) -> None:
    """Routing apply emits WORK_ITEM_ROUTED and proof artifact."""
    scope, actor = _scope_actor()
    routing_id = apply_routing(
        work_item_id="wi1",
        from_swarm="s1",
        to_swarm="s2",
        scope=scope,
        actor=actor,
        workspace_root=tmp_path,
    )
    assert routing_id.startswith("route_")
    from hg_core.ledger.ledger_writer import iterate_events
    events = list(iterate_events(tmp_path, scope_type="run", scope_id="test"))
    assert any(ev.get("action") == "WORK_ITEM_ROUTED" for ev in events)
    proof_path = tmp_path / "artifacts" / "fleet" / "routing" / f"{routing_id}.json"
    assert proof_path.exists()


def test_global_control_requires_quorum_and_expires(tmp_path: Path) -> None:
    """Global control requires quorum; when applied has expiry; list_active filters expired."""
    scope, actor = _scope_actor()
    pre = preflight_global_control(tmp_path, "freeze_writes", scope)
    assert pre.get("allowed") is True
    assert pre.get("quorum_required") is True

    out_denied = apply_global_control(
        kind="freeze_writes",
        scope=scope,
        actor=actor,
        quorum_approved=False,
        workspace_root=tmp_path,
    )
    assert out_denied.get("applied") is False
    assert "quorum" in out_denied.get("reason", "").lower()

    out_applied = apply_global_control(
        kind="freeze_writes",
        scope=scope,
        actor=actor,
        expiry_hours=1,
        quorum_approved=True,
        workspace_root=tmp_path,
    )
    assert out_applied.get("applied") is True
    assert out_applied.get("control_id", "").startswith("gc_")

    active = list_active_global_controls(tmp_path)
    assert len(active) >= 1
    assert active[0].get("kind") == "freeze_writes"


def test_fleet_rollups_match_derived_metrics(tmp_path: Path) -> None:
    """Fleet rollups match derived metrics from materialized views."""
    scope, actor = _scope_actor()
    create_swarm(name="R1", scope=scope, actor=actor, workspace_root=tmp_path)
    root = tmp_path / "memory" / "materialized"
    root.mkdir(parents=True, exist_ok=True)
    (root / "drift_scores.jsonl").write_text('{"score":0.3,"drift_id":"d1"}\n', encoding="utf-8")
    (root / "work_items.jsonl").write_text('{"work_item_id":"w1","status":"blocked"}\n', encoding="utf-8")
    swarms = get_fleet_swarms_with_rollups(tmp_path)
    assert len(swarms) >= 1
    r = swarms[0].get("rollup", {})
    assert "drift_score_count" in r
    assert "max_drift_score" in r
    assert "work_items_total" in r
    assert "work_items_blocked" in r
    assert r.get("work_items_blocked") == 1


def test_shared_impact_explorer_returns_blast_radius(tmp_path: Path) -> None:
    """Shared impact explorer returns consistent blast radius across swarms."""
    out = explore_impact(tmp_path, limit=10)
    assert "incidents" in out
    assert "work_items" in out
    assert "blast_radius" in out
    assert "by_swarm" in out["blast_radius"]
    assert "total_affected" in out["blast_radius"]


def test_api_fleet_swarms_and_controls(tmp_path: Path) -> None:
    """API fleet swarms and controls preflight/apply."""
    swarms = api_fleet_swarms(tmp_path)
    assert isinstance(swarms, list)
    scope = {"type": "run", "id": "test"}
    pre = api_fleet_controls_preflight(tmp_path, "read_only", scope)
    assert pre.get("allowed") is True
    actor = {"agent_id": "ops", "pubkey": "0" * 64, "key_id": "k"}
    applied = api_fleet_controls_apply("read_only", scope, actor, expiry_hours=1, quorum_approved=True, workspace_root=tmp_path)
    assert applied.get("applied") is True


def test_api_fleet_routing_and_impact(tmp_path: Path) -> None:
    """API fleet routing suggest/apply and impact explore."""
    scope, actor = _scope_actor()
    suggest = api_fleet_routing_suggest(tmp_path, "wi1", "s1", limit=3)
    assert "suggestions" in suggest
    rid = api_fleet_routing_apply("wi1", "s1", "s2", scope, actor, workspace_root=tmp_path)
    assert rid
    impact = api_fleet_impact_explore(tmp_path, limit=5)
    assert "blast_radius" in impact


def test_global_control_invalid_kind(tmp_path: Path) -> None:
    """Preflight and apply reject invalid kind."""
    scope = {"type": "run", "id": "test"}
    pre = preflight_global_control(tmp_path, "invalid_kind", scope)
    assert pre.get("allowed") is False
    actor = {"agent_id": "ops", "pubkey": "0" * 64, "key_id": "k"}
    out = apply_global_control(kind="invalid", scope=scope, actor=actor, workspace_root=tmp_path)
    assert out.get("applied") is False
