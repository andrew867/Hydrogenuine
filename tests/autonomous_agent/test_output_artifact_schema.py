"""Output artifact schema tests."""
from __future__ import annotations
import sys
from pathlib import Path
WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))
from hg_runtime.output_artifacts.artifacts import build_draft_artifact
from hg_runtime.output_artifacts.source_binding import bind_sources

def test_draft_hash_deterministic():
    binding = bind_sources(observe_snapshot_ref="snap-1", turn_intent_ref="intent-1")
    a = build_draft_artifact(body="Meaningful draft content for review.", source_binding=binding,
        provider_receipt_refs=["prov-1"], broker_decision_ref="dec-1")
    assert a.hash == a.with_hash().hash
