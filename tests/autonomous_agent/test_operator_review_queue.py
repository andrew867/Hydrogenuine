"""Operator review queue tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.operator_review.review_queue import build_review_queue_snapshot
from hg_runtime.operator_review.schema import FreshnessStatus, ReviewQueueVerdict
from hg_runtime.output_artifacts.artifact_store import ArtifactStore
from hg_runtime.output_artifacts.artifacts import build_draft_artifact
from hg_runtime.output_artifacts.output_quality import evaluate_output_quality
from hg_runtime.output_artifacts.review_candidates import create_review_candidate
from hg_runtime.output_artifacts.source_binding import bind_sources


@pytest.fixture
def artifact_setup(tmp_path, monkeypatch):
    monkeypatch.setattr("hg_runtime.output_artifacts.artifact_store.artifacts_root", lambda base=None: tmp_path / "artifacts")
    monkeypatch.setattr("hg_runtime.operator_review.review_store.review_root", lambda base=None: tmp_path / "review")
    binding = bind_sources(observe_snapshot_ref="snap-q")
    art = build_draft_artifact(
        body="Queue test body with enough content for quality checks.",
        source_binding=binding,
        provider_receipt_refs=["prov-q"],
        broker_decision_ref="dec-q",
        surface="moltbook",
    )
    store = ArtifactStore("run-q")
    store.store_artifact(art)
    q = evaluate_output_quality(art)
    store.store_quality_receipt(q)
    cand = create_review_candidate(artifact=art, quality_receipt=q)
    store.store_review_candidate(cand)
    return {"run_id": "run-q", "candidate": cand, "artifact": art, "quality": q}


def test_empty_queue_without_source_returns_red(tmp_path, monkeypatch):
    monkeypatch.setattr("hg_runtime.output_artifacts.artifact_store.artifacts_root", lambda base=None: tmp_path / "artifacts")
    monkeypatch.setattr("hg_runtime.operator_review.review_store.review_root", lambda base=None: tmp_path / "review")
    snap = build_review_queue_snapshot("missing-run")
    assert snap.verdict == ReviewQueueVerdict.RED_REVIEW_QUEUE_EMPTY_GREEN_WITHOUT_SOURCE
    assert snap.freshness_status == FreshnessStatus.MISSING


def test_empty_queue_with_fresh_source_returns_yellow(tmp_path, monkeypatch):
    monkeypatch.setattr("hg_runtime.output_artifacts.artifact_store.artifacts_root", lambda base=None: tmp_path / "artifacts")
    monkeypatch.setattr("hg_runtime.operator_review.review_store.review_root", lambda base=None: tmp_path / "review")
    store = ArtifactStore("empty-run")
    store.root.mkdir(parents=True)
    store.manifest_path.write_text('{"kind":"manifest"}\n', encoding="utf-8")
    snap = build_review_queue_snapshot("empty-run")
    assert snap.verdict == ReviewQueueVerdict.YELLOW_REVIEW_QUEUE_EMPTY_FRESH
    assert snap.item_count == 0


def test_queue_with_candidate_requires_refs(artifact_setup):
    snap = build_review_queue_snapshot(artifact_setup["run_id"])
    assert snap.item_count == 1
    item = snap.items[0]
    assert item.artifact_ref
    assert item.artifact_hash
    assert item.quality_receipt_ref
    assert item.source_refs
    assert snap.verdict == ReviewQueueVerdict.GREEN_REVIEW_QUEUE_READY


def test_stale_queue_returns_yellow(artifact_setup, tmp_path, monkeypatch):
    import os
    import time

    monkeypatch.setattr("hg_runtime.operator_review.truth_state.STALE_TTL_SECONDS", 1)
    manifest = ArtifactStore(artifact_setup["run_id"]).manifest_path
    old = time.time() - 10
    os.utime(manifest, (old, old))
    snap = build_review_queue_snapshot(artifact_setup["run_id"])
    assert snap.verdict == ReviewQueueVerdict.YELLOW_REVIEW_QUEUE_STALE
