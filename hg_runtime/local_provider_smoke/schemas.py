"""Phase 33.5 local-provider-smoke schemas and authority/safety guardrails.

Provider availability is not authority. Provider health is not authority. Loading or
unloading a model is not authority. A model response is not authority. A local
provider smoke is not deployment approval and not a live-action permit; it cannot
widen scope, claim AGI, or authorize tools. Every record in this phase may *probe,
classify, time, or compare a local endpoint* -- never grant authority, authorize a
tool, call an external API, read a credential, or create a live external side effect.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from hg_runtime.memory_ledger.schemas import OperationControl

LOCAL_PROVIDER_SMOKE_CONFIG_SCHEMA = "local_provider_smoke_config_v1"
PROVIDER_HEALTH_PROBE_SCHEMA = "provider_health_probe_v1"
PROVIDER_CAPABILITY_RECORD_SCHEMA = "provider_capability_record_v1"
PROVIDER_INVENTORY_RECORD_SCHEMA = "provider_inventory_record_v1"
OPENAI_COMPATIBLE_ENDPOINT_PROBE_SCHEMA = "openai_compatible_endpoint_probe_v1"
LMSTUDIO_SMOKE_RECORD_SCHEMA = "lmstudio_smoke_record_v1"
OPENVINO_SMOKE_RECORD_SCHEMA = "openvino_smoke_record_v1"
MODEL_SMOKE_PROMPT_SCHEMA = "model_smoke_prompt_v1"
MODEL_SMOKE_RESPONSE_SCHEMA = "model_smoke_response_v1"
MODEL_LATENCY_RECORD_SCHEMA = "model_latency_record_v1"
MODEL_MEMORY_ESTIMATE_SCHEMA = "model_memory_estimate_v1"
PROVIDER_LOAD_PLAN_SCHEMA = "provider_load_plan_v1"
PROVIDER_LOAD_RECEIPT_SCHEMA = "provider_load_receipt_v1"
PROVIDER_UNLOAD_RECEIPT_SCHEMA = "provider_unload_receipt_v1"
PROVIDER_COMPARISON_RECORD_SCHEMA = "provider_comparison_record_v1"
PROVIDER_INCOMPATIBILITY_RECORD_SCHEMA = "provider_incompatibility_record_v1"
LOCAL_PROVIDER_SMOKE_RECEIPT_SCHEMA = "local_provider_smoke_receipt_v1"

SMOKE_CLAIM_BOUNDARY = "local_provider_smoke_advisory_default"

# The single harmless local smoke prompt and its compatibility token.
HARMLESS_SMOKE_PROMPT = "Reply with exactly: LOCAL_PROVIDER_SMOKE_OK"
SMOKE_OK_TOKEN = "LOCAL_PROVIDER_SMOKE_OK"

# Partial verdicts -- a missing OpenVINO server is reported honestly, never hidden.
VERDICT_GREEN_BOTH = "GREEN_LOCAL_PROVIDER_SMOKE_BOTH_PROVIDERS"
VERDICT_GREEN_LMSTUDIO_ONLY = "GREEN_LOCAL_PROVIDER_SMOKE_LMSTUDIO_ONLY_OPENVINO_NOT_CONFIGURED"
VERDICT_YELLOW_PARTIAL = "YELLOW_LOCAL_PROVIDER_SMOKE_PARTIAL"
VERDICT_RED_FAILED = "RED_LOCAL_PROVIDER_SMOKE_FAILED"

LOCAL_PROVIDER_KINDS = {"fake_local", "lmstudio", "openvino"}
EXTERNAL_PROVIDER_KINDS = {"external_network"}

# Tiny models safe for a first smoke (by marker substring).
_TINY_MODEL_MARKERS = ("0.5b", "0.8b", "1b", "qwen2.5-0.5b", "llama-3.2-1b", "qwen3.5-0.8b")
# Large (30B-class) markers -- load-on-demand only, never required for GREEN.
_LARGE_MODEL_MARKERS = ("30b", "30-b", "a3b")
# Security / offensive markers -- never smoke-tested by default.
_SECURITY_MODEL_MARKERS = ("baronllm", "offensive_security", "offensive-security", "cybersecurity")

GREEN_LIKE = {"green", "ok", "pass", "passed", "success", "healthy", "compatible"}

_AUTHORITY_KEYS = {
    "authority_created",
    "permission_granted",
    "tool_authorized",
    "authorizes_tool",
    "authorize_tool",
    "live_side_effects_created",
    "live_external_side_effects_created",
    "creates_live_effect",
    "grants_authority",
    "grant_authority",
    "widens_authority",
    "widen_authority",
    "widens_scope",
    "override_gpp",
    "override_hal",
    "override_ueak",
    "override_oea",
    "smoke_grants_authority",
    "probe_grants_authority",
    "smoke_authorizes_tool",
    "deployment_approved",
    "phase35_field_trial_approved",
    "auto_execute",
}
_AS_PERMISSION_KEYS = {
    "smoke_as_permission",
    "probe_as_permission",
    "health_as_permission",
    "provider_as_permission",
    "response_as_permission",
    "load_as_permission",
}
_TRUTH_KEYS = {
    "model_response_is_truth",
    "response_is_truth",
    "output_is_truth",
    "treat_response_as_truth",
    "model_output_is_authority",
}

_FORBIDDEN_CLAIM_BOUNDARIES = {
    "self_authorizing",
    "authority_grant",
    "permit",
    "deployment_approval",
    "smoke_is_authority",
    "phase35_approval",
}

_FORBIDDEN_CLAIM_PHRASES = (
    ("artificial general intelligence", "agi_claim_rejected"),
    ("deployment ready", "deployment_readiness_claim_rejected"),
    ("deployment readiness", "deployment_readiness_claim_rejected"),
    ("phase 35 approved", "phase35_approval_claim_rejected"),
    ("phase35 approved", "phase35_approval_claim_rejected"),
)
_FORBIDDEN_CLAIM_TOKENS = ((r"\bagi\b", "agi_claim_rejected"),)

_CREDENTIAL_MARKERS = (
    ".env",
    "secret",
    "credential",
    "id_rsa",
    ".pem",
    ".key",
    "password",
    "api_key",
    "apikey",
    ".netrc",
    "token",
    "bearer",
    "authorization:",
)
_NETWORK_PREFIXES = ("http://", "https://", "ftp://", "ws://", "wss://")
# Local hosts are allowed for a local-provider endpoint; everything else is external.
_LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1", "0.0.0.0", "host.docker.internal")


class LocalProviderSmokeError(ValueError):
    """Phase 33.5 validation or operation refusal."""


def require_fields(payload: Mapping[str, Any], fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if field not in payload or payload[field] in (None, "")]
    if missing:
        raise LocalProviderSmokeError(f"schema_violation:missing:{','.join(missing)}")


def as_list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise LocalProviderSmokeError(f"schema_violation:{key}_must_be_list")
    return value


def reject_authority_payload(payload: Mapping[str, Any]) -> None:
    """Refuse any attempt to grant authority, treat a smoke as permission, or claim truth."""
    for key, value in payload.items():
        if value:
            if key in _TRUTH_KEYS:
                raise LocalProviderSmokeError(f"model_response_is_not_truth:{key}")
            if key in _AS_PERMISSION_KEYS:
                raise LocalProviderSmokeError(f"smoke_is_not_permission:{key}")
            if key in _AUTHORITY_KEYS:
                raise LocalProviderSmokeError(f"authority_bypass_attempt:{key}")
        if isinstance(value, Mapping):
            reject_authority_payload(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    reject_authority_payload(item)


def reject_forbidden_claim_boundary(payload: Mapping[str, Any]) -> None:
    if payload.get("claim_boundary") in _FORBIDDEN_CLAIM_BOUNDARIES:
        raise LocalProviderSmokeError("self_authorization_rejected:smoke_is_advisory_only")


def reject_forbidden_claim_text(*texts: Any) -> None:
    for text in texts:
        if not text:
            continue
        low = str(text).lower()
        for phrase, tag in _FORBIDDEN_CLAIM_PHRASES:
            if phrase in low:
                raise LocalProviderSmokeError(tag)
        for pattern, tag in _FORBIDDEN_CLAIM_TOKENS:
            if re.search(pattern, low):
                raise LocalProviderSmokeError(tag)


def locator_is_credential(locator: Any) -> bool:
    low = str(locator).lower()
    return any(marker in low for marker in _CREDENTIAL_MARKERS)


def locator_is_network(locator: Any) -> bool:
    return str(locator).lower().startswith(_NETWORK_PREFIXES)


def endpoint_is_local(endpoint: Any) -> bool:
    """A URL whose host is a loopback/local host is local; anything else is external."""
    low = str(endpoint).lower()
    if not low.startswith(_NETWORK_PREFIXES):
        # bare host:port or empty -> treat as local only if it names a local host
        return any(host in low for host in _LOCAL_HOSTS) if low else False
    rest = low.split("://", 1)[1]
    host = rest.split("/", 1)[0]
    return any(host.startswith(local) for local in _LOCAL_HOSTS)


def reject_credentials(*locators: Any) -> None:
    for locator in locators:
        if locator is None:
            continue
        if locator_is_credential(locator):
            raise LocalProviderSmokeError("credential_read_rejected")


def require_local_endpoint(endpoint: Any, *, allow_external: bool = False) -> None:
    """A provider smoke endpoint must be local; external endpoints refuse by default."""
    reject_credentials(endpoint)
    if not endpoint_is_local(endpoint) and not allow_external:
        raise LocalProviderSmokeError("external_provider_refuses_by_default")


def is_security_model(model_id: Any) -> bool:
    low = str(model_id).lower()
    return any(marker in low for marker in _SECURITY_MODEL_MARKERS)


def is_large_model(model_id: Any) -> bool:
    low = str(model_id).lower()
    return any(marker in low for marker in _LARGE_MODEL_MARKERS)


def is_tiny_model(model_id: Any) -> bool:
    low = str(model_id).lower()
    if is_security_model(low) or is_large_model(low):
        return False
    return any(marker in low for marker in _TINY_MODEL_MARKERS)


def classify_model_size(model_id: Any) -> str:
    if is_large_model(model_id):
        return "large"
    if is_tiny_model(model_id):
        return "tiny"
    return "medium"


def assert_safe_smoke_model(model_id: Any, *, allow_large: bool = False, allow_security: bool = False) -> str:
    """A default smoke uses tiny, non-security models only."""
    if is_security_model(model_id) and not allow_security:
        raise LocalProviderSmokeError("security_model_smoke_refused_by_default")
    if is_large_model(model_id) and not allow_large:
        raise LocalProviderSmokeError("large_model_not_allowed_in_default_smoke")
    if not is_tiny_model(model_id) and not (allow_large or allow_security):
        raise LocalProviderSmokeError("default_smoke_requires_tiny_model")
    return classify_model_size(model_id)


def neutral_flags() -> dict[str, bool]:
    return {
        "authority_created": False,
        "permission_granted": False,
        "tool_authorized": False,
        "widens_authority": False,
        "live_external_side_effects_created": False,
        "smoke_treated_as_authority": False,
        "model_response_treated_as_truth": False,
        "deployment_approved": False,
        "phase35_field_trial_approved": False,
        "is_permission": False,
    }


def preempt_if_needed(control: OperationControl | None, *, stop_blocks: bool = True) -> None:
    reason = (control or OperationControl()).refuse_reason(stop_blocks=stop_blocks)
    if reason:
        raise LocalProviderSmokeError(reason)


__all__ = [
    "EXTERNAL_PROVIDER_KINDS",
    "GREEN_LIKE",
    "HARMLESS_SMOKE_PROMPT",
    "LOCAL_PROVIDER_KINDS",
    "LOCAL_PROVIDER_SMOKE_CONFIG_SCHEMA",
    "LOCAL_PROVIDER_SMOKE_RECEIPT_SCHEMA",
    "LMSTUDIO_SMOKE_RECORD_SCHEMA",
    "MODEL_LATENCY_RECORD_SCHEMA",
    "MODEL_MEMORY_ESTIMATE_SCHEMA",
    "MODEL_SMOKE_PROMPT_SCHEMA",
    "MODEL_SMOKE_RESPONSE_SCHEMA",
    "OPENAI_COMPATIBLE_ENDPOINT_PROBE_SCHEMA",
    "OPENVINO_SMOKE_RECORD_SCHEMA",
    "PROVIDER_CAPABILITY_RECORD_SCHEMA",
    "PROVIDER_COMPARISON_RECORD_SCHEMA",
    "PROVIDER_HEALTH_PROBE_SCHEMA",
    "PROVIDER_INCOMPATIBILITY_RECORD_SCHEMA",
    "PROVIDER_INVENTORY_RECORD_SCHEMA",
    "PROVIDER_LOAD_PLAN_SCHEMA",
    "PROVIDER_LOAD_RECEIPT_SCHEMA",
    "PROVIDER_UNLOAD_RECEIPT_SCHEMA",
    "SMOKE_CLAIM_BOUNDARY",
    "SMOKE_OK_TOKEN",
    "VERDICT_GREEN_BOTH",
    "VERDICT_GREEN_LMSTUDIO_ONLY",
    "VERDICT_RED_FAILED",
    "VERDICT_YELLOW_PARTIAL",
    "LocalProviderSmokeError",
    "as_list",
    "assert_safe_smoke_model",
    "classify_model_size",
    "endpoint_is_local",
    "is_large_model",
    "is_security_model",
    "is_tiny_model",
    "locator_is_credential",
    "locator_is_network",
    "neutral_flags",
    "preempt_if_needed",
    "reject_authority_payload",
    "reject_credentials",
    "reject_forbidden_claim_boundary",
    "reject_forbidden_claim_text",
    "require_fields",
    "require_local_endpoint",
]
