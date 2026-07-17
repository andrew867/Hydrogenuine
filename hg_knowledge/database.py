#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite FTS5 database for knowledge engine.

Handles database creation, document insertion, updates, and queries.
Supports UTF-8 and Unicode throughout.
"""

import sqlite3
import hashlib
import os
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import unicodedata


class KnowledgeDatabase:
    """SQLite FTS5 database for knowledge files"""

    def __init__(self, database_path: str):
        """
        Initialize database connection.

        Args:
            database_path: Path to SQLite database file
        """
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        # Create database and tables
        self._create_schema()

    def _create_schema(self):
        """Create database schema (FTS5 table and metadata table)"""
        conn = sqlite3.connect(str(self.database_path))
        conn.execute("PRAGMA encoding = 'UTF-8'")

        # Create FTS5 virtual table for full-text search
        # FTS5 columns don't need type declarations - all are text
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
                content,
                title,
                category,
                file_path,
                language,
                last_updated,
                content_normalized,
                tokenize='unicode61'
            )
        """)

        # Create metadata table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_metadata (
                file_path TEXT PRIMARY KEY,
                title TEXT,
                category TEXT,
                language TEXT,
                word_count INTEGER,
                last_indexed TEXT,
                file_hash TEXT
            )
        """)

        conn.commit()
        conn.close()

    def _mirror_enabled(self) -> bool:
        return (os.environ.get("HG_GATEWAY_STORE") or "").strip().lower() in {"sqlite", "postgres"}

    def _upsert_gateway_document(
        self,
        *,
        file_path: str,
        title: str,
        category: str,
        language: str,
        content: str,
        word_count: int,
        last_indexed: str,
        file_hash: str,
    ) -> None:
        """Mirror one doc to gateway. One row per (title, category): remove older rows with same
        title+category then insert, so timestamped duplicate files (e.g. finance-20260309T193219Z.md)
        don't create duplicate rows."""
        if not self._mirror_enabled():
            return
        try:
            from hg_gateway.db import get_connection

            t = (title or "").strip()
            c = (category or "").strip()
            with get_connection() as conn:
                conn.execute(
                    "DELETE FROM knowledge_documents WHERE COALESCE(TRIM(title),'') = ? AND COALESCE(TRIM(category),'') = ?",
                    (t, c),
                )
                conn.execute(
                    """
                    INSERT INTO knowledge_documents
                    (file_path, title, category, language, content, word_count, last_indexed, file_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (file_path, title, category, language, content, word_count, last_indexed, file_hash),
                )
        except Exception:
            return

    def _delete_gateway_document(self, file_path: str) -> None:
        if not self._mirror_enabled():
            return
        try:
            from hg_gateway.db import get_connection

            with get_connection() as conn:
                conn.execute("DELETE FROM knowledge_documents WHERE file_path = ?", (file_path,))
        except Exception:
            return

    def _calculate_file_hash(self, content: str) -> str:
        """
        Calculate SHA256 hash of file content for change detection.

        Args:
            content: File content as string

        Returns:
            SHA256 hash as hex string
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def mirror_document(
        self,
        *,
        file_path: str,
        title: str,
        content: str,
        category: str,
        language: str,
        word_count: Optional[int] = None,
    ) -> None:
        if word_count is None:
            word_count = len(content.split())
        file_hash = self._calculate_file_hash(content)
        now = datetime.now().isoformat()
        self._upsert_gateway_document(
            file_path=file_path,
            title=title,
            category=category,
            language=language,
            content=content,
            word_count=word_count,
            last_indexed=now,
            file_hash=file_hash,
        )

    def _normalize_unicode(self, text: str) -> str:
        """
        Normalize Unicode text (NFKC normalization).

        Args:
            text: Input text

        Returns:
            Normalized text
        """
        return unicodedata.normalize("NFKC", text)

    def insert_document(
        self,
        file_path: str,
        title: str,
        content: str,
        category: str,
        language: str,
        word_count: Optional[int] = None,
    ):
        """
        Insert a document into the database.

        Args:
            file_path: Relative path to source file
            title: Document title
            content: Full text content
            category: Category (e.g., "technology", "politics")
            language: Language code (e.g., "en", "zh", "ja")
            word_count: Optional word count
        """
        if word_count is None:
            word_count = len(content.split())

        file_hash = self._calculate_file_hash(content)
        content_normalized = self._normalize_unicode(content)
        now = datetime.now().isoformat()

        conn = sqlite3.connect(str(self.database_path))
        conn.execute("PRAGMA encoding = 'UTF-8'")

        try:
            # Insert into FTS5 table
            conn.execute(
                """
                INSERT INTO knowledge_fts (
                    content, title, category, file_path, language,
                    last_updated, content_normalized
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (content, title, category, file_path, language, now, content_normalized),
            )

            # Insert into metadata table
            conn.execute(
                """
                INSERT OR REPLACE INTO knowledge_metadata (
                    file_path, title, category, language, word_count,
                    last_indexed, file_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (file_path, title, category, language, word_count, now, file_hash),
            )

            conn.commit()
        finally:
            conn.close()
        self._upsert_gateway_document(
            file_path=file_path,
            title=title,
            category=category,
            language=language,
            content=content,
            word_count=word_count,
            last_indexed=now,
            file_hash=file_hash,
        )

    def update_document(
        self,
        file_path: str,
        title: str,
        content: str,
        category: str,
        language: str,
        word_count: Optional[int] = None,
    ):
        """
        Update an existing document.

        Args:
            file_path: Relative path to source file
            title: Document title
            content: Full text content
            category: Category
            language: Language code
            word_count: Optional word count
        """
        # Delete old entry and insert new one
        self.delete_document(file_path)
        self.insert_document(
            file_path, title, content, category, language, word_count
        )

    def delete_document(self, file_path: str):
        """
        Delete a document from the database.

        Args:
            file_path: Relative path to source file
        """
        conn = sqlite3.connect(str(self.database_path))
        conn.execute("PRAGMA encoding = 'UTF-8'")

        try:
            # Delete from FTS5 table
            conn.execute(
                "DELETE FROM knowledge_fts WHERE file_path = ?", (file_path,)
            )

            # Delete from metadata table
            conn.execute(
                "DELETE FROM knowledge_metadata WHERE file_path = ?",
                (file_path,),
            )

            conn.commit()
        finally:
            conn.close()
        self._delete_gateway_document(file_path)

    def check_file_changed(self, file_path: str, content: str) -> bool:
        """
        Check if file has changed since last indexing.

        Args:
            file_path: Relative path to source file
            content: Current file content

        Returns:
            True if file is new or changed, False if unchanged
        """
        conn = sqlite3.connect(str(self.database_path))
        conn.execute("PRAGMA encoding = 'UTF-8'")

        try:
            cursor = conn.execute(
                "SELECT file_hash FROM knowledge_metadata WHERE file_path = ?",
                (file_path,),
            )
            result = cursor.fetchone()

            if result is None:
                # File not indexed yet
                return True

            stored_hash = result[0]
            current_hash = self._calculate_file_hash(content)

            return stored_hash != current_hash
        finally:
            conn.close()

    def get_indexed_files(self) -> List[str]:
        """
        Get list of all indexed file paths.

        Returns:
            List of file paths
        """
        conn = sqlite3.connect(str(self.database_path))
        conn.execute("PRAGMA encoding = 'UTF-8'")

        try:
            cursor = conn.execute("SELECT file_path FROM knowledge_metadata")
            return [row[0] for row in cursor.fetchall()]
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
        conn = sqlite3.connect(str(self.database_path))
        conn.execute("PRAGMA encoding = 'UTF-8'")

        try:
            cursor = conn.execute(
                "SELECT file_path, title, category, language, word_count, last_indexed, file_hash "
                "FROM knowledge_metadata WHERE file_path = ?",
                (file_path,),
            )
            result = cursor.fetchone()

            if result is None:
                return None

            return {
                "file_path": result[0],
                "title": result[1],
                "category": result[2],
                "language": result[3],
                "word_count": result[4],
                "last_indexed": result[5],
                "file_hash": result[6],
            }
        finally:
            conn.close()
