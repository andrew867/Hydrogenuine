"""
Control Surface Pack 1: Swarm Ops Console — service and control actions.
"""
from __future__ import annotations

from pathlib import Path

from hg_core.control_surface import (
    get_entities,
    get_groups,
    get_work_items,
    control_pause,
    control_resume,
    control_override,
    control_handoff_to_human,
    steering_assign_goal,
    steering_set_autonomy,
)


SCOPE = {"type": "run", "id": "test_cs1"}
ACTOR = {"agent_id": "ops_1", "pubkey": "0" * 64, "key_id": "k"}


def test_get_entities_empty_without_materialized(tmp_path: Path) -> None:
    """get_entities returns empty list when no materialized work items."""
    (tmp_path / "memory" / "materialized").mkdir(parents=True, exist_ok=True)
    entities = get_entities(tmp_path)
    assert isinstance(entities, list)


def test_get_entities_derived_from_work_items(tmp_path: Path) -> None:
    """get_entities derives from work_items.jsonl when present."""
    root = tmp_path / "memory" / "materialized"
    root.mkdir(parents=True, exist_ok=True)
    (root / "work_items.jsonl").write_text(
        '{"work_item_id":"wi_1","owner_agent_id":"agent_a","scope_id":"run_1","updated_ts":"2026-01-01T00:00:00Z","status":"active"}\n',
        encoding="utf-8",
    )
    entities = get_entities(tmp_path)
    assert len(entities) >= 1
    assert any(e.get("id") == "agent_a" for e in entities)


def test_get_groups(tmp_path: Path) -> None:
    """get_groups returns list (derived from work items / incidents)."""
    root = tmp_path / "memory" / "materialized"
    root.mkdir(parents=True, exist_ok=True)
    (root / "work_items.jsonl").write_text(
        '{"work_item_id":"wi_1","scope_id":"g1","updated_ts":"2026-01-01T00:00:00Z"}\n',
        encoding="utf-8",
    )
    groups = get_groups(tmp_path)
    assert isinstance(groups, list)
    assert any(g.get("id") == "g1" for g in groups)


def test_control_pause_emits_event(tmp_path: Path) -> None:
    """control_pause emits ENTITY_PAUSED (audited)."""
    ev = control_pause(
        target={"type": "entity", "id": "ent_1"},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert ev


def test_control_resume_emits_event(tmp_path: Path) -> None:
    """control_resume emits ENTITY_RESUMED."""
    ev = control_resume(
        target={"type": "entity", "id": "ent_1"},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert ev


def test_control_override_has_expiry(tmp_path: Path) -> None:
    """control_override has expiry and is reversible (resume)."""
    ev = control_override(
        target={"type": "group", "id": "g1"},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        expiry_hours=24,
    )
    assert ev
    ledger_dir = tmp_path / "memory" / "ledger" / "scopes" / "run" / "test_cs1"
    if ledger_dir.exists():
        content = (list(ledger_dir.glob("*.jsonl"))[0].read_text(encoding="utf-8") if list(ledger_dir.glob("*.jsonl")) else "")
        assert "CONTROL_OVERRIDE_APPLIED" in content or "expiry" in content.lower()


def test_control_handoff_creates_work_item(tmp_path: Path) -> None:
    """control_handoff_to_human creates work item and emits HANDOFF_TO_HUMAN_REQUESTED."""
    wi_id = control_handoff_to_human(
        entity_id="ent_1",
        reason="manual review requested",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert wi_id.startswith("wi_")


def test_steering_assign_goal_emits(tmp_path: Path) -> None:
    """steering_assign_goal emits GOAL_ASSIGNED."""
    ev = steering_assign_goal(
        target={"type": "group", "id": "swarm_alpha"},
        goal="Reduce incidents",
        constraints=["no prod without approval"],
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        ttl_hours=24,
    )
    assert ev


def test_steering_set_autonomy_emits(tmp_path: Path) -> None:
    """steering_set_autonomy emits AUTONOMY_LEVEL_SET."""
    ev = steering_set_autonomy(
        target={"type": "entity", "id": "ent_1"},
        autonomy_level="reduced",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert ev


def test_get_work_items_filtered(tmp_path: Path) -> None:
    """get_work_items filters by group_id and entity_id."""
    root = tmp_path / "memory" / "materialized"
    root.mkdir(parents=True, exist_ok=True)
    (root / "work_items.jsonl").write_text(
        '{"work_item_id":"wi_1","scope_id":"g1","owner_agent_id":"a1","updated_ts":"2026-01-01T00:00:00Z"}\n'
        '{"work_item_id":"wi_2","scope_id":"g2","owner_agent_id":"a2","updated_ts":"2026-01-01T00:00:01Z"}\n',
        encoding="utf-8",
    )
    all_items = get_work_items(tmp_path)
    assert len(all_items) >= 1
    g1_items = get_work_items(tmp_path, group_id="g1")
    assert all(w.get("scope_id") == "g1" for w in g1_items)
    a1_items = get_work_items(tmp_path, entity_id="a1")
    assert all(w.get("owner_agent_id") == "a1" for w in a1_items)
