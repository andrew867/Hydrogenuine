import os
import sqlite3

from operator_console.server.app.services.knowledge_service import get_categories, get_stats, search


def test_knowledge_service_reads_shared_gateway_store(tmp_path):
    gateway_db = tmp_path / "gateway.sqlite3"
    prev_backend = os.environ.get("HG_GATEWAY_STORE")
    prev_gateway_db = os.environ.get("HG_GATEWAY_DB_PATH")
    try:
        os.environ["HG_GATEWAY_STORE"] = "sqlite"
        os.environ["HG_GATEWAY_DB_PATH"] = str(gateway_db)
        from hg_gateway.db import get_connection

        with get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO knowledge_documents
                (file_path, title, category, language, content, word_count, last_indexed, file_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "knowledge/demo/postgres.md",
                    "Postgres Demo",
                    "database",
                    "en",
                    "The operator console should read this from the shared database.",
                    11,
                    "2026-03-08T12:00:00Z",
                    "hash-demo",
                ),
            )
        stats = get_stats()
        assert stats is not None
        assert stats["total_documents"] >= 1
        categories = get_categories()
        assert any(row["category"] == "database" for row in categories)
        results = search("shared database", limit=5)
        assert any(row["title"] == "Postgres Demo" for row in results)
    finally:
        if prev_backend is not None:
            os.environ["HG_GATEWAY_STORE"] = prev_backend
        else:
            os.environ.pop("HG_GATEWAY_STORE", None)
        if prev_gateway_db is not None:
            os.environ["HG_GATEWAY_DB_PATH"] = prev_gateway_db
        else:
            os.environ.pop("HG_GATEWAY_DB_PATH", None)


def test_knowledge_service_ignores_legacy_sqlite_index_when_gateway_is_empty(tmp_path, monkeypatch):
    legacy_db = tmp_path / "knowledge_index.db"
    gateway_db = tmp_path / "gateway.sqlite3"
    conn = sqlite3.connect(str(legacy_db))
    conn.execute(
        "CREATE TABLE knowledge_metadata (file_path TEXT PRIMARY KEY, title TEXT, category TEXT, language TEXT, word_count INTEGER, last_indexed TEXT, file_hash TEXT)"
    )
    conn.execute(
        "CREATE TABLE knowledge_fts (content TEXT, title TEXT, category TEXT, file_path TEXT, language TEXT, last_updated TEXT, content_normalized TEXT)"
    )
    conn.execute(
        "INSERT INTO knowledge_metadata (file_path, title, category, language, word_count, last_indexed, file_hash) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("knowledge/boot/doc.md", "Bootstrapped", "migration", "en", 5, "2026-03-08T12:00:00Z", "hash1"),
    )
    conn.execute(
        "INSERT INTO knowledge_fts (content, title, category, file_path, language, last_updated, content_normalized) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("Legacy sqlite content mirrored into gateway.", "Bootstrapped", "migration", "knowledge/boot/doc.md", "en", "2026-03-08T12:00:00Z", "Legacy sqlite content mirrored into gateway."),
    )
    conn.commit()
    conn.close()

    prev_backend = os.environ.get("HG_GATEWAY_STORE")
    prev_gateway_db = os.environ.get("HG_GATEWAY_DB_PATH")
    try:
        os.environ["HG_GATEWAY_STORE"] = "sqlite"
        os.environ["HG_GATEWAY_DB_PATH"] = str(gateway_db)
        monkeypatch.setattr("operator_console.server.app.services.knowledge_service._db_path", lambda: legacy_db)
        stats = get_stats()
        assert stats is None
        results = search("mirrored into gateway", limit=5)
        assert results == []
    finally:
        if prev_backend is not None:
            os.environ["HG_GATEWAY_STORE"] = prev_backend
        else:
            os.environ.pop("HG_GATEWAY_STORE", None)
        if prev_gateway_db is not None:
            os.environ["HG_GATEWAY_DB_PATH"] = prev_gateway_db
        else:
            os.environ.pop("HG_GATEWAY_DB_PATH", None)
