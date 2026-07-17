"""Operator review decision tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.operator_review.review_decisions import (
    add_operator_note,
    archive_review_item,
    attempt_forbidden_action,
    hold_review_item,
    mark_review_item_needs_edit,
    reject_review_item,
)
from hg_runtime.operator_review.review_queue import build_review_queue_snapshot
from hg_runtime.operator_review.schema import ReviewDecisionVerdict
from hg_runtime.output_artifacts.artifact_store import ArtifactStore
from hg_runtime.output_artifacts.artifacts import build_draft_artifact
from hg_runtime.output_artifacts.output_quality import evaluate_output_quality
from hg_runtime.output_artifacts.review_candidates import create_review_candidate
from hg_runtime.output_artifacts.source_binding import bind_sources


@pytest.fixture
def review_env(tmp_path, monkeypatch):
    monkeypatch.setattr("hg_runtime.output_artifacts.artifact_store.artifacts_root", lambda base=None: tmp_path / "artifacts")
    monkeypatch.setattr("hg_runtime.operator_review.review_store.review_root", lambda base=None: tmp_path / "review")
    binding = bind_sources(observe_snapshot_ref="snap-d")
    art = build_draft_artifact(
        body="Decision test body with enough content for quality checks.",
        source_binding=binding,
        provider_receipt_refs=["prov-d"],
        broker_decision_ref="dec-d",
        surface="moltbook",
    )
    store = ArtifactStore("run-d")
    store.store_artifact(art)
    q = evaluate_output_quality(art)
    store.store_quality_receipt(q)
    cand = create_review_candidate(artifact=art, quality_receipt=q)
    store.store_review_candidate(cand)
    build_review_queue_snapshot("run-d")
    return {"run_id": "run-d", "candidate_id": cand.candidate_id}


@pytest.mark.parametrize("fn", [hold_review_item, reject_review_item, mark_review_item_needs_edit, archive_review_item])
def test_decision_writes_receipt(review_env, fn):
    result = fn(run_id=review_env["run_id"], candidate_ref=review_env["candidate_id"])
    assert result.verdict == ReviewDecisionVerdict.GREEN_REVIEW_DECISION_RECORDED
    assert result.receipt is not None
    assert result.receipt.external_side_effect is False
    assert result.receipt.published is False
    assert result.receipt.sent is False
    assert result.receipt_path


def test_operator_note_writes_receipt(review_env):
    result = add_operator_note(
        run_id=review_env["run_id"],
        candidate_ref=review_env["candidate_id"],
        operator_note="Looks good for local review only.",
    )
    assert result.receipt is not None


def test_needs_edit_invalidates_hash(review_env):
    result = mark_review_item_needs_edit(run_id=review_env["run_id"], candidate_ref=review_env["candidate_id"])
    assert result.receipt.artifact_hash_after is None


@pytest.mark.parametrize("action", ["approve", "publish", "send", "reply_live", "comment_live"])
def test_forbidden_actions(action, review_env):
    result = attempt_forbidden_action(action, run_id=review_env["run_id"], candidate_ref=review_env["candidate_id"])
    assert result.verdict == ReviewDecisionVerdict.RED_REVIEW_ACTION_FORBIDDEN


def test_review_candidate_not_approval(review_env):
    result = hold_review_item(run_id=review_env["run_id"], candidate_ref=review_env["candidate_id"])
    assert result.receipt.published is False
