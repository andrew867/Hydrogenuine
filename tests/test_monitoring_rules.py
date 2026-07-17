"""Pack 15.4: Monitoring rules — condition evaluator, cooldown, rule evaluation and drift.detected."""

import os
import tempfile
import pytest

from hg_gateway.monitoring_rules import (
    RULE_ACTIONS,
    default_rules_v1,
    evaluate_condition,
)
from hg_gateway.monitoring_rules_store import (
    evaluate_rules_after_turn,
    get_features_for_chat,
    is_rule_in_cooldown,
    monitor_rules_list,
    record_rule_triggered,
)


def test_evaluate_condition_simple():
    features = {"drift_erosion.capability_creep_score": 0.8}
    assert evaluate_condition({"op": ">=", "key": "drift_erosion.capability_creep_score", "value": 0.7}, features) is True
    assert evaluate_condition({"op": ">=", "key": "drift_erosion.capability_creep_score", "value": 0.9}, features) is False
    assert evaluate_condition({"op": ">", "key": "drift_erosion.capability_creep_score", "value": 0.7}, features) is True
    assert evaluate_condition({"op": "<", "key": "drift_erosion.capability_creep_score", "value": 0.9}, features) is True


def test_evaluate_condition_missing_key():
    features = {"other": 1.0}
    assert evaluate_condition({"op": ">=", "key": "drift_erosion.capability_creep_score", "value": 0.7}, features) is False


def test_evaluate_condition_and():
    features = {"a": 0.7, "b": 0.6}
    cond = {"and": [{"op": ">=", "key": "a", "value": 0.5}, {"op": ">=", "key": "b", "value": 0.5}]}
    assert evaluate_condition(cond, features) is True
    cond2 = {"and": [{"op": ">=", "key": "a", "value": 0.8}, {"op": ">=", "key": "b", "value": 0.5}]}
    assert evaluate_condition(cond2, features) is False


def test_evaluate_condition_or():
    features = {"a": 0.3, "b": 0.8}
    cond = {"or": [{"op": ">=", "key": "a", "value": 0.5}, {"op": ">=", "key": "b", "value": 0.5}]}
    assert evaluate_condition(cond, features) is True


def test_default_rules_v1():
    rules = default_rules_v1()
    assert len(rules) >= 5
    ids = [r["rule_id"] for r in rules]
    assert "capability_creep_quarantine" in ids
    assert "privacy_risk_pause" in ids
    for r in rules:
        assert r["action"] in RULE_ACTIONS


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    prev = os.environ.get("HG_GATEWAY_DB_PATH")
    os.environ["HG_GATEWAY_DB_PATH"] = path
    try:
        yield path
    finally:
        if prev is not None:
            os.environ["HG_GATEWAY_DB_PATH"] = prev
        else:
            os.environ.pop("HG_GATEWAY_DB_PATH", None)
        try:
            os.unlink(path)
        except Exception:
            pass


def test_monitor_rules_list_seeds_defaults(temp_db):
    from hg_gateway.db import get_connection
    with get_connection():
        pass
    rules = monitor_rules_list("t1")
    assert len(rules) >= 5
    assert any(r["rule_id"] == "capability_creep_quarantine" for r in rules)


def test_get_features_for_chat_empty(temp_db):
    from hg_gateway.db import get_connection
    with get_connection():
        pass
    features, event_ids = get_features_for_chat("t1", "c1")
    assert features == {}
    assert event_ids == []


def test_cooldown(temp_db):
    from hg_gateway.db import get_connection
    with get_connection():
        pass
    record_rule_triggered("r1", "t1", "c1")
    assert is_rule_in_cooldown("r1", "t1", "c1", 300) is True
    assert is_rule_in_cooldown("r1", "t1", "c1", 0) is False
    assert is_rule_in_cooldown("r2", "t1", "c1", 300) is False


def test_evaluate_rules_after_turn_no_features(temp_db):
    from hg_gateway.db import get_connection
    with get_connection():
        pass
    fired = evaluate_rules_after_turn("t1", "c1")
    assert fired == []


def test_evaluate_rules_after_turn_fires(temp_db):
    from hg_gateway.db import get_connection
    from hg_gateway.signals_store import signal_event_insert, signal_feature_insert
    with get_connection():
        pass
    # Create an event with capability_creep_score >= 0.7
    event_id = signal_event_insert(
        tenant_id="t1",
        chat_id="c1",
        direction="out",
        signals_json={"schema_version": "1.0", "drift_erosion": {"capability_creep_score": 0.75}},
    )
    signal_feature_insert(event_id=event_id, tenant_id="t1", feature_key="drift_erosion.capability_creep_score", feature_value=0.75)
    fired = evaluate_rules_after_turn("t1", "c1")
    assert len(fired) >= 1
    assert any(f["rule_id"] == "capability_creep_quarantine" for f in fired)
    assert any(f["action"] == "quarantine" for f in fired)
    # Second call: same rule in cooldown, should not fire again for same chat
    fired2 = evaluate_rules_after_turn("t1", "c1")
    assert len(fired2) == 0
