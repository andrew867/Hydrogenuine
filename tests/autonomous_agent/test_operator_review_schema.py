"""Operator review schema tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.operator_review.schema import (
    ALLOWED_REVIEW_ACTIONS,
    FORBIDDEN_REVIEW_ACTIONS,
    OperatorReviewItem,
    ReviewAction,
    ReviewItemStatus,
    load_operator_review_policy,
    new_review_item_id,
    now_iso,
)


def test_review_item_requires_fields():
    item = OperatorReviewItem(
        review_item_id=new_review_item_id(),
        candidate_ref="candidate-abc",
        artifact_ref="artifact-abc",
        artifact_hash="sha256:abc",
        quality_receipt_ref="quality-abc",
        source_refs=["snap-1"],
        provider_receipt_refs=["prov-1"],
        status=ReviewItemStatus.QUEUED,
        created_at=now_iso(),
        updated_at=now_iso(),
        truth_state_ref="truth-abc",
    ).with_hash()
    payload = item.to_payload()
    assert payload["artifact_ref"]
    assert payload["artifact_hash"]
    assert payload["quality_receipt_ref"]
    assert payload["source_refs"]
    assert payload["hash"]


def test_forbidden_actions_not_allowed():
    policy = load_operator_review_policy()
    for action in policy["forbidden_review_actions"]:
        assert ReviewAction(action) in FORBIDDEN_REVIEW_ACTIONS


def test_allowed_actions_only():
    assert ReviewAction.HOLD in ALLOWED_REVIEW_ACTIONS
    assert ReviewAction.APPROVE in FORBIDDEN_REVIEW_ACTIONS
    assert ReviewAction.PUBLISH in FORBIDDEN_REVIEW_ACTIONS
