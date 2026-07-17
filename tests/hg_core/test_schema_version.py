"""Tests for schema version and migration helper (Phase 9)."""

import pytest
from hg_core.schema_version import SCHEMA_VERSION, ensure_schema_version


def test_ensure_schema_version_adds_version_if_missing():
    """ensure_schema_version adds version=1 if missing (v0 -> v1)."""
    data = {"timestamp": "2026-02-19T12:00:00", "agents": {}}
    out = ensure_schema_version(data)
    assert out["version"] == SCHEMA_VERSION
    assert out["timestamp"] == data["timestamp"]


def test_ensure_schema_version_idempotent():
    """Running ensure_schema_version on v1 data leaves it unchanged."""
    data = {"version": 1, "timestamp": "2026-02-19T12:00:00"}
    out = ensure_schema_version(data)
    assert out["version"] == 1
    assert out["timestamp"] == data["timestamp"]


def test_ensure_schema_version_non_dict_returns_unchanged():
    """ensure_schema_version returns input unchanged if not a dict."""
    assert ensure_schema_version([]) == []
    assert ensure_schema_version(None) is None
