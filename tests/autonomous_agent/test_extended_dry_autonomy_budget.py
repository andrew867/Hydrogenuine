"""Endurance budget tests."""

from __future__ import annotations

import pytest

from hg_runtime.extended_dry_autonomy.endurance_budget import new_endurance_budget_state
from hg_runtime.extended_dry_autonomy.errors import EnduranceBudgetExceeded


def test_rejects_missing_receipt():
    b = new_endurance_budget_state()
    with pytest.raises(EnduranceBudgetExceeded):
        b.record_missing_receipt()


def test_rejects_replay_failure():
    b = new_endurance_budget_state()
    with pytest.raises(EnduranceBudgetExceeded):
        b.record_replay_failure()


def test_rejects_checkpoint_failure():
    b = new_endurance_budget_state()
    with pytest.raises(EnduranceBudgetExceeded):
        b.record_checkpoint_failure()


def test_rejects_external_side_effect():
    b = new_endurance_budget_state()
    with pytest.raises(EnduranceBudgetExceeded):
        b.record_external_side_effect()


def test_rejects_fixture_truth():
    b = new_endurance_budget_state()
    with pytest.raises(EnduranceBudgetExceeded):
        b.record_fixture_truth()


def test_provider_unavailable_does_not_raise_budget():
    b = new_endurance_budget_state()
    assert b.counters.red_turns == 0
