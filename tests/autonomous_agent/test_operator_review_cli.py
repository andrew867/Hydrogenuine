"""Operator review CLI tests."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]


def test_cli_no_approve_command():
    text = (WORKSPACE / "scripts/dev/agent_zero_artifact_review_queue.py").read_text(encoding="utf-8")
    for cmd in ("--approve", "--publish", "--send", "--reply", "--comment"):
        assert cmd not in text


def test_cli_decision_commands_exist():
    text = (WORKSPACE / "scripts/dev/agent_zero_artifact_review_queue.py").read_text(encoding="utf-8")
    for cmd in ("--hold", "--reject", "--needs-edit", "--archive", "--note"):
        assert cmd in text


def test_cli_hold_writes_receipt(tmp_path, monkeypatch):
    monkeypatch.setattr("hg_runtime.output_artifacts.artifact_store.artifacts_root", lambda base=None: tmp_path / "artifacts")
    monkeypatch.setattr("hg_runtime.operator_review.review_store.review_root", lambda base=None: tmp_path / "review")
    sys.path.insert(0, str(WORKSPACE))
    from hg_runtime.output_artifacts.artifact_store import ArtifactStore
    from hg_runtime.output_artifacts.artifacts import build_draft_artifact
    from hg_runtime.output_artifacts.output_quality import evaluate_output_quality
    from hg_runtime.output_artifacts.review_candidates import create_review_candidate
    from hg_runtime.output_artifacts.source_binding import bind_sources

    binding = bind_sources(observe_snapshot_ref="snap-cli2")
    art = build_draft_artifact(
        body="CLI hold test body with enough content for quality checks.",
        source_binding=binding,
        provider_receipt_refs=["prov-cli2"],
        broker_decision_ref="dec-cli2",
        surface="moltbook",
    )
    store = ArtifactStore("run-cli2")
    store.store_artifact(art)
    q = evaluate_output_quality(art)
    store.store_quality_receipt(q)
    cand = create_review_candidate(artifact=art, quality_receipt=q)
    store.store_review_candidate(cand)

    env = {**__import__("os").environ, "HG_ARTIFACT_ROOT": str(tmp_path / "artifacts"), "HG_REVIEW_ROOT": str(tmp_path / "review")}
    proc = subprocess.run(
        [sys.executable, str(WORKSPACE / "scripts/dev/agent_zero_artifact_review_queue.py"),
         "--run-id", "run-cli2", "--hold", cand.candidate_id],
        cwd=WORKSPACE, capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["receipt_hash"]
    assert data["external_side_effect"] is False
    assert data["published"] is False
