#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base class for SQLite FTS5 databases in memory engine.

Provides common functionality for all memory graph databases.
"""

import hashlib
import sqlite3
import unicodedata
from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Optional

from hg_gateway.shared_storage import use_shared_gateway_db


class DatabaseBase(ABC):
    """Base class for SQLite FTS5 databases"""

    def __init__(self, database_path: str):
        """
        Initialize database connection.

        Args:
            database_path: Path to SQLite database file
        """
        self.database_path = Path(database_path)
        self._shared_gateway_db = use_shared_gateway_db(self.database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_schema()

    @abstractmethod
    def _create_schema(self) -> None:
        """Create database schema - must be implemented by subclasses."""
        pass

    def _calculate_file_hash(self, content: str) -> str:
        """Calculate SHA256 hash of file content for change detection."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _normalize_unicode(self, text: str) -> str:
        """Normalize Unicode text (NFKC normalization)."""
        return unicodedata.normalize("NFKC", text)

    def _get_connection(self):
        """Get database connection with UTF-8 encoding."""
        if self._shared_gateway_db:
            from hg_gateway.shared_storage import shared_connection
            return _SharedGatewayConnection(shared_connection())
        conn = sqlite3.connect(str(self.database_path))
        conn.execute("PRAGMA encoding = 'UTF-8'")
        return conn

    def _shared_agent_id(self) -> Optional[str]:
        for part in self.database_path.parts:
            if part.startswith("automation-"):
                return part.replace("automation-", "", 1)
        return None

    def check_file_changed(self, file_path: str, content: str) -> bool:
        """
        Check if file has changed since last indexing.

        Args:
            file_path: Relative path to source file
            content: Current file content

        Returns:
            True if file is new or changed, False if unchanged
        """
        if self._shared_gateway_db and self._shared_agent_id():
            from hg_gateway.shared_storage import check_agent_memory_file_changed

            return check_agent_memory_file_changed(self._shared_agent_id() or "", file_path, content)
        with self._get_connection() as conn:
            metadata_table = getattr(self, "_metadata_table_name", "metadata")
            cursor = conn.execute(
                f"SELECT file_hash FROM {metadata_table} WHERE file_path = ?",
                (file_path,),
            )
            result = cursor.fetchone()
            if result is None:
                return True
            stored_hash = result[0]
            current_hash = self._calculate_file_hash(content)
            return stored_hash != current_hash


class _SharedGatewayConnection(AbstractContextManager):
    """Adapter that looks like a DB-API connection and safely closes shared DB handles."""

    def __init__(self, manager):
        self._manager = manager
        self._conn = manager.__enter__()

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def close(self) -> None:
        if self._manager is not None:
            self._manager.__exit__(None, None, None)
            self._manager = None
            self._conn = None

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
