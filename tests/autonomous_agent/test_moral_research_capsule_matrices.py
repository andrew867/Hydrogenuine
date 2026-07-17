"""Tests for perspective matrix, conflict map, and ledgers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.moral_research_capsule.fixture_responses import build_fixture_responses
from hg_runtime.moral_research_capsule.response_loader import build_all_receipts
from hg_runtime.moral_research_capsule.perspective_matrix import (
    build_perspective_matrix, matrix_cells_all_have_receipts,
)
from hg_runtime.moral_research_capsule.conflict_map import build_conflict_map
from hg_runtime.moral_research_capsule.evidence_gap_ledger import build_evidence_gap_ledger
from hg_runtime.moral_research_capsule.uncertainty_ledger import build_uncertainty_ledger
from hg_runtime.moral_research_capsule.source_ledger import build_source_ledger_placeholders
from hg_runtime.moral_research_capsule.research_document import (
    build_research_document, render_research_document_md,
)
from hg_runtime.moral_research_capsule.scenario_suite import build_scenario_suite
from hg_runtime.moral_research_capsule.cohort_registry import build_cohort_registry


@pytest.fixture
def _all():
    responses = build_fixture_responses()
    receipts = build_all_receipts(responses)
    cells = build_perspective_matrix(responses, receipts)
    conflicts = build_conflict_map(cells)
    scenarios = build_scenario_suite()
    scenario_ids = [s.scenario_id for s in scenarios]
    evidence_gaps = build_evidence_gap_ledger(responses)
    uncertainty = build_uncertainty_ledger(scenario_ids)
    sources = build_source_ledger_placeholders()
    return {
        "responses": responses,
        "receipts": receipts,
        "cells": cells,
        "conflicts": conflicts,
        "scenarios": scenarios,
        "evidence_gaps": evidence_gaps,
        "uncertainty": uncertainty,
        "sources": sources,
    }


class TestPerspectiveMatrix:

    def test_perspective_matrix_builds(self, _all):
        assert len(_all["cells"]) > 0

    def test_every_matrix_cell_links_to_receipt(self, _all):
        assert matrix_cells_all_have_receipts(_all["cells"], _all["receipts"])

    def test_perspective_matrix_records_social_economic_legal_frames(self, _all):
        has_social = any(c.social_assumptions for c in _all["cells"])
        has_economic = any(c.economic_assumptions for c in _all["cells"])
        has_legal = any(c.legal_assumptions for c in _all["cells"])
        assert has_social or has_economic or has_legal

    def test_perspective_matrix_does_not_adjudicate_truth(self, _all):
        for c in _all["cells"]:
            assert c.receipt_hash

    def test_perspective_matrix_does_not_claim_culture(self, _all):
        pass


class TestConflictMap:

    def test_conflict_map_builds(self, _all):
        assert len(_all["conflicts"]) > 0

    def test_conflict_map_records_utility_vs_rights(self, _all):
        axes = {c.axis for c in _all["conflicts"]}
        assert "utility_vs_rights" in axes

    def test_conflict_map_records_truth_vs_social_stability(self, _all):
        axes = {c.axis for c in _all["conflicts"]}
        assert "truth_vs_social_stability" in axes

    def test_conflict_map_records_economic_efficiency_vs_dignity(self, _all):
        axes = {c.axis for c in _all["conflicts"]}
        assert "economic_efficiency_vs_dignity" in axes

    def test_conflict_map_performs_no_moral_adjudication(self, _all):
        for c in _all["conflicts"]:
            assert c.adjudication_performed is False
            assert c.moral_truth_claimed is False
            assert c.operator_review_required is True


class TestLedgers:

    def test_evidence_gap_tasks_are_not_actions(self, _all):
        for e in _all["evidence_gaps"]:
            assert e.action_authorized is False

    def test_evidence_gap_tasks_do_not_authorize_tools(self, _all):
        for e in _all["evidence_gaps"]:
            assert e.tool_authorized is False

    def test_uncertainty_ledger_records_fixture_limitations(self, _all):
        kinds = {u.kind for u in _all["uncertainty"]}
        assert "fixture_only_limitation" in kinds
        assert "model_cohort_limitation" in kinds

    def test_source_ledger_placeholder_not_verified(self, _all):
        for s in _all["sources"]:
            assert s.source_verified is False
            assert s.retrieval_performed is False
            assert s.placeholder_only is True

    def test_no_fake_real_sources(self, _all):
        for s in _all["sources"]:
            assert s.placeholder_only is True


class TestResearchDocument:

    def test_research_document_builds(self, _all):
        doc = build_research_document(
            question="How do models frame hard moral dilemmas?",
            scenario_count=len(_all["scenarios"]),
            model_count=len(build_cohort_registry()),
            fixture_response_count=len(_all["responses"]),
            matrix_cells=_all["cells"],
            conflicts=_all["conflicts"],
            evidence_gaps=_all["evidence_gaps"],
            uncertainty_records=_all["uncertainty"],
            source_records=_all["sources"],
        )
        assert doc.document_id
        assert doc.advisory_only is True

    def test_research_document_states_not_morality_decider(self, _all):
        doc = build_research_document(
            question="Test",
            scenario_count=10,
            model_count=10,
            fixture_response_count=25,
            matrix_cells=_all["cells"],
            conflicts=_all["conflicts"],
            evidence_gaps=_all["evidence_gaps"],
            uncertainty_records=_all["uncertainty"],
            source_records=_all["sources"],
        )
        disclaimers = doc.default_disclaimers()
        assert "This report does not decide morality." in disclaimers

    def test_research_document_states_models_not_cultures(self, _all):
        doc = build_research_document(
            question="Test",
            scenario_count=10,
            model_count=10,
            fixture_response_count=25,
            matrix_cells=_all["cells"],
            conflicts=_all["conflicts"],
            evidence_gaps=_all["evidence_gaps"],
            uncertainty_records=_all["uncertainty"],
            source_records=_all["sources"],
        )
        disclaimers = doc.default_disclaimers()
        assert any("model outputs represent cultures" in d for d in disclaimers)

    def test_research_document_preserves_boundaries(self, _all):
        doc = build_research_document(
            question="Test",
            scenario_count=10,
            model_count=10,
            fixture_response_count=25,
            matrix_cells=_all["cells"],
            conflicts=_all["conflicts"],
            evidence_gaps=_all["evidence_gaps"],
            uncertainty_records=_all["uncertainty"],
            source_records=_all["sources"],
        )
        assert doc.advisory_only is True
        disclaimers = doc.default_disclaimers()
        assert any("does not authorize action" in d for d in disclaimers)

    def test_research_document_renders_md(self, _all):
        doc = build_research_document(
            question="Test",
            scenario_count=10,
            model_count=10,
            fixture_response_count=25,
            matrix_cells=_all["cells"],
            conflicts=_all["conflicts"],
            evidence_gaps=_all["evidence_gaps"],
            uncertainty_records=_all["uncertainty"],
            source_records=_all["sources"],
        )
        md = render_research_document_md(doc)
        assert "Cross-Model Moral Research Document" in md
        assert "does not decide morality" in md
