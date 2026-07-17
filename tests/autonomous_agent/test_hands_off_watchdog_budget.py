"""Watchdog budget tests."""
from __future__ import annotations

import pytest

from hg_runtime.hands_off_session.errors import HandsOffBudgetError
from hg_runtime.hands_off_session.watchdog_budget import WatchdogBudget


def test_missing_receipt_stops():
    b = WatchdogBudget()
    b.missing_receipts = 1
    with pytest.raises(HandsOffBudgetError):
        b._enforce()


def test_external_side_effect_stops():
    b = WatchdogBudget()
    b.external_side_effects = 1
    with pytest.raises(HandsOffBudgetError):
        b._enforce()


def test_resource_pressure_yellow():
    b = WatchdogBudget(max_resource_pressure_level_before_pause=3)
    b.resource_pressure_level = 3
    with pytest.raises(HandsOffBudgetError):
        b._enforce()
