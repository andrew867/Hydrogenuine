"""Tests for the assumption inversion runner."""

from __future__ import annotations

import pytest

from hg_runtime.profile_model_autopilot.assumption_inversion import run_assumption_inversion


def _run(tmp_path=None):
    return run_assumption_inversion(
        research_seed_id="observer_state_frequency_hypothesis",
        problem_statement="observer-state time perception",
        domain_tags=["relativity", "observer state"],
        output_dir=str(tmp_path) if tmp_path else None,
    )


def test_assumption_inversion_runs_required_modes():
    r = _run()
    for mode in ("build_the_case", "disprove_the_case", "assume_real", "assume_false",
                 "boring_explanation_first", "units_and_math_audit",
                 "falsification_design", "synthesis_after_opposition"):
        assert mode in r["modes_run"]


def test_assumption_inversion_records_expected_if_true():
    r = _run()
    assert len(r["expected_if_real"]) > 0


def test_assumption_inversion_records_expected_if_false():
    r = _run()
    assert len(r["expected_if_false"]) > 0


def test_assumption_inversion_records_boring_explanation():
    r = _run()
    assert len(r["boring_explanations"]) > 0


def test_assumption_inversion_records_units_audit():
    r = _run()
    assert "dimensional_consistency" in r["units_math_audit"]


def test_assumption_inversion_records_synthesis():
    r = _run()
    assert "Synthesis after opposition" in r["synthesis_after_opposition"]


def test_assume_real_pass_does_not_promote_fact():
    r = _run()
    assert r["promotion_allowed"] is False


def test_assume_false_pass_does_not_block_future_evidence():
    from hg_runtime.profile_model_autopilot.science_modes import get_mode
    m = get_mode("assume_false")
    assert "does not prohibit future evidence" in " ".join(m.required_boundaries)


def test_all_assumption_passes_write_receipts(tmp_path):
    r = _run(tmp_path)
    assert (tmp_path / "assumption_pass_receipts.jsonl").exists()
    assert (tmp_path / "falsification_targets.jsonl").exists()
    assert (tmp_path / "boring_explanations.jsonl").exists()
    assert (tmp_path / "synthesis_after_opposition.md").exists()
    for p in r["passes"]:
        assert p["promotion_allowed"] is False
        assert p["authority_granted"] is False
        assert p["live_effects_created"] is False
