"""Unit tests for all HG Cognition detectors. Plan: score in [0,1], level in {0,1,2,3}, stable_id present and deterministic."""
import time
from hg_cognition.schemas.trace import StepTrace, ToolCallTrace
from hg_cognition.detectors import (
    IntentDriftDetector,
    ResponseDriftDetector,
    ConstraintErosionDetector,
    VerificationAvoidanceDetector,
    EuphemismPressureDetector,
    BoundaryProbingDetector,
    OrthogonalGhostDetector,
    LatentCollapseDetector,
    PathfindingCollapseDetector,
    CognitiveDissonanceDetector,
)
from hg_cognition.detectors.base import DetectorContext
from hg_cognition.embeddings.hashing import hash_embed


def _ctx():
    base = hash_embed("baseline intent")
    resp = hash_embed("baseline response")
    return DetectorContext(
        correlation_id="test-corr",
        baseline_intent_vec=base,
        baseline_response_vec=resp,
        baseline_diversity=0.35,
        baseline_alternatives=1.5,
        denied_intent_centroids=[hash_embed("denied")],
    )


def _steps():
    now = time.time()
    return [
        StepTrace(
            ts=now - 2,
            correlation_id="test-corr",
            run_id="r1",
            node_id="n1",
            actor_id="human",
            role="human",
            input_text="Please do safe verified research",
            output_text="",
            constraints=["safe", "verified"],
            constraints_satisfied=["safe"],
            verifications_expected=2,
            verifications_performed=1,
            planned_alternatives=2,
            tool_calls=[],
        ),
        StepTrace(
            ts=now - 1,
            correlation_id="test-corr",
            run_id="r1",
            node_id="n2",
            actor_id="agent",
            role="agent",
            input_text="",
            output_text="Maybe definitely.",
            constraints=["safe", "verified"],
            constraints_satisfied=["safe", "verified"],
            verifications_expected=2,
            verifications_performed=2,
            planned_alternatives=1,
            tool_calls=[
                ToolCallTrace("tool_a", "key1", {}, True, False, now - 1),
                ToolCallTrace("tool_b", "key2", {}, False, True, now - 1),
            ],
        ),
    ]


def _assert_score(score):
    assert 0.0 <= score.value <= 1.0
    assert score.level in (0, 1, 2, 3)
    assert score.stable_id
    assert isinstance(score.evidence, list)


def test_intent_drift_detector():
    steps = _steps()
    ctx = _ctx()
    d = IntentDriftDetector()
    s = d.run(steps, ctx)
    _assert_score(s)
    assert s.name == "intent_drift"
    s2 = d.run(steps, ctx)
    assert s.stable_id == s2.stable_id


def test_response_drift_detector():
    steps = _steps()
    ctx = _ctx()
    d = ResponseDriftDetector()
    s = d.run(steps, ctx)
    _assert_score(s)
    assert s.name == "response_drift"


def test_constraint_erosion_detector():
    steps = _steps()
    ctx = _ctx()
    d = ConstraintErosionDetector()
    s = d.run(steps, ctx)
    _assert_score(s)
    assert s.name == "constraint_erosion"


def test_verification_avoidance_detector():
    steps = _steps()
    ctx = _ctx()
    d = VerificationAvoidanceDetector()
    s = d.run(steps, ctx)
    _assert_score(s)
    assert s.name == "verification_avoidance"


def test_euphemism_pressure_detector():
    steps = _steps()
    ctx = _ctx()
    d = EuphemismPressureDetector()
    s = d.run(steps, ctx)
    _assert_score(s)
    assert s.name == "euphemism_pressure"


def test_boundary_probing_detector():
    steps = _steps()
    ctx = _ctx()
    d = BoundaryProbingDetector()
    s = d.run(steps, ctx)
    _assert_score(s)
    assert s.name == "boundary_probing"


def test_orthogonal_ghost_detector():
    steps = _steps()
    ctx = _ctx()
    d = OrthogonalGhostDetector()
    s = d.run(steps, ctx)
    _assert_score(s)
    assert s.name == "orthogonal_ghost"


def test_latent_collapse_detector():
    steps = _steps()
    ctx = _ctx()
    d = LatentCollapseDetector()
    s = d.run(steps, ctx)
    _assert_score(s)
    assert s.name == "latent_collapse"


def test_pathfinding_collapse_detector():
    steps = _steps()
    ctx = _ctx()
    d = PathfindingCollapseDetector()
    s = d.run(steps, ctx)
    _assert_score(s)
    assert s.name == "pathfinding_collapse"


def test_cognitive_dissonance_detector():
    steps = _steps()
    ctx = _ctx()
    d = CognitiveDissonanceDetector()
    s = d.run(steps, ctx)
    _assert_score(s)
    assert s.name == "cognitive_dissonance"
