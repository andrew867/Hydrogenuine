from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


@pytest.fixture()
def seeded_workspace(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    root.mkdir(parents=True, exist_ok=True)
    (root / ".hg_root").write_text("", encoding="utf-8")
    db_path = root / "memory" / "gateway.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HG_WORKSPACE", str(root))
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("SAFE_LOCAL_ONLY", "1")
    monkeypatch.setenv("HG_DISABLE_RUN_DISCOVERY", "1")
    import hg_gateway.store as store_module
    store_module._store = None
    yield root
    store_module._store = None


def test_zero_budget_seed_populates_local_demo_surface(seeded_workspace):
    from hg_gateway.zero_budget_seed import SEED_MARKER_KEY, seed_zero_budget_validation
    from hg_gateway.operational_state_ledger import load_operational_json_state
    from hg_gateway.db import get_connection

    summary = seed_zero_budget_validation(seeded_workspace)
    assert summary["version"] == 1
    assert len(summary["task_names"]) == 5

    marker = load_operational_json_state(seeded_workspace, state_key=SEED_MARKER_KEY)
    assert marker["present"] is True

    job_registry = seeded_workspace / "memory" / "automation" / "job_registry.json"
    assert job_registry.exists()
    registry = json.loads(job_registry.read_text(encoding="utf-8"))
    assert "zero-budget-state-sheet" in registry

    with get_connection(str(seeded_workspace / "memory" / "gateway.sqlite3")) as conn:
        for task_name in summary["task_names"]:
            chat_id = f"{task_name}-chat"
            chat = conn.execute(
                "SELECT chat_id, title FROM chats WHERE tenant_id = ? AND chat_id = ?",
                ("default", chat_id),
            ).fetchone()
            assert chat is not None
            messages = conn.execute(
                "SELECT message_id, role, content FROM messages WHERE tenant_id = ? AND chat_id = ? ORDER BY created_at ASC",
                ("default", chat_id),
            ).fetchall()
            assert len(messages) == 2
            provenance = conn.execute(
                "SELECT message_id FROM turn_provenance WHERE tenant_id = ? AND message_id = ?",
                ("default", f"{chat_id}-assistant"),
            ).fetchone()
            assert provenance is not None
        run_rows = conn.execute(
            "SELECT run_id FROM runs ORDER BY started_at DESC, run_id DESC",
        ).fetchall()
        run_ids = {row[0] for row in run_rows}
        for run_id in summary["runs"]:
            assert run_id in run_ids
        approval = conn.execute(
            "SELECT id, status FROM approvals WHERE tenant_id = ? AND id = ?",
            ("default", "zero-budget-approval-1"),
        ).fetchone()
        assert approval is not None
        drift_count = conn.execute("SELECT COUNT(*) FROM constitutional_drift_events").fetchone()[0]
        assert drift_count >= 1
        event_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        assert event_count >= 10
        notification = conn.execute(
            "SELECT payload_json FROM human_notifications ORDER BY recorded_at DESC LIMIT 1",
        ).fetchone()
        assert notification is not None
        reflection = conn.execute(
            "SELECT artifact_id FROM artifact_registry_entries WHERE artifact_id = ?",
            ("zero-budget-reflection-1",),
        ).fetchone()
        assert reflection is not None


def test_zero_budget_seed_is_idempotent(seeded_workspace):
    from hg_gateway.zero_budget_seed import seed_zero_budget_validation

    first = seed_zero_budget_validation(seeded_workspace)
    second = seed_zero_budget_validation(seeded_workspace)
    assert first["task_names"] == second["task_names"]
    assert first["runs"] == second["runs"]
