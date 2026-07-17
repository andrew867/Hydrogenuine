#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for overseer_access (hg_memory).

Tests permission checks, identity report shapes when identity graph
unavailable, and search_agent_identity behavior.
"""

import sys
import pytest
from pathlib import Path

workspace_root = Path(__file__).resolve().parent.parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from hg_memory.overseer_access import OverseerAccess, get_overseer_access


class TestOverseerAccessPermission:
    """Test permission and access control."""

    def test_is_overseer(self):
        access = OverseerAccess()
        assert access._is_overseer("overseer") is True
        assert access._is_overseer("agent-x") is False

    def test_can_access_agent_overseer_can_access_any(self):
        access = OverseerAccess()
        assert access._can_access_agent("overseer", "any-agent") is True
        assert access._can_access_agent("overseer", "other") is True

    def test_can_access_agent_self_only(self):
        access = OverseerAccess()
        assert access._can_access_agent("agent-a", "agent-a") is True
        assert access._can_access_agent("agent-a", "agent-b") is False

    def test_search_agent_identity_denies_non_overseer_non_self(self):
        access = OverseerAccess()
        with pytest.raises(PermissionError) as exc:
            access.search_agent_identity(
                requester_id="agent-a",
                target_agent_id="agent-b",
                query="test",
            )
        assert "cannot access identity" in str(exc.value).lower() or "cannot access" in str(exc.value).lower()

    def test_search_agent_identity_overseer_allowed(self):
        access = OverseerAccess()
        result = access.search_agent_identity(
            requester_id="overseer",
            target_agent_id="any-agent",
            query="test",
        )
        assert isinstance(result, list)

    def test_get_identity_evolution_report_denies_non_overseer_non_self(self):
        access = OverseerAccess()
        with pytest.raises(PermissionError):
            access.get_identity_evolution_report(
                requester_id="agent-a",
                target_agent_id="agent-b",
                days=30,
            )

    def test_get_identity_evolution_report_returns_shape_when_unavailable(self):
        access = OverseerAccess()
        report = access.get_identity_evolution_report(
            requester_id="overseer",
            target_agent_id="nonexistent-agent-no-db",
            days=30,
        )
        assert isinstance(report, dict)
        assert "period_days" in report
        assert "total_evolutions" in report
        assert "evolutions_by_type" in report
        assert "most_evolved_entities" in report
        assert "evolution_timeline" in report
        assert report["period_days"] == 30
        assert report["total_evolutions"] == 0

    def test_get_identity_conflict_report_denies_non_overseer_non_self(self):
        access = OverseerAccess()
        with pytest.raises(PermissionError):
            access.get_identity_conflict_report(
                requester_id="agent-a",
                target_agent_id="agent-b",
            )

    def test_get_identity_conflict_report_returns_shape_when_unavailable(self):
        access = OverseerAccess()
        report = access.get_identity_conflict_report(
            requester_id="overseer",
            target_agent_id="nonexistent-agent-no-db",
        )
        assert isinstance(report, dict)
        assert "total_conflicts" in report
        assert "conflicts_by_type" in report
        assert "conflicting_pairs" in report
        assert report["total_conflicts"] == 0
        assert isinstance(report["conflicting_pairs"], list)


class TestOverseerAccessSingleton:
    """Test get_overseer_access singleton."""

    def test_get_overseer_access_returns_overseer_access_instance(self):
        inst = get_overseer_access()
        assert isinstance(inst, OverseerAccess)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
