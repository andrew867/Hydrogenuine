"""Governed large-model trial lane for bounded full-send soak.

A trial lane, not a promotion lane. Large model trials require operator
review. The large model cannot become the permanent main brain without
operator approval. Available model is not permission.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict

from hg_runtime.profile_model_autopilot.model_slots import (
    is_allowed, is_forbidden, is_large, default_policy,
)


LARGE_TRIAL_CANDIDATES = (
    "qwen2.5-coder-7b-instruct",
    "gemma-3-4b-it",
    "lmstudio-community/qwen2.5-coder-3b-instruct",
    "qwen/qwen2.5-coder-3b-instruct",
)

TWELVE_B_CANDIDATES = (
    "gemma-4-12b-coder-fable5-composer2.5-v1",
)


@dataclass
class LargeTrialPolicy:
    large_trial_enabled: bool = True
    max_large_models: int = 1
    large_model_trial_required_if_available: bool = True
    large_model_trial_optional_if_resource_unsafe: bool = True
    operator_review_required: bool = True
    permanent_switch_allowed: bool = False
    main_brain_switch_allowed: bool = False
    available_model_is_permission: bool = False
    endpoint_reachability_is_authorization: bool = False
    twelve_b_requires_explicit_allow: bool = True
    no_tools: bool = True
    no_live_effects: bool = True


def default_large_trial_policy() -> LargeTrialPolicy:
    return LargeTrialPolicy()


@dataclass
class ResourcePreflight:
    gpu_memory_total_mb: float = 0.0
    gpu_memory_used_mb: float = 0.0
    gpu_memory_free_mb: float = 0.0
    system_memory_total_mb: float = 0.0
    system_memory_used_mb: float = 0.0
    system_memory_free_mb: float = 0.0
    loaded_models: list[str] = field(default_factory=list)
    candidate_model: str = ""
    candidate_size_gb: float = 0.0
    estimated_additional_memory_gb: float = 0.0
    resource_safe: bool = False
    telemetry_available: bool = False
    reason: str = ""
    empirical_status: str = ""  # untested | success | failure
    resource_confidence: str = "unknown"  # high | medium | low | unknown
    static_estimate_may_be_wrong: bool = True
    can_attempt_trial: bool = False
    requires_operator_review: bool = True


_MODEL_SIZE_ESTIMATES_GB = {
    "qwen2.5-coder-7b-instruct": 4.5,
    "gemma-3-4b-it": 2.5,
    "lmstudio-community/qwen2.5-coder-3b-instruct": 2.0,
    "qwen/qwen2.5-coder-3b-instruct": 2.0,
    "gemma-4-12b-coder-fable5-composer2.5-v1": 8.0,
}


def _get_system_memory() -> tuple[float, float]:
    try:
        import psutil
        vm = psutil.virtual_memory()
        return vm.total / (1024**2), vm.used / (1024**2)
    except ImportError:
        return 0.0, 0.0


def run_resource_preflight(
    candidate_model: str,
    loaded_models: list[str],
    *,
    twelve_b_explicit_allow: bool = False,
    empirical_probe_success: bool | None = None,
) -> ResourcePreflight:
    pf = ResourcePreflight(
        candidate_model=candidate_model,
        loaded_models=list(loaded_models),
        static_estimate_may_be_wrong=True,
        requires_operator_review=True,
    )
    pf.candidate_size_gb = _MODEL_SIZE_ESTIMATES_GB.get(candidate_model, 5.0)

    total, used = _get_system_memory()
    if total > 0:
        pf.system_memory_total_mb = total
        pf.system_memory_used_mb = used
        pf.system_memory_free_mb = total - used
        pf.telemetry_available = True
        pf.resource_confidence = "medium"
    else:
        pf.resource_confidence = "low"

    is_12b = candidate_model in TWELVE_B_CANDIDATES or "12b" in candidate_model.lower()
    if is_12b and not twelve_b_explicit_allow:
        pf.resource_safe = False
        pf.can_attempt_trial = False
        pf.reason = "12B model requires explicit resource allow"
        return pf

    if pf.telemetry_available:
        free_gb = pf.system_memory_free_mb / 1024
        if free_gb < pf.candidate_size_gb * 1.2:
            if empirical_probe_success:
                pf.resource_safe = True
                pf.can_attempt_trial = True
                pf.empirical_status = "success"
                pf.resource_confidence = "high"
                pf.reason = (
                    f"static estimate says unsafe ({free_gb:.1f}GB < "
                    f"{pf.candidate_size_gb * 1.2:.1f}GB) but empirical "
                    f"probe succeeded — operator defaults may have changed")
            else:
                pf.resource_safe = False
                pf.can_attempt_trial = False
                pf.reason = (
                    f"insufficient free memory: {free_gb:.1f}GB < "
                    f"{pf.candidate_size_gb * 1.2:.1f}GB needed")
            return pf
        pf.resource_safe = True
        pf.can_attempt_trial = True
        pf.resource_confidence = "high" if pf.telemetry_available else "medium"
        pf.reason = (
            f"memory sufficient: {free_gb:.1f}GB free >= "
            f"{pf.candidate_size_gb * 1.2:.1f}GB needed")
    else:
        if is_12b:
            pf.resource_safe = False
            pf.can_attempt_trial = False
            pf.reason = "no telemetry available and 12B model too risky"
        elif empirical_probe_success:
            pf.resource_safe = True
            pf.can_attempt_trial = True
            pf.empirical_status = "success"
            pf.resource_confidence = "medium"
            pf.reason = (
                f"no telemetry but empirical probe succeeded "
                f"(candidate {pf.candidate_size_gb:.1f}GB)")
        elif pf.candidate_size_gb <= 5.0:
            pf.resource_safe = True
            pf.can_attempt_trial = True
            pf.reason = (
                f"no telemetry but candidate is {pf.candidate_size_gb:.1f}GB "
                f"(conservative allow for <=5GB)")
        else:
            pf.resource_safe = False
            pf.can_attempt_trial = False
            pf.reason = (
                f"no telemetry and candidate is {pf.candidate_size_gb:.1f}GB "
                f"(too large without telemetry)")

    return pf


def select_large_trial_candidate(
    available_models: list[str],
    *,
    twelve_b_explicit_allow: bool = False,
    policy: LargeTrialPolicy | None = None,
) -> str | None:
    policy = policy or default_large_trial_policy()
    if not policy.large_trial_enabled:
        return None

    slot_policy = default_policy()

    for cand in LARGE_TRIAL_CANDIDATES:
        if cand not in available_models:
            continue
        if is_forbidden(cand, slot_policy):
            continue
        allowed, _ = is_allowed(cand, slot_policy)
        if not allowed:
            continue
        return cand

    if twelve_b_explicit_allow:
        for cand in TWELVE_B_CANDIDATES:
            if cand not in available_models:
                continue
            if is_forbidden(cand, slot_policy):
                continue
            return cand

    return None


@dataclass
class LargeTrialTask:
    task_id: str = ""
    candidate_model: str = ""
    seed_id: str = ""
    science_mode: str = ""
    prompt: str = ""
    input_sources: list[str] = field(default_factory=list)
    content_char_count: int = 0
    reasoning_char_count: int = 0
    finish_reason: str = ""
    classification: str = ""
    latency_seconds: float = 0.0
    usable: bool = False
    error: str = ""
    quality_notes: str = ""
    boundary_notes: str = ""
    operator_review_required: bool = True
    authority_granted: bool = False
    tools_authorized: bool = False
    live_effects_created: bool = False
    main_brain_switch: bool = False
    recommendation_keep: bool = False
    recommendation_promote: bool = False
    recommendation_large_synthesis: bool = False


LARGE_TRIAL_PROMPT = (
    "Task: peer review.\n"
    "Input: fast triage summary + Gemma synthesis summary.\n"
    "Seed: {seed_title}\n"
    "Review the hypothesis.\n"
    "Return 3 strengths, 3 failure risks, and 1 next experiment.\n"
    "Label speculation.\n"
    "No tool calls. No truth claims.\n"
    "Max 220 words."
)


def build_large_trial_task(
    candidate_model: str,
    seed_id: str,
    seed_title: str,
    triage_task_id: str = "",
    gemma_task_id: str = "",
) -> LargeTrialTask:
    return LargeTrialTask(
        task_id=f"large_trial_{seed_id}_{int(time.time())}",
        candidate_model=candidate_model,
        seed_id=seed_id,
        science_mode="adversarial_peer_review",
        prompt=LARGE_TRIAL_PROMPT.format(seed_title=seed_title),
        input_sources=[s for s in [triage_task_id, gemma_task_id] if s],
        operator_review_required=True,
        authority_granted=False,
        tools_authorized=False,
        live_effects_created=False,
        main_brain_switch=False,
    )


@dataclass
class LargeTrialComparison:
    seed_id: str = ""
    fast_triage_model: str = ""
    fast_triage_content_chars: int = 0
    fast_triage_usable: bool = False
    gemma_model: str = "google/gemma-4-e4b"
    gemma_content_chars: int = 0
    gemma_reasoning_chars: int = 0
    gemma_usable: bool = False
    large_trial_model: str = ""
    large_trial_content_chars: int = 0
    large_trial_reasoning_chars: int = 0
    large_trial_usable: bool = False
    large_trial_latency_seconds: float = 0.0
    operator_review_required: bool = True
    recommendation_keep: bool = False
    recommendation_promote: bool = False
    recommendation_large_synthesis: bool = False


def evaluate_large_trial_result(
    trial_task: LargeTrialTask,
    fast_triage_chars: int = 0,
    gemma_chars: int = 0,
) -> LargeTrialComparison:
    comp = LargeTrialComparison(
        seed_id=trial_task.seed_id,
        large_trial_model=trial_task.candidate_model,
        large_trial_content_chars=trial_task.content_char_count,
        large_trial_reasoning_chars=trial_task.reasoning_char_count,
        large_trial_usable=trial_task.usable,
        large_trial_latency_seconds=trial_task.latency_seconds,
        fast_triage_content_chars=fast_triage_chars,
        gemma_content_chars=gemma_chars,
        operator_review_required=True,
        recommendation_promote=False,
    )
    if trial_task.usable and trial_task.content_char_count > 50:
        comp.recommendation_keep = True
        comp.recommendation_large_synthesis = True
    return comp


def policy_snapshot(policy: LargeTrialPolicy | None = None) -> dict:
    policy = policy or default_large_trial_policy()
    return {
        "policy": asdict(policy),
        "candidates": list(LARGE_TRIAL_CANDIDATES),
        "twelve_b_candidates": list(TWELVE_B_CANDIDATES),
        "model_size_estimates_gb": dict(_MODEL_SIZE_ESTIMATES_GB),
    }
