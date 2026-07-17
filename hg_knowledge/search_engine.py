#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Search engine for knowledge files.

Provides multi-language search using SQLite FTS5.
"""

import sqlite3
from typing import List, Dict, Optional

from .database import KnowledgeDatabase
from .query_processor import QueryProcessor


class SearchResult:
    """Search result with metadata"""

    def __init__(self, row: tuple, columns: List[str]):
        """
        Initialize from database row.

        Args:
            row: Database row tuple
            columns: Column names
        """
        self._data = dict(zip(columns, row))

    def __getitem__(self, key: str):
        """Get result field"""
        return self._data.get(key)

    def __contains__(self, key: str) -> bool:
        """Check if field exists"""
        return key in self._data

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return self._data.copy()


class SearchEngine:
    """Multi-language search engine using SQLite FTS5"""

    def __init__(self, database: KnowledgeDatabase):
        """
        Initialize search engine.

        Args:
            database: KnowledgeDatabase instance
        """
        self.database = database
        self.query_processor = QueryProcessor()

    def search(
        self,
        query: str,
        language: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Search knowledge base.

        Args:
            query: Search query
            language: Optional language code (auto-detected if None)
            limit: Maximum number of results

        Returns:
            List of search results (dicts with file_path, title, snippet, etc.)
        """
        if language is None:
            language = self.query_processor.detect_query_language(query)

        # Build FTS5 query
        fts5_query = self.query_processor.build_fts5_query(query, language)

        # Execute search
        conn = sqlite3.connect(str(self.database.database_path))
        conn.execute("PRAGMA encoding = 'UTF-8'")

        try:
            # FTS5 search with ranking
            # Try bm25() first, fallback to simple match if not available
            try:
                cursor = conn.execute(
                    """
                    SELECT
                        file_path,
                        title,
                        category,
                        language,
                        snippet(knowledge_fts, 2, '<b>', '</b>', '...', 32) as snippet,
                        bm25(knowledge_fts) as rank
                    FROM knowledge_fts
                    WHERE knowledge_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """,
                    (fts5_query, limit),
                )
            except sqlite3.OperationalError:
                # bm25() not available, use simple search
                cursor = conn.execute(
                    """
                    SELECT
                        file_path,
                        title,
                        category,
                        language,
                        snippet(knowledge_fts, 2, '<b>', '</b>', '...', 32) as snippet,
                        0.0 as rank
                    FROM knowledge_fts
                    WHERE knowledge_fts MATCH ?
                    LIMIT ?
                """,
                    (fts5_query, limit),
                )

            results = []
            for row in cursor.fetchall():
                result = {
                    "file_path": row[0],
                    "title": row[1],
                    "category": row[2],
                    "language": row[3],
                    "snippet": row[4] if row[4] else "",
                    "rank": row[5] if len(row) > 5 else 0.0,
                }
                results.append(result)

            return results
        finally:
            conn.close()

    def search_cross_language(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Cross-language search (query in one language, find in any).

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of search results
        """
        # Detect query language
        self.query_processor.detect_query_language(query)

        # Search without language restriction
        # FTS5 will match across languages
        return self.search(query, language=None, limit=limit)

    def search_by_category(
        self,
        query: str,
        category: str,
        language: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Search within a specific category.

        Args:
            query: Search query
            category: Category to search in
            language: Optional language code
            limit: Maximum number of results

        Returns:
            List of search results
        """
        if language is None:
            language = self.query_processor.detect_query_language(query)

        fts5_query = self.query_processor.build_fts5_query(query, language)

        conn = sqlite3.connect(str(self.database.database_path))
        conn.execute("PRAGMA encoding = 'UTF-8'")

        try:
            # Try bm25() first, fallback to simple match if not available
            try:
                cursor = conn.execute(
                    """
                    SELECT
                        file_path,
                        title,
                        category,
                        language,
                        snippet(knowledge_fts, 2, '<b>', '</b>', '...', 32) as snippet,
                        bm25(knowledge_fts) as rank
                    FROM knowledge_fts
                    WHERE knowledge_fts MATCH ? AND category = ?
                    ORDER BY rank
                    LIMIT ?
                """,
                    (fts5_query, category, limit),
                )
            except sqlite3.OperationalError:
                # bm25() not available, use simple search
                cursor = conn.execute(
                    """
                    SELECT
                        file_path,
                        title,
                        category,
                        language,
                        snippet(knowledge_fts, 2, '<b>', '</b>', '...', 32) as snippet,
                        0.0 as rank
                    FROM knowledge_fts
                    WHERE knowledge_fts MATCH ? AND category = ?
                    LIMIT ?
                """,
                    (fts5_query, category, limit),
                )

            results = []
            for row in cursor.fetchall():
                result = {
                    "file_path": row[0],
                    "title": row[1],
                    "category": row[2],
                    "language": row[3],
                    "snippet": row[4] if row[4] else "",
                    "rank": row[5] if len(row) > 5 else 0.0,
                }
                results.append(result)

            return results
        finally:
            conn.close()
