"""Tests for local model whitelist policy enforcement.

/v1/models availability is not permission.
Only explicitly configured selected models may be used.
Forbidden model names must be rejected even if available.
"""

from __future__ import annotations

import pytest

from hg_runtime.local_inference_qa_orchestrator.receipt_classifier import (
    DEFAULT_ALLOWED_MODELS,
    FORBIDDEN_MODEL_PATTERNS,
    classify_receipt,
    is_model_allowed,
    is_model_forbidden,
)


class TestForbiddenModelRejection:

    def test_deepseek_rejected(self):
        assert is_model_forbidden("deepseek-coder-v2-lite-instruct") is True

    def test_deepseek_case_insensitive(self):
        assert is_model_forbidden("DeepSeek-V3") is True

    def test_cybersecurity_rejected(self):
        assert is_model_forbidden("cybersecurity-baronllm_offensive_security_llm_q6_k_gguf") is True

    def test_offensive_rejected(self):
        assert is_model_forbidden("some-offensive-model") is True

    def test_uncensored_rejected(self):
        assert is_model_forbidden("supergemma4-26b-uncensored-v2") is True

    def test_30b_rejected(self):
        assert is_model_forbidden("qwen3-coder-30b-a3b-instruct") is True

    def test_gemma_4_e4b_not_forbidden(self):
        assert is_model_forbidden("google/gemma-4-e4b") is False

    def test_small_safe_model_not_forbidden(self):
        assert is_model_forbidden("qwen2.5-coder-0.5b-instruct") is False


class TestModelAllowedPolicy:

    def test_whitelisted_model_allowed(self):
        assert is_model_allowed("google/gemma-4-e4b") is True

    def test_non_whitelisted_model_rejected(self):
        assert is_model_allowed("qwen2.5-coder-0.5b-instruct") is False

    def test_forbidden_model_never_allowed(self):
        assert is_model_allowed("deepseek-coder-v2-lite-instruct") is False

    def test_forbidden_model_not_allowed_even_if_whitelisted(self):
        custom_allow = frozenset({"deepseek-coder-v2-lite-instruct"})
        assert is_model_allowed("deepseek-coder-v2-lite-instruct", allowed=custom_allow) is False

    def test_custom_whitelist(self):
        custom = frozenset({"gemma-3-4b-it"})
        assert is_model_allowed("gemma-3-4b-it", allowed=custom) is True
        assert is_model_allowed("google/gemma-4-e4b", allowed=custom) is False

    def test_missing_model_yellow_not_fallback(self):
        r = classify_receipt(
            model_id="nonexistent-model-xyz",
            endpoint="http://127.0.0.1:1234/v1",
            content=None,
            finish_reason=None,
        )
        assert r["selected_model_allowed"] is False
        assert r["selected_model_forbidden"] is False
        assert r["remote_fallback_used"] is False


class TestAvailableModelNotPermission:

    def test_available_model_not_permission_field(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="Response.",
            finish_reason="stop",
        )
        assert r["available_model_not_permission"] is True

    def test_forbidden_model_flagged_in_receipt(self):
        r = classify_receipt(
            model_id="deepseek-coder-v2-lite-instruct",
            endpoint="http://127.0.0.1:1234/v1",
            content="Response from deepseek.",
            finish_reason="stop",
        )
        assert r["selected_model_allowed"] is False
        assert r["selected_model_forbidden"] is True
        assert r["available_model_not_permission"] is True

    def test_uncensored_model_flagged(self):
        r = classify_receipt(
            model_id="supergemma4-26b-uncensored-v2",
            endpoint="http://127.0.0.1:1234/v1",
            content="Response.",
            finish_reason="stop",
        )
        assert r["selected_model_allowed"] is False
        assert r["selected_model_forbidden"] is True

    def test_30b_model_flagged(self):
        r = classify_receipt(
            model_id="qwen3-coder-30b-a3b-instruct",
            endpoint="http://127.0.0.1:1234/v1",
            content="Response.",
            finish_reason="stop",
        )
        assert r["selected_model_allowed"] is False
        assert r["selected_model_forbidden"] is True


class TestRemoteFallbackRejected:

    def test_remote_fallback_flagged(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="http://127.0.0.1:1234/v1",
            content="Response.",
            finish_reason="stop",
            remote_fallback_used=True,
        )
        assert r["remote_fallback_used"] is True

    def test_remote_endpoint_not_loopback(self):
        r = classify_receipt(
            model_id="google/gemma-4-e4b",
            endpoint="https://api.anthropic.com/v1",
            content="Response.",
            finish_reason="stop",
        )
        assert r["loopback_only"] is False


class TestDefaultAllowedModels:

    def test_default_includes_gemma_4_e4b(self):
        assert "google/gemma-4-e4b" in DEFAULT_ALLOWED_MODELS

    def test_default_does_not_include_deepseek(self):
        for model in DEFAULT_ALLOWED_MODELS:
            assert "deepseek" not in model.lower()

    def test_default_does_not_include_offensive(self):
        for model in DEFAULT_ALLOWED_MODELS:
            assert "offensive" not in model.lower()
