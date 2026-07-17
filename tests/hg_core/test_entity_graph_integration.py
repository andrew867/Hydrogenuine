"""Integration tests for entity graph (life/ indexer and search)."""

import json
from pathlib import Path

import pytest

from hg_memory.agent.entity_graph_db import (
    EntityGraphDatabase,
    search_entity_facts,
    get_recent_entities,
    get_entity_graph_db_path,
)
from hg_memory.agent.entity_graph_indexer import run_entity_graph_indexer


class TestEntityGraphIntegration:
    """Test life/ indexer and search_entity_facts."""

    def test_life_indexer_populates_db_and_search_returns_results(self, tmp_path):
        # Create life/areas/people/foo with summary.md and items.json
        agent_id = "entity-test-agent"
        life_people = tmp_path / "memory" / "automation" / f"automation-{agent_id}" / "life" / "areas" / "people"
        life_people.mkdir(parents=True)
        foo_dir = life_people / "foo"
        foo_dir.mkdir()
        (foo_dir / "summary.md").write_text("Foo is a test person.", encoding="utf-8")
        (foo_dir / "items.json").write_text(
            json.dumps([
                {"fact": "Foo works on the project.", "category": "work", "source": "test"},
            ]),
            encoding="utf-8",
        )
        # Run indexer (uses get_config() which may use default workspace; we need to pass tmp_path)
        from hg_memory.config import get_config
        orig = get_config().workspace_root
        try:
            get_config().workspace_root = tmp_path
            result = run_entity_graph_indexer(agent_id, workspace_root=tmp_path)
        finally:
            get_config().workspace_root = orig
        assert result.get("errors", 0) >= 0
        # DB should exist and have entity + facts
        db_path = get_entity_graph_db_path(tmp_path, agent_id)
        assert db_path.exists()
        results = search_entity_facts(tmp_path, agent_id, "project", limit=5)
        assert len(results) >= 1
        assert any("project" in (r.get("fact") or "") for r in results)
        recent = get_recent_entities(tmp_path, agent_id, limit=5)
        assert len(recent) >= 1
        assert any(e.get("name") == "foo" for e in recent)
