"""Tests for autonomy Phase 3: change governance (G1–G5)."""

import json
import pytest
from pathlib import Path

from hg_core.task_graph.change_governance import (
    validate_proposal_schema,
    validate_proposal_node_types,
    save_proposal,
    load_proposal,
    save_last_known_good,
    rollback_scope,
    record_applied_change,
)


# --- G1 / G2: Proposal schema and static validation ---


def test_proposal_schema_valid():
    """Valid proposal passes schema validation."""
    payload = {
        "proposal_id": "prop-001",
        "created_at": "2026-02-23T12:00:00Z",
        "originating_run_id": "run-123",
        "scope": "single_workflow",
        "risk_level": "low",
        "validation_plan": "run tests",
        "rollback_plan": "restore LKG",
    }
    ok, errors = validate_proposal_schema(payload)
    assert ok is True
    assert len(errors) == 0


def test_proposal_schema_invalid_missing_fields():
    """Proposal missing required fields fails validation."""
    payload = {"scope": "single_workflow"}
    ok, errors = validate_proposal_schema(payload)
    assert ok is False
    assert any("missing_field" in e for e in errors)


def test_proposal_schema_invalid_scope():
    """Proposal with invalid scope fails validation."""
    payload = {
        "proposal_id": "p1",
        "created_at": "2026-02-23T12:00:00Z",
        "originating_run_id": "r1",
        "scope": "invalid_scope",
        "risk_level": "low",
        "validation_plan": "x",
        "rollback_plan": "y",
    }
    ok, errors = validate_proposal_schema(payload)
    assert ok is False
    assert "invalid_scope" in errors


def test_static_validation_rejects_disallowed_node_types():
    """Proposal with disallowed node type fails node-type validation."""
    change = {"nodes": [{"id": "n1", "type": "tool"}, {"id": "n2", "type": "unknown_type"}]}
    ok, errors = validate_proposal_node_types(change)
    assert ok is False
    assert any("unknown_type" in e or "invalid_type" in e for e in errors)


def test_static_validation_allows_allowed_node_types():
    """Proposal with only allowed node types passes."""
    change = {"nodes": [{"id": "n1", "type": "tool"}, {"id": "n2", "type": "agent"}]}
    ok, errors = validate_proposal_node_types(change)
    assert ok is True
    assert len(errors) == 0


# --- G4: Rollback drill ---


def test_rollback_drill(tmp_path):
    """Apply change, save LKG, then one-step rollback restores state."""
    scope = "test_workflow"
    original = {"version": "1", "config": "original"}

    save_last_known_good(tmp_path, scope, original)
    lkg_path = tmp_path / "memory" / "automation" / "last_known_good" / f"{scope}.json"
    assert lkg_path.exists()

    restored = rollback_scope(tmp_path, scope)
    assert restored is not None
    assert restored == original
    assert restored.get("version") == "1"
    assert restored.get("config") == "original"


def test_save_and_load_proposal(tmp_path):
    """Save proposal then load by id."""
    payload = {
        "proposal_id": "prop-test",
        "created_at": "2026-02-23T12:00:00Z",
        "originating_run_id": "run-1",
        "scope": "single_workflow",
        "risk_level": "medium",
        "validation_plan": "static + shadow",
        "rollback_plan": "rollback_scope",
    }
    path = save_proposal(tmp_path, payload)
    assert path.exists()
    loaded = load_proposal(tmp_path, "prop-test")
    assert loaded is not None
    assert loaded["proposal_id"] == "prop-test"
    assert loaded["risk_level"] == "medium"


def test_record_applied_change_audit_trail(tmp_path):
    """record_applied_change appends to audit trail."""
    record_applied_change(tmp_path, "prop-1", "operator", canary_results={"passed": True})
    audit_path = tmp_path / "memory" / "automation" / "change_audit.jsonl"
    assert audit_path.exists()
    lines = audit_path.read_text().strip().split("\n")
    assert len(lines) >= 1
    entry = json.loads(lines[0])
    assert entry["proposal_id"] == "prop-1"
    assert entry["approved_by"] == "operator"
    assert entry.get("canary_results", {}).get("passed") is True
