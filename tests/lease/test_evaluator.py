"""Deterministic evaluator: allow, deny, replay, clock, reproducibility."""

from hg_lease.evaluator import (
    ActionRequest,
    OUTCOME_ALLOW,
    OUTCOME_ASK,
    OUTCOME_DENY,
    OUTCOME_ERROR,
    evaluate,
)
from hg_lease.lease import CapabilityLease
from hg_lease.policy import (
    AllOf,
    CanonicalPolicy,
    FactCondition,
    NotCond,
    NumericLimit,
    TimeWindowCondition,
)
from hg_lease.stores import SituationFact

NOW = "2026-07-17T12:00:00.000000Z"
MONO = 500.0


def make_policy(**overrides):
    base = dict(
        policy_id="pol_1",
        issuer_operator_id="op:local",
        subjects=("agent:zero",),
        actions=("open_window",),
        objects=("window:kitchen_west",),
        purpose="ventilation",
        condition=AllOf((
            TimeWindowCondition("09:00", "18:00"),
            FactCondition("outdoor_temp_c", "gt", 21.0, unit="C"),
            FactCondition("raining", "eq", False),
            NotCond(FactCondition("alarm_armed", "eq", True)),
            FactCondition("someone_home", "eq", True),
        )),
        numeric_limits=(NumericLimit(parameter="opening", max_value=100.0, unit="mm"),),
        risk_class="LOW",
        renewal_mode="MANUAL",
        unknown_fact_policy="DENY",
        valid_from="2026-07-17T00:00:00.000000Z",
        valid_until="2026-07-24T00:00:00.000000Z",
        display_summary="window lease",
    )
    base.update(overrides)
    return CanonicalPolicy(**base)


def make_lease(policy, **overrides):
    base = dict(
        lease_id="lease_1",
        policy_id=policy.policy_id,
        policy_hash=policy.canonical_policy_hash,
        issuer="op:local",
        subject="agent:zero",
        action_scope=policy.actions,
        object_scope=policy.objects,
        purpose_scope=(policy.purpose,),
        issued_at_wall=NOW,
        issued_at_monotonic_anchor=100.0,
        not_before=policy.valid_from,
        expires_at=policy.valid_until,
        risk_class="LOW",
        state="ACTIVE",
        remaining_uses=None,
    )
    base.update(overrides)
    return CapabilityLease(**base)


def good_snapshot():
    def fact(name, value, unit=None):
        return SituationFact(name=name, typed_value=value, unit=unit,
                             observed_at=NOW, source_id="sim", fact_id=f"fact_{name}")
    return {
        "outdoor_temp_c": fact("outdoor_temp_c", 24.0, "C"),
        "raining": fact("raining", False),
        "alarm_armed": fact("alarm_armed", False),
        "someone_home": fact("someone_home", True),
    }


def request(**overrides):
    base = dict(
        request_id="req_1",
        subject="agent:zero",
        action_type="open_window",
        object_id="window:kitchen_west",
        purpose="ventilation",
        requested_at=NOW,
        parameters={"opening": {"value": 80, "unit": "mm"}},
    )
    base.update(overrides)
    return ActionRequest(**base)


def run(req=None, lease=None, policy=None, snapshot=None, **kw):
    policy = policy or make_policy()
    lease = lease if lease is not None else make_lease(policy)
    return evaluate(
        req or request(), lease, policy,
        good_snapshot() if snapshot is None else snapshot,
        now_wall=kw.get("now_wall", NOW),
        now_monotonic=kw.get("now_monotonic", MONO),
        seen_request_ids=kw.get("seen_request_ids"),
    )


def test_happy_path_allows():
    decision = run()
    assert decision.outcome == OUTCOME_ALLOW
    assert decision.reason_codes == ()


def test_no_lease_denies():
    decision = evaluate(request(), None, None, good_snapshot(),
                        now_wall=NOW, now_monotonic=MONO)
    assert decision.outcome == OUTCOME_DENY
    assert "lease.none_matching" in decision.reason_codes


def test_scope_mismatches_deny():
    for override, expected in (
        ({"object_id": "window:bedroom"}, "scope.object_mismatch"),
        ({"action_type": "close_window"}, "scope.action_mismatch"),
        ({"subject": "guest:visitor"}, "scope.subject_mismatch"),
        ({"purpose": "prank"}, "scope.purpose_mismatch"),
    ):
        decision = run(req=request(**override))
        assert decision.outcome == OUTCOME_DENY, override
        assert expected in decision.reason_codes


def test_wider_opening_denied():
    decision = run(req=request(parameters={"opening": {"value": 150, "unit": "mm"}}))
    assert decision.outcome == OUTCOME_DENY
    assert any(r.startswith("limit.exceeded") for r in decision.reason_codes)


def test_rain_denies():
    snap = good_snapshot()
    snap["raining"] = SituationFact(name="raining", typed_value=True,
                                    observed_at=NOW, source_id="sim")
    decision = run(snapshot=snap)
    assert decision.outcome == OUTCOME_DENY


def test_expired_lease_denies():
    decision = run(now_wall="2026-08-01T12:00:00.000000Z")
    assert decision.outcome == OUTCOME_DENY
    assert "lease.expired" in decision.reason_codes


def test_not_yet_valid_denies():
    policy = make_policy(valid_from="2026-07-18T00:00:00.000000Z")
    decision = run(policy=policy, lease=make_lease(policy, not_before=policy.valid_from))
    assert decision.outcome == OUTCOME_DENY
    assert "lease.not_yet_valid" in decision.reason_codes


def test_suspended_lease_denies():
    policy = make_policy()
    decision = run(policy=policy, lease=make_lease(policy, state="SUSPENDED"))
    assert decision.outcome == OUTCOME_DENY
    assert any(r.startswith("lease.not_active") for r in decision.reason_codes)


def test_exhausted_lease_denies():
    policy = make_policy()
    decision = run(policy=policy, lease=make_lease(policy, remaining_uses=0))
    assert decision.outcome == OUTCOME_DENY
    assert "lease.exhausted" in decision.reason_codes


def test_replayed_request_id_denied():
    decision = run(seen_request_ids={"req_1"})
    assert decision.outcome == OUTCOME_DENY
    assert "replay.duplicate_request" in decision.reason_codes


def test_monotonic_regression_fails_closed():
    decision = run(now_monotonic=50.0)  # anchor is 100.0
    assert decision.outcome == OUTCOME_ERROR
    assert "clock.monotonic_regression" in decision.reason_codes


def test_policy_hash_mismatch_fails_closed():
    policy = make_policy()
    tampered = make_lease(policy, policy_hash="sha256:someone_else")
    decision = run(policy=policy, lease=tampered)
    assert decision.outcome == OUTCOME_ERROR
    assert "lease.policy_hash_mismatch" in decision.reason_codes


def test_unknown_fact_denies_by_default():
    snap = good_snapshot()
    del snap["someone_home"]
    decision = run(snapshot=snap)
    assert decision.outcome == OUTCOME_DENY
    assert any("unknown_fact" in r for r in decision.reason_codes)


def test_unknown_fact_ask_policy_asks():
    policy = make_policy(
        unknown_fact_policy="ASK",
        condition=FactCondition("someone_home", "eq", True),
        numeric_limits=(),
    )
    decision = run(req=request(parameters={}), policy=policy,
                   lease=make_lease(policy), snapshot={})
    assert decision.outcome == OUTCOME_ASK


def test_decision_trace_is_reproducible():
    d1 = run()
    d2 = run()
    assert d1.decision_trace_hash == d2.decision_trace_hash
    d3 = run(req=request(parameters={"opening": {"value": 90, "unit": "mm"}}))
    assert d3.decision_trace_hash != d1.decision_trace_hash


def test_required_fact_missing_denies():
    policy = make_policy(required_facts=("interlock_ok",))
    decision = run(policy=policy, lease=make_lease(policy))
    assert decision.outcome == OUTCOME_DENY
    assert "policy.required_fact_missing:interlock_ok" in decision.reason_codes
