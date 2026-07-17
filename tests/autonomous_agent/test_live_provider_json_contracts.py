"""JSON contract tests."""
from __future__ import annotations

from hg_runtime.live_provider.json_contracts import evaluate_json_output, validate_json_text, validate_turn_decision_schema
from hg_runtime.live_provider.schema import LiveProviderVerdict


def test_invalid_json_rejected():
    ok, parsed, err = validate_json_text("not json")
    assert not ok
    assert err


def test_valid_json_passes():
    ok, parsed, err = validate_json_text('{"task":"x"}')
    assert ok
    assert parsed == {"task": "x"}


def test_turn_schema_requires_fields():
    ok, err = validate_turn_decision_schema({"chosen_action": "rest_turn"})
    assert not ok


def test_evaluate_invalid_json_verdict():
    jv, sv, verdict = evaluate_json_output("bad", require_turn_schema=False)
    assert not jv
    assert verdict == LiveProviderVerdict.YELLOW_PROVIDER_JSON_INVALID_DEFERRED
