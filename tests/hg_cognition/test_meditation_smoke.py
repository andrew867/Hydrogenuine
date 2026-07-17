import time
from hg_cognition.schemas.trace import StepTrace, ToolCallTrace
from hg_cognition.workflows.meditation import run_meditation, find_contradictions
from hg_cognition.persona.quad import QuadCoords
from hg_cognition.profiles import HyperfocusProfile, DefaultModeNetworkProfile

def test_meditation_produces_scores_and_recs():
    now = time.time()
    corr = "c1"
    steps = [
        StepTrace(
            ts=now-2,
            correlation_id=corr,
            run_id="r1",
            node_id="n1",
            actor_id="human",
            role="human",
            input_text="Please do safe verified research",
            output_text="",
            constraints=["safe","verified"],
            constraints_satisfied=["safe","verified"],
            verifications_expected=1,
            verifications_performed=1,
            planned_alternatives=2,
            tool_calls=[],
            notes={"contradictions_found": 0},
        ),
        StepTrace(
            ts=now-1,
            correlation_id=corr,
            run_id="r1",
            node_id="n2",
            actor_id="agent",
            role="agent",
            input_text="",
            output_text="Definitely maybe.",
            constraints=["safe","verified"],
            constraints_satisfied=["safe"],
            verifications_expected=2,
            verifications_performed=0,
            planned_alternatives=0,
            tool_calls=[ToolCallTrace(tool_name="x", idempotency_key="k", args={}, ok=False, policy_denied=True, ts=now-1)],
            notes={"contradictions_found": 1},
        ),
    ]
    persona_history = {"human":[QuadCoords(0,0,0.2)], "agent":[QuadCoords(0,0,0.2)]}
    rep = run_meditation(
        steps=steps,
        baseline_intent_text=steps[0].input_text,
        baseline_response_text="safe verified",
        denied_intent_texts=["bypass policies"],
        persona_history=persona_history,
    )
    assert rep.report_id
    assert len(rep.scores) >= 8
    assert isinstance(rep.persona_updates, dict)
    assert isinstance(rep.signature_updates, dict)
    assert isinstance(rep.contradictions, list)
    assert isinstance(rep.steering_recommendations, list)
    assert rep.summary
    assert any(r.kind == "profile_switch" for r in rep.steering_recommendations)


def test_find_contradictions():
    now = time.time()
    steps = [
        StepTrace(now, "c1", "r1", "n1", "a", "agent", "", "X is not Y", [], [], 0, 0, 0, [], None),
        StepTrace(now + 1, "c1", "r1", "n2", "a", "agent", "", "X is Y", [], [], 0, 0, 0, [], None),
    ]
    contras = find_contradictions(steps)
    assert isinstance(contras, list)


def test_profiles_have_required_fields():
    assert HyperfocusProfile.name == "hyperfocus"
    assert 0 <= HyperfocusProfile.steering_strength <= 1
    assert DefaultModeNetworkProfile.name == "default_mode_network"
    assert hasattr(HyperfocusProfile, "max_tool_calls_multiplier")
    assert hasattr(HyperfocusProfile, "max_children_multiplier")
