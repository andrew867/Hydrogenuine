"""Tests for moral research capsule scenario suite and cohort registry."""

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


class TestScenarioSuite:

    def test_scenario_suite_has_required_10_scenarios(self):
        suite = build_scenario_suite()
        assert len(suite) >= 10

    def test_each_scenario_has_decision_points(self):
        for s in build_scenario_suite():
            assert len(s.decision_points) >= 1, f"{s.scenario_id} missing decision_points"

    def test_each_scenario_has_boundary_risks(self):
        for s in build_scenario_suite():
            assert len(s.expected_boundary_risks) >= 1, f"{s.scenario_id} missing boundary_risks"

    def test_overtraining_risk_recorded_for_trolley_variants(self):
        suite = build_scenario_suite()
        trolley_ids = {"classic_trolley", "doctor_transplant"}
        for s in suite:
            if s.scenario_id in trolley_ids:
                assert s.known_overtraining_risk is True, f"{s.scenario_id}"

    def test_each_scenario_has_required_fields(self):
        for s in build_scenario_suite():
            assert s.scenario_id
            assert s.title
            assert s.prompt
            assert s.dilemma_type
            assert len(s.involved_parties) >= 2
            assert s.operator_review_required is True

    def test_scenario_ids_unique(self):
        ids = [s.scenario_id for s in build_scenario_suite()]
        assert len(ids) == len(set(ids))


class TestCohortRegistry:

    def test_cohort_registry_has_comparable_size_metadata(self):
        cohort = build_cohort_registry()
        assert len(cohort) >= 10
        sizes = {m.nominal_size_class for m in cohort}
        assert len(sizes) >= 3

    def test_model_family_is_not_country(self):
        for m in build_cohort_registry():
            assert m.model_family_is_not_country is True, f"{m.model_id}"

    def test_available_model_is_not_permission(self):
        for m in build_cohort_registry():
            if m.local_available:
                assert m.allowed_for_live_mode_default is False, f"{m.model_id}"

    def test_live_mode_default_false(self):
        for m in build_cohort_registry():
            assert m.allowed_for_live_mode_default is False, f"{m.model_id}"

    def test_forbidden_models_rejected_if_present(self):
        for m in build_cohort_registry():
            if m.forbidden_reason:
                assert m.allowed_for_fixture_mode is False or m.allowed_for_live_mode_default is False

    def test_metadata_does_not_infer_culture(self):
        for m in build_cohort_registry():
            assert m.model_family_is_not_country is True
            assert "culture" not in (m.notes or "").lower() or "not" in (m.notes or "").lower()


class TestFixtureResponses:

    def test_fixture_responses_cover_multiple_models_and_scenarios(self):
        responses = build_fixture_responses()
        models = {r.model_id for r in responses}
        scenarios = {r.scenario_id for r in responses}
        assert len(models) >= 5
        assert len(scenarios) >= 5

    def test_fixture_response_receipts_are_hashable(self):
        receipts = build_all_receipts()
        for r in receipts:
            assert r.receipt_hash
            assert len(r.receipt_hash) == 16

    def test_fixture_responses_include_refusal(self):
        receipts = build_all_receipts()
        assert any(r.refusal_present for r in receipts)

    def test_fixture_responses_include_willing_but_unsourced(self):
        receipts = build_all_receipts()
        assert any(r.willingness_present and not r.asks_for_context for r in receipts)

    def test_fixture_responses_include_cultural_overclaim(self):
        receipts = build_all_receipts()
        assert any(r.overclaims_culture for r in receipts)

    def test_fixture_responses_include_generic_slop(self):
        receipts = build_all_receipts()
        assert any(r.generic_slop_score > 0.3 for r in receipts)

    def test_fixture_responses_include_omission(self):
        receipts = build_all_receipts()
        assert any(len(r.missing_party_mentions) > 0 for r in receipts)
