"""Live-local LM Studio client with reasoning classification and final-answer retry.

Allowlist-enforced (forbidden models refused even when reachable). No tools, no
live effects, no remote fallback. Reasoning trace captured as scratchpad only.
"""

from __future__ import annotations

import json
import time
import urllib.request

from hg_runtime.profile_model_autopilot.model_slots import is_allowed, default_policy
from .reasoning_classifier import classify_response, ReasoningReceipt
from .model_policy import get_policy, gemma_policy
from .compact_prompts import FINAL_ANSWER_RETRY_PROMPT, FINAL_ANSWER_RETRY_PROMPT_SHORT


# Classifications that should trigger a final-answer retry.
_RETRY_TRIGGERS = {"reasoning_only", "reasoning_only_truncated", "empty_content",
                   "truncated_content"}


def _raw_call(base_url: str, model: str, prompt: str, max_tokens: int, timeout_s: int):
    url = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": max_tokens, "temperature": 0.3}).encode("utf-8")
    req = urllib.request.Request(url, data=body,
                                headers={"Content-Type": "application/json"}, method="POST")
    t = time.time()
    with urllib.request.urlopen(req, timeout=timeout_s) as r:
        d = json.load(r)
    dt = time.time() - t
    ch = d["choices"][0]
    msg = ch.get("message", {})
    usage = d.get("usage", {}) or {}
    details = usage.get("completion_tokens_details", {}) or {}
    return {
        "elapsed": dt, "finish": ch.get("finish_reason", ""),
        "content": msg.get("content") or "", "reasoning": msg.get("reasoning_content") or "",
        "tool_calls": msg.get("tool_calls") or [],
        "content_tokens": usage.get("completion_tokens"),
        "reasoning_tokens": details.get("reasoning_tokens"),
    }


def infer_with_retry(
    *, base_url: str, model: str, prompt: str, prompt_id: str = "", task_id: str = "",
    science_mode: str = "", seed_id: str = "", final_answer_retry: bool = True,
    timeout_s: int | None = None, max_tokens: int | None = None,
) -> tuple[ReasoningReceipt, ReasoningReceipt | None]:
    """Returns (primary_receipt, retry_receipt_or_None). Forbidden models refused."""
    allowed, why = is_allowed(model, default_policy())
    if not allowed:
        rec = classify_response(model_id=model, endpoint=base_url, prompt_id=prompt_id,
                                task_id=task_id, science_mode=science_mode, seed_id=seed_id,
                                error=f"model refused: {why}")
        # Force forbidden classification via the classifier's forbidden check.
        return rec, None

    pol = get_policy(model) or gemma_policy()
    to = timeout_s or pol.default_timeout_seconds
    mt = max_tokens or pol.default_max_tokens

    try:
        r = _raw_call(base_url, model, prompt, mt, to)
        primary = classify_response(
            model_id=model, endpoint=base_url, prompt_id=prompt_id, task_id=task_id,
            science_mode=science_mode, seed_id=seed_id, requested_max_tokens=mt,
            requested_timeout_seconds=to, elapsed_seconds=r["elapsed"],
            finish_reason=r["finish"], content=r["content"], reasoning=r["reasoning"],
            tool_calls=r["tool_calls"], content_tokens=r["content_tokens"],
            reasoning_tokens=r["reasoning_tokens"])
    except Exception as e:  # noqa: BLE001
        primary = classify_response(
            model_id=model, endpoint=base_url, prompt_id=prompt_id, task_id=task_id,
            science_mode=science_mode, seed_id=seed_id, requested_max_tokens=mt,
            requested_timeout_seconds=to, finish_reason="error", error=str(e)[:200])

    if not final_answer_retry or primary.classification not in _RETRY_TRIGGERS:
        return primary, None

    # --- final-answer-only retry (once) ---
    primary.retry_attempted = True
    primary.retry_policy = "final_answer_only_once"
    retry_prompt = FINAL_ANSWER_RETRY_PROMPT + "\n\nQuestion:\n" + prompt
    retry_to = min(pol.max_timeout_seconds, to + 60)
    try:
        r2 = _raw_call(base_url, model, retry_prompt, pol.final_answer_retry_max_tokens, retry_to)
        retry = classify_response(
            model_id=model, endpoint=base_url, prompt_id=prompt_id + "_retry", task_id=task_id,
            science_mode=science_mode, seed_id=seed_id,
            requested_max_tokens=pol.final_answer_retry_max_tokens,
            requested_timeout_seconds=retry_to, elapsed_seconds=r2["elapsed"],
            finish_reason=r2["finish"], content=r2["content"], reasoning=r2["reasoning"],
            tool_calls=r2["tool_calls"], content_tokens=r2["content_tokens"],
            reasoning_tokens=r2["reasoning_tokens"])
    except Exception as e:  # noqa: BLE001
        retry = classify_response(
            model_id=model, endpoint=base_url, prompt_id=prompt_id + "_retry", task_id=task_id,
            science_mode=science_mode, seed_id=seed_id, finish_reason="error", error=str(e)[:200])

    # Finalize the primary receipt FIRST (it now carries retry_attempted/retry_result),
    # then link the retry to the primary's final hash. Never erase the original failure.
    if retry.content_char_count > 0 and retry.classification in (
            "normal_content", "content_plus_reasoning", "truncated_content"):
        retry.classification = "final_answer_retry_success"
        retry.usable_for_research_summary = True
        primary.retry_result = "success"
    else:
        retry.classification = "final_answer_retry_failed"
        retry.severity = "YELLOW"
        primary.retry_result = "failed"
    primary.receipt_hash = primary.compute_hash()
    retry.linked_receipt_hash = primary.receipt_hash
    retry.receipt_hash = retry.compute_hash()
    return primary, retry
