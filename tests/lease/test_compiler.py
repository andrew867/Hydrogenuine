"""Compiler: ambiguity asks, never guesses permissively; no code execution."""

from hg_lease.compiler import ClarificationNeeded, compile_draft
from hg_lease.policy import CanonicalPolicy


def full_draft(**overrides):
    base = dict(
        subjects=["agent:zero"],
        actions=["open_window"],
        objects=["window:kitchen_west"],
        purpose="ventilation",
        risk_class="LOW",
        valid_from="2026-07-17T00:00:00.000000Z",
        valid_until="2026-07-24T00:00:00.000000Z",
        numeric_limits=[{"parameter": "opening", "max_value": 100.0, "unit": "mm"}],
    )
    base.update(overrides)
    return base


def test_complete_draft_compiles():
    policy = compile_draft(full_draft(), issuer_operator_id="op:local")
    assert isinstance(policy, CanonicalPolicy)
    assert policy.display_summary
    assert "100.0 mm" in policy.display_summary
    assert policy.unknown_fact_policy == "DENY"  # conservative default


def test_missing_fields_ask_instead_of_defaulting():
    for missing in ("subjects", "actions", "objects", "purpose", "valid_until", "risk_class"):
        d = full_draft()
        d.pop(missing)
        result = compile_draft(d, issuer_operator_id="op:local")
        assert isinstance(result, ClarificationNeeded), missing
        assert result.questions


def test_wildcard_asks_for_exact_values():
    result = compile_draft(full_draft(objects=["*"]), issuer_operator_id="op:local")
    assert isinstance(result, ClarificationNeeded)
    assert any("wildcard" in q.lower() for q in result.questions)


def test_high_risk_draft_refused_by_default():
    result = compile_draft(full_draft(risk_class="HIGH"), issuer_operator_id="op:local")
    assert isinstance(result, ClarificationNeeded)
    assert any("high_risk_not_leaseable" in q for q in result.questions)


def test_moderate_requires_opt_in_flag():
    refused = compile_draft(full_draft(risk_class="MODERATE"), issuer_operator_id="op:local")
    assert isinstance(refused, ClarificationNeeded)
    allowed = compile_draft(
        full_draft(risk_class="MODERATE"), issuer_operator_id="op:local", allow_moderate=True
    )
    assert isinstance(allowed, CanonicalPolicy)


def test_unknown_condition_type_cannot_execute():
    result = compile_draft(
        full_draft(condition={"type": "shell", "cmd": "rm -rf /"}),
        issuer_operator_id="op:local",
    )
    assert isinstance(result, ClarificationNeeded)
    assert any("could not be compiled safely" in q for q in result.questions)


def test_unrecognized_risk_class_asks():
    result = compile_draft(full_draft(risk_class="MEDIUM"), issuer_operator_id="op:local")
    assert isinstance(result, ClarificationNeeded)


def test_empty_validity_window_refused():
    result = compile_draft(
        full_draft(valid_until="2026-07-17T00:00:00.000000Z"),
        issuer_operator_id="op:local",
    )
    assert isinstance(result, ClarificationNeeded)
    assert any("empty_validity_window" in q for q in result.questions)
