"""Model-role routing for daemon science-mode tasks.

Route science modes to model roles. Fast triage models handle short
falsification/boring/units tasks. Gemma handles synthesis/public-safe/review.
Forbidden models never selected. Available model is not permission.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional

from hg_runtime.profile_model_autopilot.model_slots import (
    is_allowed, is_forbidden, default_policy, is_large,
)


SCIENCE_MODE_MODEL_ROLE = {
    "build_the_case": "fast_triage",
    "disprove_the_case": "fast_triage",
    "assume_real": "fast_triage",
    "assume_false": "fast_triage",
    "boring_explanation_first": "fast_triage",
    "units_and_math_audit": "fast_math_or_coder",
    "falsification_design": "fast_triage",
    "source_discovery": "fast_triage",
    "mechanism_builder": "fast_triage",
    "public_safe_explainer": "main_synthesis",
    "adversarial_peer_review": "main_synthesis",
    "synthesis_after_opposition": "main_synthesis",
}


FAST_TRIAGE_CANDIDATES = (
    "qwen2.5-0.5b-instruct",
    "qwen2.5-1.5b-instruct",
    "qwen/qwen2.5-coder-1.5b-instruct",
    "lmstudio-community/qwen2.5-coder-1.5b-instruct",
    "lmstudio-community/qwen2.5-coder-3b-instruct",
    "qwen/qwen2.5-coder-3b-instruct",
    "qwen2.5-coder-3b-instruct",
    "smollm2-1.7b",
    "llama-3.2-1b-instruct",
    "qwen3.5-0.8b",
)

FAST_MATH_OR_CODER_CANDIDATES = (
    "qwen/qwen2.5-coder-1.5b-instruct",
    "lmstudio-community/qwen2.5-coder-1.5b-instruct",
    "lmstudio-community/qwen2.5-coder-3b-instruct",
    "qwen/qwen2.5-coder-3b-instruct",
    "qwen2.5-coder-3b-instruct",
    "qwen2.5-0.5b-instruct",
    "qwen2.5-1.5b-instruct",
)

GEMMA_MODEL_ID = "google/gemma-4-e4b"


@dataclass
class ModelRolePolicy:
    role: str
    model_id: str = ""
    preferred_timeout_seconds: int = 90
    max_timeout_seconds: int = 180
    default_max_tokens: int = 384
    retry_max_tokens: int = 192
    capture_reasoning_content: bool = True
    reasoning_content_is_scratchpad: bool = True
    reasoning_content_is_not_final_answer: bool = True
    require_final_answer_for_green_task: bool = True
    use_ultra_compact_prompts: bool = False
    use_compact_prompts: bool = True
    use_structured_outputs: bool = False
    no_tools: bool = True
    no_live_effects: bool = True


FAST_TRIAGE_POLICY = ModelRolePolicy(
    role="fast_triage",
    preferred_timeout_seconds=90,
    max_timeout_seconds=180,
    default_max_tokens=384,
    retry_max_tokens=192,
    use_ultra_compact_prompts=True,
)

FAST_MATH_OR_CODER_POLICY = ModelRolePolicy(
    role="fast_math_or_coder",
    preferred_timeout_seconds=120,
    max_timeout_seconds=240,
    default_max_tokens=512,
    retry_max_tokens=256,
    use_structured_outputs=True,
)

MAIN_SYNTHESIS_POLICY = ModelRolePolicy(
    role="main_synthesis",
    model_id=GEMMA_MODEL_ID,
    preferred_timeout_seconds=300,
    max_timeout_seconds=360,
    default_max_tokens=1024,
    retry_max_tokens=512,
    use_compact_prompts=True,
)


def get_model_role(science_mode: str) -> str | None:
    return SCIENCE_MODE_MODEL_ROLE.get(science_mode)


def get_role_policy(role: str) -> ModelRolePolicy | None:
    if role == "fast_triage":
        return FAST_TRIAGE_POLICY
    if role == "fast_math_or_coder":
        return FAST_MATH_OR_CODER_POLICY
    if role == "main_synthesis":
        return MAIN_SYNTHESIS_POLICY
    return None


def _is_candidate_allowed(model_id: str) -> bool:
    if is_forbidden(model_id):
        return False
    if is_large(model_id):
        return False
    allowed, _ = is_allowed(model_id, default_policy())
    return allowed


def select_fast_triage_model(available_models: list[str]) -> str | None:
    for cand in FAST_TRIAGE_CANDIDATES:
        if cand in available_models and _is_candidate_allowed(cand):
            return cand
    return None


def select_fast_math_model(available_models: list[str]) -> str | None:
    for cand in FAST_MATH_OR_CODER_CANDIDATES:
        if cand in available_models and _is_candidate_allowed(cand):
            return cand
    return None


@dataclass
class ModelRouteDecision:
    science_mode: str
    subagent_role: str
    model_role: str
    selected_model_id: str
    reason: str
    allowlist_decision: str
    forbidden_pattern_result: str
    endpoint_reachable: bool | None = None
    model_available: bool = True
    fast_triage_unavailable: bool = False
    gemma_tiny_prompt: bool = False
    authority_granted: bool = False
    tools_authorized: bool = False
    live_effects_created: bool = False


def route_task(
    science_mode: str,
    subagent_role: str,
    available_models: list[str],
    *,
    endpoint_reachable: bool | None = None,
) -> ModelRouteDecision:
    model_role = get_model_role(science_mode)
    if model_role is None:
        return ModelRouteDecision(
            science_mode=science_mode, subagent_role=subagent_role,
            model_role="denied", selected_model_id="",
            reason=f"no model role for science mode {science_mode}",
            allowlist_decision="no_mapping",
            forbidden_pattern_result="n/a",
            endpoint_reachable=endpoint_reachable,
            model_available=False,
        )

    if model_role == "main_synthesis":
        return ModelRouteDecision(
            science_mode=science_mode, subagent_role=subagent_role,
            model_role="main_synthesis", selected_model_id=GEMMA_MODEL_ID,
            reason="synthesis/review mode routes to Gemma",
            allowlist_decision="gemma_always_allowed",
            forbidden_pattern_result="not_forbidden",
            endpoint_reachable=endpoint_reachable,
        )

    if model_role == "fast_triage":
        sel = select_fast_triage_model(available_models)
        if sel is not None:
            return ModelRouteDecision(
                science_mode=science_mode, subagent_role=subagent_role,
                model_role="fast_triage", selected_model_id=sel,
                reason=f"fast triage model {sel} available and allowed",
                allowlist_decision="allowed",
                forbidden_pattern_result="not_forbidden",
                endpoint_reachable=endpoint_reachable,
            )
        return ModelRouteDecision(
            science_mode=science_mode, subagent_role=subagent_role,
            model_role="fast_triage", selected_model_id=GEMMA_MODEL_ID,
            reason="no fast triage model available; fallback to Gemma with tiny prompt",
            allowlist_decision="fallback_to_gemma",
            forbidden_pattern_result="not_forbidden",
            endpoint_reachable=endpoint_reachable,
            fast_triage_unavailable=True, gemma_tiny_prompt=True,
        )

    if model_role == "fast_math_or_coder":
        sel = select_fast_math_model(available_models)
        if sel is not None:
            return ModelRouteDecision(
                science_mode=science_mode, subagent_role=subagent_role,
                model_role="fast_math_or_coder", selected_model_id=sel,
                reason=f"fast math model {sel} available and allowed",
                allowlist_decision="allowed",
                forbidden_pattern_result="not_forbidden",
                endpoint_reachable=endpoint_reachable,
            )
        return ModelRouteDecision(
            science_mode=science_mode, subagent_role=subagent_role,
            model_role="fast_math_or_coder", selected_model_id=GEMMA_MODEL_ID,
            reason="no fast math model available; fallback to Gemma with tiny prompt",
            allowlist_decision="fallback_to_gemma",
            forbidden_pattern_result="not_forbidden",
            endpoint_reachable=endpoint_reachable,
            fast_triage_unavailable=True, gemma_tiny_prompt=True,
        )

    return ModelRouteDecision(
        science_mode=science_mode, subagent_role=subagent_role,
        model_role="denied", selected_model_id="",
        reason=f"unknown model role {model_role}",
        allowlist_decision="denied",
        forbidden_pattern_result="n/a",
        endpoint_reachable=endpoint_reachable,
        model_available=False,
    )


GEMMA_TINY_FALSIFICATION_PROMPT = (
    "Return JSON only. No reasoning. No prose.\n"
    "Task: speculative falsification.\n"
    "Give exactly 3 items.\n"
    "Each item keys: variable, if_real, if_false.\n"
    "Seed: {seed_title}\n"
    "No truth claims. No tool calls."
)

GEMMA_TINY_BORING_PROMPT = (
    "Return JSON only. No reasoning. No prose.\n"
    "Task: conventional explanation.\n"
    "Give exactly 3 items.\n"
    "Each item keys: mechanism, explanation.\n"
    "Seed: {seed_title}\n"
    "No truth claims. No tool calls."
)

GEMMA_TINY_UNITS_PROMPT = (
    "Return JSON only. No reasoning. No prose.\n"
    "Task: units/dimensional check.\n"
    "Give exactly 3 items.\n"
    "Each item keys: variable, units, coherent.\n"
    "Seed: {seed_title}\n"
    "No truth claims. No tool calls."
)


def gemma_tiny_prompt_for_mode(science_mode: str, seed_title: str) -> str:
    if science_mode in ("falsification_design", "disprove_the_case"):
        return GEMMA_TINY_FALSIFICATION_PROMPT.format(seed_title=seed_title)
    if science_mode in ("boring_explanation_first", "assume_false"):
        return GEMMA_TINY_BORING_PROMPT.format(seed_title=seed_title)
    if science_mode == "units_and_math_audit":
        return GEMMA_TINY_UNITS_PROMPT.format(seed_title=seed_title)
    return GEMMA_TINY_FALSIFICATION_PROMPT.format(seed_title=seed_title)


SYNTHESIS_FROM_TRIAGE_PROMPT = (
    "Task: SYNTHESIS from triage outputs.\n"
    "Seed: {seed_title}\n"
    "Triage results:\n{triage_summary}\n\n"
    "Synthesize a public-safe summary. Separate known physics / plausible "
    "cognition / metaphor / speculation. No hype, no fear. No "
    "consciousness-collapse, no manifestation-as-physics.\n"
    "No reasoning. No tool calls. Max 200 words."
)


def build_synthesis_prompt(seed_title: str, triage_summary: str) -> str:
    return SYNTHESIS_FROM_TRIAGE_PROMPT.format(
        seed_title=seed_title, triage_summary=triage_summary[:800],
    )


@dataclass
class SeedModeFailureTracker:
    failures: dict = field(default_factory=dict)
    max_failures_per_combo: int = 2

    def record_failure(self, seed_id: str, mode: str, model_id: str) -> None:
        key = f"{seed_id}:{mode}:{model_id}"
        self.failures[key] = self.failures.get(key, 0) + 1

    def should_skip(self, seed_id: str, mode: str, model_id: str) -> bool:
        key = f"{seed_id}:{mode}:{model_id}"
        return self.failures.get(key, 0) >= self.max_failures_per_combo

    def all_modes_failed(self, seed_id: str, modes: list[str]) -> bool:
        for mode in modes:
            mode_failed = False
            for key, count in self.failures.items():
                if key.startswith(f"{seed_id}:{mode}:") and count >= self.max_failures_per_combo:
                    mode_failed = True
                    break
            if not mode_failed:
                return False
        return True

    def seed_failure_count(self, seed_id: str) -> int:
        return sum(v for k, v in self.failures.items() if k.startswith(f"{seed_id}:"))


def routing_snapshot() -> dict:
    return {
        "science_mode_model_role": dict(SCIENCE_MODE_MODEL_ROLE),
        "fast_triage_candidates": list(FAST_TRIAGE_CANDIDATES),
        "fast_math_or_coder_candidates": list(FAST_MATH_OR_CODER_CANDIDATES),
        "gemma_model_id": GEMMA_MODEL_ID,
        "fast_triage_policy": asdict(FAST_TRIAGE_POLICY),
        "fast_math_or_coder_policy": asdict(FAST_MATH_OR_CODER_POLICY),
        "main_synthesis_policy": asdict(MAIN_SYNTHESIS_POLICY),
    }
