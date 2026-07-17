#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Per-agent entity/fact knowledge graph (PARA-style) in SQLite.

Uses the same DB file as agent memory (agent_memory.db). Tables: entity, fact,
FTS5 entity_facts_fts for full-text search over facts.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from hg_memory.shared import DatabaseBase
from hg_gateway.shared_storage import (
    delete_memory_facts_for_entity,
    get_memory_entity_summary,
    get_recent_memory_entities,
    search_memory_facts,
    upsert_memory_entity,
    upsert_memory_fact,
    use_shared_gateway_db,
)


class EntityGraphDatabase(DatabaseBase):
    """
    Entity and fact tables plus FTS5 for "what do I know about X".
    Co-located with agent_memory.db (same path).
    """

    def __init__(self, database_path: str):
        """
        Args:
            database_path: Path to SQLite DB (e.g. agent_memory.db).
        """
        super().__init__(database_path)

    def _create_schema(self) -> None:
        if self._shared_gateway_db:
            return
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    summary_excerpt TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(type, name)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fact (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id INTEGER NOT NULL,
                    fact TEXT NOT NULL,
                    category TEXT,
                    timestamp TEXT,
                    source TEXT,
                    status TEXT,
                    related_entities_json TEXT,
                    last_accessed_at TEXT,
                    FOREIGN KEY (entity_id) REFERENCES entity(id)
                )
            """)
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS entity_facts_fts USING fts5(
                    fact,
                    entity_id,
                    entity_name,
                    category,
                    tokenize='unicode61'
                )
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS fact_ai AFTER INSERT ON fact BEGIN
                    INSERT INTO entity_facts_fts(rowid, fact, entity_id, entity_name, category)
                    VALUES (new.id, new.fact, new.entity_id,
                        (SELECT name FROM entity WHERE id = new.entity_id),
                        COALESCE(new.category, ''));
                END
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS fact_ad AFTER DELETE ON fact BEGIN
                    INSERT INTO entity_facts_fts(entity_facts_fts, rowid, fact, entity_id, entity_name, category)
                    VALUES ('delete', old.id, old.fact, old.entity_id,
                        (SELECT name FROM entity WHERE id = old.entity_id),
                        COALESCE(old.category, ''));
                END
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS fact_au AFTER UPDATE ON fact BEGIN
                    INSERT INTO entity_facts_fts(entity_facts_fts, rowid, fact, entity_id, entity_name, category)
                    VALUES ('delete', old.id, old.fact, old.entity_id,
                        (SELECT name FROM entity WHERE id = old.entity_id),
                        COALESCE(old.category, ''));
                    INSERT INTO entity_facts_fts(rowid, fact, entity_id, entity_name, category)
                    VALUES (new.id, new.fact, new.entity_id,
                        (SELECT name FROM entity WHERE id = new.entity_id),
                        COALESCE(new.category, ''));
                END
            """)
            conn.commit()
        finally:
            conn.close()

    def upsert_entity(
        self,
        type: str,
        name: str,
        path: str,
        summary_excerpt: Optional[str] = None,
    ) -> int:
        if self._shared_gateway_db:
            return upsert_memory_entity(self._shared_agent_id() or "", type, name, path, summary_excerpt)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT id FROM entity WHERE type = ? AND name = ?",
                (type, name),
            )
            row = cursor.fetchone()
            if row:
                conn.execute(
                    "UPDATE entity SET path = ?, summary_excerpt = ?, updated_at = ? WHERE id = ?",
                    (path, summary_excerpt or "", now, row[0]),
                )
                conn.commit()
                return row[0]
            cursor = conn.execute(
                """INSERT INTO entity (type, name, path, summary_excerpt, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (type, name, path, summary_excerpt or "", now, now),
            )
            conn.commit()
            return cursor.lastrowid or 0
        finally:
            conn.close()

    def upsert_fact(
        self,
        entity_id: int,
        fact: str,
        category: Optional[str] = None,
        timestamp: Optional[str] = None,
        source: Optional[str] = None,
        status: Optional[str] = None,
        related_entities_json: Optional[str] = None,
    ) -> int:
        if self._shared_gateway_db:
            return upsert_memory_fact(
                agent_id=self._shared_agent_id() or "",
                entity_id=entity_id,
                fact=fact,
                category=category,
                timestamp=timestamp,
                source=source,
                status=status,
                related_entities_json=related_entities_json,
            )
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn = self._get_connection()
        try:
            conn.execute(
                """INSERT INTO fact (entity_id, fact, category, timestamp, source, status, related_entities_json, last_accessed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entity_id,
                    fact,
                    category or "",
                    timestamp or now,
                    source or "",
                    status or "active",
                    related_entities_json or "[]",
                    now,
                ),
            )
            conn.commit()
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        finally:
            conn.close()

    def delete_facts_for_entity(self, entity_id: int) -> None:
        if self._shared_gateway_db:
            delete_memory_facts_for_entity(self._shared_agent_id() or "", entity_id)
            return
        conn = self._get_connection()
        try:
            try:
                conn.execute("DELETE FROM fact WHERE entity_id = ?", (entity_id,))
                conn.commit()
            except sqlite3.OperationalError:
                # Some legacy DBs can throw generic SQL logic errors via FTS triggers.
                # Fallback: temporarily drop triggers, delete, rebuild FTS index, recreate triggers.
                conn.rollback()
                conn.execute("DROP TRIGGER IF EXISTS fact_ai")
                conn.execute("DROP TRIGGER IF EXISTS fact_ad")
                conn.execute("DROP TRIGGER IF EXISTS fact_au")
                conn.execute("DELETE FROM fact WHERE entity_id = ?", (entity_id,))
                conn.execute("DELETE FROM entity_facts_fts")
                conn.execute(
                    """INSERT INTO entity_facts_fts(rowid, fact, entity_id, entity_name, category)
                       SELECT f.id, f.fact, f.entity_id, e.name, COALESCE(f.category, '')
                       FROM fact f
                       JOIN entity e ON e.id = f.entity_id"""
                )
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS fact_ai AFTER INSERT ON fact BEGIN
                        INSERT INTO entity_facts_fts(rowid, fact, entity_id, entity_name, category)
                        VALUES (new.id, new.fact, new.entity_id,
                            (SELECT name FROM entity WHERE id = new.entity_id),
                            COALESCE(new.category, ''));
                    END
                """)
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS fact_ad AFTER DELETE ON fact BEGIN
                        INSERT INTO entity_facts_fts(entity_facts_fts, rowid, fact, entity_id, entity_name, category)
                        VALUES ('delete', old.id, old.fact, old.entity_id,
                            (SELECT name FROM entity WHERE id = old.entity_id),
                            COALESCE(old.category, ''));
                    END
                """)
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS fact_au AFTER UPDATE ON fact BEGIN
                        INSERT INTO entity_facts_fts(entity_facts_fts, rowid, fact, entity_id, entity_name, category)
                        VALUES ('delete', old.id, old.fact, old.entity_id,
                            (SELECT name FROM entity WHERE id = old.entity_id),
                            COALESCE(old.category, ''));
                        INSERT INTO entity_facts_fts(rowid, fact, entity_id, entity_name, category)
                        VALUES (new.id, new.fact, new.entity_id,
                            (SELECT name FROM entity WHERE id = new.entity_id),
                            COALESCE(new.category, ''));
                    END
                """)
                conn.commit()
        finally:
            conn.close()

    def search_entity_facts(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        if self._shared_gateway_db:
            return search_memory_facts(self._shared_agent_id() or "", query, limit)
        q = query.replace('"', '""')
        fts_query = f'"{q}"'
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """SELECT f.id, f.entity_id, f.fact, f.category, f.timestamp, f.source, e.name as entity_name
                   FROM entity_facts_fts efs
                   JOIN fact f ON f.id = efs.rowid
                   JOIN entity e ON e.id = f.entity_id
                   WHERE entity_facts_fts MATCH ?
                   LIMIT ?""",
                (fts_query, limit),
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "entity_id": r[1],
                    "fact": r[2],
                    "category": r[3],
                    "timestamp": r[4],
                    "source": r[5],
                    "entity_name": r[6],
                }
                for r in rows
            ]
        except sqlite3.OperationalError:
            return []
        finally:
            conn.close()

    def get_entity_summary(self, entity_name: str) -> Optional[str]:
        if self._shared_gateway_db:
            return get_memory_entity_summary(self._shared_agent_id() or "", entity_name)
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT summary_excerpt FROM entity WHERE name = ? LIMIT 1",
                (entity_name,),
            )
            row = cursor.fetchone()
            return row[0] if row and row[0] else None
        finally:
            conn.close()

    def get_recent_entities(self, limit: int = 5) -> List[Dict[str, Any]]:
        if self._shared_gateway_db:
            return get_recent_memory_entities(self._shared_agent_id() or "", limit)
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """SELECT e.id, e.type, e.name, e.summary_excerpt, e.updated_at
                   FROM entity e
                   LEFT JOIN fact f ON f.entity_id = e.id
                   GROUP BY e.id
                   ORDER BY MAX(COALESCE(f.last_accessed_at, e.updated_at)) DESC
                   LIMIT ?""",
                (limit,),
            )
            return [
                {
                    "id": r[0],
                    "type": r[1],
                    "name": r[2],
                    "summary_excerpt": r[3] or "",
                    "updated_at": r[4],
                }
                for r in cursor.fetchall()
            ]
        finally:
            conn.close()


def get_entity_graph_db_path(workspace_root: Path, agent_id: str) -> Path:
    """Path to agent_memory.db (entity graph lives in same DB)."""
    return (
        workspace_root
        / "memory"
        / "automation"
        / f"automation-{agent_id}"
        / "agent_memory.db"
    )


def search_entity_facts(
    workspace_root: Path,
    agent_id: str,
    query: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    path = get_entity_graph_db_path(workspace_root, agent_id)
    if not path.exists() and not use_shared_gateway_db(path):
        return []
    db = EntityGraphDatabase(str(path))
    return db.search_entity_facts(query, limit=limit)


def get_entity_summary(
    workspace_root: Path,
    agent_id: str,
    entity_name: str,
) -> Optional[str]:
    path = get_entity_graph_db_path(workspace_root, agent_id)
    if not path.exists() and not use_shared_gateway_db(path):
        return None
    db = EntityGraphDatabase(str(path))
    return db.get_entity_summary(entity_name)


def get_recent_entities(
    workspace_root: Path,
    agent_id: str,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    path = get_entity_graph_db_path(workspace_root, agent_id)
    if not path.exists() and not use_shared_gateway_db(path):
        return []
    db = EntityGraphDatabase(str(path))
    return db.get_recent_entities(limit=limit)
