"""Artifact store tests."""
from __future__ import annotations
import sys
from pathlib import Path
import pytest
WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))
from hg_runtime.output_artifacts.artifact_store import ArtifactStore
from hg_runtime.output_artifacts.artifacts import build_draft_artifact
from hg_runtime.output_artifacts.errors import ArtifactStoreError
from hg_runtime.output_artifacts.output_quality import evaluate_output_quality
from hg_runtime.output_artifacts.source_binding import bind_sources

def test_store_append_read(tmp_path, monkeypatch):
    monkeypatch.setattr("hg_runtime.output_artifacts.artifact_store.artifacts_root", lambda base=None: tmp_path)
    store = ArtifactStore("run-store-1")
    binding = bind_sources(observe_snapshot_ref="snap-1", turn_intent_ref="intent-1")
    art = build_draft_artifact(body="Stored draft content for local review.", source_binding=binding,
        provider_receipt_refs=["prov-1"], broker_decision_ref="dec-1")
    store.store_artifact(art)
    q = evaluate_output_quality(art)
    store.store_quality_receipt(q)
    assert len(store.read_manifest()) == 2
    assert store.read_artifact(art.artifact_id)["artifact_id"] == art.artifact_id

def test_no_silent_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr("hg_runtime.output_artifacts.artifact_store.artifacts_root", lambda base=None: tmp_path)
    store = ArtifactStore("run-store-2")
    binding = bind_sources(observe_snapshot_ref="snap-1")
    art = build_draft_artifact(body="First artifact content stored here.", source_binding=binding,
        provider_receipt_refs=["prov-1"], broker_decision_ref="dec-1")
    store.store_artifact(art)
    with pytest.raises(ArtifactStoreError):
        store.store_artifact(art)
