from __future__ import annotations

from pathlib import Path

from hg_core.retention.churn_policy import classify_artifact_path, scan_churn_candidates


def test_protected_proof_index_not_auto_tombstone(tmp_path: Path):
    path = tmp_path / "docs" / "proofs" / "index.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}", encoding="utf-8")
    result = classify_artifact_path(tmp_path, path)
    assert result.category == "protected_truth_source"
    assert result.auto_tombstone_eligible is False


def test_ephemeral_tmp_is_churn(tmp_path: Path):
    path = tmp_path / ".tmp" / "scratch.txt"
    path.parent.mkdir(parents=True)
    path.write_text("x", encoding="utf-8")
    result = classify_artifact_path(tmp_path, path)
    assert result.category == "ephemeral_churn"
    assert result.auto_tombstone_eligible is True


def test_scan_churn_candidates(tmp_path: Path):
    churn = tmp_path / ".pytest-tmp-demo" / "file.bin"
    churn.parent.mkdir(parents=True)
    churn.write_bytes(b"demo")
    protected = tmp_path / "docs" / "proofs" / "index.json"
    protected.parent.mkdir(parents=True)
    protected.write_text("{}", encoding="utf-8")
    rows = scan_churn_candidates(tmp_path)
    rels = {row["rel_path"] for row in rows}
    assert ".pytest-tmp-demo/file.bin" in rels
    assert "docs/proofs/index.json" not in rels
