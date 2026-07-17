"""WILL envelope schema tests."""

from __future__ import annotations

from hg_runtime.will_module.envelope import WillEnvelope, build_envelope_from_config, validate_envelope_payload
from hg_runtime.will_module.hash import will_hash
from hg_runtime.will_module.policy import attempt_will_approval, inferred_consent_allowed
from hg_runtime.will_module.registry import load_will_config, load_will_envelope
from hg_runtime.will_module.schema import ConsentPosture, IntentVector, PersistenceBudget, PersistenceBudgetClass, ValueVector, WillSource
from hg_runtime.will_module.receipts import create_envelope_receipt


def test_envelope_advisory_invariants():
    env, _ = load_will_envelope("configs/will/agent0_dev_boot_will.example.json", run_id="run-test")
    payload = env.to_payload()
    assert payload["advisory_only"] is True
    assert payload["permission_granted"] is False
    assert payload["authority_created"] is False


def test_envelope_hash_stable():
    config = load_will_config("configs/will/agent0_dev_boot_will.example.json")
    env1 = build_envelope_from_config(config, run_id="run-hash", will_id="will-fixed")
    env2 = build_envelope_from_config(config, run_id="run-hash", will_id="will-fixed")
    env1.expires_at = env2.expires_at = "2026-06-15T12:00:00+00:00"
    h1 = will_hash(env1.semantic_payload())
    h2 = will_hash(env2.semantic_payload())
    assert h1 == h2


def test_validate_envelope_payload():
    env, receipt = load_will_envelope("configs/will/agent0_default_will.example.json", run_id="run-val")
    failures = validate_envelope_payload(env.to_payload())
    assert failures == []


def test_will_cannot_approve_tool():
    result = attempt_will_approval("social_publish_request")
    assert result["rejected"] is True


def test_inferred_intent_not_consent():
    assert inferred_consent_allowed(WillSource.INFERRED_FROM_CONTEXT, ConsentPosture.EXPLICIT_YES) is False
    assert inferred_consent_allowed(WillSource.OPERATOR, ConsentPosture.EXPLICIT_YES) is True


def test_expired_requires_reaffirmation():
    from hg_runtime.will_module.policy import check_expiry

    config = load_will_config("configs/will/agent0_default_will.example.json")
    env = build_envelope_from_config(config, run_id="run-exp", will_id="will-exp")
    env.expires_at = "2020-01-01T00:00:00+00:00"
    assert check_expiry(env, now="2026-06-15T04:00:00+00:00").value == "REQUEST_REAFFIRMATION"


def test_persistence_bounded():
    from hg_runtime.will_module.policy import persistence_within_bounds

    config = load_will_config("configs/will/agent0_dev_boot_will.example.json")
    env = build_envelope_from_config(config, run_id="run-persist", will_id="will-persist")
    assert persistence_within_bounds(env, attempts=5, wallclock_s=600, tokens=1000) is True
    assert persistence_within_bounds(env, attempts=9999, wallclock_s=600, tokens=1000) is False
