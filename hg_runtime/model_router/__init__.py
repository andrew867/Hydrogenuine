"""Phase 33 Multi-Model Specialist Router and Local Model Residency Manager.

Routes bounded work items to model roles (planner/coder/critic/security_reviewer/
math_verifier/summarizer/cheap/large local models/document_writer) and manages local
model residency (catalog, providers, role/privacy/safety policies, load/unload,
keep-warm, TTL, eviction, health). Routing is not authority; loading is not
authority; a model output is not authority. A cheap/fast model cannot bypass critic
or security review; a larger model cannot widen scope; a local model cannot bypass
proof gates; a route cannot authorize tools or live actions. Only the fake local
provider runs in tests; LM Studio and OpenVINO are dry-run contracts; vLLM refuses.
"""

from __future__ import annotations

from hg_runtime.model_router.schemas import (
    ModelRouterError,
    MODEL_ROLES,
    SECURITY_ROLES,
    is_security_role,
    neutral_flags,
    reject_authority_payload,
)
from hg_runtime.model_router.catalog import register_model
from hg_runtime.model_router.providers import FakeLocalProvider, register_provider
from hg_runtime.model_router.lmstudio import LMStudioProviderContract
from hg_runtime.model_router.openvino import FutureVLLMProviderContract, OpenVINOProviderContract
from hg_runtime.model_router.roles import (
    define_role_policy,
    require_security_role_is_critic_only,
    validate_role_binding,
)
from hg_runtime.model_router.privacy import check_privacy, define_privacy_tier
from hg_runtime.model_router.safety import define_safety_policy, enforce_safety
from hg_runtime.model_router.routing import (
    build_provider_failure_record,
    create_route_request,
    handle_provider_failure,
    record_health_check,
    record_model_output,
    route_work_item,
)
from hg_runtime.model_router.residency import (
    DEFAULT_MAX_LOADED_MODELS,
    ResidencyManager,
    create_load_request,
    create_unload_request,
    define_residency_policy,
)
from hg_runtime.model_router.receipts import (
    assert_not_permission,
    build_residency_receipt,
    build_routing_receipt,
)
from hg_runtime.model_router.replay import (
    ModelRouterLog,
    RouterRecord,
    RouterReplayResult,
)
from hg_runtime.model_router.gate import (
    evaluate_phase33_gate,
    validate_phase33_proof_bundle,
)

__all__ = [
    "DEFAULT_MAX_LOADED_MODELS",
    "FakeLocalProvider",
    "FutureVLLMProviderContract",
    "LMStudioProviderContract",
    "MODEL_ROLES",
    "ModelRouterError",
    "ModelRouterLog",
    "OpenVINOProviderContract",
    "ResidencyManager",
    "RouterRecord",
    "RouterReplayResult",
    "SECURITY_ROLES",
    "assert_not_permission",
    "build_provider_failure_record",
    "build_residency_receipt",
    "build_routing_receipt",
    "check_privacy",
    "create_load_request",
    "create_route_request",
    "create_unload_request",
    "define_privacy_tier",
    "define_residency_policy",
    "define_role_policy",
    "define_safety_policy",
    "enforce_safety",
    "evaluate_phase33_gate",
    "handle_provider_failure",
    "is_security_role",
    "neutral_flags",
    "record_health_check",
    "record_model_output",
    "register_model",
    "register_provider",
    "reject_authority_payload",
    "require_security_role_is_critic_only",
    "route_work_item",
    "validate_phase33_proof_bundle",
    "validate_role_binding",
]
