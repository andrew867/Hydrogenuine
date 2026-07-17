from __future__ import annotations

from types import SimpleNamespace


def test_search_agent_memory_is_db_only_when_database_missing(tmp_path, monkeypatch):
    from hg_memory.agent.agent_task_integration import search_agent_memory

    workspace_root = tmp_path
    agent_dir = workspace_root / "memory" / "automation" / "automation-demo-agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "2026-03-22.md").write_text("needle in the file fallback", encoding="utf-8")

    fake_config = SimpleNamespace(
        workspace_root=workspace_root,
        get_agent_memory_db_path=lambda agent_id: workspace_root / "memory" / "agent_memory" / f"{agent_id}.sqlite3",
    )
    monkeypatch.setattr("hg_memory.agent.agent_task_integration.get_config", lambda: fake_config)

    results = search_agent_memory("demo-agent", "needle", fallback_to_files=True)

    assert results == []
