"""Policy AST: typed, bounded, fail-closed."""

import pytest

from hg_lease.policy import (
    AllOf,
    AnyOf,
    CanonicalPolicy,
    EvalContext,
    FactCondition,
    NotCond,
    NumericLimit,
    PolicyValidationError,
    TimeWindowCondition,
    condition_from_payload,
    validate_policy,
)
from hg_lease.stores import SituationFact

NOW = "2026-07-17T12:00:00.000000Z"


def fact(name, value, unit=None, expires_at=None):
    return SituationFact(
        name=name, typed_value=value, unit=unit,
        observed_at=NOW, source_id="sim:test", expires_at=expires_at,
    )


def ctx(*facts):
    return EvalContext(facts={f.name: f for f in facts}, now_wall=NOW)


def test_comparison_ops_allow_and_deny():
    cond = FactCondition("outdoor_temp_c", "gt", 21.0, unit="C")
    assert cond.evaluate(ctx(fact("outdoor_temp_c", 25.0, "C"))).ok
    res = cond.evaluate(ctx(fact("outdoor_temp_c", 18.0, "C")))
    assert not res.ok and any("condition_false" in r for r in res.reasons)


def test_unknown_fact_fails_closed():
    cond = FactCondition("raining", "eq", False)
    res = cond.evaluate(ctx())
    assert not res.ok
    assert any("unknown_fact" in r for r in res.reasons)


def test_stale_fact_fails_closed():
    cond = FactCondition("raining", "eq", False)
    res = cond.evaluate(ctx(fact("raining", False, expires_at="2026-07-17T11:00:00.000000Z")))
    assert not res.ok
    assert any("stale_fact" in r for r in res.reasons)


def test_unit_mismatch_fails_closed():
    cond = FactCondition("outdoor_temp_c", "gt", 70.0, unit="F")
    res = cond.evaluate(ctx(fact("outdoor_temp_c", 25.0, "C")))
    assert not res.ok
    assert any("unit_mismatch" in r for r in res.reasons)


def test_not_of_unknown_fact_still_fails_closed():
    """NOT(unknown) must never become an allow path."""
    cond = NotCond(FactCondition("alarm_armed", "eq", True))
    res = cond.evaluate(ctx())
    assert not res.ok
    assert any("unknown_fact" in r for r in res.reasons)


def test_not_inverts_known_fact():
    cond = NotCond(FactCondition("alarm_armed", "eq", True))
    assert cond.evaluate(ctx(fact("alarm_armed", False))).ok
    assert not cond.evaluate(ctx(fact("alarm_armed", True))).ok


def test_boolean_composition():
    cond = AllOf((
        FactCondition("someone_home", "eq", True),
        AnyOf((
            FactCondition("outdoor_temp_c", "gt", 21.0, unit="C"),
            FactCondition("manual_override", "eq", True),
        )),
    ))
    good = ctx(fact("someone_home", True), fact("outdoor_temp_c", 24.0, "C"))
    assert cond.evaluate(good).ok
    bad = ctx(fact("someone_home", False), fact("outdoor_temp_c", 24.0, "C"))
    assert not cond.evaluate(bad).ok


def test_time_window_inside_outside_and_midnight_crossing():
    day = TimeWindowCondition("09:00", "18:00")
    assert day.evaluate(ctx()).ok  # NOW is 12:00
    night = TimeWindowCondition("22:00", "06:00")
    res = night.evaluate(ctx())
    assert not res.ok


def test_disallowed_op_rejected():
    with pytest.raises(PolicyValidationError):
        FactCondition("x", "matches_regex", ".*")


def test_condition_from_payload_rejects_unknown_type():
    with pytest.raises(PolicyValidationError):
        condition_from_payload({"type": "python_eval", "code": "1==1"})


def test_condition_payload_roundtrip():
    cond = AllOf((
        FactCondition("raining", "eq", False),
        TimeWindowCondition("09:00", "18:00"),
        NotCond(FactCondition("alarm_armed", "eq", True)),
    ))
    rebuilt = condition_from_payload(cond.to_payload())
    assert rebuilt.to_payload() == cond.to_payload()


def test_numeric_limit_requires_unit_and_bounds():
    with pytest.raises(PolicyValidationError):
        NumericLimit(parameter="opening", max_value=100, unit="")
    limit = NumericLimit(parameter="opening", max_value=100, unit="mm")
    assert limit.check({"opening": {"value": 80, "unit": "mm"}}).ok
    assert not limit.check({"opening": {"value": 150, "unit": "mm"}}).ok
    assert not limit.check({"opening": {"value": 80, "unit": "cm"}}).ok
    assert not limit.check({}).ok
    assert not limit.check({"opening": {"value": "80", "unit": "mm"}}).ok


def _policy(**overrides):
    base = dict(
        policy_id="pol_x",
        issuer_operator_id="op:local",
        subjects=("agent:zero",),
        actions=("open_window",),
        objects=("window:kitchen_west",),
        purpose="ventilation",
        condition=None,
        numeric_limits=(),
        risk_class="LOW",
        renewal_mode="MANUAL",
        unknown_fact_policy="DENY",
        valid_from="2026-07-17T00:00:00.000000Z",
        valid_until="2026-07-24T00:00:00.000000Z",
        display_summary="test policy",
    )
    base.update(overrides)
    return CanonicalPolicy(**base)


def test_validate_policy_happy_path():
    assert validate_policy(_policy()) == []


def test_wildcard_scope_flagged():
    problems = validate_policy(_policy(objects=("*",)))
    assert "policy.wildcard_scope_requires_dedicated_confirmation" in problems


def test_high_risk_not_leaseable_by_default():
    problems = validate_policy(_policy(risk_class="HIGH"))
    assert "policy.high_risk_not_leaseable" in problems
    assert validate_policy(_policy(risk_class="HIGH"), allow_high_risk_local_policy=True) == []


def test_moderate_risk_requires_opt_in():
    problems = validate_policy(_policy(risk_class="MODERATE"))
    assert "policy.moderate_risk_requires_explicit_opt_in" in problems
    assert validate_policy(_policy(risk_class="MODERATE"), allow_moderate=True) == []


def test_canonical_hash_stable_and_sensitive():
    a, b = _policy(), _policy()
    assert a.canonical_policy_hash == b.canonical_policy_hash
    c = _policy(purpose="different")
    assert c.canonical_policy_hash != a.canonical_policy_hash
