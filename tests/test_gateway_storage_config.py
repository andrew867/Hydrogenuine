from __future__ import annotations

from pathlib import Path

import pytest

from hg_gateway.db import get_connection
from hg_gateway.storage_config import (
    gateway_db_path,
    gateway_db_path_is_workspace_memory,
    gateway_postgres_dsn,
    gateway_requires_postgres,
    gateway_storage_diagnostics,
    gateway_store_backend,
    validate_gateway_storage_config,
)


def test_gateway_storage_config_defaults(monkeypatch):
    monkeypatch.delenv("HG_GATEWAY_STORE", raising=False)
    monkeypatch.delenv("HG_GATEWAY_DB_PATH", raising=False)
    monkeypatch.delenv("HG_GATEWAY_POSTGRES_DSN", raising=False)
    monkeypatch.delenv("HG_GATEWAY_REQUIRE_POSTGRES", raising=False)

    assert gateway_store_backend() == "sqlite"
    assert Path(gateway_db_path()).parts[-2:] == ("memory", "gateway.sqlite3")
    assert gateway_postgres_dsn(required=False) == ""
    assert gateway_requires_postgres() is False
    diag = gateway_storage_diagnostics()
    assert diag["backend"] == "sqlite"
    assert diag["canonical_store"] == "sqlite"
    assert diag["db_path_is_workspace_memory"] is True
    assert gateway_db_path_is_workspace_memory() is True


def test_gateway_require_postgres_blocks_sqlite_backend(monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_REQUIRE_POSTGRES", "1")
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")

    with pytest.raises(RuntimeError, match="requires HG_GATEWAY_STORE=postgres"):
        with get_connection():
            pass


def test_gateway_storage_validate_requires_dsn_for_postgres(monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_STORE", "postgres")
    monkeypatch.delenv("HG_GATEWAY_POSTGRES_DSN", raising=False)

    with pytest.raises(RuntimeError, match="HG_GATEWAY_POSTGRES_DSN is required"):
        validate_gateway_storage_config()


def test_gateway_storage_diagnostics_reports_postgres_mode(monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_STORE", "postgres")
    monkeypatch.setenv("HG_GATEWAY_POSTGRES_DSN", "postgresql://user:pass@localhost:5432/hg")
    diag = gateway_storage_diagnostics()
    assert diag["backend"] == "postgres"
    assert diag["canonical_store"] == "postgres"
    assert diag["postgres_dsn_configured"] is True
