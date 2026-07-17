"""Unit tests for persona quad, signatures, and interventions engine."""
from hg_cognition.persona.quad import QuadCoords, update_quad, quad_entropy
from hg_cognition.signatures.signature import build_signature
from hg_cognition.interventions.engine import generate_recommendations
from hg_cognition.schemas.common import Score


def test_update_quad():
    q = QuadCoords(0.0, 0.0, 0.5)
    q2 = update_quad(q, 0.2, -0.1)
    assert -1.0 <= q2.x <= 1.0 and -1.0 <= q2.y <= 1.0
    assert q2.confidence >= 0


def test_quad_entropy():
    hist = [QuadCoords(0.0, 0.0, 0.2), QuadCoords(0.5, 0.3, 0.2), QuadCoords(-0.2, 0.1, 0.2)]
    e = quad_entropy(hist)
    assert 0.0 <= e <= 1.0
    assert quad_entropy([QuadCoords(0, 0, 0.2)]) >= 0


def test_build_signature():
    sig = build_signature(
        entity_id="agent1",
        text_samples=["hello", "world"],
        tool_calls=2,
        policy_denials=0,
        verif_expected=1,
        verif_performed=1,
        steering_events=2,
        steering_successes=1,
    )
    assert sig.entity_id == "agent1"
    assert len(sig.vec) == 256
    assert "tool_rate" in sig.meta and "verification_rate" in sig.meta
    assert sig.meta["verification_rate"] == 1.0


def test_generate_recommendations_returns_steering_with_stable_id():
    scores = [
        Score("constraint_erosion", 0.5, 1, [], "sid1"),
        Score("intent_drift", 0.2, 0, [], "sid2"),
    ]
    recs = generate_recommendations(scores, "I feel good and calm", "corr-1")
    assert isinstance(recs, list)
    assert len(recs) >= 1
    for r in recs:
        assert r.stable_id
        assert r.kind
        assert 0 <= r.strength <= 1
