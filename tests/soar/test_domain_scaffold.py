"""SOAR Phase 1 domain scaffold unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_hal import arbitrate, request_from_proposal
from hg_hal.types import ArbitrationCandidate, ArbitrationRequest
from hg_soar import (
    DOMAIN_IDS,
    apply_critique,
    audit_d7,
    binding_rank,
    run_soar,
    soar_run_drafts,
)
from hg_soar.critique import weakened_binding
from hg_soar.d7 import arbitrate_d7
from hg_soar.domains import evaluate_all_domains
from hg_soar.types import D7Decision


def _proposal(**content_overrides) -> dict:
    content = {
        "proposal_id": "prop_soar_1",
        "kind": "candidate_action",
        "capability_id": "cap.oea_stub_log",
        "effect_class": "audit_log",
        "action_type": "oea_stub_log",
    }
    content.update(content_overrides)
    return {
        "event_id": "evt_prop_1",
        "type": "PROPOSAL_EMITTED",
        "payload": {"proposal_id": content["proposal_id"], "kind": content["kind"], "content": content},
    }


def test_seven_domain_records_emitted_for_soar_run():
    run = run_soar(_proposal(), context_refs=("evt_ctx",))
    drafts = soar_run_drafts(run, causal_parents=["evt_prop_1"])
    domain_events = [draft for draft in drafts if draft["type"] == "SOAR_DOMAIN_EVALUATED"]
    assert len(domain_events) == 7
    assert {event["payload"]["domain_id"] for event in domain_events} == set(DOMAIN_IDS)


def test_d7_decision_is_present():
    run = run_soar(_proposal(), context_refs=())
    drafts = soar_run_drafts(run, causal_parents=["evt_prop_1"])
    types = [draft["type"] for draft in drafts]
    assert "SOAR_D7_DECISION_RECORDED" in types
    assert "SOAR_D7_CRITIQUE_RECORDED" in types
    assert run.d7_decision.decision_id == run.to_payload()["d7_decision_ref"]
    assert run.binding in ("ACCEPT", "DEFER", "REJECT", "NO_OP")


def test_d7_critique_cannot_upgrade_defer_to_accept():
    evaluations = evaluate_all_domains(proposal=_proposal(memory_stale=True), input_refs=("evt",))
    primary = arbitrate_d7(
        request_id="soar_req_defer",
        proposal_ref="prop_soar_1",
        evaluations=evaluations,
    )
    assert primary.binding == "DEFER"
    critique = audit_d7(primary, evaluations=evaluations)
    final = apply_critique(primary, critique)
    assert binding_rank(final) <= binding_rank(primary.binding)
    assert final != "ACCEPT"


def test_d7_critique_force_defer_downgrades_accept():
    evaluations = evaluate_all_domains(proposal=_proposal(), input_refs=("evt",))
    primary = D7Decision(
        decision_id="d7_force",
        request_id="soar_req",
        binding="ACCEPT",
        domain_evaluation_refs=tuple(evaluation.evaluation_id for evaluation in evaluations),
        reason_code="test_accept",
        hard_veto=True,
    )
    critique = audit_d7(primary, evaluations=evaluations)
    assert critique.verdict == "FORCE_DEFER"
    assert apply_critique(primary, critique) == "DEFER"


def test_no_recursive_critique():
    source = Path("hg_soar/critique.py").read_text(encoding="utf-8")
    assert "audit_d7(" not in source.split("def audit_d7", 1)[1]
    assert "CritiqueCritique" not in source


def test_soar_modules_have_no_execution_or_permit_imports():
    forbidden = (
        "PermitBinder",
        "mint_permit",
        "hg_ueak",
        "hg_oea",
        "dispatch_committed",
        "kernel.execute",
        "hg_aep",
        "ArousalState",
    )
    for path in Path("hg_soar").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path} must not reference {token}"


def test_soar_outputs_feed_hal_reference_path():
    run = run_soar(_proposal(), context_refs=("evt_ctx",))
    request = request_from_proposal(
        _proposal(),
        context_refs=("evt_ctx",),
        aep_state={"max_severity": 0},
        soar_run=run,
    )
    assert request.soar_run_ref == run.request_id
    assert request.soar_binding == run.binding
    result = arbitrate(request)
    assert "soar:run:" in result.trace_refs[0] or any(
        ref.startswith("soar:run:") for ref in result.trace_refs
    )


def test_hal_cannot_loosen_soar_defer(monkeypatch: pytest.MonkeyPatch):
    run = run_soar(_proposal(memory_stale=True), context_refs=())
    assert run.binding == "DEFER"
    request = ArbitrationRequest(
        request_id="hal_req_soar",
        proposal_ref="prop_soar_1",
        candidates=(
            ArbitrationCandidate(
                candidate_id="c1",
                action_ref="act_1",
                capability_id="cap.oea_stub_log",
                effect_class="audit_log",
                priority=99,
            ),
        ),
        context_refs=(),
        soar_run_ref=run.request_id,
        soar_binding=run.binding,
    )
    result = arbitrate(request)
    assert result.routing == "DEFER"
    assert result.reason_code == "soar_binding_defer"


def test_weakened_binding_monotonic():
    evaluations = evaluate_all_domains(proposal=_proposal(), input_refs=())
    primary = arbitrate_d7(
        request_id="soar_req_mono",
        proposal_ref="prop",
        evaluations=evaluations,
    )
    critique = audit_d7(primary, evaluations=evaluations)
    assert binding_rank(weakened_binding(primary, critique)) <= binding_rank(primary.binding)
