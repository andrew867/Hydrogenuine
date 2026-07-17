"""Tests for main brain candidate trials."""

from __future__ import annotations

import pytest

from hg_runtime.profile_model_autopilot.main_brain_trials import (
    propose_trial, can_zero_permanently_switch, persistent_change_requires_operator,
    trial_comparison_dimensions,
)
from hg_runtime.profile_model_autopilot.proposal import propose, dispose


def test_zero_can_propose_main_brain_trial():
    p = propose(proposal_kind="main_brain_trial", proposed_at="t", model_id="qwen2.5-7b-instruct")
    assert p.proposal_kind == "main_brain_trial"


def test_main_brain_trial_is_temporary():
    t = propose_trial("trial1", "qwen2.5-7b-instruct")
    assert t.temporary is True
    assert t.permanent_switch is False


def test_permanent_switch_requires_operator_approval():
    t = propose_trial("trial1", "qwen2.5-7b-instruct")
    assert persistent_change_requires_operator(t) is True


def test_zero_cannot_permanently_switch_main_brain():
    assert can_zero_permanently_switch() is False
    t = propose_trial("trial1", "qwen2.5-7b-instruct")
    assert t.permanent_switch_allowed_by_zero is False


def test_trial_result_is_recommendation_not_permission():
    t = propose_trial("trial1", "qwen2.5-7b-instruct")
    assert t.result_is_recommendation_only is True


def test_trial_writes_receipts():
    # A trial proposal carries a receipt hash via the proposal layer.
    p = propose(proposal_kind="main_brain_trial", proposed_at="t", model_id="qwen2.5-7b-instruct")
    assert p.receipt_hash


def test_trial_dispose_is_modified_not_permanent():
    p = propose(proposal_kind="main_brain_trial", proposed_at="t", model_id="qwen2.5-7b-instruct")
    d = dispose(p, decided_at="t")
    assert d.decision == "modified"
    assert d.modified_fields.get("permanent_switch") is False


def test_forbidden_candidate_rejected():
    t = propose_trial("trial1", "deepseek-v3")
    assert t.candidate_allowed is False


def test_comparison_dimensions_present():
    dims = trial_comparison_dimensions()
    assert "receipt_quality" in dims
    assert "boundary_adherence" in dims
    assert "falsification_target_quality" in dims
