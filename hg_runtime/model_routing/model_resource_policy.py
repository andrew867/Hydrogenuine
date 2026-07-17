"""Model resource policy — governs model lane assignment and resource preflight.

Forbidden models remain forbidden. Large models require resource preflight.
Available model is not permission. Endpoint reachability is not authorization.
"""

from __future__ import annotations

MODEL_LANES = frozenset({
    "fast_triage_model",
    "math_units_model",
    "synthesis_model",
    "code_review_model",
    "large_model_optional",
    "fallback_model",
})

LANE_MODEL_MAP = {
    "fast_triage_model": ["qwen2.5-0.5b-instruct", "qwen/qwen2.5-coder-1.5b-instruct"],
    "math_units_model": ["qwen/qwen2.5-coder-1.5b-instruct", "qwen2.5-0.5b-instruct"],
    "synthesis_model": ["google/gemma-4-e4b"],
    "code_review_model": ["qwen/qwen2.5-coder-1.5b-instruct"],
    "large_model_optional": ["google/gemma-4-e4b"],
    "fallback_model": ["qwen2.5-0.5b-instruct"],
}

FORBIDDEN_MODEL_PATTERNS = (
    "deepseek", "cybersecurity", "offensive", "uncensored",
    "30b", "qwen3-coder-30b",
)

LARGE_MODEL_PATTERNS = ("e4b", "7b", "8b", "13b", "30b", "33b", "34b", "70b", "72b")


def is_model_forbidden(model_id: str) -> bool:
    low = model_id.lower()
    return any(p in low for p in FORBIDDEN_MODEL_PATTERNS)


def is_large_model(model_id: str) -> bool:
    low = model_id.lower()
    return any(p in low for p in LARGE_MODEL_PATTERNS)


def resource_preflight(model_id: str, lane: str) -> dict:
    if lane not in MODEL_LANES:
        raise ValueError(f"unknown model lane: {lane}")

    forbidden = is_model_forbidden(model_id)
    large = is_large_model(model_id)
    requires_preflight = large and not forbidden
    lane_models = LANE_MODEL_MAP.get(lane, [])
    model_in_lane = model_id in lane_models

    return {
        "model_id": model_id,
        "lane": lane,
        "forbidden": forbidden,
        "is_large": large,
        "requires_preflight": requires_preflight,
        "preflight_passed": not forbidden and (not large or lane == "large_model_optional"),
        "model_in_lane": model_in_lane,
        "available_is_not_permission": True,
        "endpoint_reachability_is_not_authorization": True,
    }


def select_model_for_lane(lane: str) -> str | None:
    candidates = LANE_MODEL_MAP.get(lane)
    if not candidates:
        return None
    return candidates[0]
