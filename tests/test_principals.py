"""
Pack2-08: Principals and availability. Real SQLite; no mocks.
"""

import json
import os
import pytest
from pathlib import Path


@pytest.fixture
def gateway_db_path(tmp_path):
    """Temp gateway DB path so principals and approvals use real SQLite."""
    return str(tmp_path / "gateway.sqlite3")


def test_principals_upsert_list_get(gateway_db_path):
    """Create principals, list and get by id — real DB."""
    from hg_gateway.principals import upsert_principal, list_principals, get_principal
    upsert_principal("op1", "user", "Primary operator", status="online", db_path=gateway_db_path)
    upsert_principal("op2", "user", "Secondary", status="offline", escalation_chain=["op1", "op2"], db_path=gateway_db_path)
    principals = list_principals(gateway_db_path)
    assert len(principals) == 2
    by_id = {p["id"]: p for p in principals}
    assert by_id["op1"]["label"] == "Primary operator"
    assert by_id["op1"]["status"] == "online"
    assert by_id["op2"]["escalation_chain"] == ["op1", "op2"]
    p = get_principal("op1", gateway_db_path)
    assert p is not None
    assert p["id"] == "op1"
    assert get_principal("nonexistent", gateway_db_path) is None


def test_principals_update_availability(gateway_db_path):
    """PATCH availability — real DB."""
    from hg_gateway.principals import upsert_principal, update_availability, get_principal
    upsert_principal("alice", "user", "Alice", status="offline", db_path=gateway_db_path)
    ok = update_availability("alice", status="away", timezone="Europe/London", db_path=gateway_db_path)
    assert ok is True
    p = get_principal("alice", gateway_db_path)
    assert p["status"] == "away"
    assert p["timezone"] == "Europe/London"
    ok = update_availability("nobody", status="online", db_path=gateway_db_path)
    assert ok is False


def test_resolve_available_principal(gateway_db_path):
    """First online or away principal in chain is returned."""
    from hg_gateway.principals import upsert_principal, resolve_available_principal
    upsert_principal("primary", "user", "Primary", status="offline", db_path=gateway_db_path)
    upsert_principal("secondary", "user", "Secondary", status="online", db_path=gateway_db_path)
    resolved = resolve_available_principal(["primary", "secondary"], gateway_db_path)
    assert resolved == "secondary"
    from hg_gateway.principals import update_availability
    update_availability("secondary", status="offline", db_path=gateway_db_path)
    resolved = resolve_available_principal(["primary", "secondary"], gateway_db_path)
    assert resolved == "primary"  # fallback to first in chain when none online/away


def test_resolve_available_principal_returns_first_online_or_away(gateway_db_path):
    """Resolve returns first principal with status online or away."""
    from hg_gateway.principals import upsert_principal, resolve_available_principal
    upsert_principal("a", "user", "A", status="offline", db_path=gateway_db_path)
    upsert_principal("b", "user", "B", status="away", db_path=gateway_db_path)
    upsert_principal("c", "user", "C", status="online", db_path=gateway_db_path)
    assert resolve_available_principal(["a", "b", "c"], gateway_db_path) == "b"
    assert resolve_available_principal(["a", "c"], gateway_db_path) == "c"
