"""Tests for the live-local reasoning output classifier."""

from __future__ import annotations

import pytest

from hg_runtime.live_local.reasoning_classifier import (
    classify_response, reasoning_trace_is_final_answer, reasoning_only_is_red,
)

M = "google/gemma-4-e4b"


def test_classifies_normal_content():
    r = classify_response(model_id=M, endpoint="x", content="answer", finish_reason="stop")
    assert r.classification == "normal_content"
    assert r.severity == "GREEN"


def test_classifies_reasoning_only():
    r = classify_response(model_id=M, endpoint="x", reasoning="thinking...", finish_reason="stop")
    assert r.classification == "reasoning_only"


def test_classifies_reasoning_only_truncated():
    r = classify_response(model_id=M, endpoint="x", reasoning="thinking...", finish_reason="length")
    assert r.classification == "reasoning_only_truncated"


def test_classifies_empty_content():
    r = classify_response(model_id=M, endpoint="x", finish_reason="length")
    assert r.classification == "empty_content"


def test_classifies_timeout():
    r = classify_response(model_id=M, endpoint="x", error="request timed out")
    assert r.classification == "timeout"


def test_classifies_client_disconnect():
    r = classify_response(model_id=M, endpoint="x", error="connection reset by peer")
    assert r.classification == "client_disconnect"


def test_classifies_tool_call_shaped():
    r = classify_response(model_id=M, endpoint="x", tool_calls=[{"name": "f"}])
    assert r.classification == "tool_call_shaped"
    assert r.tools_authorized is False


def test_reasoning_only_is_yellow_not_red():
    r = classify_response(model_id=M, endpoint="x", reasoning="x", finish_reason="stop")
    assert r.severity == "YELLOW"
    assert reasoning_only_is_red(r) is False


def test_reasoning_trace_not_final_answer():
    r = classify_response(model_id=M, endpoint="x", reasoning="x", finish_reason="stop")
    assert reasoning_trace_is_final_answer(r) is False
    assert r.usable_for_research_summary is False


def test_content_plus_reasoning_usable_with_boundaries():
    r = classify_response(model_id=M, endpoint="x", content="answer", reasoning="trace",
                          finish_reason="stop")
    assert r.classification == "content_plus_reasoning"
    assert r.usable_for_research_summary is True
    assert r.usable_for_knowledge_candidate is True
    assert r.promotion_allowed is False


def test_forbidden_model_attempt_is_red():
    r = classify_response(model_id="deepseek-coder-v2-lite-instruct", endpoint="x", content="x")
    assert r.classification == "forbidden_model_attempt"
    assert r.severity == "RED"


def test_remote_fallback_attempt_is_red():
    r = classify_response(model_id=M, endpoint="x", content="x", remote_fallback=True)
    assert r.classification == "remote_fallback_attempt"
    assert r.severity == "RED"


def test_receipt_hash_stable_excludes_self():
    r = classify_response(model_id=M, endpoint="x", content="a", finish_reason="stop")
    assert r.receipt_hash == r.compute_hash()
