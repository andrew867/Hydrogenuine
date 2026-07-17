"""CSM Phase 1 — classification, policy, lifecycle."""

from __future__ import annotations

from hg_csm import (
    OUTCOME_ALLOWED,
    OUTCOME_NEEDS_EXTRA_HIGH_RISK,
    OUTCOME_NEEDS_HUMAN_APPROVAL,
    OUTCOME_REFUSED,
    STATE_CSM_ALLOWED,
    STATE_CSM_REFUSED,
    STATE_HUMAN_APPROVAL_REQUIRED,
    STATE_PROPOSED,
    STATE_TER_READY,
    ChangeRequest,
    classify_file,
    evaluate_change,
    validate_transition,
)
from hg_csm.types import record_hash

NOW = "2026-06-11T12:00:00.000000Z"


def _request(files: tuple[str, ...], **kwargs) -> ChangeRequest:
    return ChangeRequest(
        change_id="csm_test_1",
        source="srp",
        bundle_id="bundle_1",
        bundle_hash="sha256:abc",
        proposed_files=files,
        proposed_commands=kwargs.get("commands", ("pytest tests/srp -q",)),
        required_tests=kwargs.get("tests", ("pytest tests/srp -q",)),
        risk_class=kwargs.get("risk_class", "low"),
        purpose=kwargs.get("purpose", "maintenance"),
        created_at=NOW,
        requested_by="test",
    )


def test_low_risk_docs_allowed():
    decision = evaluate_change(_request(("docs/reports/phases/test_status.md",)))
    assert decision.outcome == OUTCOME_ALLOWED
    assert classify_file("docs/reports/phases/x.md") == "low"


def test_medium_risk_requires_approval():
    decision = evaluate_change(_request(("hg_srp/bundle.py",), tests=("pytest tests/srp -q",)))
    assert decision.outcome == OUTCOME_NEEDS_HUMAN_APPROVAL


def test_high_risk_requires_extra_confirmation():
    decision = evaluate_change(_request(("hg_ter/policy.py",), tests=("pytest tests/ter -q",)))
    assert decision.outcome == OUTCOME_NEEDS_EXTRA_HIGH_RISK


def test_prohibited_secret_refused():
    decision = evaluate_change(_request((".env.production",), tests=()))
    assert decision.outcome == OUTCOME_REFUSED
    assert "prohibited" in decision.reason_code


def test_policy_self_relaxation_refused():
    decision = evaluate_change(
        _request(("hg_ter/policy.py",), purpose="relax policy enforcement", tests=("pytest tests/ter -q",))
    )
    assert decision.outcome == OUTCOME_REFUSED
    assert decision.reason_code == "policy_self_relaxation_refused"


def test_illegal_lifecycle_transitions():
    assert not validate_transition(STATE_PROPOSED, STATE_TER_READY).ok
    assert not validate_transition(STATE_CSM_REFUSED, STATE_TER_READY).ok
    assert not validate_transition(STATE_HUMAN_APPROVAL_REQUIRED, STATE_TER_READY, human_approved=False).ok
    assert not validate_transition(STATE_PROPOSED, "MERGED").ok
    assert validate_transition(STATE_CSM_ALLOWED, STATE_TER_READY, csm_allowed=True).ok


def test_decision_hash_deterministic():
    req = _request(("docs/proofs/test.json",))
    d1 = evaluate_change(req)
    d2 = evaluate_change(req)
    assert d1.decision_hash == d2.decision_hash
