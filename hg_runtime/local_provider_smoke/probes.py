"""Provider health probes and read-only startup autodetect.

A health probe and a startup autodetect are read-only by default: they record what a
local endpoint *would* report, never load or unload a model, and never call an
external API. A probe over a configured-but-down provider records the failure
honestly and never silently falls back to another provider.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.local_provider_smoke.schemas import (
    OPENAI_COMPATIBLE_ENDPOINT_PROBE_SCHEMA,
    PROVIDER_HEALTH_PROBE_SCHEMA,
    LocalProviderSmokeError,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    require_local_endpoint,
)


def probe_health(
    *,
    provider_id: str,
    kind: str,
    endpoint: str,
    configured: bool,
    reachable: bool | None = None,
    allow_external: bool = False,
    control=None,
) -> dict[str, Any]:
    """Record a read-only health probe. ``reachable`` is None in dry mode (not contacted)."""
    preempt_if_needed(control)
    if configured and endpoint:
        require_local_endpoint(endpoint, allow_external=allow_external)
    status = "not_configured"
    if configured:
        if reachable is True:
            status = "healthy"
        elif reachable is False:
            status = "unreachable"
        else:
            status = "configured_not_contacted"
    probe = {
        "schema": PROVIDER_HEALTH_PROBE_SCHEMA,
        "provider_id": provider_id,
        "kind": kind,
        "endpoint": endpoint,
        "configured": bool(configured),
        "reachable": reachable,
        "status": status,
        "read_only": True,
        "loaded_model": False,
        "unloaded_model": False,
        "network_call_made": bool(reachable is not None),
        "claim_boundary": "local_provider_smoke_advisory_default",
        **neutral_flags(),
    }
    probe["probe_hash"] = canonical_hash(probe)
    return probe


def autodetect_providers(config: Mapping[str, Any], *, control=None) -> dict[str, Any]:
    """Read-only autodetect: classify configured providers without loading anything."""
    preempt_if_needed(control)
    reject_authority_payload(dict(config))
    detected = []
    if config.get("lmstudio_configured"):
        detected.append({"provider_id": "lmstudio", "kind": "lmstudio", "endpoint": config.get("lmstudio_base_url", "")})
    if config.get("openvino_configured"):
        detected.append({"provider_id": "openvino", "kind": "openvino", "endpoint": config.get("openvino_base_url", "")})
    result = {
        "schema": "provider_autodetect_v1",
        "detected": detected,
        "read_only": True,
        "loaded_model": False,
        "unloaded_model": False,
        "network_call_made": False,
        **neutral_flags(),
    }
    result["autodetect_hash"] = canonical_hash(result)
    return result


def probe_openai_compatible_endpoint(
    *,
    provider_id: str,
    endpoint: str,
    supports_models_list: bool,
    supports_chat_completions: bool,
    configured: bool = True,
    allow_external: bool = False,
    control=None,
) -> dict[str, Any]:
    """Record OpenAI-compatible endpoint capabilities (read-only)."""
    preempt_if_needed(control)
    if configured and endpoint:
        require_local_endpoint(endpoint, allow_external=allow_external)
    probe = {
        "schema": OPENAI_COMPATIBLE_ENDPOINT_PROBE_SCHEMA,
        "provider_id": provider_id,
        "endpoint": endpoint,
        "configured": bool(configured),
        "supports_models_list": bool(supports_models_list),
        "supports_chat_completions": bool(supports_chat_completions),
        "read_only": True,
        **neutral_flags(),
    }
    probe["probe_hash"] = canonical_hash(probe)
    return probe


def assert_no_silent_fallback(failed_provider_id: str, fallback_provider_id: str | None) -> None:
    """A provider failure must not silently fall back to a different provider."""
    if fallback_provider_id and fallback_provider_id != failed_provider_id:
        raise LocalProviderSmokeError("provider_failure_silent_fallback_refused")


__all__ = [
    "assert_no_silent_fallback",
    "autodetect_providers",
    "probe_health",
    "probe_openai_compatible_endpoint",
]
