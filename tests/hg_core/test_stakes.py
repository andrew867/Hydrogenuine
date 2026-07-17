"""Tests for Sticky Reality Ch1 stakes and gating."""
from __future__ import annotations

import pytest
from pathlib import Path

from hg_core.stakes import load_policy, get_action_cost, get_trust_band_limits, check_gate, GateResult


def test_load_policy_default_when_no_file(tmp_path):
    """load_policy returns default when no YAML file."""
    policy = load_policy(tmp_path)
    assert "action_costs" in policy
    assert "budget" in policy


def test_get_action_cost():
    """get_action_cost returns cost from policy or 1.0."""
    policy = {"action_costs": {"READ": 0.1, "WRITE": 1.0}}
    assert get_action_cost(policy, "READ") == 0.1
    assert get_action_cost(policy, "UNKNOWN") == 1.0


def test_check_gate_allowed():
    """check_gate returns allowed when under budget and band ok."""
    r = check_gate("READ", "agent1", current_budget_used=0, trust_band=1, escrow_locked=0)
    assert r.allowed is True
    assert r.reason == "ok"


def test_check_gate_deny_budget():
    """check_gate denies when budget would be exceeded (hard limit)."""
    r = check_gate("WRITE", "agent1", current_budget_used=99, trust_band=2, escrow_locked=0)
    # default limit 100, cost 1.0 -> 99+1=100, allowed
    r2 = check_gate("WRITE", "agent1", current_budget_used=100, trust_band=2, escrow_locked=0)
    assert r2.allowed is False
    assert "budget" in r2.reason.lower()
