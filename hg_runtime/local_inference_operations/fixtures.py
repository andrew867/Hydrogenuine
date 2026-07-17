"""CLIFT-03 / CAGI-68 fixture data for local inference operations."""

from __future__ import annotations


def fixture_model_registry_entry() -> dict:
    return {
        "model_id": "local-phi3-mini",
        "model_name": "Phi-3 Mini 3.8B",
        "parameter_count_b": 3.8,
        "format": "ONNX",
        "provider": "local_openvino",
        "provider_enabled": False,
        "requires_explicit_config": False,
        "output_boundary": "advisory_non_truth",
    }


def fixture_model_registry() -> list[dict]:
    return [
        fixture_model_registry_entry(),
        {
            "model_id": "local-llama3-8b",
            "model_name": "Llama 3 8B",
            "parameter_count_b": 8.0,
            "format": "GGUF",
            "provider": "local_llama_cpp",
            "provider_enabled": False,
            "requires_explicit_config": False,
            "output_boundary": "advisory_non_truth",
        },
        {
            "model_id": "local-codestral-22b",
            "model_name": "Codestral 22B",
            "parameter_count_b": 22.0,
            "format": "GGUF",
            "provider": "local_llama_cpp",
            "provider_enabled": False,
            "requires_explicit_config": False,
            "output_boundary": "advisory_non_truth",
        },
    ]


def fixture_large_model_entry() -> dict:
    return {
        "model_id": "local-llama3-70b",
        "model_name": "Llama 3 70B",
        "parameter_count_b": 70.0,
        "format": "GGUF",
        "provider": "local_llama_cpp",
        "provider_enabled": False,
        "requires_explicit_config": True,
        "output_boundary": "advisory_non_truth",
    }


def fixture_resource_estimate() -> dict:
    return {
        "model_id": "local-phi3-mini",
        "estimated_ram_mb": 2048,
        "estimated_vram_mb": 1024,
        "estimated_load_seconds": 5,
        "within_limits": True,
    }


def fixture_load_request() -> dict:
    return {
        "request_id": "load-001",
        "model_id": "local-phi3-mini",
        "requested_by": "operator",
        "approved": False,
        "provider_enabled": False,
        "resource_check_passed": True,
    }


def fixture_unsafe_load_refusal() -> dict:
    return {
        "request_id": "load-002",
        "model_id": "local-llama3-70b",
        "refused": True,
        "reason": "30B-class model requires explicit operator configuration",
        "parameter_count_b": 70.0,
        "explicit_config_present": False,
    }


def fixture_provider_disabled_record() -> dict:
    return {
        "provider": "local_openvino",
        "enabled_by_default": False,
        "requires_operator_activation": True,
    }


def fixture_output_boundary_record() -> dict:
    return {
        "model_id": "local-phi3-mini",
        "output_is_truth": False,
        "output_is_authority": False,
        "output_is_permission": False,
        "boundary": "advisory_non_truth",
    }


def fixture_inference_overreach_attempt() -> dict:
    return {
        "inference_treated_as_authority": True,
        "output_treated_as_truth": True,
        "large_model_default_load": True,
        "provider_enabled_by_default": True,
    }


def fixture_inference_status_snapshot() -> dict:
    return {
        "models_registered": 3,
        "models_loaded": 0,
        "provider_enabled": False,
        "network_required": False,
        "large_model_default_load": False,
        "all_outputs_advisory": True,
        "phase19_yellow": True,
        "phase24_infrastructure_only": True,
    }
