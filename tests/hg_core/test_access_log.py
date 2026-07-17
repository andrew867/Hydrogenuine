"""
Tests for access_log: log_access, canonicalize_subject, get_molecule_from_access_log.
Co-access (molecules) layer: atoms log and molecule derivation.
"""

from __future__ import annotations

from unittest.mock import patch

from hg_core.access_log import (
    canonicalize_subject,
    get_co_occurrence,
    get_molecule_from_access_log,
    iter_access_events,
    log_access,
)
from hg_gateway.db import get_connection


def test_canonicalize_subject_path():
    """canonicalize_subject normalizes path separators and strips ./."""
    assert canonicalize_subject("path", "memory/automation/x.json") == "memory/automation/x.json"
    assert canonicalize_subject("path", ".\\memory\\automation\\x.json") == "memory/automation/x.json"
    assert canonicalize_subject("path", "./memory/automation/x.json") == "memory/automation/x.json"
    assert canonicalize_subject("path", "  memory/x  ") == "memory/x"


def test_canonicalize_subject_entity_id():
    """canonicalize_subject passes through entity_id and other types."""
    assert canonicalize_subject("entity_id", "obs-123") == "obs-123"
    assert canonicalize_subject("other", "anything") == "anything"


def test_log_access_records_audit_event(tmp_path):
    """log_access persists a JSON payload into the gateway audit ledger."""
    db_path = tmp_path / "gateway.sqlite3"
    with patch.dict("os.environ", {"HG_GATEWAY_STORE": "sqlite", "HG_GATEWAY_DB_PATH": str(db_path)}):
        with patch("hg_core.access_log.get_workspace_root", return_value=tmp_path):
            with patch("hg_core.scope_context.get_scope", return_value={"scope_type": "session", "scope_id": "automation-test", "session_id": "automation-test"}):
                log_access(
                    "test-agent",
                    "read",
                    "path",
                    "memory/automation/automation-test/posts.json",
                    "memory.load_compacted",
                    workspace_root=tmp_path,
                )

    with get_connection(str(db_path)) as conn:
        row = conn.execute("SELECT COUNT(*) FROM audit_events WHERE event_type = ?", ("access_log",)).fetchone()
        assert row[0] == 1
        payload_row = conn.execute("SELECT payload FROM audit_events WHERE event_type = ?", ("access_log",)).fetchone()
        assert '"subject": "memory/automation/automation-test/posts.json"' in payload_row[0]


def test_get_molecule_from_access_log(tmp_path, monkeypatch):
    """get_molecule_from_access_log returns subjects, counts, sources for a scope."""
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    with patch("hg_core.access_log.get_workspace_root", return_value=tmp_path):
        with patch("hg_core.scope_context.get_scope", return_value={"scope_type": "session", "scope_id": "s1", "session_id": "s1"}):
            log_access("a1", "read", "path", "memory/a/posts.json", "memory.load_compacted", workspace_root=tmp_path)
            log_access("a1", "read", "path", "memory/a/context.json", "memory.load_compacted", workspace_root=tmp_path)
            log_access("a1", "read", "path", "memory/a/posts.json", "memory.load_compacted", workspace_root=tmp_path)

    mol = get_molecule_from_access_log("session", "s1", agent_id="a1", workspace_root=tmp_path)
    assert "subjects" in mol
    assert set(mol["subjects"]) == {"memory/a/posts.json", "memory/a/context.json"}
    assert mol["counts"]["memory/a/posts.json"] == 2
    assert mol["counts"]["memory/a/context.json"] == 1
    assert "memory.load_compacted" in mol["sources"]


def test_get_co_occurrence_uses_db_events(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    with patch("hg_core.access_log.get_workspace_root", return_value=tmp_path):
        with patch("hg_core.scope_context.get_scope", return_value={"scope_type": "session", "scope_id": "s1", "session_id": "s1"}):
            log_access("a1", "read", "path", "memory/a/posts.json", "memory.load_compacted", workspace_root=tmp_path)
            log_access("a1", "read", "path", "memory/a/context.json", "memory.load_compacted", workspace_root=tmp_path)
            log_access("a1", "read", "path", "memory/a/posts.json", "memory.load_compacted", workspace_root=tmp_path)

    co = get_co_occurrence("memory/a/posts.json", agent_id="a1", workspace_root=tmp_path)
    assert co
    assert co[0][0] == "memory/a/context.json"


def test_iter_access_events_reads_db(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    with patch("hg_core.access_log.get_workspace_root", return_value=tmp_path):
        with patch("hg_core.scope_context.get_scope", return_value={"scope_type": "session", "scope_id": "s1", "session_id": "s1"}):
            log_access("a1", "read", "path", "memory/a/posts.json", "memory.load_compacted", workspace_root=tmp_path)

    rows = list(iter_access_events(agent_id="a1", workspace_root=tmp_path))
    assert len(rows) == 1
    assert rows[0]["subject"] == "memory/a/posts.json"
