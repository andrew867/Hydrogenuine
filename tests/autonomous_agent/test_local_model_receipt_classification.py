"""Tests for local model receipt classification.

Local model output is always advisory only.
Local model output is never truth.
"""

from __future__ import annotations

import pytest

from hg_runtime.local_inference_qa_orchestrator.receipt_classifier import (
    classify_receipt,
    is_loopback_endpoint,
    is_model_allowed,
    is_model_forbidden,
)


class TestReceiptClassifierContentPresent:

    def test_normal_content_output(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="This is a normal response.",
            finish_reason="stop",
        )
        assert r["content_present"] is True
        assert r["content_length"] == 26
        assert r["model_final_answer_complete"] is True
        assert r["model_reasoning_only_output"] is False
        assert r["model_empty_total_output"] is False
        assert r["model_output_truncated"] is False
        assert r["advisory_only"] is True
        assert r["model_output_treated_as_truth"] is False
        assert r["local_inference_treated_as_authority"] is False

    def test_content_with_reasoning(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="Final answer.",
            reasoning_content="Let me think about this.",
            finish_reason="stop",
        )
        assert r["content_present"] is True
        assert r["reasoning_content_present"] is True
        assert r["model_reasoning_only_output"] is False
        assert r["model_final_answer_complete"] is True


class TestReceiptClassifierReasoningOnly:

    def test_reasoning_only_output(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="",
            reasoning_content="I thought about this deeply.",
            finish_reason="stop",
        )
        assert r["model_reasoning_only_output"] is True
        assert r["content_present"] is False
        assert r["reasoning_content_present"] is True
        assert r["model_final_answer_complete"] is False
        assert r["retry_reason"] == "MODEL_REASONING_ONLY_OUTPUT"
        assert r["model_output_treated_as_truth"] is False

    def test_reasoning_only_none_content(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content=None,
            reasoning_content="Thinking only.",
            finish_reason="stop",
        )
        assert r["model_reasoning_only_output"] is True
        assert r["model_empty_content_output"] is True


class TestReceiptClassifierEmptyOutput:

    def test_empty_content_no_reasoning(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="",
            reasoning_content="",
            finish_reason="stop",
        )
        assert r["model_empty_total_output"] is True
        assert r["model_final_answer_complete"] is False
        assert r["retry_reason"] == "MODEL_EMPTY_TOTAL_OUTPUT"

    def test_none_content_none_reasoning(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content=None,
            reasoning_content=None,
            finish_reason="stop",
        )
        assert r["model_empty_total_output"] is True


class TestReceiptClassifierFinishReasonLength:

    def test_truncated_output(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="Partial response that was cut off because the max_tokens",
            finish_reason="length",
        )
        assert r["finish_reason_length"] is True
        assert r["model_output_truncated"] is True
        assert r["model_final_answer_complete"] is False
        assert r["retry_reason"] == "MODEL_OUTPUT_TRUNCATED"

    def test_normal_stop_not_truncated(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="Complete response.",
            finish_reason="stop",
        )
        assert r["finish_reason_length"] is False
        assert r["model_output_truncated"] is False


class TestReceiptClassifierToolCalls:

    def test_tool_calls_recorded_not_executed(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="I want to call a tool.",
            tool_calls=[{"function": {"name": "deploy"}}],
            finish_reason="tool_calls",
        )
        assert r["tool_calls_present"] is True
        assert r["tools_authorized"] is False

    def test_no_tool_calls(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="No tools needed.",
            finish_reason="stop",
        )
        assert r["tool_calls_present"] is False
        assert r["tools_authorized"] is False


class TestReceiptClassifierEndpoint:

    def test_loopback_endpoint(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="Response.",
            finish_reason="stop",
        )
        assert r["loopback_only"] is True

    def test_remote_endpoint_flagged(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="https://api.example.com/v1",
            content="Response.",
            finish_reason="stop",
        )
        assert r["loopback_only"] is False

    def test_remote_fallback_flagged(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="Response.",
            finish_reason="stop",
            remote_fallback_used=True,
        )
        assert r["remote_fallback_used"] is True


class TestReceiptClassifierInvariants:

    def test_always_advisory(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="Any response.",
            finish_reason="stop",
        )
        assert r["advisory_only"] is True
        assert r["model_output_treated_as_truth"] is False
        assert r["model_confidence_treated_as_evidence"] is False
        assert r["model_willingness_treated_as_permission"] is False
        assert r["local_inference_treated_as_authority"] is False
        assert r["tools_authorized"] is False
        assert r["available_model_not_permission"] is True


class TestLoopbackValidation:

    def test_localhost(self):
        assert is_loopback_endpoint("http://localhost:1234/v1") is True

    def test_ipv4_loopback(self):
        assert is_loopback_endpoint("http://127.0.0.1:1234/v1") is True

    def test_ipv6_loopback(self):
        assert is_loopback_endpoint("http://[::1]:1234/v1") is True

    def test_remote_host(self):
        assert is_loopback_endpoint("https://api.openai.com/v1") is False

    def test_empty_string(self):
        assert is_loopback_endpoint("") is False
