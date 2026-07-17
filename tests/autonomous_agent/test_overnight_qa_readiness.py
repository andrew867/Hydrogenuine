"""Tests for overnight QA / knowledge acquisition readiness."""

from __future__ import annotations

import pytest


def test_readiness_gate_requires_source_policy():
    from hg_runtime.overnight_qa.readiness import run_readiness_gate
    result = run_readiness_gate()
    names = {c["name"] for c in result["checks"]}
    assert "source_policy_exists" in names
    assert any(c["name"] == "source_policy_exists" and c["passed"] for c in result["checks"])


def test_readiness_gate_requires_knowledge_policy():
    from hg_runtime.overnight_qa.readiness import run_readiness_gate
    result = run_readiness_gate()
    assert any(c["name"] == "knowledge_policy_exists" and c["passed"] for c in result["checks"])


def test_readiness_gate_requires_stop_panic_plan():
    from hg_runtime.overnight_qa.readiness import run_readiness_gate
    result = run_readiness_gate()
    assert any(c["name"] == "stop_panic_checks_planned" and c["passed"] for c in result["checks"])


def test_readiness_gate_requires_checkpoint_cadence():
    from hg_runtime.overnight_qa.readiness import run_readiness_gate
    result = run_readiness_gate()
    assert any(c["name"] == "checkpoint_cadence_planned" and c["passed"] for c in result["checks"])


def test_readiness_gate_disables_browsing_by_default():
    from hg_runtime.overnight_qa.readiness import run_readiness_gate
    result = run_readiness_gate(browsing_enabled=False)
    assert result["browsing_enabled"] is False
    assert any(c["name"] == "browsing_disabled_by_default" and c["passed"] for c in result["checks"])


def test_readiness_gate_allows_browsing_only_with_source_policy():
    from hg_runtime.overnight_qa.readiness import run_readiness_gate
    result = run_readiness_gate(browsing_enabled=True)
    assert any(c["name"] == "browsing_requires_source_policy" for c in result["checks"])


def test_knowledge_candidate_not_truth():
    from hg_runtime.overnight_qa.schemas import KnowledgeCandidate
    from hg_runtime.overnight_qa.knowledge_policy import candidate_is_truth
    c = KnowledgeCandidate(candidate_id="k1", claim="x")
    assert candidate_is_truth(c) is False


def test_source_not_truth():
    from hg_runtime.overnight_qa.source_policy import make_source_record, source_is_truth
    r = make_source_record(source_id="s1", url_or_fixture_id="fixture:1",
                           retrieval_time="t", retrieval_performed=False,
                           retrieval_method="fixture", title="T")
    assert source_is_truth(r) is False
    assert r.is_truth is False


def test_promotion_requires_provenance():
    from hg_runtime.overnight_qa.schemas import KnowledgeCandidate
    from hg_runtime.overnight_qa.knowledge_policy import can_promote
    c = KnowledgeCandidate(candidate_id="k2", claim="x")  # no sources
    ok, blockers = can_promote(c)
    assert ok is False
    assert any("evidence gap" in b for b in blockers)


def test_promotion_succeeds_with_full_provenance():
    from hg_runtime.overnight_qa.schemas import KnowledgeCandidate
    from hg_runtime.overnight_qa.knowledge_policy import can_promote
    c = KnowledgeCandidate(
        candidate_id="k3", claim="x", source_ids=["s1"], uncertainty="moderate",
        conflict_checked=True, has_authority_fields=False, operator_reviewed=True,
    )
    ok, blockers = can_promote(c)
    assert ok is True, blockers


def test_evidence_gap_not_action():
    from hg_runtime.overnight_qa.schemas import KnowledgeCandidate
    from hg_runtime.overnight_qa.knowledge_policy import can_promote
    c = KnowledgeCandidate(candidate_id="k4", claim="x")
    ok, blockers = can_promote(c)
    assert ok is False


def test_no_posting_no_messaging_no_purchases():
    from hg_runtime.overnight_qa.qa_cycle_plan import build_default_plan
    plan = build_default_plan()
    assert plan.no_posting is True
    assert plan.no_messaging is True
    assert plan.no_purchases is True


def test_operator_review_required_in_morning():
    from hg_runtime.overnight_qa.qa_cycle_plan import build_default_plan
    plan = build_default_plan()
    assert plan.operator_morning_review_required is True


def test_gate_green_default():
    from hg_runtime.overnight_qa.readiness import run_readiness_gate
    result = run_readiness_gate()
    assert result["verdict"] == "GREEN_OVERNIGHT_QA_READINESS"


def test_soak_not_run_in_this_pass():
    from hg_runtime.overnight_qa.readiness import run_readiness_gate
    result = run_readiness_gate()
    assert result["soak_run_in_this_pass"] is False
