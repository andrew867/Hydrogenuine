"""Tests for deployment database packaging."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _fixture_env(monkeypatch, tmp_path):
    db_path = str(tmp_path / "state" / "hydrogenuine.sqlite3")
    monkeypatch.setenv("HG_MODE", "fixture")
    monkeypatch.setenv("HG_RUNTIME_PROFILE", "fixture")
    monkeypatch.setenv("HG_PROOF_DIR", str(tmp_path / "proofs"))
    monkeypatch.setenv("HG_REPORT_DIR", str(tmp_path / "reports"))
    monkeypatch.setenv("HG_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("HG_DB_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("HG_DISABLE_REMOTE_PROVIDERS", "true")
    monkeypatch.setenv("HG_DISABLE_LIVE_EFFECTS", "true")
    monkeypatch.setenv("HG_REQUIRE_OPERATOR_REVIEW", "true")
    monkeypatch.setenv("HG_LMSTUDIO_BASE_URL", "http://host.docker.internal:1234/v1")
    monkeypatch.setenv("HG_LMSTUDIO_SELECTED_MODEL", "google/gemma-4-e4b")
    monkeypatch.setenv("HG_LMSTUDIO_ALLOWED_MODELS", "google/gemma-4-e4b")
    monkeypatch.setenv("HG_LMSTUDIO_FORBIDDEN_PATTERNS", "deepseek,offensive,uncensored,30b")
    monkeypatch.setenv("HG_OPENVINO_MODEL_DIR", "/models/openvino")
    monkeypatch.setenv("HG_ALLOW_MODEL_DOWNLOADS", "false")
    monkeypatch.setenv("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "false")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "1")


def test_init_database_creates_file():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.database import init_database, get_db_path
    from pathlib import Path
    cfg = load_runtime_config()
    db_path = init_database(cfg)
    assert Path(db_path).exists()


def test_init_database_creates_tables():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.database import init_database, list_tables
    cfg = load_runtime_config()
    init_database(cfg)
    tables = list_tables(cfg)
    assert "deployment_runs" in tables
    assert "deployment_receipts" in tables
    assert "proof_bundles" in tables
    assert "operator_reviews" in tables
    assert "deployment_health" in tables


def test_record_run_and_read():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.database import init_database, record_run, get_db_path
    import sqlite3
    cfg = load_runtime_config()
    init_database(cfg)
    record_run(cfg, "test-run-001", "fixture", verdict="GREEN")
    db_path = get_db_path(cfg)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute("SELECT run_id, mode, verdict FROM deployment_runs WHERE run_id='test-run-001'")
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "test-run-001"
        assert row[1] == "fixture"
        assert row[2] == "GREEN"
    finally:
        conn.close()


def test_get_db_path_from_url():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.database import get_db_path
    cfg = load_runtime_config()
    path = get_db_path(cfg)
    assert path.endswith("hydrogenuine.sqlite3")


def test_list_tables_empty_before_init(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_DB_URL", f"sqlite:///{tmp_path / 'nonexistent.sqlite3'}")
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.database import list_tables
    cfg = load_runtime_config()
    assert list_tables(cfg) == []


def test_idempotent_init():
    from hg_runtime.deployment.runtime_config import load_runtime_config
    from hg_runtime.deployment.database import init_database, list_tables
    cfg = load_runtime_config()
    init_database(cfg)
    init_database(cfg)
    tables = list_tables(cfg)
    assert len(tables) == 5
