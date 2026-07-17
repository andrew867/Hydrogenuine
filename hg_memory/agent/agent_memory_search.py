#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent memory search interface.

Provides full-text search across agent memory with multilingual support.
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Optional, Any

from hg_lib.language_detector import detect_language

from hg_memory.agent.agent_memory_db import AgentMemoryDatabase
from hg_gateway.shared_storage import search_agent_memory_documents, use_shared_gateway_db


class AgentMemorySearch:
    """Search interface for agent memory"""

    def __init__(self, database: AgentMemoryDatabase):
        """
        Initialize search interface.

        Args:
            database: AgentMemoryDatabase instance
        """
        self.database = database

    def search_agent_memory(
        self,
        query: str,
        language: Optional[str] = None,
        limit: int = 10,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        source_type: Optional[str] = None,
        include_metadata: bool = True,
    ) -> List[Dict]:
        """
        Search agent memory.

        Args:
            query: Search query
            language: Optional language code (auto-detected if None)
            limit: Maximum number of results
            date_start: Optional start date (YYYY-MM-DD)
            date_end: Optional end date (YYYY-MM-DD)
            source_type: Optional source type filter (e.g., "daily_log", "posts", "decisions")
            include_metadata: Whether to perform per-result metadata lookups

        Returns:
            List of search results (dicts with file_path, excerpt, timestamp, etc.)
        """
        if language is None:
            language = detect_language(query)

        # Build FTS5 query
        fts5_query = self._build_fts5_query(query)

        # Build WHERE clause for filters
        where_clauses = []
        params = [fts5_query]

        if date_start:
            where_clauses.append("date >= ?")
            params.append(date_start)

        if date_end:
            where_clauses.append("date <= ?")
            params.append(date_end)

        if source_type:
            # Need to join with metadata table to filter by source_type
            where_clauses.append("source_type = ?")
            params.append(source_type)

        where_sql = " AND " + " AND ".join(where_clauses) if where_clauses else ""

        if self.database._shared_gateway_db:
            results = search_agent_memory_documents(
                self.database._shared_agent_id() or "",
                query,
                limit=limit,
                date_start=date_start,
                date_end=date_end,
                source_type=source_type,
            )
            if not include_metadata:
                for result in results:
                    result.pop("metadata", None)
            return results
        conn = self.database._get_connection()
        try:
            # Try bm25() first, fallback to simple match if not available
            try:
                if source_type:
                    # Join with metadata table for source_type filter
                    cursor = conn.execute(
                        f"""
                        SELECT 
                            am.source_file,
                            am.date,
                            am.language,
                            snippet(agent_memory_fts, 2, '<b>', '</b>', '...', 32) as snippet,
                            bm25(agent_memory_fts) as rank,
                            amd.source_type
                        FROM agent_memory_fts am
                        JOIN agent_memory_metadata amd ON am.source_file = amd.file_path
                        WHERE agent_memory_fts MATCH ?{where_sql}
                        ORDER BY rank
                        LIMIT ?
                    """,
                        params + [limit],
                    )
                else:
                    cursor = conn.execute(
                        f"""
                        SELECT 
                            source_file,
                            date,
                            language,
                            snippet(agent_memory_fts, 2, '<b>', '</b>', '...', 32) as snippet,
                            bm25(agent_memory_fts) as rank
                        FROM agent_memory_fts
                        WHERE agent_memory_fts MATCH ?{where_sql}
                        ORDER BY rank
                        LIMIT ?
                    """,
                        params + [limit],
                    )
            except sqlite3.OperationalError:
                # bm25() not available, use simple search
                if source_type:
                    cursor = conn.execute(
                        f"""
                        SELECT 
                            am.source_file,
                            am.date,
                            am.language,
                            snippet(agent_memory_fts, 2, '<b>', '</b>', '...', 32) as snippet,
                            1.0 as rank,
                            amd.source_type
                        FROM agent_memory_fts am
                        JOIN agent_memory_metadata amd ON am.source_file = amd.file_path
                        WHERE agent_memory_fts MATCH ?{where_sql}
                        LIMIT ?
                    """,
                        params + [limit],
                    )
                else:
                    cursor = conn.execute(
                        f"""
                        SELECT 
                            source_file,
                            date,
                            language,
                            snippet(agent_memory_fts, 2, '<b>', '</b>', '...', 32) as snippet,
                            1.0 as rank
                        FROM agent_memory_fts
                        WHERE agent_memory_fts MATCH ?{where_sql}
                        LIMIT ?
                    """,
                        params + [limit],
                    )

            results = []
            for row in cursor.fetchall():
                if source_type:
                    result = {
                        "file_path": row[0],
                        "date": row[1],
                        "language": row[2],
                        "snippet": row[3],
                        "rank": row[4],
                        "source_type": row[5],
                    }
                else:
                    result = {
                        "file_path": row[0],
                        "date": row[1],
                        "language": row[2],
                        "snippet": row[3],
                        "rank": row[4],
                    }

                if include_metadata:
                    metadata = self.database.get_file_metadata(result["file_path"])
                    if metadata:
                        result["metadata"] = metadata

                results.append(result)

            return results
        finally:
            conn.close()

    def _build_fts5_query(self, query: str) -> str:
        """
        Build FTS5 query string from user query.

        Args:
            query: User search query

        Returns:
            FTS5 query string
        """
        # Escape special FTS5 characters
        query = query.replace('"', '""')
        return f'"{query}"'

    def get_recent_snippets(
        self,
        days: int = 7,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get recent FTS snippets for wake context (date-bounded, no semantic query).
        """
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        date_start = start.strftime("%Y-%m-%d")
        date_end = end.strftime("%Y-%m-%d")
        results = self.search_agent_memory(
            query="the",
            date_start=date_start,
            date_end=date_end,
            limit=limit,
        )
        return [
            {
                "snippet": r.get("snippet", ""),
                "date": r.get("date"),
                "file_path": r.get("file_path"),
            }
            for r in results
        ]


def get_wake_fts_snippets(
    workspace_root: Path,
    agent_id: str,
    max_snippets: int = 5,
    days: int = 7,
) -> List[Dict[str, Any]]:
    """
    Get FTS snippets for wake context. Used by session_manager.load_compacted_memory.
    Sets config.workspace_root so the correct agent_memory.db is used.
    """
    from hg_memory.config import get_config

    config = get_config()
    orig_workspace = config.workspace_root
    try:
        config.workspace_root = Path(workspace_root).resolve()
        db_path = config.get_agent_memory_db_path(agent_id)
        if not db_path.exists() and not use_shared_gateway_db(db_path):
            return []
        database = AgentMemoryDatabase(str(db_path))
        search = AgentMemorySearch(database)
        return search.get_recent_snippets(days=days, limit=max_snippets)
    finally:
        config.workspace_root = orig_workspace
