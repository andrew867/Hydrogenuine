"""Unfinished work classification tests."""

from __future__ import annotations

from hg_runtime.wake_refresh.schema import UnfinishedWorkClassification, UnfinishedWorkItem
from hg_runtime.wake_refresh.unfinished_work import count_requires_review, dropped_unfinished


def test_unknown_needs_review():
    items = [UnfinishedWorkItem("u1", "open tool", UnfinishedWorkClassification.UNKNOWN_NEEDS_REVIEW)]
    assert count_requires_review(items) == 1


def test_not_dropped():
    before = [UnfinishedWorkItem("a", "x", UnfinishedWorkClassification.SAFE_TO_RETRY)]
    after = list(before)
    assert dropped_unfinished(before, after) is False


def test_dropped_detected():
    before = [UnfinishedWorkItem("a", "x", UnfinishedWorkClassification.UNKNOWN_NEEDS_REVIEW)]
    after = []
    assert dropped_unfinished(before, after) is True
