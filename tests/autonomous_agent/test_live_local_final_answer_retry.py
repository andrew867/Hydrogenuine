"""Tests for the final-answer retry policy (no network — monkeypatched client)."""

from __future__ import annotations

import pytest

import hg_runtime.live_local.client as client


def _fake_raw(seq):
    calls = {"n": 0}

    def _raw(base_url, model, prompt, max_tokens, timeout_s):
        r = seq[calls["n"]]
        calls["n"] += 1
        return r
    return _raw


def test_retries_reasoning_only_with_final_answer_prompt(monkeypatch):
    seq = [
        {"elapsed": 5.0, "finish": "stop", "content": "", "reasoning": "lots of thinking",
         "tool_calls": [], "content_tokens": 0, "reasoning_tokens": 200},
        {"elapsed": 3.0, "finish": "stop", "content": "Final: hypothesis X.", "reasoning": "",
         "tool_calls": [], "content_tokens": 6, "reasoning_tokens": 0},
    ]
    monkeypatch.setattr(client, "_raw_call", _fake_raw(seq))
    primary, retry = client.infer_with_retry(
        base_url="x", model="google/gemma-4-e4b", prompt="q", final_answer_retry=True)
    assert primary.classification == "reasoning_only"
    assert primary.retry_attempted is True
    assert retry is not None
    assert retry.classification == "final_answer_retry_success"


def test_retry_links_to_original_receipt(monkeypatch):
    seq = [
        {"elapsed": 5.0, "finish": "length", "content": "", "reasoning": "x",
         "tool_calls": [], "content_tokens": 0, "reasoning_tokens": 100},
        {"elapsed": 3.0, "finish": "stop", "content": "answer", "reasoning": "",
         "tool_calls": [], "content_tokens": 2, "reasoning_tokens": 0},
    ]
    monkeypatch.setattr(client, "_raw_call", _fake_raw(seq))
    primary, retry = client.infer_with_retry(base_url="x", model="google/gemma-4-e4b", prompt="q")
    assert retry.linked_receipt_hash == primary.receipt_hash


def test_retry_does_not_erase_original_failure(monkeypatch):
    seq = [
        {"elapsed": 5.0, "finish": "stop", "content": "", "reasoning": "x",
         "tool_calls": [], "content_tokens": 0, "reasoning_tokens": 100},
        {"elapsed": 3.0, "finish": "stop", "content": "ok", "reasoning": "",
         "tool_calls": [], "content_tokens": 1, "reasoning_tokens": 0},
    ]
    monkeypatch.setattr(client, "_raw_call", _fake_raw(seq))
    primary, retry = client.infer_with_retry(base_url="x", model="google/gemma-4-e4b", prompt="q")
    # original receipt still reflects the reasoning_only failure
    assert primary.classification == "reasoning_only"
    assert primary.retry_result == "success"


def test_retry_success_records_final_answer(monkeypatch):
    seq = [
        {"elapsed": 5.0, "finish": "length", "content": "", "reasoning": "x",
         "tool_calls": [], "content_tokens": 0, "reasoning_tokens": 100},
        {"elapsed": 3.0, "finish": "stop", "content": "FINAL ANSWER", "reasoning": "",
         "tool_calls": [], "content_tokens": 2, "reasoning_tokens": 0},
    ]
    monkeypatch.setattr(client, "_raw_call", _fake_raw(seq))
    _, retry = client.infer_with_retry(base_url="x", model="google/gemma-4-e4b", prompt="q")
    assert retry.content_char_count > 0
    assert retry.usable_for_research_summary is True


def test_retry_failure_records_yellow(monkeypatch):
    seq = [
        {"elapsed": 5.0, "finish": "length", "content": "", "reasoning": "x",
         "tool_calls": [], "content_tokens": 0, "reasoning_tokens": 100},
        {"elapsed": 3.0, "finish": "length", "content": "", "reasoning": "still thinking",
         "tool_calls": [], "content_tokens": 0, "reasoning_tokens": 100},
    ]
    monkeypatch.setattr(client, "_raw_call", _fake_raw(seq))
    primary, retry = client.infer_with_retry(base_url="x", model="google/gemma-4-e4b", prompt="q")
    assert retry.classification == "final_answer_retry_failed"
    assert retry.severity == "YELLOW"
    assert primary.retry_result == "failed"


def test_retry_authorizes_no_tools(monkeypatch):
    seq = [
        {"elapsed": 5.0, "finish": "stop", "content": "", "reasoning": "x",
         "tool_calls": [], "content_tokens": 0, "reasoning_tokens": 100},
        {"elapsed": 3.0, "finish": "stop", "content": "answer", "reasoning": "",
         "tool_calls": [], "content_tokens": 1, "reasoning_tokens": 0},
    ]
    monkeypatch.setattr(client, "_raw_call", _fake_raw(seq))
    primary, retry = client.infer_with_retry(base_url="x", model="google/gemma-4-e4b", prompt="q")
    assert retry.tools_authorized is False
    assert retry.live_effects_created is False


def test_forbidden_model_refused_no_call(monkeypatch):
    def _boom(*a, **k):
        raise AssertionError("should not call forbidden model")
    monkeypatch.setattr(client, "_raw_call", _boom)
    primary, retry = client.infer_with_retry(
        base_url="x", model="deepseek-coder-v2-lite-instruct", prompt="q")
    assert retry is None
    assert "refused" in primary.error.lower() or primary.classification == "forbidden_model_attempt"


def test_normal_content_no_retry(monkeypatch):
    seq = [{"elapsed": 2.0, "finish": "stop", "content": "answer", "reasoning": "",
            "tool_calls": [], "content_tokens": 1, "reasoning_tokens": 0}]
    monkeypatch.setattr(client, "_raw_call", _fake_raw(seq))
    primary, retry = client.infer_with_retry(base_url="x", model="google/gemma-4-e4b", prompt="q")
    assert primary.classification == "normal_content"
    assert retry is None
