"""Phase 33.5 Local Provider Smoke and Compatibility Probe.

Verifies that local provider endpoints (LM Studio, OpenVINO) can be probed,
classified, and optionally smoke-tested without becoming authority, deployment
approval, or live-action permission. Dry-run/fixture-safe by default: real local
calls, loads, and unloads happen only when the operator explicitly enables them. It
is a local-provider integration smoke, not a new authority layer and not Phase 35.
"""

from __future__ import annotations

from hg_runtime.local_provider_smoke.schemas import (
    HARMLESS_SMOKE_PROMPT,
    SMOKE_OK_TOKEN,
    VERDICT_GREEN_BOTH,
    VERDICT_GREEN_LMSTUDIO_ONLY,
    VERDICT_RED_FAILED,
    VERDICT_YELLOW_PARTIAL,
    LocalProviderSmokeError,
    assert_safe_smoke_model,
    classify_model_size,
    endpoint_is_local,
    is_large_model,
    is_security_model,
    is_tiny_model,
    neutral_flags,
    reject_authority_payload,
    reject_credentials,
    reject_forbidden_claim_text,
    require_local_endpoint,
)
from hg_runtime.local_provider_smoke.config import (
    build_smoke_config,
    load_smoke_config_from_env,
)
from hg_runtime.local_provider_smoke.probes import (
    assert_no_silent_fallback,
    autodetect_providers,
    probe_health,
    probe_openai_compatible_endpoint,
)
from hg_runtime.local_provider_smoke.capabilities import (
    record_capability,
    record_incompatibility,
    record_inventory,
    reject_openvino_gguf_assumption,
)
from hg_runtime.local_provider_smoke.model_smoke import (
    build_smoke_prompt,
    record_latency,
    record_smoke_response,
)
from hg_runtime.local_provider_smoke.memory import (
    estimate_model_memory,
    require_memory_estimate_before_large_load,
)
from hg_runtime.local_provider_smoke.lmstudio_smoke import lmstudio_smoke
from hg_runtime.local_provider_smoke.openvino_smoke import openvino_smoke
from hg_runtime.local_provider_smoke.comparison import (
    compare_providers,
    determine_smoke_verdict,
)
from hg_runtime.local_provider_smoke.receipts import (
    assert_not_fake_green,
    assert_not_permission,
    build_load_plan,
    build_load_receipt,
    build_smoke_receipt,
    build_unload_receipt,
)
from hg_runtime.local_provider_smoke.replay import LocalProviderSmokeLog

__all__ = [
    "HARMLESS_SMOKE_PROMPT",
    "LocalProviderSmokeError",
    "LocalProviderSmokeLog",
    "SMOKE_OK_TOKEN",
    "VERDICT_GREEN_BOTH",
    "VERDICT_GREEN_LMSTUDIO_ONLY",
    "VERDICT_RED_FAILED",
    "VERDICT_YELLOW_PARTIAL",
    "assert_no_silent_fallback",
    "assert_not_fake_green",
    "assert_not_permission",
    "assert_safe_smoke_model",
    "autodetect_providers",
    "build_load_plan",
    "build_load_receipt",
    "build_smoke_config",
    "build_smoke_prompt",
    "build_smoke_receipt",
    "build_unload_receipt",
    "classify_model_size",
    "compare_providers",
    "determine_smoke_verdict",
    "endpoint_is_local",
    "estimate_model_memory",
    "is_large_model",
    "is_security_model",
    "is_tiny_model",
    "lmstudio_smoke",
    "load_smoke_config_from_env",
    "neutral_flags",
    "openvino_smoke",
    "probe_health",
    "probe_openai_compatible_endpoint",
    "record_capability",
    "record_incompatibility",
    "record_inventory",
    "record_latency",
    "record_smoke_response",
    "reject_authority_payload",
    "reject_credentials",
    "reject_forbidden_claim_text",
    "reject_openvino_gguf_assumption",
    "require_local_endpoint",
    "require_memory_estimate_before_large_load",
]
