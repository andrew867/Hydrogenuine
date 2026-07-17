from __future__ import annotations

import pytest

from hg_aep.severity import (
    HysteresisState,
    decayed_severity,
    map_measurement_to_severity,
    max_only_aggregate,
    validate_severity_ordinal,
)


NOW = "2026-06-11T03:00:00.000000Z"
LATER = "2026-06-11T03:01:00.000000Z"


def test_ordinal_severity_validation():
    validate_severity_ordinal(0)
    validate_severity_ordinal(10)
    with pytest.raises(ValueError):
        validate_severity_ordinal(11)
    with pytest.raises(ValueError):
        validate_severity_ordinal(3.5)


def test_anchor_mapping_is_deterministic():
    assert map_measurement_to_severity("UNCERTAINTY", 0.6) == 0
    assert map_measurement_to_severity("UNCERTAINTY", 0.4) == 3
    assert map_measurement_to_severity("UNCERTAINTY", 0.04) == 9
    assert map_measurement_to_severity("RESOURCE_PRESSURE", 0.91) == 7


def test_max_only_aggregation_never_sums():
    assert max_only_aggregate([3, 3, 3, 6]) == 6
    assert max_only_aggregate([10, 1, 1, 1]) == 10


def test_decay_is_deterministic_and_testable():
    assert decayed_severity(7, emitted_at=NOW, computed_at=NOW, ttl_s=600, decay_half_life_s=120) == 7
    assert decayed_severity(7, emitted_at=NOW, computed_at=LATER, ttl_s=600, decay_half_life_s=120) == 5


def test_hysteresis_engages_fast_and_releases_slowly():
    state = HysteresisState()
    assert state.evaluate(6, engage_threshold=5, release_threshold=3, observed_at=NOW) is True
    assert state.engaged is True
    assert state.evaluate(2, engage_threshold=5, release_threshold=3, observed_at=NOW) is True
    assert state.evaluate(2, engage_threshold=5, release_threshold=3, observed_at=LATER) is False
