from __future__ import annotations

import pytest

from hg_quantum.cognition.contracts import MediatorSpec
from hg_quantum.cognition.mediator_registry import MediatorRegistry


def test_catalog_lists_builtin_four():
    reg = MediatorRegistry()
    ids = {s.mediator_id for s in reg.catalog()}
    assert ids == {
        "paired_probe",
        "amplification_context",
        "perturbation_probe",
        "capability_elicitation",
    }


def test_register_requires_complete_spec():
    reg = MediatorRegistry()
    with pytest.raises(ValueError, match="required fields"):
        reg.register(
            MediatorSpec(
                mediator_id="bad",
                latent_state_class="latent_capability",
                coupling_mechanism="",
                cost_profile={},
                surfacing_policy="",
                consent_constraints={},
            )
        )


def test_register_is_level2_action():
    reg = MediatorRegistry()
    reg.register(
        MediatorSpec(
            mediator_id="custom_probe",
            latent_state_class="latent_capability",
            coupling_mechanism="test",
            cost_profile={"tokens": 10},
            surfacing_policy="reflection_artifact",
            consent_constraints={"target_scope": "entity"},
        )
    )
    events = reg.governance_events()
    assert any(e.get("event_type") == "mediator_registered" and e.get("level") == 2 for e in events)


def test_probe_unknown_class_raises():
    reg = MediatorRegistry()
    with pytest.raises(ValueError, match="unknown latent_state_class"):
        reg.probe("ent_1", "bogus")


def test_probe_emits_proof_entry():
    reg = MediatorRegistry()
    result = reg.probe(
        "ent_1",
        "unexpressed_disagreement",
        context={"position_a": {"agreement": 0.8}, "position_b": {"agreement": 0.2}},
    )
    assert result.proof_logged is True
    log = reg.activation_log()
    assert log and log[-1]["result_digest"] == result.result_digest


def test_user_latent_state_out_of_scope():
    reg = MediatorRegistry()
    with pytest.raises(ValueError, match="consent"):
        reg.register(
            MediatorSpec(
                mediator_id="human_probe",
                latent_state_class="latent_capability",
                coupling_mechanism="test",
                cost_profile={"tokens": 1},
                surfacing_policy="operator_review",
                consent_constraints={"target_scope": "human"},
                target_scope="human",
            )
        )


def test_rate_limit_enforced():
    reg = MediatorRegistry()
    spec = next(s for s in reg.catalog() if s.mediator_id == "paired_probe")
    limited = MediatorSpec(**{**spec.to_dict(), "rate_limit_per_hour": 2})
    reg._specs["paired_probe"] = limited
    reg.probe("e1", "unexpressed_disagreement", context={"position_a": {"x": 0.9}, "position_b": {"x": 0.1}})
    reg.probe("e1", "unexpressed_disagreement", context={"position_a": {"x": 0.8}, "position_b": {"x": 0.2}})
    with pytest.raises(ValueError, match="rate limit"):
        reg.probe("e1", "unexpressed_disagreement", context={"position_a": {"x": 0.7}, "position_b": {"x": 0.3}})


def test_all_builtin_mediators_produce_results():
    reg = MediatorRegistry()
    contexts = {
        "unexpressed_disagreement": {"position_a": {"a": 0.9}, "position_b": {"a": 0.1}},
        "suppressed_reasoning": {"reasoning_depth": 0.9, "output_token_count": 10},
        "eroding_confidence": {"baseline_confidence": 0.8, "response_confidence": 0.5},
        "latent_capability": {"variant_score": 0.9, "track_record": [{"score": 0.4}]},
    }
    for latent_class, ctx in contexts.items():
        result = reg.probe("ent_demo", latent_class, context=ctx)
        assert result.latent_state_class == latent_class
        assert 0.0 <= result.strength <= 1.0
