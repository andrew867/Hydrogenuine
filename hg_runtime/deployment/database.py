"""Database packaging — deployment-state SQLite initializer.

Minimal schema for runs, receipts, proof bundles, operator reviews,
and deployment health. Does not replace existing app DB architecture.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .runtime_config import RuntimeConfig


_SCHEMA = """
CREATE TABLE IF NOT EXISTS deployment_runs (
    run_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    mode TEXT NOT NULL,
    verdict TEXT,
    proof_path TEXT,
    report_path TEXT,
    live_effects_created INTEGER DEFAULT 0,
    tools_authorized INTEGER DEFAULT 0,
    phase19_yellow_preserved INTEGER DEFAULT 1,
    phase24_infrastructure_only_preserved INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS deployment_receipts (
    receipt_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    receipt_type TEXT NOT NULL,
    receipt_hash TEXT,
    data_json TEXT
);

CREATE TABLE IF NOT EXISTS proof_bundles (
    bundle_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    bundle_path TEXT NOT NULL,
    gate_verdict TEXT
);

CREATE TABLE IF NOT EXISTS operator_reviews (
    review_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    reviewer TEXT,
    verdict TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS deployment_health (
    check_id TEXT PRIMARY KEY,
    checked_at TEXT NOT NULL,
    mode TEXT NOT NULL,
    healthy INTEGER NOT NULL,
    details_json TEXT
);
"""


def get_db_path(cfg: RuntimeConfig) -> str:
    url = cfg.db_url
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "", 1)
    return str(Path(cfg.state_dir) / "hydrogenuine.sqlite3")


def init_database(cfg: RuntimeConfig) -> str:
    db_path = get_db_path(cfg)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()
    return db_path


def record_run(cfg: RuntimeConfig, run_id: str, mode: str, verdict: str = "",
               proof_path: str = "", report_path: str = "") -> None:
    db_path = get_db_path(cfg)
    if not Path(db_path).exists():
        return
    conn = sqlite3.connect(db_path)
    try:
        from datetime import datetime, timezone
        conn.execute(
            "INSERT OR REPLACE INTO deployment_runs "
            "(run_id, created_at, mode, verdict, proof_path, report_path) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, datetime.now(timezone.utc).isoformat(), mode, verdict, proof_path, report_path),
        )
        conn.commit()
    finally:
        conn.close()


def list_tables(cfg: RuntimeConfig) -> list[str]:
    db_path = get_db_path(cfg)
    if not Path(db_path).exists():
        return []
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()
