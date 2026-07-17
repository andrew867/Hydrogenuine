from pathlib import Path

from hg_memory.context.context_graph_db import ContextGraphDatabase
from hg_memory.health_check import HealthCheck
from hg_memory.graph_pruner import GraphPruner


def test_context_graph_shared_db_get_entity_uses_shared_lookup(monkeypatch, tmp_path: Path):
    db = ContextGraphDatabase(str(tmp_path / "context_graph.db"))
    db._shared_gateway_db = True

    monkeypatch.setattr(
        "hg_memory.context.context_graph_db.get_context_entity",
        lambda entity_id: {"entity_id": entity_id, "entity_type": "decision"},
    )

    entity = db.get_entity("decision-1")

    assert entity is not None
    assert entity["entity_id"] == "decision-1"


def test_context_graph_shared_db_get_related_entities_uses_shared_lookup(monkeypatch, tmp_path: Path):
    db = ContextGraphDatabase(str(tmp_path / "context_graph.db"))
    db._shared_gateway_db = True

    monkeypatch.setattr(
        "hg_memory.context.context_graph_db.get_related_context_entities",
        lambda entity_id, relation_type=None, direction="both": [
            {
                "entity_id": "decision-2",
                "relation_type": relation_type,
                "direction": direction,
            }
        ],
    )

    related = db.get_related_entities("decision-1", relation_type="precedes", direction="from")

    assert len(related) == 1
    assert related[0]["entity_id"] == "decision-2"
    assert related[0]["relation_type"] == "precedes"


def test_health_check_shared_context_graph_counts_shared_tables(monkeypatch, tmp_path: Path):
    health = HealthCheck()
    db_path = tmp_path / "memory" / "context_graph.db"

    monkeypatch.setattr("hg_memory.health_check.use_shared_gateway_db", lambda path: True)
    monkeypatch.setattr(
        HealthCheck,
        "_shared_table_has_rows_or_exists",
        staticmethod(lambda conn, table: table in {"memory_context_entities", "memory_context_relations"}),
    )

    status = health._check_single_database(db_path, "context_graph")

    assert status["exists"] is True
    assert status["integrity"] is True
    assert status["table_count"] == 2


def test_graph_pruner_shared_prune_deletes_from_shared_tables(monkeypatch):
    pruner = GraphPruner()
    executed = []

    class FakeConn:
        def execute(self, sql, params=()):
            executed.append((sql, params))
            return self

        def fetchone(self):
            return None

    class FakeManager:
        def __enter__(self):
            return FakeConn()

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("hg_gateway.db.get_connection", lambda: FakeManager())

    stats = {"removed": 0, "archived": 0, "errors": 0}
    pruner._prune_shared_entities(["entity-1", "entity-2"], stats)

    assert stats["removed"] == 2
    assert any("memory_context_relations" in sql for sql, _ in executed)
    assert any("memory_context_entities" in sql for sql, _ in executed)
