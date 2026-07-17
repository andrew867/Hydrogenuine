"""DRB→TEP integration — wrapped advisory path; refused history/proof/permission paths."""

from __future__ import annotations

from hg_runtime.translation_envelope_protocol.drb_integration import (
    EXECUTION_HISTORY_REFERENCE,
    PERMIT_REFERENCE,
    PROOF_REFERENCE,
    PROPOSAL_REFERENCE,
    run_drb_tep_integration_path,
    tep_consume_drb_output,
    wrap_drb_counterfactual,
    wrap_drb_dream_fragment,
    wrap_drb_lesson_candidate,
    wrap_drb_memory_mutation_proposal,
)
from hg_runtime.translation_envelope_protocol.fixtures import fixture_claim


def test_naked_drb_fragment_refused():
    claim = fixture_claim(
        claim_type="SIMULATION_RESULT",
        claim_id="naked:drb",
        structured_value={"drb_output_kind": "dream_fragment"},
    )
    result = tep_consume_drb_output(claim, None, PROPOSAL_REFERENCE)
    assert result["status"] == "refused"


def test_wrapped_dream_fragment_not_translatable():
    fragment = {
        "fragment_id": "frag:test",
        "fragment_type": "residue",
        "content": "rehearse export check",
    }
    claim, envelope = wrap_drb_dream_fragment(fragment)
    result = tep_consume_drb_output(claim, envelope, PROPOSAL_REFERENCE)
    assert result["tep_decision"] == "REJECT_NOT_TRANSLATABLE"


def test_wrapped_lesson_advisory_accepted():
    fragment = {"fragment_id": "frag:lesson", "fragment_type": "lesson", "content": "check exports"}
    claim, envelope = wrap_drb_lesson_candidate(fragment)
    result = tep_consume_drb_output(claim, envelope, PROPOSAL_REFERENCE)
    assert result["status"] == "accepted"


def test_counterfactual_refused_as_history_and_proof():
    scenario = {
        "scenario_id": "sc:test",
        "scenario_type": "alternative_past_outcome",
        "scenario_summary": "what if export had been checked",
        "explicitly_counterfactual": True,
        "not_history": True,
    }
    claim, envelope = wrap_drb_counterfactual(scenario)
    history = tep_consume_drb_output(claim, envelope, EXECUTION_HISTORY_REFERENCE)
    proof = tep_consume_drb_output(claim, envelope, PROOF_REFERENCE)
    assert history["tep_decision"] in ("REJECT_NOT_TRANSLATABLE", "ROUTE_TO_REVIEW", "FAIL_CLOSED")
    assert proof["tep_decision"] == "REJECT_NOT_TRANSLATABLE"


def test_lesson_refused_as_permission():
    fragment = {"fragment_id": "frag:lesson", "fragment_type": "lesson", "content": "check exports"}
    claim, envelope = wrap_drb_lesson_candidate(fragment)
    result = tep_consume_drb_output(claim, envelope, PERMIT_REFERENCE)
    assert result["tep_decision"] in ("REJECT_NOT_TRANSLATABLE", "ROUTE_TO_REVIEW", "FAIL_CLOSED")


def test_memory_mutation_proposal_only():
    proposal = {
        "proposal_id": "claim:mem-prop",
        "envelope_id": "env:mem-prop",
        "target_refs": ("mem:slot",),
        "rationale": "governed write required",
    }
    claim, envelope = wrap_drb_memory_mutation_proposal(proposal)
    assert envelope.structured_value["proposal_only"] is True
    assert envelope.authority_semantics.may_grant_memory is False


def test_run_drb_tep_integration_path_green():
    path = run_drb_tep_integration_path()
    assert path["naked_drb_fragment_refused"] is True
    assert path["counterfactual_not_history"] is True
    assert path["counterfactual_not_proof"] is True
    assert path["lesson_not_permission"] is True
    assert path["gpp_no_permit_from_drb"] is True
    assert path["ueak_no_admission_from_drb"] is True
