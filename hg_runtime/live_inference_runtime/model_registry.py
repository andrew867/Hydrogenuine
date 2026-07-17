"""INFER-LIVE model profile registry — per-organ lightest-model assignment."""

from __future__ import annotations

from hg_runtime.live_inference_runtime.types import BackendKind, ModelProfile, ModelTier

MODEL_PROFILE_REGISTRY: tuple[ModelProfile, ...] = (
    ModelProfile(
        profile_id="model:small-default",
        tier="small",
        model_name="hydrogenuine-small-v1",
        parameter_scale="<1B",
        organ_assignments=("OEF", "NRV", "BRB"),
        preferred_backend="openvino_igpu",
    ),
    ModelProfile(
        profile_id="model:small-cpu-fallback",
        tier="small",
        model_name="hydrogenuine-small-cpu-v1",
        parameter_scale="<1B",
        organ_assignments=("DAB", "WDB"),
        preferred_backend="openvino_cpu",
    ),
    ModelProfile(
        profile_id="model:medium-escalation",
        tier="medium",
        model_name="hydrogenuine-medium-v1",
        parameter_scale="1-3B",
        organ_assignments=("DRB", "H8"),
        preferred_backend="openvino_igpu",
    ),
    ModelProfile(
        profile_id="model:large-advisory-only",
        tier="large",
        model_name="hydrogenuine-large-v1",
        parameter_scale="7B",
        organ_assignments=(),
        preferred_backend="vllm_openvino_planned",
    ),
)


def lookup_model_profile(profile_id: str) -> ModelProfile | None:
    for profile in MODEL_PROFILE_REGISTRY:
        if profile.profile_id == profile_id:
            return profile
    return None


def assign_model_for_organ(organ_ref: str, *, depth: str = "low") -> ModelProfile:
    """Select lightest capable model for organ depth; escalation is advisory only."""
    organ = organ_ref.split(":")[-1].upper()
    if depth == "low":
        for profile in MODEL_PROFILE_REGISTRY:
            if profile.tier == "small" and organ in profile.organ_assignments:
                return profile
        return MODEL_PROFILE_REGISTRY[0]
    if depth == "medium":
        for profile in MODEL_PROFILE_REGISTRY:
            if profile.tier == "medium":
                return profile
    return MODEL_PROFILE_REGISTRY[0]


def backend_priority() -> tuple[BackendKind, ...]:
    return ("openvino_igpu", "openvino_cpu", "vllm_openvino_planned", "cuda_optional")


def cuda_is_optional_only() -> bool:
    return True


__all__ = [
    "MODEL_PROFILE_REGISTRY",
    "assign_model_for_organ",
    "backend_priority",
    "cuda_is_optional_only",
    "lookup_model_profile",
]
