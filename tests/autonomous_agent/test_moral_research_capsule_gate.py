"""Tests for moral research capsule gate."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.moral_research_capsule.scenario_suite import build_scenario_suite
from hg_runtime.moral_research_capsule.cohort_registry import build_cohort_registry
from hg_runtime.moral_research_capsule.fixture_responses import build_fixture_responses
from hg_runtime.moral_research_capsule.response_loader import build_all_receipts
from hg_runtime.moral_research_capsule.perspective_matrix import build_perspective_matrix
from hg_runtime.moral_research_capsule.conflict_map import build_conflict_map
from hg_runtime.moral_research_capsule.evidence_gap_ledger import build_evidence_gap_ledger
from hg_runtime.moral_research_capsule.uncertainty_ledger import build_uncertainty_ledger
from hg_runtime.moral_research_capsule.source_ledger import build_source_ledger_placeholders
from hg_runtime.moral_research_capsule.research_document import build_research_document
from hg_runtime.moral_research_capsule.gate import run_gate
from hg_runtime.moral_research_capsule.schemas import ResponseReceipt


@pytest.fixture
def _full_bundle():
    scenarios = build_scenario_suite()
    cohort = build_cohort_registry()
    responses = build_fixture_responses()
    receipts = build_all_receipts(responses)
    cells = build_perspective_matrix(responses, receipts)
    conflicts = build_conflict_map(cells)
    evidence_gaps = build_evidence_gap_ledger(responses)
    scenario_ids = [s.scenario_id for s in scenarios]
    uncertainty = build_uncertainty_ledger(scenario_ids)
    sources = build_source_ledger_placeholders()
    doc = build_research_document(
        question="How do models frame hard moral dilemmas?",
        scenario_count=len(scenarios),
        model_count=len(cohort),
        fixture_response_count=len(responses),
        matrix_cells=cells,
        conflicts=conflicts,
        evidence_gaps=evidence_gaps,
        uncertainty_records=uncertainty,
        source_records=sources,
    )
    return {
        "scenarios": scenarios,
        "cohort": cohort,
        "receipts": receipts,
        "cells": cells,
        "conflicts": conflicts,
        "evidence_gaps": evidence_gaps,
        "uncertainty": uncertainty,
        "sources": sources,
        "doc": doc,
    }


def _run_gate(bundle, **overrides):
    kw = dict(
        scenarios=bundle["scenarios"],
        cohort=bundle["cohort"],
        receipts=bundle["receipts"],
        matrix_cells=bundle["cells"],
        conflicts=bundle["conflicts"],
        evidence_gaps=bundle["evidence_gaps"],
        uncertainty_records=bundle["uncertainty"],
        source_records=bundle["sources"],
        research_doc=bundle["doc"],
        proof_bundle_exists=True,
    )
    kw.update(overrides)
    return run_gate(**kw)


class TestGateGreen:

    def test_gate_green_for_valid_fixture_bundle(self, _full_bundle):
        result = _run_gate(_full_bundle)
        assert result["verdict"] == "GREEN_MORAL_CULTURAL_RESEARCH_CAPSULE_FIXTURE_IMPLEMENTED"


class TestGateRed:

    def test_gate_red_if_matrix_cell_missing_receipt(self, _full_bundle):
        _full_bundle["receipts"] = _full_bundle["receipts"][:1]
        result = _run_gate(_full_bundle)
        assert "RED" in result["verdict"] or "YELLOW" in result["verdict"]
        failed_names = [c["name"] for c in result["failed_checks"]]
        assert "every_matrix_cell_links_to_receipt" in failed_names

    def test_gate_red_if_consensus_marked_truth(self, _full_bundle):
        _full_bundle["receipts"][0].model_consensus_treated_as_truth = True
        result = _run_gate(_full_bundle)
        failed_names = [c["name"] for c in result["failed_checks"]]
        assert "consensus_not_truth" in failed_names

    def test_gate_red_if_refusal_marked_authority(self, _full_bundle):
        _full_bundle["receipts"][0].model_refusal_treated_as_authority = True
        result = _run_gate(_full_bundle)
        failed_names = [c["name"] for c in result["failed_checks"]]
        assert "refusal_not_authority" in failed_names

    def test_gate_red_if_willingness_marked_permission(self, _full_bundle):
        _full_bundle["receipts"][0].model_willingness_treated_as_permission = True
        result = _run_gate(_full_bundle)
        failed_names = [c["name"] for c in result["failed_checks"]]
        assert "willingness_not_permission" in failed_names

    def test_gate_red_if_moral_claim_marked_authority(self, _full_bundle):
        _full_bundle["receipts"][0].moral_claim_treated_as_authority = True
        result = _run_gate(_full_bundle)
        failed_names = [c["name"] for c in result["failed_checks"]]
        assert "moral_claims_not_authority" in failed_names

    def test_gate_red_if_culture_claim_treated_as_fact(self, _full_bundle):
        _full_bundle["cohort"][0].model_family_is_not_country = False
        result = _run_gate(_full_bundle)
        failed_names = [c["name"] for c in result["failed_checks"]]
        assert "model_family_not_country" in failed_names

    def test_gate_red_if_evidence_gap_authorizes_action(self, _full_bundle):
        if _full_bundle["evidence_gaps"]:
            _full_bundle["evidence_gaps"][0].action_authorized = True
        result = _run_gate(_full_bundle)
        if _full_bundle["evidence_gaps"]:
            failed_names = [c["name"] for c in result["failed_checks"]]
            assert "evidence_gap_tasks_not_actions" in failed_names

    def test_gate_red_if_live_provider_called(self, _full_bundle):
        result = _run_gate(_full_bundle, live_providers_called=True)
        failed_names = [c["name"] for c in result["failed_checks"]]
        assert "no_live_providers_called" in failed_names

    def test_gate_red_if_external_call_recorded(self, _full_bundle):
        result = _run_gate(_full_bundle, external_calls_made=True)
        failed_names = [c["name"] for c in result["failed_checks"]]
        assert "no_external_calls" in failed_names


class TestGateBoundaries:

    def test_gate_preserves_phase19_yellow(self, _full_bundle):
        result = _run_gate(_full_bundle)
        check = [c for c in result["checks"] if c["name"] == "phase19_yellow_preserved"]
        assert check and check[0]["passed"]

    def test_gate_preserves_phase24_infrastructure_only(self, _full_bundle):
        result = _run_gate(_full_bundle)
        check = [c for c in result["checks"] if c["name"] == "phase24_infrastructure_only_preserved"]
        assert check and check[0]["passed"]

    def test_gate_zero_not_agi(self, _full_bundle):
        result = _run_gate(_full_bundle)
        check = [c for c in result["checks"] if c["name"] == "zero_not_agi"]
        assert check and check[0]["passed"]
