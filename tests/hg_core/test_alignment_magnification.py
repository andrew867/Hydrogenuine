"""Pack2-03: Alignment magnification rule engine — unit tests. Real YAML rules, no mocks."""

import pytest
from hg_core.alignment.magnification import run_magnify, _load_rules, _match_rule


def test_magnify_gateway_echo_returns_low_risk():
    r = run_magnify(planned_action={"tool_name": "gateway.echo", "inputs": {"message": "hi"}})
    assert r["risk_score"] == 0
    assert r["required_controls"]["step_up_auth"] == "none"
    assert r["required_controls"]["approval"] is False


def test_magnify_moltbook_post_returns_high_risk():
    r = run_magnify(planned_action={"tool_name": "moltbook.post_or_reply", "inputs": {}})
    assert r["risk_score"] == 75
    assert r["required_controls"]["step_up_auth"] == "strong"
    assert r["required_controls"]["approval"] is True
    assert "reasons" in r and len(r["reasons"]) >= 1
    assert "suggested_tests" in r


def test_magnify_moltbook_verify_returns_medium_risk():
    r = run_magnify(planned_action={"tool_name": "moltbook.submit_verification", "inputs": {}})
    assert r["risk_score"] == 60
    assert r["required_controls"]["step_up_auth"] == "basic"
    assert r["required_controls"]["approval"] is True


def test_magnify_social_prefix_matches():
    r = run_magnify(planned_action={"tool_name": "social.fourclaw.create_thread", "inputs": {}})
    assert r["risk_score"] == 70
    assert r["required_controls"]["step_up_auth"] == "strong"


def test_magnify_determinism_same_input_same_score():
    a = run_magnify(planned_action={"tool_name": "moltbook.post_or_reply", "inputs": {"x": 1}})
    b = run_magnify(planned_action={"tool_name": "moltbook.post_or_reply", "inputs": {"x": 2}})
    assert a["risk_score"] == b["risk_score"]
    assert a["reasons"] == b["reasons"]


def test_magnify_unknown_tool_uses_default():
    r = run_magnify(planned_action={"tool_name": "unknown.tool.foo", "inputs": {}})
    assert 0 <= r["risk_score"] <= 100
    assert r["required_controls"]["approval"] is True
    assert "reasons" in r


def test_magnify_accepts_context():
    r = run_magnify(
        planned_action={"tool_name": "gateway.echo"},
        context={"chat_id": "c1"},
    )
    assert r["risk_score"] == 0


def test_load_rules_returns_list():
    rules = _load_rules()
    assert isinstance(rules, list)
    assert len(rules) >= 1


def test_match_rule_exact():
    rule = {"match": {"tool_name": "moltbook.post_or_reply"}}
    assert _match_rule(rule, "moltbook.post_or_reply") is True
    assert _match_rule(rule, "moltbook.submit_verification") is False


def test_match_rule_prefix():
    rule = {"match": {"tool_name_prefix": "social."}}
    assert _match_rule(rule, "social.fourclaw.getposts") is True
    assert _match_rule(rule, "moltbook.post_or_reply") is False
