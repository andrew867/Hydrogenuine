"""Live-local reasoning output classifier.

Classifies a model response (or a request failure) into a bounded set of
categories and writes a receipt. Reasoning trace is never treated as the final
answer. Reasoning-only is YELLOW, not RED.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict

from hg_runtime.profile_model_autopilot.model_slots import is_allowed, is_forbidden, default_policy


CLASSIFICATIONS = (
    "normal_content", "content_plus_reasoning", "reasoning_only",
    "reasoning_only_truncated", "empty_content", "truncated_content",
    "timeout", "client_disconnect", "tool_call_shaped",
    "forbidden_model_attempt", "remote_fallback_attempt", "malformed_response",
    "final_answer_retry_success", "final_answer_retry_failed",
)

# RED classifications stop the run; YELLOW are recorded and the run continues.
_RED = {"forbidden_model_attempt", "remote_fallback_attempt"}
_YELLOW = {"reasoning_only", "reasoning_only_truncated", "empty_content",
           "truncated_content", "timeout", "client_disconnect", "malformed_response",
           "tool_call_shaped", "final_answer_retry_failed"}


@dataclass
class ReasoningReceipt:
    model_id: str
    endpoint: str
    prompt_id: str
    task_id: str
    science_mode: str
    seed_id: str
    requested_max_tokens: int
    requested_timeout_seconds: int
    elapsed_seconds: float
    finish_reason: str
    content_char_count: int
    reasoning_char_count: int
    content_token_count: int | None
    reasoning_token_count: int | None
    tool_call_count: int
    classification: str
    retry_attempted: bool = False
    retry_policy: str = ""
    retry_result: str = ""
    retry_index: int = 0
    usable_for_research_summary: bool = False
    usable_for_knowledge_candidate: bool = False
    promotion_allowed: bool = False
    authority_granted: bool = False
    tools_authorized: bool = False
    live_effects_created: bool = False
    severity: str = "GREEN"
    full_text: str = ""
    content_excerpt: str = ""
    reasoning_excerpt: str = ""
    provider_status: str = ""
    failure_reason: str = ""
    error: str = ""
    linked_receipt_hash: str = ""
    receipt_hash: str = ""

    def is_substantive(self) -> bool:
        """A response is substantive if it has non-empty final content and a usable classification."""
        if self.classification in _RED | {
            "timeout", "client_disconnect", "empty_content", "malformed_response",
            "final_answer_retry_failed", "reasoning_only", "reasoning_only_truncated",
        }:
            return False
        return len(self.full_text.strip()) > 0

    def compute_hash(self) -> str:
        d = {k: v for k, v in asdict(self).items() if k != "receipt_hash"}
        return hashlib.sha256(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()


def classify_response(
    *, model_id: str, endpoint: str, prompt_id: str = "", task_id: str = "",
    science_mode: str = "", seed_id: str = "", requested_max_tokens: int = 0,
    requested_timeout_seconds: int = 0, elapsed_seconds: float = 0.0,
    finish_reason: str = "", content: str = "", reasoning: str = "",
    tool_calls: list | None = None, content_tokens: int | None = None,
    reasoning_tokens: int | None = None, error: str = "",
    remote_fallback: bool = False, malformed: bool = False,
) -> ReasoningReceipt:
    tool_calls = tool_calls or []
    content = content or ""
    reasoning = reasoning or ""

    # Determine classification (priority order: hard-deny first).
    if is_forbidden(model_id, default_policy()):
        cls = "forbidden_model_attempt"
    elif remote_fallback:
        cls = "remote_fallback_attempt"
    elif error and "tim" in error.lower():
        cls = "timeout"
    elif error and ("disconnect" in error.lower() or "reset" in error.lower()
                    or "connection" in error.lower()):
        cls = "client_disconnect"
    elif malformed or (error and not content and not reasoning):
        cls = "malformed_response" if malformed else "timeout"
    elif tool_calls:
        cls = "tool_call_shaped"
    elif content.strip() and reasoning.strip():
        cls = "content_plus_reasoning"
    elif content.strip():
        cls = "truncated_content" if finish_reason == "length" else "normal_content"
    elif reasoning.strip():
        cls = "reasoning_only_truncated" if finish_reason == "length" else "reasoning_only"
    else:
        cls = "empty_content"

    severity = "RED" if cls in _RED else ("YELLOW" if cls in _YELLOW else "GREEN")

    # Usability: content is usable (with boundaries); reasoning trace is NOT a final answer.
    has_final_content = cls in ("normal_content", "content_plus_reasoning", "truncated_content")
    usable_summary = has_final_content and len(content.strip()) > 0
    usable_candidate = has_final_content  # still needs promotion gate + operator review

    failure_reason = ""
    provider_status = "ok"
    if cls == "timeout":
        failure_reason = "timeout"
        provider_status = "timeout"
    elif cls == "client_disconnect":
        failure_reason = "client_disconnect"
        provider_status = "disconnect"
    elif cls == "empty_content":
        failure_reason = "empty_response"
        provider_status = "empty"
    elif cls == "malformed_response":
        failure_reason = "malformed"
        provider_status = "malformed"
    elif cls in ("forbidden_model_attempt", "remote_fallback_attempt"):
        failure_reason = cls
        provider_status = "denied"
    elif error:
        failure_reason = "provider_error"
        provider_status = "error"

    rec = ReasoningReceipt(
        model_id=model_id, endpoint=endpoint, prompt_id=prompt_id, task_id=task_id,
        science_mode=science_mode, seed_id=seed_id,
        requested_max_tokens=requested_max_tokens,
        requested_timeout_seconds=requested_timeout_seconds,
        elapsed_seconds=round(elapsed_seconds, 2), finish_reason=finish_reason,
        content_char_count=len(content), reasoning_char_count=len(reasoning),
        content_token_count=content_tokens, reasoning_token_count=reasoning_tokens,
        tool_call_count=len(tool_calls), classification=cls,
        usable_for_research_summary=usable_summary,
        usable_for_knowledge_candidate=usable_candidate,
        severity=severity,
        full_text=content,
        content_excerpt=content[:280],
        reasoning_excerpt=reasoning[:200],
        provider_status=provider_status,
        failure_reason=failure_reason,
        error=error[:200],
        # Tools are always denied for tool-shaped output; never authorize.
        tools_authorized=False, authority_granted=False, live_effects_created=False,
        promotion_allowed=False,
    )
    rec.receipt_hash = rec.compute_hash()
    return rec


def reasoning_only_is_red(rec: ReasoningReceipt) -> bool:
    """Reasoning-only is never RED."""
    return rec.classification in ("reasoning_only", "reasoning_only_truncated") and rec.severity == "RED"


def reasoning_trace_is_final_answer(rec: ReasoningReceipt) -> bool:
    """A reasoning trace is never the final answer."""
    return False
