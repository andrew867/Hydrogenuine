"""Provider identity resolution."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from hg_runtime.live_provider.schema import (
    LiveProviderKind,
    LiveProviderVerdict,
    ModelIdentity,
    ProviderIdentity,
    ProviderRuntimeMode,
    load_live_provider_policy,
    now_iso,
)

WORKSPACE = Path(__file__).resolve().parents[2]
EXAMPLE_CONFIG = WORKSPACE / "configs/agent_zero/live_provider.example.json"


def _load_example_config() -> dict[str, Any]:
    if not EXAMPLE_CONFIG.is_file():
        return {}
    return json.loads(EXAMPLE_CONFIG.read_text(encoding="utf-8"))


def resolve_provider_kind_from_env() -> LiveProviderKind:
    explicit = os.environ.get("HG_LIVE_PROVIDER_KIND", "").strip().lower()
    if explicit:
        try:
            return LiveProviderKind(explicit)
        except ValueError:
            return LiveProviderKind.DRY_UNAVAILABLE
    if os.environ.get("HG_OPENVINO_ENDPOINT") or os.environ.get("HG_PROVIDER_LOCAL_OPENVINO_CONFIGURED", "").lower() in ("1", "true", "yes"):
        return LiveProviderKind.OPENVINO
    if _openvino_health_ok():
        return LiveProviderKind.OPENVINO
    if os.environ.get("HG_LM_STUDIO_ENDPOINT"):
        return LiveProviderKind.LM_STUDIO
    if os.environ.get("HG_LLAMA_CPP_ENDPOINT"):
        return LiveProviderKind.LLAMA_CPP
    if os.environ.get("HG_VLLM_ENDPOINT"):
        return LiveProviderKind.VLLM
    if os.environ.get("HG_OPENAI_COMPAT_ENDPOINT"):
        return LiveProviderKind.HTTP_OPENAI_COMPATIBLE
    cfg = _load_example_config()
    kind = cfg.get("provider_kind")
    if kind:
        try:
            return LiveProviderKind(kind)
        except ValueError:
            return LiveProviderKind.DRY_UNAVAILABLE
    return LiveProviderKind.OPENVINO if _openvino_health_ok() else LiveProviderKind.DRY_UNAVAILABLE


def _openvino_health_ok() -> bool:
    try:
        from hg_runtime.live_provider.openvino_config import openvino_endpoint_base
        from hg_runtime.live_provider.local_provider_clients import probe_http_endpoint

        result = probe_http_endpoint(openvino_endpoint_base())
        return bool(result.get("available"))
    except Exception:
        return False


def resolve_endpoint_ref(provider_kind: LiveProviderKind) -> str | None:
    env_map = {
        LiveProviderKind.LM_STUDIO: "HG_LM_STUDIO_ENDPOINT",
        LiveProviderKind.LLAMA_CPP: "HG_LLAMA_CPP_ENDPOINT",
        LiveProviderKind.VLLM: "HG_VLLM_ENDPOINT",
        LiveProviderKind.OPENVINO: "HG_OPENVINO_ENDPOINT",
        LiveProviderKind.HTTP_OPENAI_COMPATIBLE: "HG_OPENAI_COMPAT_ENDPOINT",
    }
    key = env_map.get(provider_kind)
    if key and os.environ.get(key):
        return os.environ[key]
    cfg = _load_example_config()
    endpoints = cfg.get("endpoints", {})
    endpoint = endpoints.get(provider_kind.value)
    if provider_kind == LiveProviderKind.OPENVINO and not endpoint:
        from hg_runtime.live_provider.openvino_config import openvino_endpoint_base

        return openvino_endpoint_base()
    return endpoint


def build_provider_identity(
    *,
    provider_kind: LiveProviderKind | None = None,
    runtime_mode: ProviderRuntimeMode = ProviderRuntimeMode.DRY_AUTONOMY,
) -> ProviderIdentity:
    kind = provider_kind or resolve_provider_kind_from_env()
    endpoint = resolve_endpoint_ref(kind)
    provider_id = f"live-provider-{kind.value}"
    if kind == LiveProviderKind.DRY_UNAVAILABLE:
        return ProviderIdentity(
            provider_id=provider_id,
            provider_kind=kind,
            provider_name="Dry Unavailable Provider",
            endpoint_ref=None,
            transport="none",
            runtime_mode=runtime_mode,
            configured_at=now_iso(),
        ).with_hash()

    return ProviderIdentity(
        provider_id=provider_id,
        provider_kind=kind,
        provider_name=kind.value.replace("_", " ").title(),
        endpoint_ref=endpoint,
        transport="http_openai_compatible",
        runtime_mode=runtime_mode,
        configured_at=now_iso(),
    ).with_hash()


def build_model_identity(provider: ProviderIdentity) -> ModelIdentity:
    cfg = _load_example_config()
    model_cfg = cfg.get("model", {})
    model_id = os.environ.get("HG_LIVE_MODEL_ID") or model_cfg.get("model_id") or f"model-{provider.provider_kind.value}"
    return ModelIdentity(
        model_id=model_id,
        model_name=model_cfg.get("model_name") or model_id,
        model_family=model_cfg.get("model_family"),
        quant_id=model_cfg.get("quant_id") or os.environ.get("HG_LIVE_MODEL_QUANT"),
        context_length=model_cfg.get("context_length"),
        backend=model_cfg.get("backend") or provider.provider_kind.value,
        device=model_cfg.get("device") or os.environ.get("HG_LIVE_MODEL_DEVICE"),
        provider_ref=provider.provider_id,
    ).with_hash()


def provider_configured(provider: ProviderIdentity) -> bool:
    if provider.provider_kind == LiveProviderKind.DRY_UNAVAILABLE:
        return False
    if provider.provider_kind == LiveProviderKind.OPENVINO:
        if provider.endpoint_ref:
            from hg_runtime.live_provider.local_provider_clients import probe_http_endpoint

            return bool(probe_http_endpoint(provider.endpoint_ref).get("available"))
        return _openvino_health_ok()
    if provider.endpoint_ref:
        return True
    return False


def unavailable_verdict_for_kind(kind: LiveProviderKind) -> LiveProviderVerdict:
    mapping = {
        LiveProviderKind.LM_STUDIO: LiveProviderVerdict.YELLOW_LM_STUDIO_NOT_RUNNING,
        LiveProviderKind.LLAMA_CPP: LiveProviderVerdict.YELLOW_LLAMA_CPP_NOT_RUNNING,
        LiveProviderKind.OPENVINO: LiveProviderVerdict.YELLOW_OPENVINO_NOT_AVAILABLE,
        LiveProviderKind.VLLM: LiveProviderVerdict.YELLOW_VLLM_NOT_AVAILABLE,
        LiveProviderKind.DRY_UNAVAILABLE: LiveProviderVerdict.YELLOW_LOCAL_MODEL_NOT_CONFIGURED,
        LiveProviderKind.HTTP_OPENAI_COMPATIBLE: LiveProviderVerdict.YELLOW_LOCAL_MODEL_NOT_CONFIGURED,
    }
    return mapping.get(kind, LiveProviderVerdict.YELLOW_PROVIDER_UNAVAILABLE_DRY_AUTONOMY_RESTRICTED)
