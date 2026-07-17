"""Local provider smoke configuration.

Configuration is read-only and dry-run-safe by default. Real local provider calls,
loads, and unloads happen only when the operator explicitly enables them through env
vars or an explicit config payload. Endpoints are configurable; defaults point at
local loopback and are never assumed to be running.
"""

from __future__ import annotations

import os
from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.local_provider_smoke.schemas import (
    LOCAL_PROVIDER_SMOKE_CONFIG_SCHEMA,
    LocalProviderSmokeError,
    locator_is_credential,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    require_local_endpoint,
)

DEFAULT_LMSTUDIO_BASE_URL = "http://localhost:1234/v1"
DEFAULT_OPENVINO_BASE_URL = ""  # not configured by default

ENV_ENABLE_REAL = "HG_LOCAL_PROVIDER_SMOKE_ENABLE_REAL"
ENV_LMSTUDIO_BASE_URL = "HG_LMSTUDIO_BASE_URL"
ENV_LMSTUDIO_TINY_MODEL = "HG_LMSTUDIO_TINY_MODEL"
ENV_OPENVINO_BASE_URL = "HG_OPENVINO_BASE_URL"
ENV_OPENVINO_TINY_MODEL = "HG_OPENVINO_TINY_MODEL"
ENV_ALLOW_LOAD = "HG_LOCAL_PROVIDER_ALLOW_LOAD"
ENV_ALLOW_UNLOAD = "HG_LOCAL_PROVIDER_ALLOW_UNLOAD"


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def build_smoke_config(payload: Mapping[str, Any] | None = None, *, control=None) -> dict[str, Any]:
    """Build a smoke config from an explicit payload (env values may be merged in)."""
    preempt_if_needed(control)
    data = dict(payload or {})
    reject_authority_payload(data)

    lmstudio_base_url = data.get("lmstudio_base_url", DEFAULT_LMSTUDIO_BASE_URL)
    openvino_base_url = data.get("openvino_base_url", DEFAULT_OPENVINO_BASE_URL)

    # Credentials must never be embedded in a configured endpoint.
    if lmstudio_base_url and locator_is_credential(lmstudio_base_url):
        raise LocalProviderSmokeError("credential_read_rejected")
    if openvino_base_url and locator_is_credential(openvino_base_url):
        raise LocalProviderSmokeError("credential_read_rejected")

    enable_real = bool(data.get("enable_real", False))
    allow_external = bool(data.get("allow_external", False))
    # A configured endpoint must be local unless external is explicitly allowed.
    if enable_real and lmstudio_base_url:
        require_local_endpoint(lmstudio_base_url, allow_external=allow_external)
    if enable_real and openvino_base_url:
        require_local_endpoint(openvino_base_url, allow_external=allow_external)

    config = {
        "schema": LOCAL_PROVIDER_SMOKE_CONFIG_SCHEMA,
        "enable_real": enable_real,
        "allow_external": allow_external,
        "lmstudio_base_url": lmstudio_base_url,
        "lmstudio_tiny_model": data.get("lmstudio_tiny_model", ""),
        "lmstudio_configured": bool(lmstudio_base_url),
        "openvino_base_url": openvino_base_url,
        "openvino_tiny_model": data.get("openvino_tiny_model", ""),
        "openvino_configured": bool(openvino_base_url),
        "allow_load": bool(data.get("allow_load", False)),
        "allow_unload": bool(data.get("allow_unload", False)),
        "read_only": not enable_real,
        "claim_boundary": "local_provider_smoke_advisory_default",
        **neutral_flags(),
    }
    config["config_hash"] = canonical_hash(config)
    return config


def load_smoke_config_from_env(env: Mapping[str, str] | None = None, *, control=None) -> dict[str, Any]:
    """Read configuration honestly from the environment. Real mode is opt-in only."""
    source = dict(os.environ if env is None else env)
    payload = {
        "enable_real": _truthy(source.get(ENV_ENABLE_REAL, "")),
        "lmstudio_base_url": source.get(ENV_LMSTUDIO_BASE_URL, DEFAULT_LMSTUDIO_BASE_URL),
        "lmstudio_tiny_model": source.get(ENV_LMSTUDIO_TINY_MODEL, ""),
        # OpenVINO is configured only if the operator set its base url.
        "openvino_base_url": source.get(ENV_OPENVINO_BASE_URL, DEFAULT_OPENVINO_BASE_URL),
        "openvino_tiny_model": source.get(ENV_OPENVINO_TINY_MODEL, ""),
        "allow_load": _truthy(source.get(ENV_ALLOW_LOAD, "")),
        "allow_unload": _truthy(source.get(ENV_ALLOW_UNLOAD, "")),
    }
    return build_smoke_config(payload, control=control)


__all__ = [
    "DEFAULT_LMSTUDIO_BASE_URL",
    "DEFAULT_OPENVINO_BASE_URL",
    "build_smoke_config",
    "load_smoke_config_from_env",
]
