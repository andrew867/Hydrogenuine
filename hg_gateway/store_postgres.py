"""
Postgres-backed gateway store.
"""

from __future__ import annotations

from hg_gateway.db_postgres import get_postgres_connection
from hg_gateway.store_sqlite import SQLiteStore


class PostgresStore(SQLiteStore):
    def __init__(self) -> None:
        super().__init__(db_path=None)

    def _conn(self):
        return get_postgres_connection()
