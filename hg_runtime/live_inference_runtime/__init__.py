"""INFER-LIVE runtime — governed local inference; outputs are not authority."""

from hg_runtime.live_inference_runtime.adapter import run_dry_run_inference
from hg_runtime.live_inference_runtime.evaluator import (
    analyze_infer_fixtures,
    process_infer_bundle,
    replay_fixture_stream,
    run_inference_runtime_fixture,
)
from hg_runtime.live_inference_runtime.fixtures import FUTURE_EXPIRY, INFER_FIXTURE_BUNDLES, PAST_EXPIRY, load_infer_fixtures
from hg_runtime.live_inference_runtime.hardware import (
    check_backend_readiness,
    detect_hardware_profile,
    select_backend,
    validate_minimum_hardware,
)
from hg_runtime.live_inference_runtime.model_registry import (
    MODEL_PROFILE_REGISTRY,
    assign_model_for_organ,
    backend_priority,
    cuda_is_optional_only,
    lookup_model_profile,
)
from hg_runtime.live_inference_runtime.tep_emission import (
    SOURCE_ORGAN,
    emit_fixture_inference_output,
    fence_live_inference_emission,
    run_infer_fixture_emission,
)
from hg_runtime.live_inference_runtime.types import (
    FIXTURE_CLOCK,
    INFER_SCHEMA_VERSION,
    BackendKind,
    BackendReadiness,
    HardwareProfile,
    InferenceOutput,
    InferenceRuntimeRequest,
    ModelProfile,
    classify_infer_claim_risk,
    hardware_from_fixture,
    is_bare_operator_ref,
    is_valid_tim_freshness,
    request_from_fixture,
)
from hg_runtime.live_inference_runtime.validator import refuse_infer_as_authority, validate_inference_request

__all__ = [
    "FIXTURE_CLOCK",
    "FUTURE_EXPIRY",
    "INFER_FIXTURE_BUNDLES",
    "INFER_SCHEMA_VERSION",
    "MODEL_PROFILE_REGISTRY",
    "PAST_EXPIRY",
    "SOURCE_ORGAN",
    "BackendKind",
    "BackendReadiness",
    "HardwareProfile",
    "InferenceOutput",
    "InferenceRuntimeRequest",
    "ModelProfile",
    "analyze_infer_fixtures",
    "assign_model_for_organ",
    "backend_priority",
    "check_backend_readiness",
    "classify_infer_claim_risk",
    "cuda_is_optional_only",
    "detect_hardware_profile",
    "emit_fixture_inference_output",
    "fence_live_inference_emission",
    "hardware_from_fixture",
    "is_bare_operator_ref",
    "is_valid_tim_freshness",
    "load_infer_fixtures",
    "lookup_model_profile",
    "process_infer_bundle",
    "refuse_infer_as_authority",
    "replay_fixture_stream",
    "request_from_fixture",
    "run_dry_run_inference",
    "run_inference_runtime_fixture",
    "run_infer_fixture_emission",
    "select_backend",
    "validate_inference_request",
    "validate_minimum_hardware",
]
