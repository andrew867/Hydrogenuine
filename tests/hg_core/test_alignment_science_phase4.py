"""
Layer 9 Phase 4: Scalable oversight — debate, eval pipeline, magnification.
"""
from pathlib import Path

import pytest

from hg_core.alignment_science import (
    run_debate,
    get_debate_outcome,
    generate_eval_cases,
    get_eval_cases,
    run_eval_scorer,
    get_eval_run_result,
    run_magnification,
    get_magnification_result,
    get_debate_api,
    run_debate_api,
    generate_eval_cases_api,
    get_eval_cases_api,
    run_eval_scorer_api,
    get_eval_run_api,
    run_magnification_api,
    get_magnification_api,
)


# --- Debate ---


def test_run_debate_produces_outcome_with_judge_and_artifact(tmp_path: Path) -> None:
    result = run_debate(tmp_path, "Test topic", max_turns=4, emit_ledger=False)
    assert "judge_outcome" in result
    assert result["judge_outcome"] in ("draw", "inconclusive", "a", "b")
    assert "artifact_ref" in result
    assert Path(result["artifact_ref"]).exists()
    assert "session_id" in result
    assert "topic" in result
    assert result["topic"] == "Test topic"


def test_get_debate_outcome_returns_none_when_missing(tmp_path: Path) -> None:
    assert get_debate_outcome(tmp_path, "no-such-session") is None


def test_get_debate_outcome_returns_result_after_run(tmp_path: Path) -> None:
    out = run_debate(tmp_path, "Topic", emit_ledger=False)
    session_id = out["session_id"]
    loaded = get_debate_outcome(tmp_path, session_id)
    assert loaded is not None
    assert loaded["session_id"] == session_id
    assert loaded["judge_outcome"] == out["judge_outcome"]


def test_get_debate_api_not_found(tmp_path: Path) -> None:
    r = get_debate_api(tmp_path, "no-such")
    assert r["ok"] is False
    assert r.get("error") == "not_found"


def test_run_debate_api_returns_result(tmp_path: Path) -> None:
    r = run_debate_api(tmp_path, "API topic", emit_ledger=False)
    assert r["ok"] is True
    assert "judge_outcome" in r["result"]
    assert "artifact_ref" in r["result"]


# --- Eval pipeline ---


def test_generate_eval_cases_produces_and_stores_cases(tmp_path: Path) -> None:
    cases = generate_eval_cases(tmp_path, "safety", count=5)
    assert len(cases) == 5
    for c in cases:
        assert "case_id" in c
        assert "input" in c
        assert "expected_or_criteria" in c
    loaded = get_eval_cases(tmp_path, "safety")
    assert len(loaded) == 5


def test_get_eval_cases_returns_empty_when_missing(tmp_path: Path) -> None:
    assert get_eval_cases(tmp_path, "no-domain") == []


def test_run_eval_scorer_produces_result_with_scores_and_aggregate(tmp_path: Path) -> None:
    generate_eval_cases(tmp_path, "ev", count=3)
    case_ids = [f"ev_{i}" for i in range(3)]
    result = run_eval_scorer(tmp_path, case_ids, emit_ledger=False)
    assert "scores" in result
    assert result["scores"] == {cid: 0.5 for cid in case_ids}
    assert "aggregate" in result
    assert result["aggregate"] == 0.5
    assert "artifact_ref" in result
    assert Path(result["artifact_ref"]).exists()
    assert "eval_run_id" in result


def test_get_eval_run_result_returns_none_when_missing(tmp_path: Path) -> None:
    assert get_eval_run_result(tmp_path, "no-such-eval-run") is None


def test_get_eval_run_result_returns_result_after_run(tmp_path: Path) -> None:
    case_ids = ["c1", "c2"]
    out = run_eval_scorer(tmp_path, case_ids, emit_ledger=False)
    eval_run_id = out["eval_run_id"]
    loaded = get_eval_run_result(tmp_path, eval_run_id)
    assert loaded is not None
    assert loaded["eval_run_id"] == eval_run_id
    assert loaded["aggregate"] == out["aggregate"]


def test_generate_eval_cases_api_returns_result(tmp_path: Path) -> None:
    r = generate_eval_cases_api(tmp_path, "api-domain", count=2)
    assert r["ok"] is True
    assert len(r["result"]) == 2


def test_get_eval_run_api_not_found(tmp_path: Path) -> None:
    r = get_eval_run_api(tmp_path, "no-such")
    assert r["ok"] is False
    assert r.get("error") == "not_found"


def test_run_eval_scorer_api_returns_result(tmp_path: Path) -> None:
    r = run_eval_scorer_api(tmp_path, ["case1", "case2"], emit_ledger=False)
    assert r["ok"] is True
    assert "scores" in r["result"]
    assert "aggregate" in r["result"]


# --- Magnification ---


def test_run_magnification_produces_result_with_magnified_ref(tmp_path: Path) -> None:
    ref = str(tmp_path / "human_feedback.json")
    result = run_magnification(tmp_path, ref, emit_ledger=False)
    assert "magnified_feedback_artifact_ref" in result
    assert Path(result["magnified_feedback_artifact_ref"]).exists()
    assert result["human_feedback_artifact_ref"] == ref
    assert "magnification_id" in result


def test_get_magnification_result_returns_none_when_missing(tmp_path: Path) -> None:
    assert get_magnification_result(tmp_path, "no-such-mag-id") is None


def test_get_magnification_result_returns_result_after_run(tmp_path: Path) -> None:
    ref = str(tmp_path / "fb.json")
    out = run_magnification(tmp_path, ref, emit_ledger=False)
    mag_id = out["magnification_id"]
    loaded = get_magnification_result(tmp_path, mag_id)
    assert loaded is not None
    assert loaded["magnification_id"] == mag_id
    assert loaded["magnified_feedback_artifact_ref"] == out["magnified_feedback_artifact_ref"]


def test_get_magnification_api_not_found(tmp_path: Path) -> None:
    r = get_magnification_api(tmp_path, "no-such")
    assert r["ok"] is False
    assert r.get("error") == "not_found"


def test_run_magnification_api_returns_result(tmp_path: Path) -> None:
    r = run_magnification_api(tmp_path, "/some/feedback/ref", emit_ledger=False)
    assert r["ok"] is True
    assert "magnified_feedback_artifact_ref" in r["result"]
