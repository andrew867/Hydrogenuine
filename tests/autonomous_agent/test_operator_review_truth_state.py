"""Operator review truth state tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.exciton.agent_zero_review_data_sources import build_agent_zero_review_panels
from hg_runtime.exciton.data_sources import CollectorContext
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.operator_review.schema import FreshnessStatus, ReviewItemTruthVerdict
from hg_runtime.operator_review.truth_state import build_review_item_truth_state


def test_truth_state_missing_hash():
    truth = build_review_item_truth_state(
        review_item_ref="ri-1",
        artifact={"artifact_id": "a1", "hash": "", "source_refs": ["s1"]},
        quality_receipt={"quality_receipt_id": "q1"},
        source_freshness=FreshnessStatus.FRESH,
    )
    assert truth.verdict == ReviewItemTruthVerdict.RED_REVIEW_ITEM_HASH_MISSING


def test_truth_state_missing_quality():
    truth = build_review_item_truth_state(
        review_item_ref="ri-1",
        artifact={"artifact_id": "a1", "hash": "sha256:x", "source_refs": ["s1"]},
        quality_receipt=None,
        source_freshness=FreshnessStatus.FRESH,
    )
    assert truth.verdict == ReviewItemTruthVerdict.RED_REVIEW_ITEM_QUALITY_MISSING


def test_truth_state_fixture_labelled():
    truth = build_review_item_truth_state(
        review_item_ref="ri-1",
        artifact={"artifact_id": "a1", "hash": "sha256:x", "source_refs": ["s1"], "data_tier": "FIXTURE"},
        quality_receipt={"quality_receipt_id": "q1"},
        source_freshness=FreshnessStatus.FRESH,
        fixture_label="test_fixture",
    )
    assert truth.verdict == ReviewItemTruthVerdict.YELLOW_REVIEW_ITEM_FIXTURE_LABELLED


def test_exciton_panel_requires_truth_state():
    panels = build_agent_zero_review_panels(CollectorContext(offline_fixture=True))
    for panel in panels:
        assert panel.fields.get("truth_state")
        assert panel.fields.get("freshness_status") is not None
        assert panel.fields.get("source_refs") is not None or panel.state == ExcitonPanelState.RED


def test_exciton_no_green_without_truth_on_missing_source():
    panels = build_agent_zero_review_panels(CollectorContext(offline_fixture=False))
    queue = next(p for p in panels if p.panel_id == "AgentZeroReviewQueuePanel")
    if not queue.fields.get("source_refs"):
        assert queue.state != ExcitonPanelState.GREEN
