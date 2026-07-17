"""Artifact review queue CLI tests."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
import pytest
WORKSPACE = Path(__file__).resolve().parents[2]

def test_cli_no_approve_command():
    text = (WORKSPACE / "scripts/dev/agent_zero_artifact_review_queue.py").read_text(encoding="utf-8")
    assert "--approve" not in text and "--publish" not in text and "--send" not in text

def test_cli_list_and_show(tmp_path, monkeypatch):
    monkeypatch.setattr("hg_runtime.output_artifacts.artifact_store.artifacts_root", lambda base=None: tmp_path)
    sys.path.insert(0, str(WORKSPACE))
    from hg_runtime.output_artifacts.artifact_store import ArtifactStore
    from hg_runtime.output_artifacts.artifacts import build_draft_artifact
    from hg_runtime.output_artifacts.output_quality import evaluate_output_quality
    from hg_runtime.output_artifacts.review_candidates import create_review_candidate
    from hg_runtime.output_artifacts.source_binding import bind_sources
    binding = bind_sources(observe_snapshot_ref="snap-cli")
    art = build_draft_artifact(body="CLI preview body content for review queue display.",
        source_binding=binding, provider_receipt_refs=["prov-cli"], broker_decision_ref="dec-cli", surface="moltbook")
    store = ArtifactStore("run-cli")
    store.store_artifact(art)
    q = evaluate_output_quality(art)
    store.store_quality_receipt(q)
    cand = create_review_candidate(artifact=art, quality_receipt=q)
    store.store_review_candidate(cand)
    monkeypatch.setattr("hg_runtime.output_artifacts.artifact_store.artifacts_root", lambda base=None: tmp_path)
    proc = subprocess.run([sys.executable, str(WORKSPACE / "scripts/dev/agent_zero_artifact_review_queue.py"),
        "--run-id", "run-cli", "--list"], cwd=WORKSPACE, capture_output=True, text=True,
        env={**__import__("os").environ, "HG_ARTIFACT_ROOT": str(tmp_path)})
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["candidates"][0]["body_preview"] == art.body_preview
    proc2 = subprocess.run([sys.executable, str(WORKSPACE / "scripts/dev/agent_zero_artifact_review_queue.py"),
        "--run-id", "run-cli", "--show", cand.candidate_id], cwd=WORKSPACE, capture_output=True, text=True,
        env={**__import__("os").environ, "HG_ARTIFACT_ROOT": str(tmp_path)})
    assert proc2.returncode == 0
    shown = json.loads(proc2.stdout)
    assert shown["artifact"]["source_refs"]
    assert shown["artifact"]["provider_receipt_refs"]
    assert shown["quality"]["verdict"].startswith("GREEN_")
