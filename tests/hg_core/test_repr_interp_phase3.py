"""
Tests for Layer 8 Phase 3: storage, API, proof-path/artifact emission.
"""
from pathlib import Path

import pytest

from hg_core.repr_interp import (
    store_inspection_result,
    get_inspection_results,
    read_run_dir_results,
    write_inspection_artifact,
    api_repr_interp_results,
    inspection_result,
)


def test_store_inspection_result_run_dir(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    result = inspection_result("p1", "req-1", "Output text.", ts="2026-01-01T00:00:00Z")
    store_inspection_result(tmp_path, result, run_dir=run_dir)
    rows = read_run_dir_results(run_dir)
    assert len(rows) == 1
    assert rows[0]["prompt_id"] == "p1"
    assert rows[0]["output_text"] == "Output text."


def test_store_inspection_result_with_decision_id_writes_global(tmp_path: Path) -> None:
    result = inspection_result("p1", "req-1", "Out", ts="2026-01-01T00:00:00Z")
    result["decision_id"] = "dec-1"
    store_inspection_result(tmp_path, result, run_dir=None)
    out = get_inspection_results(tmp_path, decision_id="dec-1")
    assert len(out) == 1
    assert out[0]["decision_id"] == "dec-1"


def test_get_inspection_results_filter_by_decision_id(tmp_path: Path) -> None:
    r1 = inspection_result("p1", "r1", "Out1", ts="1")
    r1["decision_id"] = "d1"
    r2 = inspection_result("p1", "r2", "Out2", ts="2")
    r2["decision_id"] = "d2"
    store_inspection_result(tmp_path, r1)
    store_inspection_result(tmp_path, r2)
    out = get_inspection_results(tmp_path, decision_id="d1")
    assert len(out) == 1
    assert out[0]["request_id"] == "r1"


def test_write_inspection_artifact(tmp_path: Path) -> None:
    result = {"inspection_id": "inv-1", "output_text": "x"}
    path = write_inspection_artifact(tmp_path, "inv-1", result)
    assert "repr_interp" in path
    assert "inv-1" in path
    assert Path(path).exists()


def test_api_repr_interp_results_shape(tmp_path: Path) -> None:
    out = api_repr_interp_results(tmp_path, limit=10)
    assert "results" in out
    assert isinstance(out["results"], list)


def test_api_repr_interp_results_respects_limit(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    for i in range(5):
        store_inspection_result(
            tmp_path,
            inspection_result("p", f"req-{i}", f"Out{i}", ts=f"2026-01-01T00:00:{i:02d}Z"),
            run_dir=run_dir,
        )
    out = api_repr_interp_results(tmp_path, run_dir=run_dir, limit=2)
    assert len(out["results"]) == 2


def test_proof_path_includes_representation_inspection_result(tmp_path: Path) -> None:
    from hg_core.metacognition.proof_path import get_proof_path

    result = inspection_result("proof_path_enrichment", "req-1", "Enrichment text.", ts="2026-01-01T00:00:00Z")
    result["decision_id"] = "dec-proof"
    store_inspection_result(tmp_path, result)
    proof = get_proof_path(tmp_path, "dec-proof")
    assert "representation_inspection_result" in proof
    assert isinstance(proof["representation_inspection_result"], list)
    assert len(proof["representation_inspection_result"]) == 1
    assert proof["representation_inspection_result"][0]["decision_id"] == "dec-proof"
