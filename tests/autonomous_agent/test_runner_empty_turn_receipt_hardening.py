"""Tests for runner empty-turn / receipt-gap hardening.

Deterministic tests that do not require live LM Studio.
No empty turn is treated as successful cognition.
No model output is treated as truth or authority.
No receipt gap is hidden.
"""

from __future__ import annotations

import pytest

from hg_runtime.local_inference_qa_orchestrator.receipt_classifier import (
    classify_receipt,
)


class TestEmptyContentNoReasoning:

    def test_classified_as_empty_total(self):
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
        assert r["model_reasoning_only_output"] is False


class TestEmptyContentWithReasoning:

    def test_classified_as_reasoning_only(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="",
            reasoning_content="I have thoughts but no final answer.",
            finish_reason="stop",
        )
        assert r["model_reasoning_only_output"] is True
        assert r["model_empty_content_output"] is True
        assert r["model_empty_total_output"] is False
        assert r["reasoning_content_present"] is True
        assert r["model_final_answer_complete"] is False
        assert r["retry_reason"] == "MODEL_REASONING_ONLY_OUTPUT"


class TestTimeout:

    def test_timeout_simulated_as_empty(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content=None,
            reasoning_content=None,
            finish_reason=None,
        )
        assert r["model_empty_total_output"] is True
        assert r["model_final_answer_complete"] is False
        assert r["finish_reason"] is None


class TestFinishReasonLength:

    def test_truncated_output(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="Partial output that was truncated by max_tok",
            finish_reason="length",
        )
        assert r["finish_reason_length"] is True
        assert r["model_output_truncated"] is True
        assert r["model_final_answer_complete"] is False
        assert r["retry_reason"] == "MODEL_OUTPUT_TRUNCATED"

    def test_stop_not_truncated(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="Complete.",
            finish_reason="stop",
        )
        assert r["finish_reason_length"] is False
        assert r["model_output_truncated"] is False
        assert r["model_final_answer_complete"] is True
        assert r["retry_reason"] is None


class TestToolCallsReturned:

    def test_tool_calls_recorded_not_authorized(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="Let me call a tool.",
            tool_calls=[{"function": {"name": "deploy", "arguments": "{}"}}],
            finish_reason="tool_calls",
        )
        assert r["tool_calls_present"] is True
        assert r["tools_authorized"] is False

    def test_empty_tool_calls_list(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="No tools.",
            tool_calls=[],
            finish_reason="stop",
        )
        assert r["tool_calls_present"] is False
        assert r["tools_authorized"] is False


class TestFixtureProviderContent:

    def test_fixture_content_classified_normally(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="Fixture response content.",
            finish_reason="stop",
        )
        assert r["content_present"] is True
        assert r["model_final_answer_complete"] is True
        assert r["advisory_only"] is True

    def test_fixture_empty_content(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="",
            finish_reason="stop",
        )
        assert r["content_present"] is False
        assert r["model_empty_content_output"] is True


class TestRetryClassification:

    def test_retry_needed_for_reasoning_only(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="",
            reasoning_content="Thinking.",
            finish_reason="stop",
        )
        assert r["retry_reason"] == "MODEL_REASONING_ONLY_OUTPUT"
        assert r["retry_attempted"] is False
        assert r["retry_result"] is None

    def test_retry_needed_for_empty(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="",
            finish_reason="stop",
        )
        assert r["retry_reason"] == "MODEL_EMPTY_TOTAL_OUTPUT"

    def test_retry_needed_for_truncated(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="Partial",
            finish_reason="length",
        )
        assert r["retry_reason"] == "MODEL_OUTPUT_TRUNCATED"

    def test_no_retry_for_complete_output(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="Complete response.",
            finish_reason="stop",
        )
        assert r["retry_reason"] is None


class TestVerdictDistinction:

    def test_complete_output_green_shape(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="Good answer.",
            finish_reason="stop",
        )
        assert r["model_final_answer_complete"] is True
        assert r["retry_reason"] is None

    def test_empty_output_red_shape(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="",
            finish_reason="stop",
        )
        assert r["model_final_answer_complete"] is False
        assert r["retry_reason"] is not None

    def test_truncated_yellow_shape(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="Partial but present.",
            finish_reason="length",
        )
        assert r["content_present"] is True
        assert r["model_output_truncated"] is True
        assert r["model_final_answer_complete"] is False

    def test_forbidden_model_red_shape(self):
        r = classify_receipt(
            model_id="deepseek-coder-v2-lite-instruct",
            endpoint="http://127.0.0.1:1234/v1",
            content="Response.",
            finish_reason="stop",
        )
        assert r["selected_model_forbidden"] is True
        assert r["selected_model_allowed"] is False


class TestReceiptAbsentVsOptional:

    def test_receipt_fields_always_present(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="Response.",
            finish_reason="stop",
        )
        required_fields = {
            "model_id", "endpoint", "loopback_only",
            "selected_model_allowed", "available_model_not_permission",
            "remote_fallback_used", "tool_calls_present",
            "content_present", "content_length",
            "reasoning_content_present", "reasoning_content_length",
            "finish_reason", "finish_reason_length",
            "model_output_truncated", "model_final_answer_complete",
            "model_reasoning_only_output", "model_empty_content_output",
            "model_empty_total_output", "retry_attempted", "retry_reason",
            "retry_result", "advisory_only",
            "model_output_treated_as_truth",
            "model_confidence_treated_as_evidence",
            "model_willingness_treated_as_permission",
            "local_inference_treated_as_authority",
            "tools_authorized",
        }
        missing = required_fields - set(r.keys())
        assert not missing, f"Missing fields: {missing}"
