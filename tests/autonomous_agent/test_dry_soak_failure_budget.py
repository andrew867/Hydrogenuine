"""Dry soak failure budget tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.dry_soak.errors import FailureBudgetExceeded
from hg_runtime.dry_soak.failure_budget import new_failure_budget_state


def test_rejects_missing_receipt():
    state = new_failure_budget_state()
    with pytest.raises(FailureBudgetExceeded):
        state.record_missing_receipt()


def test_rejects_replay_failure():
    state = new_failure_budget_state()
    with pytest.raises(FailureBudgetExceeded):
        state.record_replay_failure()


def test_rejects_external_side_effect():
    state = new_failure_budget_state()
    with pytest.raises(FailureBudgetExceeded):
        state.record_external_side_effect()


def test_rejects_fixture_truth():
    state = new_failure_budget_state()
    with pytest.raises(FailureBudgetExceeded):
        state.record_fixture_truth()


def test_allows_provider_unavailable():
    state = new_failure_budget_state()
    state.record_provider_unavailable()
    state.record_provider_unavailable()
    assert state.counters.consecutive_provider_unavailable == 2


def test_allows_live_read_unavailable():
    state = new_failure_budget_state()
    state.record_live_read_unavailable()
    assert state.counters.consecutive_live_read_unavailable == 1
