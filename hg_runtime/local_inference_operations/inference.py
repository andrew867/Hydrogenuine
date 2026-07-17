"""CLIFT-03 / CAGI-68 local inference domain logic."""

from __future__ import annotations

from hg_runtime.local_inference_operations.schemas import (
    LARGE_MODEL_THRESHOLD_B,
    LocalInferenceError,
    reject_inference_overreach,
)


def validate_model_entry(entry: dict) -> list[str]:
    issues = []
    if not entry.get("model_id"):
        issues.append("missing_model_id")
    if not entry.get("model_name"):
        issues.append("missing_model_name")
    if entry.get("output_boundary") != "advisory_non_truth":
        issues.append("output_must_be_advisory_non_truth")
    if entry.get("provider_enabled"):
        issues.append("provider_must_not_be_enabled_by_default")
    return issues


def validate_resource_estimate(estimate: dict) -> list[str]:
    issues = []
    if not estimate.get("model_id"):
        issues.append("missing_model_id")
    if estimate.get("estimated_ram_mb", 0) <= 0:
        issues.append("invalid_ram_estimate")
    return issues


def is_large_model(entry: dict) -> bool:
    return entry.get("parameter_count_b", 0) >= LARGE_MODEL_THRESHOLD_B


def requires_explicit_config(entry: dict) -> bool:
    return is_large_model(entry) and not entry.get("explicit_config_present")


def refuse_unsafe_load(entry: dict) -> dict | None:
    if is_large_model(entry) and not entry.get("explicit_config_present"):
        return {
            "refused": True,
            "model_id": entry.get("model_id"),
            "reason": f"{entry.get('parameter_count_b', 0)}B model exceeds {LARGE_MODEL_THRESHOLD_B}B threshold without explicit config",
        }
    return None


def validate_output_boundary(record: dict) -> list[str]:
    issues = []
    if record.get("output_is_truth"):
        issues.append("output_must_not_be_truth")
    if record.get("output_is_authority"):
        issues.append("output_must_not_be_authority")
    if record.get("output_is_permission"):
        issues.append("output_must_not_be_permission")
    return issues
