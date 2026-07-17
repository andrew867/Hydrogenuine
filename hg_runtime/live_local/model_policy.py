"""Per-model live-local policy.

Gemma 4 E4B is a reasoning model: longer timeouts, generous tokens, capture
reasoning as scratchpad (never final answer), require a final answer for a GREEN
task. Fast triage models only if allowlisted. Forbidden models never get a policy
that permits selection.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict

from hg_runtime.profile_model_autopilot.model_slots import is_allowed, is_forbidden, default_policy


@dataclass
class LiveLocalModelPolicy:
    model_id: str
    model_role: str  # main_brain / synthesis / fast_triage
    is_reasoning_model: bool = False
    default_timeout_seconds: int = 240
    max_timeout_seconds: int = 360
    default_max_tokens: int = 768
    final_answer_retry_max_tokens: int = 192
    prefer_short_prompts: bool = True
    capture_reasoning_content: bool = True
    reasoning_content_is_scratchpad: bool = True
    reasoning_content_is_not_final_answer: bool = True
    allow_reasoning_summary: bool = True
    require_final_answer_for_green_task: bool = True
    no_tools: bool = True
    no_live_effects: bool = True
    allowlisted: bool = True


_GEMMA = LiveLocalModelPolicy(
    model_id="google/gemma-4-e4b",
    model_role="main_brain",
    is_reasoning_model=True,
    default_timeout_seconds=300,
    max_timeout_seconds=360,
    default_max_tokens=1024,
    final_answer_retry_max_tokens=512,
)

# Fast triage candidates — only usable if allowlisted by project model policy.
_FAST_TRIAGE_CANDIDATES = (
    "qwen2.5-0.5b-instruct",
    "qwen2.5-1.5b-instruct",
    "qwen2.5-coder-3b-instruct",
    "qwen2.5-coder-7b-instruct",
    "smollm2-1.7b",
    "llama-3.2-1b-instruct",
    "qwen3.5-0.8b",
)


def get_policy(model_id: str) -> LiveLocalModelPolicy | None:
    if model_id == "google/gemma-4-e4b":
        return _GEMMA
    # Fast triage policy only if allowlisted and not forbidden.
    allowed, _ = is_allowed(model_id, default_policy())
    if allowed and model_id in _FAST_TRIAGE_CANDIDATES:
        return LiveLocalModelPolicy(
            model_id=model_id, model_role="fast_triage",
            is_reasoning_model=False, default_timeout_seconds=120,
            max_timeout_seconds=180, default_max_tokens=256,
            final_answer_retry_max_tokens=128, allowlisted=True)
    return None


def gemma_policy() -> LiveLocalModelPolicy:
    return _GEMMA


def fast_triage_candidates() -> tuple:
    return _FAST_TRIAGE_CANDIDATES


def select_fast_triage(available_models: list[str]) -> str | None:
    """Pick a fast triage model only if it is allowlisted AND present. Availability
    alone is never permission."""
    for cand in _FAST_TRIAGE_CANDIDATES:
        if cand in available_models:
            allowed, _ = is_allowed(cand, default_policy())
            if allowed and not is_forbidden(cand):
                return cand
    return None


def policy_snapshot() -> dict:
    out = {"google/gemma-4-e4b": asdict(_GEMMA),
           "fast_triage_candidates": list(_FAST_TRIAGE_CANDIDATES)}
    return out
