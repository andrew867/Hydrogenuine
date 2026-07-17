"""Operator absence policy tests."""

from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.bounded_soak.operator_absence import (  # noqa: E402
    FORBIDDEN_EXTERNAL_ACTIONS,
    OperatorPresenceState,
    evaluate_operator_absence,
)


def test_operator_absent_refuses_external_actions():
    for action in FORBIDDEN_EXTERNAL_ACTIONS:
        decision = evaluate_operator_absence(
            operator_state=OperatorPresenceState.OPERATOR_ABSENT,
            chosen_action=action,
        )
        assert decision.allowed is False
        assert decision.refusal_verdict == "RED_OPERATOR_ABSENT_EXTERNAL_REFUSED"
        assert decision.witness_receipt_ref


def test_operator_absent_allows_internal_actions():
    for action in (
        "synthesize_internal_notes",
        "propose_operator_question",
        "request_more_scope",
        "rest_turn",
        "witness_turn",
    ):
        decision = evaluate_operator_absence(
            operator_state=OperatorPresenceState.OPERATOR_ABSENT,
            chosen_action=action,
        )
        assert decision.allowed is True
        assert decision.refusal_verdict == "YELLOW_OPERATOR_ABSENT_INTERNAL_ONLY"


def test_operator_unknown_is_restrictive():
    decision = evaluate_operator_absence(
        operator_state=OperatorPresenceState.OPERATOR_UNKNOWN,
        chosen_action="publish",
    )
    assert decision.allowed is False

    internal = evaluate_operator_absence(
        operator_state=OperatorPresenceState.OPERATOR_UNKNOWN,
        chosen_action="rest_turn",
    )
    assert internal.allowed is True
