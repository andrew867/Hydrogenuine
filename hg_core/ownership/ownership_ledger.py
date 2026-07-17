"""Append-only ownership event ledger backed by SQLite."""
from __future__ import annotations
import time
from typing import Any, Dict, List, Optional

from . import ownership_db


class OwnershipLedger:
    """Append-only ledger of ownership events. Persisted in SQLite (ownership_events table)."""

    def __init__(self, database_path: str, run_id: str):
        self.database_path = database_path
        self.run_id = run_id
        ownership_db.init_ownership_schema(self.database_path)

    def append(
        self,
        task_id: str,
        type_: str,
        actor: str,
        payload: Dict[str, Any],
        expected_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        ts = time.time()
        ev = ownership_db.ledger_append(
            self.database_path,
            self.run_id,
            task_id,
            type_,
            actor,
            ts,
            payload,
            expected_version=expected_version,
        )
        return ev

    def list_events(
        self,
        task_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        return ownership_db.ledger_list_events(
            self.database_path,
            self.run_id,
            task_id=task_id,
            limit=limit,
        )

    def search(self, query: str, task_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Full-text search over events (FTS5)."""
        return ownership_db.search_events_fts(
            self.database_path,
            self.run_id,
            query,
            task_id=task_id,
            limit=limit,
        )
