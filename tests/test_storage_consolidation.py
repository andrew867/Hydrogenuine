from __future__ import annotations

import os
from pathlib import Path

from hg_core.wrappers.decision_context import record_decision
from hg_memory.agent.agent_memory_db import AgentMemoryDatabase
from hg_memory.agent.agent_memory_search import AgentMemorySearch
from hg_memory.agent.entity_graph_db import EntityGraphDatabase
from hg_overseer.overseer_core.observability import OverseerLogger
from operator_console.server.app.services import activity_service, entities_service


def _configure_workspace(monkeypatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "memory" / "gateway.sqlite3"
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    import hg_lib.config

    monkeypatch.setattr(hg_lib.config, "get_workspace_root", lambda: tmp_path)
    return db_path


def test_agent_memory_moves_into_gateway_db(monkeypatch, tmp_path: Path):
    _configure_workspace(monkeypatch, tmp_path)
    db_path = tmp_path / "memory" / "automation" / "automation-alpha" / "agent_memory.db"
    database = AgentMemoryDatabase(str(db_path))
    database.insert_document(
        file_path="2026-03-08.md",
        content="alpha decided to migrate storage to postgres",
        date="2026-03-08",
        language="en",
        source_type="daily_log",
        metadata={"agent_id": "alpha"},
    )

    assert not db_path.exists()
    search = AgentMemorySearch(database)
    results = search.search_agent_memory("postgres", limit=5)
    assert results
    assert results[0]["file_path"] == "2026-03-08.md"


def test_entity_graph_service_reads_shared_gateway_db(monkeypatch, tmp_path: Path):
    _configure_workspace(monkeypatch, tmp_path)
    db_path = tmp_path / "memory" / "automation" / "automation-alpha" / "agent_memory.db"
    graph = EntityGraphDatabase(str(db_path))
    entity_id = graph.upsert_entity("project", "postgres-cutover", "life/projects/postgres-cutover", "storage migration")
    graph.upsert_fact(
        entity_id=entity_id,
        fact="postgres cutover owns runtime storage migration",
        category="project",
        timestamp="2026-03-08T00:00:00Z",
        source="test",
    )

    monkeypatch.setattr(
        entities_service,
        "_get_registry",
        lambda: {"alpha": {"session_target": "automation-alpha", "job_id": "job-1", "platform": "test", "mode": "auto"}},
    )
    monkeypatch.setattr(entities_service, "_workspace_root", lambda: tmp_path)
    payload = entities_service.get_entity_graph("alpha")
    assert payload["entities"]
    assert payload["facts"]
    assert payload["entities"][0]["name"] == "postgres-cutover"


def test_decisions_and_overseer_history_use_gateway_db(monkeypatch, tmp_path: Path):
    _configure_workspace(monkeypatch, tmp_path)
    record_decision("alpha", "migrate storage", "sqlite is too slow", context="postgres cutover")

    decisions_path = tmp_path / "memory" / "automation" / "automation-alpha" / "decisions.json"
    assert not decisions_path.exists()

    monkeypatch.setattr(
        activity_service,
        "_get_registry",
        lambda: {"alpha": {"session_target": "automation-alpha"}},
    )
    monkeypatch.setattr(activity_service, "_workspace_root", lambda: tmp_path)
    decisions = activity_service.get_recent_decisions(limit=10)
    assert decisions
    assert decisions[0]["action"] == "migrate storage"

    logger = OverseerLogger()
    logger.log_cycle(
        {
            "agent_states": {"alpha": {"current_mode": "normal", "violations": []}},
            "budgets": {"chaos": {"remaining": 5}, "credibility": {"earned": 2}},
            "actions": [],
            "oscillations": [],
        }
    )

    assert not (tmp_path / "memory" / "overseer" / "timeseries.jsonl").exists()
    dashboard = activity_service.get_dashboard_data(hours=24)
    assert dashboard["timeseries"]
    assert dashboard["summary"]["timeseries_count_24h"] >= 1


def test_legacy_decision_file_is_ignored_by_default(monkeypatch, tmp_path: Path):
    _configure_workspace(monkeypatch, tmp_path)
    agent_dir = tmp_path / "memory" / "automation" / "automation-alpha"
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "decisions.json").write_text(
        '{"decisions":[{"timestamp":"2026-03-08T00:00:00Z","action":"legacy-only","rationale":"old path"}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        activity_service,
        "_get_registry",
        lambda: {"alpha": {"session_target": "automation-alpha"}},
    )
    monkeypatch.setattr(activity_service, "_workspace_root", lambda: tmp_path)
    assert activity_service.get_recent_decisions(limit=10) == []
