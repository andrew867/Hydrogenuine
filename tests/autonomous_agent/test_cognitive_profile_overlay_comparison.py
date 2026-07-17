"""Tests for profile comparison runner and prompt adapter boundaries."""

from __future__ import annotations

import pytest

APPLIED = "2026-06-23T00:00:00Z"


def _ids(n=3):
    from hg_runtime.cognitive_profile_overlay.profile_loader import load_all_profiles
    return [p.profile_id for p in load_all_profiles()[:n]]


# Prompt adapter boundary tests
def test_historical_profile_prompt_preserves_boundary():
    from hg_runtime.cognitive_profile_overlay.profile_loader import load_all_profiles
    from hg_runtime.cognitive_profile_overlay.prompt_adapter import (
        build_profile_prompt, prompt_preserves_identity_boundary,
    )
    prof = [p for p in load_all_profiles() if p.profile_kind == "historical"][0]
    prompt = build_profile_prompt(base_task_prompt="Analyze.", profile=prof, task_scope="research")
    assert prompt_preserves_identity_boundary(prompt)


def test_fictional_profile_prompt_preserves_boundary():
    from hg_runtime.cognitive_profile_overlay.profile_loader import load_all_profiles
    from hg_runtime.cognitive_profile_overlay.prompt_adapter import build_profile_prompt
    prof = [p for p in load_all_profiles() if p.profile_kind == "fictional"][0]
    prompt = build_profile_prompt(base_task_prompt="Analyze.", profile=prof, task_scope="research")
    low = prompt.lower()
    assert "not real" in low and "no canonical authority" in low


def test_modern_profile_prompt_does_not_impersonate():
    from hg_runtime.cognitive_profile_overlay.profile_loader import load_all_profiles
    from hg_runtime.cognitive_profile_overlay.prompt_adapter import build_profile_prompt
    prof = [p for p in load_all_profiles() if p.profile_kind == "modern"][0]
    prompt = build_profile_prompt(base_task_prompt="Analyze.", profile=prof, task_scope="research")
    assert "do not impersonate" in prompt.lower()


def test_prompt_says_not_this_person_or_character():
    from hg_runtime.cognitive_profile_overlay.profile_loader import load_profile_by_id
    from hg_runtime.cognitive_profile_overlay.prompt_adapter import build_profile_prompt
    prof = load_profile_by_id(_ids(1)[0])
    prompt = build_profile_prompt(base_task_prompt="X", profile=prof, task_scope="audit")
    assert "not this person or character" in prompt.lower()


def test_prompt_says_profile_is_temporary_lens():
    from hg_runtime.cognitive_profile_overlay.profile_loader import load_profile_by_id
    from hg_runtime.cognitive_profile_overlay.prompt_adapter import build_profile_prompt
    prof = load_profile_by_id(_ids(1)[0])
    prompt = build_profile_prompt(base_task_prompt="X", profile=prof, task_scope="audit")
    assert "temporary analytical lens" in prompt.lower()


def test_prompt_says_no_authority():
    from hg_runtime.cognitive_profile_overlay.profile_loader import load_profile_by_id
    from hg_runtime.cognitive_profile_overlay.prompt_adapter import (
        build_profile_prompt, prompt_preserves_no_authority,
    )
    prof = load_profile_by_id(_ids(1)[0])
    prompt = build_profile_prompt(base_task_prompt="X", profile=prof, task_scope="audit")
    assert prompt_preserves_no_authority(prompt)


def test_prompt_says_no_identity_memory_write():
    from hg_runtime.cognitive_profile_overlay.profile_loader import load_profile_by_id
    from hg_runtime.cognitive_profile_overlay.prompt_adapter import (
        build_profile_prompt, prompt_preserves_no_memory_write,
    )
    prof = load_profile_by_id(_ids(1)[0])
    prompt = build_profile_prompt(base_task_prompt="X", profile=prof, task_scope="audit")
    assert prompt_preserves_no_memory_write(prompt)


def test_prompt_contains_no_secret_patterns():
    import re
    from hg_runtime.cognitive_profile_overlay.profile_loader import load_profile_by_id
    from hg_runtime.cognitive_profile_overlay.prompt_adapter import build_profile_prompt
    prof = load_profile_by_id(_ids(1)[0])
    prompt = build_profile_prompt(base_task_prompt="X", profile=prof, task_scope="audit")
    assert not re.search(r"sk-[a-zA-Z0-9]{16,}", prompt)


# Comparison runner tests
def test_runs_same_problem_across_multiple_profiles_fixture_mode(tmp_path):
    from hg_runtime.cognitive_profile_overlay.comparison_runner import run_comparison
    result = run_comparison(
        problem_statement="Should we prioritize speed or safety?",
        profile_ids=_ids(3), task_scope="research", applied_at=APPLIED,
        output_dir=str(tmp_path),
    )
    assert result["profile_count"] == 3
    assert result["adjudication_performed"] is False


def test_comparison_matrix_links_to_receipts(tmp_path):
    from hg_runtime.cognitive_profile_overlay.comparison_runner import run_comparison
    result = run_comparison(
        problem_statement="Q", profile_ids=_ids(2), task_scope="research",
        applied_at=APPLIED, output_dir=str(tmp_path),
    )
    for cell in result["comparison_matrix"]:
        assert cell["source_receipt_hash"]


def test_conflict_map_builds_without_adjudication(tmp_path):
    from hg_runtime.cognitive_profile_overlay.comparison_runner import run_comparison
    result = run_comparison(
        problem_statement="Q", profile_ids=_ids(2), task_scope="research",
        applied_at=APPLIED, output_dir=str(tmp_path),
    )
    for axis in result["conflict_map"].values():
        assert axis["adjudicated"] is False


def test_evidence_gap_ledger_written(tmp_path):
    from hg_runtime.cognitive_profile_overlay.comparison_runner import run_comparison
    run_comparison(problem_statement="Q", profile_ids=_ids(2), task_scope="research",
                   applied_at=APPLIED, output_dir=str(tmp_path))
    assert (tmp_path / "profile_evidence_gap_ledger.jsonl").exists()


def test_uncertainty_ledger_written(tmp_path):
    from hg_runtime.cognitive_profile_overlay.comparison_runner import run_comparison
    run_comparison(problem_statement="Q", profile_ids=_ids(2), task_scope="research",
                   applied_at=APPLIED, output_dir=str(tmp_path))
    assert (tmp_path / "profile_uncertainty_ledger.jsonl").exists()


def test_profile_outputs_not_truth(tmp_path):
    from hg_runtime.cognitive_profile_overlay.comparison_runner import run_comparison
    result = run_comparison(problem_statement="Q", profile_ids=_ids(2),
                            task_scope="research", applied_at=APPLIED, output_dir=str(tmp_path))
    assert result["profile_outputs_are_truth"] is False
    for r in result["responses"]:
        assert r["is_truth"] is False


def test_profile_consensus_not_truth(tmp_path):
    from hg_runtime.cognitive_profile_overlay.comparison_runner import run_comparison
    result = run_comparison(problem_statement="Q", profile_ids=_ids(2),
                            task_scope="research", applied_at=APPLIED, output_dir=str(tmp_path))
    assert result["consensus_is_truth"] is False


def test_profile_disagreement_not_evidence(tmp_path):
    from hg_runtime.cognitive_profile_overlay.comparison_runner import run_comparison
    result = run_comparison(problem_statement="Q", profile_ids=_ids(2),
                            task_scope="research", applied_at=APPLIED, output_dir=str(tmp_path))
    assert result["disagreement_is_evidence"] is False


def test_agent_zero_against_itself_multiple_overlays(tmp_path):
    from hg_runtime.cognitive_profile_overlay.comparison_runner import run_comparison
    # Same problem, multiple lenses = Agent Zero against itself under overlays.
    result = run_comparison(problem_statement="Self-review this plan.",
                            profile_ids=_ids(4), task_scope="QA",
                            applied_at=APPLIED, output_dir=str(tmp_path))
    assert result["profile_count"] >= 2
    assert (tmp_path / "profile_operator_review.md").exists()
