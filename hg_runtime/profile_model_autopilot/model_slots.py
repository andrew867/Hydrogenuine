"""Model slot governor.

Available model is not permission. Endpoint reachability is not authorization.
Forbidden patterns override the allowlist. Zero cannot permanently switch its
own main brain.
"""

from __future__ import annotations

from dataclasses import dataclass, field


DEFAULT_MAIN_BRAIN = "google/gemma-4-e4b"

DEFAULT_ALLOWED_MODELS = (
    "google/gemma-4-e4b", "gemma-3-4b-it", "qwen2.5-7b-instruct",
    "qwen2.5-coder-7b-instruct", "qwen2.5-coder-3b-instruct",
    "qwen2.5-0.5b-instruct", "qwen2.5-1.5b-instruct",
    "qwen/qwen2.5-coder-1.5b-instruct",
    "lmstudio-community/qwen2.5-coder-1.5b-instruct",
    "lmstudio-community/qwen2.5-coder-3b-instruct",
    "qwen/qwen2.5-coder-3b-instruct",
    "smollm2-1.7b", "llama-3.2-1b-instruct", "qwen3.5-0.8b",
)

FORBIDDEN_PATTERNS = (
    "deepseek", "cybersecurity", "offensive", "uncensored", "30b", "qwen3-coder-30b",
)

_LARGE_PATTERNS = ("30b", "33b", "34b", "70b", "72b")


@dataclass
class ModelSlotPolicy:
    main_brain_model: str = DEFAULT_MAIN_BRAIN
    main_brain_always_loaded: bool = True
    max_small_models_loaded: int = 3
    max_large_models_loaded: int = 1
    large_model_requires_operator_review: bool = True
    main_brain_switch_requires_operator_review: bool = True
    main_brain_trial_allowed: bool = True
    permanent_main_brain_switch_allowed_by_zero: bool = False
    available_model_is_not_permission: bool = True
    thirty_b_denied_by_default: bool = True
    allowed_models: tuple = DEFAULT_ALLOWED_MODELS
    forbidden_patterns: tuple = FORBIDDEN_PATTERNS


def default_policy() -> ModelSlotPolicy:
    return ModelSlotPolicy()


def is_forbidden(model_id: str, policy: ModelSlotPolicy | None = None) -> bool:
    policy = policy or default_policy()
    low = model_id.lower()
    return any(p in low for p in policy.forbidden_patterns)


def is_large(model_id: str) -> bool:
    low = model_id.lower()
    return any(p in low for p in _LARGE_PATTERNS)


def is_allowed(model_id: str, policy: ModelSlotPolicy | None = None) -> tuple[bool, str]:
    policy = policy or default_policy()
    if is_forbidden(model_id, policy):
        return False, f"model matches forbidden pattern"
    if is_large(model_id) and policy.thirty_b_denied_by_default:
        return False, "30B-class or larger model denied by default"
    if model_id not in policy.allowed_models:
        return False, "model not in allowlist (available model is not permission)"
    return True, ""


@dataclass
class SlotAllocation:
    requested_model: str
    slot_type: str  # main / small_specialist / large_synthesis / fixture / unavailable
    granted: bool
    reason: str
    operator_review_required: bool = True
    available_is_not_permission: bool = True
    endpoint_reachable: bool | None = None


def allocate_slot(
    model_id: str, slot_type: str,
    *, small_loaded: int = 0, large_loaded: int = 0,
    endpoint_reachable: bool | None = None,
    policy: ModelSlotPolicy | None = None,
) -> SlotAllocation:
    policy = policy or default_policy()
    allowed, reason = is_allowed(model_id, policy)
    if not allowed:
        return SlotAllocation(model_id, slot_type, False, reason,
                              endpoint_reachable=endpoint_reachable)

    if slot_type == "small_specialist" and small_loaded >= policy.max_small_models_loaded:
        return SlotAllocation(model_id, slot_type, False,
                              f"max small models ({policy.max_small_models_loaded}) reached",
                              endpoint_reachable=endpoint_reachable)
    if slot_type == "large_synthesis":
        if large_loaded >= policy.max_large_models_loaded:
            return SlotAllocation(model_id, slot_type, False,
                                  f"max large models ({policy.max_large_models_loaded}) reached",
                                  endpoint_reachable=endpoint_reachable)
        # large slot needs operator review before use
        return SlotAllocation(model_id, slot_type, True,
                              "large slot proposed; requires operator review",
                              operator_review_required=True,
                              endpoint_reachable=endpoint_reachable)

    return SlotAllocation(model_id, slot_type, True, "allocated within policy",
                          endpoint_reachable=endpoint_reachable)


def endpoint_reachability_is_authorization() -> bool:
    """Reachability is never authorization."""
    return False


def policy_snapshot(policy: ModelSlotPolicy | None = None) -> dict:
    from dataclasses import asdict
    policy = policy or default_policy()
    d = asdict(policy)
    d["allowed_models"] = list(policy.allowed_models)
    d["forbidden_patterns"] = list(policy.forbidden_patterns)
    return d
