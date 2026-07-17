"""Tests: science-mode → subagent-role mapping — explicit, validated, no string splitting."""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import pytest

from hg_runtime.overnight_daemon.role_mapping import (
    SCIENCE_MODE_TO_SUBAGENT_ROLE, resolve_subagent_role,
    validate_role_mapping,
)
from hg_runtime.overnight_daemon.subagents import (
    SUBAGENT_ROLES, registered_subagent_roles, is_registered_subagent_role,
    create_task,
)
from hg_runtime.overnight_daemon.scheduler import _SCIENCE_CYCLE


def test_maps_boring_explanation_first_to_registered_role():
    role = resolve_subagent_role("boring_explanation_first")
    assert role == "boring_explanation_worker"
    assert is_registered_subagent_role(role)


def test_maps_falsification_design_to_registered_role():
    role = resolve_subagent_role("falsification_design")
    assert role == "falsification_worker"
    assert is_registered_subagent_role(role)


def test_maps_units_and_math_audit_to_registered_role():
    role = resolve_subagent_role("units_and_math_audit")
    assert role == "units_math_audit_worker"
    assert is_registered_subagent_role(role)


def test_maps_public_safe_explainer_to_registered_role():
    role = resolve_subagent_role("public_safe_explainer")
    assert role == "public_safe_explainer_worker"
    assert is_registered_subagent_role(role)


def test_no_science_mode_uses_string_split_role():
    src = inspect.getsource(
        __import__("hg_runtime.overnight_daemon.scheduler", fromlist=["run_cycle"]).run_cycle
    )
    assert "mode.split(" not in src
    assert "split('_')[0]" not in src


def test_role_mapping_validates_against_registry():
    rv = validate_role_mapping(registered_subagent_roles(), set(_SCIENCE_CYCLE))
    assert rv.valid, f"missing={rv.missing_science_modes} unknown={rv.unknown_roles}"
    assert len(rv.missing_science_modes) == 0
    assert len(rv.unknown_roles) == 0


def test_all_scheduler_modes_have_mapping():
    for mode in _SCIENCE_CYCLE:
        role = resolve_subagent_role(mode)
        assert role is not None, f"no mapping for {mode}"
        assert is_registered_subagent_role(role), f"{role} not registered"


def test_all_mapped_roles_are_registered():
    for mode, role in SCIENCE_MODE_TO_SUBAGENT_ROLE.items():
        assert is_registered_subagent_role(role), \
            f"mode {mode} maps to unregistered role {role}"


def test_unknown_mode_returns_none():
    assert resolve_subagent_role("nonexistent_mode") is None


def test_validation_detects_missing_mode():
    rv = validate_role_mapping(registered_subagent_roles(), {"nonexistent_mode"})
    assert not rv.valid
    assert "nonexistent_mode" in rv.missing_science_modes


def test_validation_detects_unknown_role():
    mapping_with_bad_role = {"test_mode": "nonexistent_worker"}
    from hg_runtime.overnight_daemon import role_mapping
    orig = role_mapping.SCIENCE_MODE_TO_SUBAGENT_ROLE.copy()
    role_mapping.SCIENCE_MODE_TO_SUBAGENT_ROLE["test_mode"] = "nonexistent_worker"
    try:
        rv = validate_role_mapping(registered_subagent_roles(), {"test_mode"})
        assert not rv.valid
        assert "nonexistent_worker" in rv.unknown_roles
    finally:
        role_mapping.SCIENCE_MODE_TO_SUBAGENT_ROLE.clear()
        role_mapping.SCIENCE_MODE_TO_SUBAGENT_ROLE.update(orig)


def test_registered_subagent_roles_returns_set():
    roles = registered_subagent_roles()
    assert isinstance(roles, set)
    assert len(roles) >= 9


def test_is_registered_subagent_role():
    assert is_registered_subagent_role("falsification_worker")
    assert is_registered_subagent_role("boring_explanation_worker")
    assert not is_registered_subagent_role("nonexistent_worker")


def test_scheduler_uses_resolve_subagent_role():
    src = inspect.getsource(
        __import__("hg_runtime.overnight_daemon.scheduler", fromlist=["run_cycle"]).run_cycle
    )
    assert "resolve_subagent_role" in src
