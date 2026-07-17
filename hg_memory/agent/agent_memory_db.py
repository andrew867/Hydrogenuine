#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite FTS5 database for agent memory.

Stores agent-specific memory (daily logs, feedback, posts, context, decisions).
"""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

from hg_memory.shared import DatabaseBase
from hg_gateway.shared_storage import (
    delete_agent_memory_document,
    get_agent_memory_documents_by_date_range,
    get_agent_memory_metadata,
    list_agent_memory_files,
    upsert_agent_memory_document,
)


class AgentMemoryDatabase(DatabaseBase):
    """SQLite FTS5 database for agent memory"""

    def __init__(self, database_path: str):
        """
        Initialize agent memory database.

        Args:
            database_path: Path to SQLite database file
        """
        self._metadata_table_name = "agent_memory_metadata"
        super().__init__(database_path)

    def _create_schema(self):
        """Create database schema (FTS5 table and metadata table)"""
        if self._shared_gateway_db:
            return
        conn = self._get_connection()

        try:
            # Create FTS5 virtual table for full-text search
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS agent_memory_fts USING fts5(
                    content,
                    source_file,
                    date,
                    language,
                    metadata,
                    content_normalized,
                    tokenize='unicode61'
                )
            """)

            # Create metadata table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_memory_metadata (
                    file_path TEXT PRIMARY KEY,
                    date TEXT,
                    language TEXT,
                    word_count INTEGER,
                    last_indexed TEXT,
                    file_hash TEXT,
                    source_type TEXT
                )
            """)

            conn.commit()
        finally:
            conn.close()

    def insert_document(
        self,
        file_path: str,
        content: str,
        date: str,
        language: str,
        source_type: str = "unknown",
        metadata: Optional[Dict] = None,
        word_count: Optional[int] = None,
    ):
        """
        Insert a document into the database.

        Args:
            file_path: Relative path to source file
            content: Full text content
            date: Date string (YYYY-MM-DD format)
            language: Language code (e.g., "en", "zh", "ja")
            source_type: Type of source (e.g., "daily_log", "feedback", "post", "context", "decision")
            metadata: Optional metadata dictionary (will be JSON-encoded)
            word_count: Optional word count
        """
        if word_count is None:
            word_count = len(content.split())

        file_hash = self._calculate_file_hash(content)
        content_normalized = self._normalize_unicode(content)
        now = datetime.now().isoformat()

        # Serialize metadata to JSON
        import json

        metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
        if self._shared_gateway_db:
            upsert_agent_memory_document(
                agent_id=self._shared_agent_id() or "",
                file_path=file_path,
                content=content,
                date=date,
                language=language,
                metadata=metadata or {},
                word_count=word_count,
                last_indexed=now,
                file_hash=file_hash,
                source_type=source_type,
                content_normalized=content_normalized,
            )
            return
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO agent_memory_fts (
                    content, source_file, date, language, metadata,
                    content_normalized
                ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                (content, file_path, date, language, metadata_json, content_normalized),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO agent_memory_metadata (
                    file_path, date, language, word_count,
                    last_indexed, file_hash, source_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (file_path, date, language, word_count, now, file_hash, source_type),
            )
            conn.commit()
        finally:
            conn.close()

    def update_document(
        self,
        file_path: str,
        content: str,
        date: str,
        language: str,
        source_type: str = "unknown",
        metadata: Optional[Dict] = None,
        word_count: Optional[int] = None,
    ):
        """
        Update an existing document.

        Args:
            file_path: Relative path to source file
            content: Full text content
            date: Date string
            language: Language code
            source_type: Type of source
            metadata: Optional metadata dictionary
            word_count: Optional word count
        """
        # Delete old entry and insert new one
        self.delete_document(file_path)
        self.insert_document(
            file_path, content, date, language, source_type, metadata, word_count
        )

    def delete_document(self, file_path: str):
        """
        Delete a document from the database.

        Args:
            file_path: Relative path to source file
        """
        if self._shared_gateway_db:
            delete_agent_memory_document(self._shared_agent_id() or "", file_path)
            return
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM agent_memory_fts WHERE source_file = ?", (file_path,))
            conn.execute("DELETE FROM agent_memory_metadata WHERE file_path = ?", (file_path,))
            conn.commit()
        finally:
            conn.close()

    def get_file_metadata(self, file_path: str) -> Optional[Dict]:
        """
        Get metadata for a file.

        Args:
            file_path: Relative path to source file

        Returns:
            Dictionary with metadata or None if not found
        """
        if self._shared_gateway_db:
            return get_agent_memory_metadata(self._shared_agent_id() or "", file_path)
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT file_path, date, language, word_count, last_indexed, file_hash, source_type "
                "FROM agent_memory_metadata WHERE file_path = ?",
                (file_path,),
            )
            result = cursor.fetchone()
            if result is None:
                return None
            return {
                "file_path": result[0],
                "date": result[1],
                "language": result[2],
                "word_count": result[3],
                "last_indexed": result[4],
                "file_hash": result[5],
                "source_type": result[6],
            }
        finally:
            conn.close()

    def get_indexed_files(self) -> List[str]:
        """
        Get list of all indexed file paths.

        Returns:
            List of file paths
        """
        if self._shared_gateway_db:
            return list_agent_memory_files(self._shared_agent_id() or "")
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT file_path FROM agent_memory_metadata")
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_documents_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Get all documents within a date range.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            List of document metadata dictionaries
        """
        if self._shared_gateway_db:
            return get_agent_memory_documents_by_date_range(self._shared_agent_id() or "", start_date, end_date)
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT file_path, date, language, word_count, source_type "
                "FROM agent_memory_metadata "
                "WHERE date >= ? AND date <= ? "
                "ORDER BY date ASC",
                (start_date, end_date),
            )
            results = []
            for row in cursor.fetchall():
                results.append(
                    {
                        "file_path": row[0],
                        "date": row[1],
                        "language": row[2],
                        "word_count": row[3],
                        "source_type": row[4],
                    }
                )
            return results
        finally:
            conn.close()
