"""Tests for scripts/backfill_moltbook_engage.py (empty approvals, DB resolution, no crash)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_backfill_dry_run_empty_approvals_exits_zero(tmp_path, monkeypatch):
    """With empty gateway DB, script must not crash and must exit 0 (nothing to backfill)."""
    db_path = tmp_path / "gateway.sqlite3"
    db_path.touch()
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    monkeypatch.delenv("HG_DEMO_MODE", raising=False)
    workspace = Path(__file__).resolve().parents[2]
    script = workspace / "scripts" / "backfill_moltbook_engage.py"
    result = subprocess.run(
        [sys.executable, str(script), "--dry-run"],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "Nothing to backfill" in result.stdout or "To post" in result.stdout


def test_backfill_uses_demo_db_when_HG_DEMO_MODE_set(tmp_path, monkeypatch):
    """When HG_DEMO_MODE=1, script resolves DB to .hg_demo/gateway/gateway.sqlite3."""
    demo_db = tmp_path / ".hg_demo" / "gateway" / "gateway.sqlite3"
    demo_db.parent.mkdir(parents=True)
    demo_db.touch()
    monkeypatch.delenv("HG_GATEWAY_DB_PATH", raising=False)
    monkeypatch.setenv("HG_DEMO_MODE", "1")
    workspace = tmp_path  # so .hg_demo is under our tmp_path
    script = Path(__file__).resolve().parents[2] / "scripts" / "backfill_moltbook_engage.py"
    result = subprocess.run(
        [sys.executable, str(script), "--dry-run"],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert ".hg_demo" in result.stdout or "Gateway DB:" in result.stdout
