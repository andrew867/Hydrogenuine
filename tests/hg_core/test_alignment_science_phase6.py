"""
Layer 9 Phase 6 (optional): Situational-awareness testbed — config, probe runner, scale-dependence metrics.
"""
from pathlib import Path

import pytest

from hg_core.alignment_science import (
    testbed_config as build_testbed_config,
    probe_result,
    run_testbed,
    get_testbed_run_result,
    run_testbed_api,
    get_testbed_run_api,
)


def test_situational_awareness_testbed_run(tmp_path: Path) -> None:
    """Testbed run with config produces probe results and metrics artifact."""
    config = build_testbed_config("eval_env", probe_types=["deception", "goal_stability"])
    result = run_testbed(tmp_path, config=config, emit_ledger=False)
    assert "run_id" in result
    assert "probe_results" in result
    assert len(result["probe_results"]) >= 1
    assert "artifact_ref" in result
    assert Path(result["artifact_ref"]).exists()
    assert "scale_dependence_metrics" in result
    assert "config" in result
    assert result["config"].get("environment_id") == "eval_env"
    assert result["config"].get("probe_types") == ["deception", "goal_stability"]


def test_testbed_run_produces_probe_results_and_metrics(tmp_path: Path) -> None:
    result = run_testbed(tmp_path, emit_ledger=False)
    assert isinstance(result["probe_results"], list)
    for pr in result["probe_results"]:
        assert "probe_id" in pr
        assert "probe_type" in pr
        assert "outcome" in pr
        assert pr["outcome"] in ("pass", "fail", "inconclusive")
        assert "metrics" in pr
    assert isinstance(result.get("scale_dependence_metrics"), dict)


def test_deception_probe_result_schema(tmp_path: Path) -> None:
    """Deception probe produces result with expected shape."""
    config = build_testbed_config("deception_env", probe_types=["deception"])
    result = run_testbed(tmp_path, config=config, emit_ledger=False)
    deception_results = [p for p in result["probe_results"] if p["probe_type"] == "deception"]
    assert len(deception_results) >= 1
    for pr in deception_results:
        assert "probe_id" in pr
        assert pr["probe_type"] == "deception"
        assert "outcome" in pr
        assert "metrics" in pr


def test_probe_result_builder_shape() -> None:
    pr = probe_result("p1", "goal_stability", "pass", metrics={"score": 0.9}, rationale="Stable.")
    assert pr["probe_id"] == "p1"
    assert pr["probe_type"] == "goal_stability"
    assert pr["outcome"] == "pass"
    assert pr["metrics"] == {"score": 0.9}
    assert pr["rationale"] == "Stable."


def test_get_testbed_run_result_returns_none_when_missing(tmp_path: Path) -> None:
    assert get_testbed_run_result(tmp_path, "no-such-run") is None


def test_get_testbed_run_result_returns_result_after_run(tmp_path: Path) -> None:
    out = run_testbed(tmp_path, emit_ledger=False)
    run_id = out["run_id"]
    loaded = get_testbed_run_result(tmp_path, run_id)
    assert loaded is not None
    assert loaded["run_id"] == run_id
    assert loaded["probe_results"] == out["probe_results"]


def test_run_testbed_api_returns_result(tmp_path: Path) -> None:
    r = run_testbed_api(tmp_path, config=build_testbed_config("api_env"), emit_ledger=False)
    assert r["ok"] is True
    assert "probe_results" in r["result"]
    assert "scale_dependence_metrics" in r["result"]


def test_get_testbed_run_api_not_found(tmp_path: Path) -> None:
    r = get_testbed_run_api(tmp_path, "no-such")
    assert r["ok"] is False
    assert r.get("error") == "not_found"


def test_get_testbed_run_api_returns_result(tmp_path: Path) -> None:
    out = run_testbed(tmp_path, emit_ledger=False)
    r = get_testbed_run_api(tmp_path, out["run_id"])
    assert r["ok"] is True
    assert r["result"]["run_id"] == out["run_id"]
