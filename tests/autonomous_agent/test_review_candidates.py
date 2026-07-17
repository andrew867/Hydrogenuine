"""Review candidate tests."""
from __future__ import annotations
import sys
from pathlib import Path
import pytest
WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))
from hg_runtime.output_artifacts.artifacts import build_draft_artifact
from hg_runtime.output_artifacts.errors import ReviewCandidateError
from hg_runtime.output_artifacts.output_quality import evaluate_output_quality
from hg_runtime.output_artifacts.review_candidates import create_review_candidate
from hg_runtime.output_artifacts.source_binding import bind_sources

def _draft():
    binding = bind_sources(observe_snapshot_ref="snap-1", turn_intent_ref="intent-1")
    return build_draft_artifact(body="Review candidate draft with meaningful content.",
        source_binding=binding, provider_receipt_refs=["prov-1"], broker_decision_ref="dec-1")

def test_quality_passed_creates_candidate():
    art = _draft()
    q = evaluate_output_quality(art)
    c = create_review_candidate(artifact=art, quality_receipt=q)
    assert c.review_status.value == "queued"
    assert c.artifact_hash == art.hash

def test_quality_failed_no_candidate():
    binding = bind_sources(observe_snapshot_ref="snap-1")
    art = build_draft_artifact(body="TODO", source_binding=binding, provider_receipt_refs=["p1"], broker_decision_ref="d1")
    q = evaluate_output_quality(art)
    with pytest.raises(ReviewCandidateError):
        create_review_candidate(artifact=art, quality_receipt=q)

def test_not_approved_or_published():
    art = _draft()
    q = evaluate_output_quality(art)
    c = create_review_candidate(artifact=art, quality_receipt=q)
    assert not c.published and not c.sent
    assert c.operator_required

def test_candidate_has_artifact_hash():
    art = _draft()
    c = create_review_candidate(artifact=art, quality_receipt=evaluate_output_quality(art))
    assert c.artifact_hash
