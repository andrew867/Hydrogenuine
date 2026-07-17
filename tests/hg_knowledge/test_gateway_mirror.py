import os

from hg_knowledge.database import KnowledgeDatabase


def test_knowledge_database_mirrors_into_gateway_store(tmp_path):
    legacy_db = tmp_path / "knowledge_index.db"
    gateway_db = tmp_path / "gateway.sqlite3"
    prev_backend = os.environ.get("HG_GATEWAY_STORE")
    prev_gateway_db = os.environ.get("HG_GATEWAY_DB_PATH")
    try:
        os.environ["HG_GATEWAY_STORE"] = "sqlite"
        os.environ["HG_GATEWAY_DB_PATH"] = str(gateway_db)
        db = KnowledgeDatabase(str(legacy_db))
        db.insert_document(
            file_path="knowledge/test/doc.md",
            title="Gateway Mirrored Doc",
            content="Postgres migration and database storage convergence.",
            category="engineering",
            language="en",
        )
        from hg_gateway.db import get_connection

        with get_connection() as conn:
            row = conn.execute(
                "SELECT title, category, content FROM knowledge_documents WHERE file_path = ?",
                ("knowledge/test/doc.md",),
            ).fetchone()
        assert row is not None
        assert row["title"] == "Gateway Mirrored Doc"
        assert row["category"] == "engineering"
    finally:
        if prev_backend is not None:
            os.environ["HG_GATEWAY_STORE"] = prev_backend
        else:
            os.environ.pop("HG_GATEWAY_STORE", None)
        if prev_gateway_db is not None:
            os.environ["HG_GATEWAY_DB_PATH"] = prev_gateway_db
        else:
            os.environ.pop("HG_GATEWAY_DB_PATH", None)
