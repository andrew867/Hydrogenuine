"""
Control Surface Pack 3: UX polish & API docs — pagination, filters, explain_block, activity_feed, OpenAPI.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hg_core.control_surface import (
    get_entities,
    get_groups,
    get_work_items,
    get_activity_feed,
    explain_block,
)


def test_get_entities_paginated_shape(tmp_path: Path) -> None:
    """get_entities with status or cursor returns { items, next_cursor }."""
    (tmp_path / "memory" / "materialized").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory" / "materialized" / "work_items.jsonl").write_text(
        '{"work_item_id":"wi1","owner_agent_id":"e1","scope_id":"g1","updated_ts":"2026-01-01T00:00:00Z"}\n'
        '{"work_item_id":"wi2","owner_agent_id":"e2","scope_id":"g1","updated_ts":"2026-01-01T00:00:01Z"}\n',
        encoding="utf-8",
    )
    # Default: list
    out = get_entities(tmp_path)
    assert isinstance(out, list)
    # With status: paginated
    out2 = get_entities(tmp_path, status="active")
    assert isinstance(out2, dict)
    assert "items" in out2
    assert "next_cursor" in out2
    assert isinstance(out2["items"], list)


def test_get_groups_paginated_shape(tmp_path: Path) -> None:
    """get_groups with cursor returns { items, next_cursor }."""
    (tmp_path / "memory" / "materialized").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory" / "materialized" / "work_items.jsonl").write_text(
        '{"work_item_id":"wi1","scope_id":"g1","updated_ts":"2026-01-01T00:00:00Z"}\n',
        encoding="utf-8",
    )
    out = get_groups(tmp_path)
    assert isinstance(out, list)
    out2 = get_groups(tmp_path, cursor="x", limit=10)
    assert isinstance(out2, dict)
    assert "items" in out2
    assert "next_cursor" in out2


def test_get_work_items_paginated_shape(tmp_path: Path) -> None:
    """get_work_items with status or cursor returns { items, next_cursor }."""
    (tmp_path / "memory" / "materialized").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory" / "materialized" / "work_items.jsonl").write_text(
        '{"work_item_id":"wi1","scope_id":"g1","updated_ts":"2026-01-01T00:00:00Z","status":"active"}\n'
        '{"work_item_id":"wi2","scope_id":"g1","updated_ts":"2026-01-01T00:00:01Z","status":"blocked"}\n',
        encoding="utf-8",
    )
    out = get_work_items(tmp_path)
    assert isinstance(out, list)
    out2 = get_work_items(tmp_path, status="blocked")
    assert isinstance(out2, dict)
    assert "items" in out2
    assert "next_cursor" in out2


def test_get_activity_feed(tmp_path: Path) -> None:
    """get_activity_feed returns { items, next_cursor }."""
    (tmp_path / "memory" / "materialized").mkdir(parents=True, exist_ok=True)
    out = get_activity_feed(tmp_path)
    assert "items" in out
    assert "next_cursor" in out
    assert isinstance(out["items"], list)


def test_explain_block_not_found(tmp_path: Path) -> None:
    """explain_block with unknown id returns explanation with blocked=False."""
    (tmp_path / "memory" / "materialized").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory" / "materialized" / "work_items.jsonl").write_text("", encoding="utf-8")
    out = explain_block(tmp_path, work_item_id="nonexistent")
    assert out is not None
    assert out["ref_id"] == "nonexistent"
    assert out["blocked"] is False


def test_explain_block_blocked_work_item(tmp_path: Path) -> None:
    """explain_block for blocked work item returns gate and recommended_next_step."""
    (tmp_path / "memory" / "materialized").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory" / "materialized" / "work_items.jsonl").write_text(
        '{"work_item_id":"wi_blocked","scope_id":"g1","status":"blocked","updated_ts":"2026-01-01T00:00:00Z"}\n',
        encoding="utf-8",
    )
    out = explain_block(tmp_path, work_item_id="wi_blocked")
    assert out is not None
    assert out["blocked"] is True
    assert out["gate"] == "work_item_blocked"
    assert "recommended_next_step" in out


def test_explain_block_no_ref_returns_none(tmp_path: Path) -> None:
    """explain_block with no work_item_id or action_id returns None."""
    assert explain_block(tmp_path) is None
    assert explain_block(tmp_path, work_item_id=None, action_id=None) is None


def test_openapi_spec_loads() -> None:
    """OpenAPI v0.2 spec file exists and is valid YAML with expected paths."""
    import json
    spec_path = Path(__file__).resolve().parent.parent.parent / "docs" / "api" / "openapi_control_surface_v0_2.yaml"
    if not spec_path.exists():
        pytest.skip("docs/api not in repo layout")
    try:
        import yaml
    except ImportError:
        pytest.skip("PyYAML not installed")
    data = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    assert data.get("openapi", "").startswith("3.0")
    assert data.get("info", {}).get("version") == "0.2.0"
    paths = data.get("paths", {})
    assert "/entities" in paths
    assert "/work_items" in paths
    assert "/explain/block" in paths
    assert "/control/pause" in paths
    assert "/steering/goal" in paths
    assert "components" in data
    assert "schemas" in data["components"]
    assert "Error" in data["components"]["schemas"]
