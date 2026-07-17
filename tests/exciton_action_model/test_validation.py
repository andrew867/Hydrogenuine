"""Tests for action risk classification and phase-3 policy rules."""

from __future__ import annotations

import pytest

from hg_runtime.exciton_action_model import (
    AgentActionDecisionKind,
    AgentActionType,
    can_be_auto_approval_candidate,
    is_action_type_executable_in_phase3,
    is_action_type_forbidden_in_phase3,
    recommended_decision_for_action,
    requires_operator_review,
    requires_permit,
)
from hg_runtime.exciton_action_model.adapters import _base_request


def test_forbidden_action_types_representable_but_not_executable():
    for action_type in (
        AgentActionType.WEB_FORM_SUBMIT,
        AgentActionType.WEB_LOGIN,
        AgentActionType.SHELL_COMMAND,
        AgentActionType.SOURCE_PATCH,
        AgentActionType.MEMORY_MUTATION,
    ):
        req = _base_request(action_type)
        assert req.action_id
        assert is_action_type_forbidden_in_phase3(action_type)
        assert not is_action_type_executable_in_phase3(action_type)


def test_social_post_requires_operator_review():
    assert requires_operator_review(AgentActionType.SOCIAL_POST)
    assert requires_permit(AgentActionType.SOCIAL_POST)
    assert recommended_decision_for_action(AgentActionType.SOCIAL_POST) == AgentActionDecisionKind.REQUIRE_PERMIT


def test_social_draft_draft_only():
    assert recommended_decision_for_action(AgentActionType.SOCIAL_DRAFT) == AgentActionDecisionKind.ALLOW_DRAFT_ONLY


def test_web_read_url_read_only_candidate():
    assert recommended_decision_for_action(AgentActionType.WEB_READ_URL, trust_ok=True) == (
        AgentActionDecisionKind.ALLOW_READ_ONLY
    )


@pytest.mark.parametrize(
    "action_type",
    [
        AgentActionType.WEB_FORM_SUBMIT,
        AgentActionType.WEB_LOGIN,
    ],
)
def test_web_form_login_denied_future(action_type):
    assert recommended_decision_for_action(action_type) == AgentActionDecisionKind.DENY


def test_web_purchase_denied():
    assert recommended_decision_for_action(AgentActionType.WEB_PURCHASE) == AgentActionDecisionKind.DENY


def test_shell_command_denied():
    assert recommended_decision_for_action(AgentActionType.SHELL_COMMAND) == AgentActionDecisionKind.DENY


def test_source_patch_denied():
    assert recommended_decision_for_action(AgentActionType.SOURCE_PATCH) == AgentActionDecisionKind.DENY


def test_memory_mutation_denied():
    assert recommended_decision_for_action(AgentActionType.MEMORY_MUTATION) == AgentActionDecisionKind.DENY


def test_proof_open_read_only():
    assert recommended_decision_for_action(AgentActionType.PROOF_OPEN) == AgentActionDecisionKind.ALLOW_READ_ONLY


def test_status_refresh_read_only():
    assert recommended_decision_for_action(AgentActionType.STATUS_REFRESH) == AgentActionDecisionKind.ALLOW_READ_ONLY


def test_panic_stop_full_stop():
    assert recommended_decision_for_action(AgentActionType.PANIC_STOP) == AgentActionDecisionKind.FULL_STOP


def test_stop_soak_full_stop_or_control():
    decision = recommended_decision_for_action(AgentActionType.STOP_SOAK)
    assert decision == AgentActionDecisionKind.FULL_STOP


def test_auto_approval_candidate_excludes_high_risk():
    assert can_be_auto_approval_candidate(AgentActionType.PROOF_OPEN)
    assert can_be_auto_approval_candidate(AgentActionType.STATUS_REFRESH)
    assert not can_be_auto_approval_candidate(AgentActionType.SOCIAL_POST)
    assert not can_be_auto_approval_candidate(AgentActionType.SHELL_COMMAND)
    assert not can_be_auto_approval_candidate(AgentActionType.WEB_PURCHASE)
