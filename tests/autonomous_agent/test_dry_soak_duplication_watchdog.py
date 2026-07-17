"""Dry soak duplication watchdog tests."""
from __future__ import annotations

import json
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.dry_soak.duplication_watchdog import analyze_duplication
from hg_runtime.dry_soak.schema import DrySoakVerdict
from hg_runtime.output_artifacts.artifact_store import ArtifactStore


def _write_artifact(tmp_path: Path, run_id: str, artifact_id: str, body: str, body_hash: str | None = None) -> None:
    store = ArtifactStore(run_id, base=tmp_path / "turns")
    store.artifacts_dir.mkdir(parents=True, exist_ok=True)
    bh = body_hash or f"hash-{artifact_id}"
    payload = {
        "artifact_id": artifact_id,
        "body": body,
        "body_hash": bh,
        "body_preview": body[:80],
    }
    (store.artifacts_dir / f"{artifact_id}.json").write_text(json.dumps(payload), encoding="utf-8")


def test_detects_duplicate_body_hashes(tmp_path):
    run_id = "dup-run"
    body = "Unique content for duplicate test " * 2
    _write_artifact(tmp_path, run_id, "a1", body, body_hash="dup-hash")
    _write_artifact(tmp_path, run_id, "a2", body, body_hash="dup-hash")
    report = analyze_duplication(run_id=run_id, turn_index=2, turn_base=tmp_path / "turns")
    assert report.duplicate_body_hash_rate > 0


def test_detects_fixture_text(tmp_path):
    run_id = "fix-run"
    _write_artifact(tmp_path, run_id, "a1", "Overnight candidate draft from template")
    report = analyze_duplication(run_id=run_id, turn_index=1, turn_base=tmp_path / "turns")
    assert report.verdict == DrySoakVerdict.RED_DRY_SOAK_FIXTURE_REGRESSION.value


def test_ignores_honest_deferred_turn_without_artifacts(tmp_path):
    report = analyze_duplication(
        run_id="rest-run",
        turn_index=1,
        turn_verdict="YELLOW_AGENT_TURN_RESTED",
        turn_base=tmp_path / "turns",
    )
    assert report.verdict == "YELLOW_DEFERRED_NO_ARTIFACTS"
    assert report.duplicate_body_hash_rate == 0.0
