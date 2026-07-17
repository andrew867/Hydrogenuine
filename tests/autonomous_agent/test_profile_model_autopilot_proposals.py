"""Tests for autopilot proposals + runtime disposition."""

from __future__ import annotations

import pytest

from hg_runtime.profile_model_autopilot.proposal import propose, dispose

AT = "2026-06-24T00:00:00Z"


def test_zero_can_propose_profile_assignment():
    p = propose(proposal_kind="profile_assignment", proposed_at=AT, task_id="t",
                profile_id="persona_historical_ada_lovelace")
    assert p.proposal_kind == "profile_assignment"
    assert p.receipt_hash


def test_zero_can_propose_model_assignment():
    p = propose(proposal_kind="model_assignment", proposed_at=AT, model_id="google/gemma-4-e4b")
    assert p.proposal_kind == "model_assignment"


def test_zero_can_propose_task_selection():
    p = propose(proposal_kind="task_selection", proposed_at=AT, task_id="t")
    assert p.proposal_kind == "task_selection"


def test_zero_can_propose_research_seed_selection():
    p = propose(proposal_kind="research_seed_selection", proposed_at=AT,
                research_seed_id="observer_state_frequency_hypothesis")
    assert p.research_seed_id == "observer_state_frequency_hypothesis"


def test_zero_can_propose_science_mode_assignment():
    p = propose(proposal_kind="science_mode_assignment", proposed_at=AT,
                science_mode_id="assume_real")
    assert p.science_mode_id == "assume_real"


def test_proposal_grants_no_authority():
    p = propose(proposal_kind="profile_assignment", proposed_at=AT)
    assert p.authority_requested is False


def test_proposal_authorizes_no_tools():
    p = propose(proposal_kind="model_assignment", proposed_at=AT)
    assert p.tools_requested is False


def test_proposal_creates_no_live_effects():
    p = propose(proposal_kind="task_selection", proposed_at=AT)
    assert p.live_effects_requested is False


def test_proposal_requires_receipt():
    p = propose(proposal_kind="task_selection", proposed_at=AT, task_id="t")
    assert p.receipt_hash == p.compute_hash()


def test_proposal_can_be_denied():
    p = propose(proposal_kind="model_assignment", proposed_at=AT, model_id="deepseek-v3")
    d = dispose(p, decided_at=AT)
    assert d.decision == "denied"


def test_proposal_can_be_modified_by_runtime():
    p = propose(proposal_kind="model_assignment", proposed_at=AT,
                model_id="google/gemma-4-e4b", requested_model_slot="large_synthesis")
    d = dispose(p, decided_at=AT)
    assert d.decision == "modified"


def test_self_authorization_always_denied():
    p = propose(proposal_kind="task_selection", proposed_at=AT, task_id="t")
    p.tools_requested = True
    d = dispose(p, decided_at=AT)
    assert d.decision == "denied"
    assert d.tools_authorized is False
