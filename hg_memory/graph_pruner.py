#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Graph pruning for memory engine.

Removes stale entities and archives old context to prevent graph bloat.
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from hg_memory.config import get_config
from hg_memory.context.context_graph_db import ContextGraphDatabase
from hg_memory.error_handling import atomic_write, backup_database
from hg_gateway.shared_storage import use_shared_gateway_db


class GraphPruner:
    """Prune and archive old graph data"""

    def __init__(self):
        """Initialize graph pruner"""
        self.config = get_config()

    def prune_stale_entities(
        self,
        days_old: int = 90,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Remove stale entities older than threshold.

        Args:
            days_old: Remove entities older than this many days
            dry_run: If True, only report what would be removed

        Returns:
            Dictionary with pruning statistics
        """
        context_db_path = self.config.get_context_graph_db_path()
        if not context_db_path.exists():
            return {"removed": 0, "archived": 0, "errors": 0}

        cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()

        stats = {"removed": 0, "archived": 0, "errors": 0}

        try:
            context_db = ContextGraphDatabase(str(context_db_path))

            old_entities = self._fetch_old_entities(context_db, cutoff_date)

            if dry_run:
                stats["removed"] = len(old_entities)
                return stats

            if use_shared_gateway_db(context_db_path):
                self._prune_shared_entities([row[0] for row in old_entities], stats)
                return stats

            backup_database(context_db_path)

            def remove_entities(conn):
                for entity_id, entity_type, timestamp in old_entities:
                    conn.execute("DELETE FROM context_relations WHERE from_entity_id = ? OR to_entity_id = ?", (entity_id, entity_id))
                    conn.execute("DELETE FROM context_fts WHERE entity_id = ?", (entity_id,))
                    conn.execute("DELETE FROM context_entities WHERE entity_id = ?", (entity_id,))
                    stats["removed"] += 1

            if atomic_write(context_db_path, remove_entities):
                return stats
            stats["errors"] = 1
            return stats
        except Exception as e:
            print(f"Error pruning stale entities: {e}")
            stats["errors"] = 1
            return stats

    def archive_old_context(
        self,
        days_old: int = 180,
        archive_db_path: Optional[Path] = None,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Archive old context to separate database.

        Args:
            days_old: Archive context older than this many days
            archive_db_path: Path to archive database (defaults to context_graph_archive.db)
            dry_run: If True, only report what would be archived

        Returns:
            Dictionary with archiving statistics
        """
        context_db_path = self.config.get_context_graph_db_path()
        if not context_db_path.exists():
            return {"archived": 0, "errors": 0}

        if archive_db_path is None:
            archive_db_path = context_db_path.parent / "context_graph_archive.db"

        cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()

        stats = {"archived": 0, "errors": 0}

        try:
            context_db = ContextGraphDatabase(str(context_db_path))

            old_entity_ids = [row[0] for row in self._fetch_old_entities(context_db, cutoff_date)]

            if dry_run:
                stats["archived"] = len(old_entity_ids)
                return stats

            # Create archive database if needed
            archive_db = ContextGraphDatabase(str(archive_db_path))

            # Copy entities to archive (content may be in properties; get_entity does not return content from FTS)
            for entity_id in old_entity_ids:
                entity = context_db.get_entity(entity_id)
                if entity:
                    content = entity.get("content") or entity.get("properties", {}).get("content", "")
                    archive_db.insert_entity(
                        entity_id=entity_id,
                        entity_type=entity["entity_type"],
                        content=content,
                        agent_id=entity.get("agent_id"),
                        timestamp=entity["timestamp"],
                        properties=entity.get("properties", {})
                    )
                    stats["archived"] += 1

            # Remove from main database (after archiving)
            self.prune_stale_entities(days_old=days_old, dry_run=False)

            return stats
        except Exception as e:
            print(f"Error archiving old context: {e}")
            stats["errors"] = 1
            return stats

    def maintain_graph_size(
        self,
        max_entities: int = 10000,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Maintain graph size by removing oldest entities if over limit.

        Args:
            max_entities: Maximum number of entities to keep
            dry_run: If True, only report what would be removed

        Returns:
            Dictionary with maintenance statistics
        """
        context_db_path = self.config.get_context_graph_db_path()
        if not context_db_path.exists():
            return {"removed": 0, "errors": 0}

        stats = {"removed": 0, "errors": 0}

        try:
            context_db = ContextGraphDatabase(str(context_db_path))
            conn = context_db._get_connection()
            table_name = "memory_context_entities" if use_shared_gateway_db(context_db_path) else "context_entities"

            cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            current_count = cursor.fetchone()[0]

            if current_count <= max_entities:
                conn.close()
                return stats

            # Remove oldest entities
            to_remove = current_count - max_entities

            cursor = conn.execute(f"""
                SELECT entity_id FROM {table_name}
                ORDER BY timestamp ASC
                LIMIT ?
            """, (to_remove,))

            entity_ids_to_remove = [row[0] for row in cursor.fetchall()]
            conn.close()

            if dry_run:
                stats["removed"] = len(entity_ids_to_remove)
                return stats

            if use_shared_gateway_db(context_db_path):
                self._prune_shared_entities(entity_ids_to_remove, stats)
                return stats

            def remove_oldest(conn):
                for entity_id in entity_ids_to_remove:
                    conn.execute("DELETE FROM context_relations WHERE from_entity_id = ? OR to_entity_id = ?", (entity_id, entity_id))
                    conn.execute("DELETE FROM context_fts WHERE entity_id = ?", (entity_id,))
                    conn.execute("DELETE FROM context_entities WHERE entity_id = ?", (entity_id,))
                    stats["removed"] += 1

            backup_database(context_db_path)
            if atomic_write(context_db_path, remove_oldest):
                return stats
            stats["errors"] = 1
            return stats
        except Exception as e:
            print(f"Error maintaining graph size: {e}")
            stats["errors"] = 1
            return stats

    @staticmethod
    def _fetch_old_entities(context_db: ContextGraphDatabase, cutoff_date: str):
        conn = context_db._get_connection()
        table_name = "memory_context_entities" if context_db._shared_gateway_db else "context_entities"
        try:
            cursor = conn.execute(
                f"""
                SELECT entity_id, entity_type, timestamp
                FROM {table_name}
                WHERE timestamp < ?
                """,
                (cutoff_date,),
            )
            return cursor.fetchall()
        finally:
            conn.close()

    @staticmethod
    def _prune_shared_entities(entity_ids: List[str], stats: Dict[str, int]) -> None:
        from hg_gateway.db import get_connection

        if not entity_ids:
            return
        with get_connection() as conn:
            for entity_id in entity_ids:
                conn.execute(
                    "DELETE FROM memory_context_relations WHERE from_entity_id = ? OR to_entity_id = ?",
                    (entity_id, entity_id),
                )
                conn.execute(
                    "DELETE FROM memory_context_entities WHERE entity_id = ?",
                    (entity_id,),
                )
                stats["removed"] += 1


def prune_graph(days_old: int = 90, dry_run: bool = False) -> Dict[str, int]:
    """
    Convenience function for graph pruning.

    Args:
        days_old: Remove entities older than this many days
        dry_run: If True, only report what would be removed

    Returns:
        Dictionary with pruning statistics
    """
    pruner = GraphPruner()
    return pruner.prune_stale_entities(days_old=days_old, dry_run=dry_run)
