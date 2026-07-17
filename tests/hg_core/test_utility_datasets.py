"""Pack 22: Tests for utility datasets loader and validation."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from hg_core.utility.datasets import (
    get_tag_allowlist,
    load_outcomes_v1,
    load_suites,
    load_templates,
    load_targets_v1,
    validate_outcomes,
    validate_suites,
    validate_targets,
)


def test_load_outcomes_v1() -> None:
    o = load_outcomes_v1()
    assert len(o) > 0
    first = o[0]
    assert "outcome_id" in first
    assert "text" in first
    assert "tags" in first


def test_load_suites() -> None:
    s = load_suites()
    assert isinstance(s, dict)
    assert "power_seeking_v1" in s or "corrigibility_reversal_v1" in s


def test_load_templates() -> None:
    t = load_templates()
    assert isinstance(t, dict)
    assert "pairwise_v1" in t or "pairwise_indiff_v1" in t


def test_load_targets_v1() -> None:
    t = load_targets_v1()
    assert isinstance(t, dict)


def test_validate_outcomes_unique_id() -> None:
    outcomes = [
        {"outcome_id": "a", "text": "x", "tags": ["t1"]},
        {"outcome_id": "a", "text": "y", "tags": ["t1"]},
    ]
    ok, errs = validate_outcomes(outcomes, tag_allowlist={"t1"})
    assert not ok
    assert any("duplicate" in e for e in errs)


def test_validate_outcomes_required_fields() -> None:
    outcomes = [{"outcome_id": "a", "text": "x", "tags": ["t1"]}]
    ok, _ = validate_outcomes(outcomes, tag_allowlist={"t1"})
    assert ok
    outcomes_bad = [{"outcome_id": "a", "tags": ["t1"]}]
    ok2, errs2 = validate_outcomes(outcomes_bad, tag_allowlist={"t1"})
    assert not ok2
    assert any("text" in e for e in errs2)


def test_validate_outcomes_tag_allowlist() -> None:
    outcomes = [{"outcome_id": "a", "text": "x", "tags": ["bad_tag"]}]
    ok, errs = validate_outcomes(outcomes, tag_allowlist={"good_tag"})
    assert not ok
    assert any("allowlist" in e for e in errs)
