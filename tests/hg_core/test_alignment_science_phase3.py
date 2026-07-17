"""
Layer 9 Phase 3: Generalization/provenance — attribution, memorization, regurgitation vs learned.
"""
from pathlib import Path

import pytest

from hg_core.alignment_science import (
    run_attribution,
    get_attribution,
    run_memorization_detection,
    get_memorization_result,
    run_regurgitation_vs_learned,
    get_regurgitation_result,
    get_attribution_api,
    run_attribution_api,
    get_memorization_api,
    run_memorization_api,
    get_regurgitation_api,
    run_regurgitation_api,
)


def test_run_attribution_produces_artifact(tmp_path: Path) -> None:
    result = run_attribution(tmp_path, "dec-1", emit_ledger=False)
    assert result["decision_id"] == "dec-1"
    assert "influential_inputs" in result
    assert isinstance(result["influential_inputs"], list)
    assert "artifact_ref" in result
    assert Path(result["artifact_ref"]).exists()


def test_get_attribution_returns_none_when_missing(tmp_path: Path) -> None:
    assert get_attribution(tmp_path, "no-such") is None


def test_get_attribution_returns_result_after_run(tmp_path: Path) -> None:
    run_attribution(tmp_path, "dec-2", emit_ledger=False)
    out = get_attribution(tmp_path, "dec-2")
    assert out is not None
    assert out["decision_id"] == "dec-2"


def test_attribution_result_shape(tmp_path: Path) -> None:
    result = run_attribution(tmp_path, "dec-shape", emit_ledger=False)
    assert "influential_inputs" in result
    assert "artifact_ref" in result
    assert "created_at" in result


def test_run_memorization_detection_produces_artifact(tmp_path: Path) -> None:
    result = run_memorization_detection(tmp_path, "dec-1", emit_ledger=False)
    assert result["decision_id"] == "dec-1"
    assert "is_memorized" in result
    assert "artifact_ref" in result
    assert Path(result["artifact_ref"]).exists()


def test_get_memorization_result_returns_none_when_missing(tmp_path: Path) -> None:
    assert get_memorization_result(tmp_path, "no-such") is None


def test_memorization_result_shape(tmp_path: Path) -> None:
    result = run_memorization_detection(tmp_path, "dec-mem", emit_ledger=False)
    assert "is_memorized" in result
    assert "artifact_ref" in result


def test_run_regurgitation_vs_learned_produces_artifact(tmp_path: Path) -> None:
    result = run_regurgitation_vs_learned(tmp_path, "dec-1", emit_ledger=False)
    assert result["decision_id"] == "dec-1"
    assert result["label"] in ("regurgitation", "learned", "mixed")
    assert "artifact_ref" in result
    assert Path(result["artifact_ref"]).exists()


def test_get_regurgitation_result_returns_none_when_missing(tmp_path: Path) -> None:
    assert get_regurgitation_result(tmp_path, "no-such") is None


def test_regurgitation_result_shape(tmp_path: Path) -> None:
    result = run_regurgitation_vs_learned(tmp_path, "dec-reg", emit_ledger=False)
    assert "label" in result
    assert "artifact_ref" in result


def test_get_attribution_api_not_found(tmp_path: Path) -> None:
    out = get_attribution_api(tmp_path, "no-such")
    assert out["ok"] is False
    assert out.get("error") == "not_found"


def test_get_attribution_api_returns_result(tmp_path: Path) -> None:
    run_attribution(tmp_path, "dec-api", emit_ledger=False)
    out = get_attribution_api(tmp_path, "dec-api")
    assert out["ok"] is True
    assert out["result"]["decision_id"] == "dec-api"


def test_run_attribution_api_returns_result(tmp_path: Path) -> None:
    out = run_attribution_api(tmp_path, "dec-run", emit_ledger=False)
    assert out["ok"] is True
    assert out["result"]["decision_id"] == "dec-run"


def test_get_memorization_api_not_found(tmp_path: Path) -> None:
    out = get_memorization_api(tmp_path, "no-such")
    assert out["ok"] is False


def test_get_regurgitation_api_not_found(tmp_path: Path) -> None:
    out = get_regurgitation_api(tmp_path, "no-such")
    assert out["ok"] is False


def test_attribution_artifact_stored(tmp_path: Path) -> None:
    result = run_attribution(tmp_path, "dec-art", emit_ledger=False)
    path = Path(result["artifact_ref"])
    assert path.exists()
    data = path.read_text(encoding="utf-8")
    assert "dec-art" in data
    assert "influential_inputs" in data
