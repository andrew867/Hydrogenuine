import sqlite3
from pathlib import Path

from hg_gateway.shared_storage import append_agent_decision, put_operational_state
from hg_memory.agent.entity_graph_db import EntityGraphDatabase
from hg_memory.agent.entity_graph_indexer import index_session_memory


def test_index_session_memory_populates_entity_graph(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "memory" / "gateway.sqlite3"))
    agent_dir = tmp_path / 'memory' / 'automation' / 'automation-test-agent'
    agent_dir.mkdir(parents=True)

    put_operational_state(
        "automation:session_memory:automation-test-agent",
        {
            "context": {"recent_activity": "posted update", "topics": ["dag", "cutover"]},
            "recent_activity": ["posted update", "reviewed cutover plan"],
            "posts": [
                {
                    "title": "Cutover update",
                    "content": "Completed the postgres migration check",
                    "timestamp": "2026-02-25T00:00:00Z",
                }
            ],
        },
    )
    append_agent_decision(
        decision_id="test-decision-1",
        agent_id="test-agent",
        timestamp="2026-02-25T00:00:00Z",
        action="migrate workflow",
        rationale="improve visibility",
        alternatives=[],
        tradeoffs=None,
        context=None,
        outcome=None,
    )
    (agent_dir / '2026-02-25.md').write_text('did migration checks\nverified insight panel', encoding='utf-8')

    db_path = agent_dir / 'agent_memory.db'
    db = EntityGraphDatabase(str(db_path))

    result = index_session_memory(agent_dir, db)
    assert result['errors'] == 0
    assert result['indexed'] > 0

    con = sqlite3.connect(db_path)
    try:
      entity_count = con.execute('SELECT COUNT(*) FROM entity').fetchone()[0]
      fact_count = con.execute('SELECT COUNT(*) FROM fact').fetchone()[0]
      names = {r[0] for r in con.execute('SELECT name FROM entity').fetchall()}
    finally:
      con.close()

    assert entity_count >= 2
    assert fact_count >= 2
    assert 'session_memory' in names
    assert 'activity' in names
    assert 'decisions' in names
