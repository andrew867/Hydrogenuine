"""
Tests for retention, redaction, and purge.

Per TEST_PLAN: fixture with mock secrets is redacted in traces/logs; purge
removes targeted artifacts and leaves tombstones where required; purge
action recorded in audit log.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


# Mock secrets fixture - must be redacted in stored artifacts
MOCK_SECRETS_FIXTURE = {
    "api_key": "sk-secret-12345",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxx",
    "token": "ghp_xxxxxxxxxxxxxxxxxxxx",
    "password": "super_secret_123",
}


def test_redaction_module_importable():
    """Retention/redaction/purge module is importable."""
    from hg_core.task_graph import retention_redaction_purge

    assert retention_redaction_purge is not None


def test_redact_removes_mock_secrets():
    """Redaction filters remove known patterns (keys, tokens, auth headers)."""
    from hg_core.task_graph.retention_redaction_purge import redact_for_storage

    payload = {"data": "ok", "api_key": "sk-secret-12345", "Authorization": "Bearer xyz"}
    out = redact_for_storage(payload)
    assert "sk-secret" not in json.dumps(out)
    assert "Bearer" not in json.dumps(out) or "REDACTED" in json.dumps(out)


def test_redaction_fixture_with_mock_secrets():
    """Fixture containing mock secrets is redacted in output."""
    from hg_core.task_graph.retention_redaction_purge import redact_for_storage

    fixture = {"trace": MOCK_SECRETS_FIXTURE, "run_id": "r1"}
    out = redact_for_storage(fixture)
    s = json.dumps(out)
    for secret_val in MOCK_SECRETS_FIXTURE.values():
        assert secret_val not in s, "Mock secret must not appear in redacted output"


def test_purge_by_run_id_removes_artifacts():
    """Purge by run_id removes targeted artifacts."""
    from hg_core.task_graph.retention_redaction_purge import purge_by_run_id

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_dir = root / "memory" / "automation" / "dag_runs" / "run_test"
        run_dir.mkdir(parents=True)
        (run_dir / "state.json").write_text("{}")
        (run_dir / "summary.json").write_text("{}")
        removed, audit_entry = purge_by_run_id(root, "run_test")
        assert len(removed) >= 1
        assert audit_entry is not None
        assert "run_id" in audit_entry
        assert audit_entry.get("action") == "purge"


def test_purge_records_audit_log():
    """Purge operation records the action in an audit log."""
    from hg_core.task_graph.retention_redaction_purge import write_audit_log

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_audit_log(root, {"action": "purge", "run_id": "r1", "removed_count": 0})
        log_file = root / "memory" / "automation" / "audit" / "purge_audit.jsonl"
        assert log_file.exists()
        content = log_file.read_text()
        assert "purge" in content and "r1" in content


def test_purge_leaves_tombstone_when_required():
    """Purge sensitive payloads can leave tombstone records."""
    from hg_core.task_graph.retention_redaction_purge import purge_sensitive_leave_tombstone

    artifact = {"run_id": "r1", "sensitive": "secret", "metrics": {"count": 1}}
    tombstone = purge_sensitive_leave_tombstone(artifact)
    assert "sensitive" not in tombstone or tombstone.get("sensitive") == "[REDACTED]"
    assert tombstone.get("run_id") == "r1"
    assert tombstone.get("_tombstone") is True or "metrics" in tombstone
