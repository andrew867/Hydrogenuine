from __future__ import annotations

import pytest

from hg_learning.guardrails.learnable_allowlist import (
    AllowlistEntry,
    AllowlistViolation,
    load_allowlist,
)


def test_unlisted_parameter_write_rejected():
    allowlist = load_allowlist()
    with pytest.raises(AllowlistViolation):
        allowlist.validate_write("not.a.real.param", 1.0, path_name="symmetry_feedback")


def test_safety_parameters_unregisterable():
    with pytest.raises(AllowlistViolation):
        load_allowlist().register_parameter(
            AllowlistEntry(
                key="safety_gate.level_threshold",
                path="symmetry_feedback",
                floor=0.0,
                ceiling=1.0,
                default=0.5,
            )
        )


def test_watchdog_prefix_rejected():
    with pytest.raises(AllowlistViolation):
        load_allowlist().register_parameter(
            AllowlistEntry(
                key="watchdog.timeout_ms",
                path="detector_tuner",
                floor=1.0,
                ceiling=100.0,
                default=10.0,
            )
        )


def test_allowlist_not_self_extensible():
    with pytest.raises(AllowlistViolation):
        load_allowlist().register_parameter(
            AllowlistEntry(
                key="learnable_allowlist.extra",
                path="symmetry_feedback",
                floor=0.0,
                ceiling=1.0,
                default=0.5,
            )
        )


def test_bounds_clamp():
    allowlist = load_allowlist()
    entry = allowlist.get("symmetry_breaker.default_delta")
    assert entry is not None
    assert allowlist.validate_write(entry.key, 999.0, path_name=entry.path) == entry.ceiling
    assert allowlist.validate_write(entry.key, 0.001, path_name=entry.path) == entry.floor


def test_wrong_path_rejected():
    allowlist = load_allowlist()
    with pytest.raises(AllowlistViolation):
        allowlist.validate_write(
            "symmetry_breaker.default_delta",
            0.12,
            path_name="detector_tuner",
        )
