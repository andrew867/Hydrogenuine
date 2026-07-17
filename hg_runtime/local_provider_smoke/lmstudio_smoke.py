"""LM Studio local smoke.

Dry-run/fixture-safe by default. The smoke probes health, optionally lists models,
and (only when the operator has enabled real mode) sends one harmless prompt to an
already-loaded tiny model. It never calls an external API, never loads a 30B-class or
security model, and records an unreachable configured server honestly.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.model_router.lmstudio import LMStudioProviderContract
from hg_runtime.local_provider_smoke.capabilities import record_capability, record_inventory
from hg_runtime.local_provider_smoke.model_smoke import build_smoke_prompt, record_smoke_response
from hg_runtime.local_provider_smoke.probes import probe_health, probe_openai_compatible_endpoint
from hg_runtime.local_provider_smoke.schemas import (
    LMSTUDIO_SMOKE_RECORD_SCHEMA,
    LocalProviderSmokeError,
    neutral_flags,
    preempt_if_needed,
)


def lmstudio_smoke(
    config: Mapping[str, Any],
    *,
    reachable: bool | None = None,
    listed_models: list[str] | None = None,
    smoke_response_text: str | None = None,
    control=None,
) -> dict[str, Any]:
    preempt_if_needed(control)
    configured = bool(config.get("lmstudio_configured"))
    enable_real = bool(config.get("enable_real"))
    endpoint = config.get("lmstudio_base_url", "")
    model_id = config.get("lmstudio_tiny_model", "")

    contract = LMStudioProviderContract(dry_run=not enable_real)
    health = probe_health(
        provider_id="lmstudio",
        kind="lmstudio",
        endpoint=endpoint,
        configured=configured,
        reachable=reachable if enable_real else None,
        allow_external=bool(config.get("allow_external")),
        control=control,
    )

    if not configured:
        status = "not_configured"
    elif not enable_real:
        status = "skipped_dry_run"
    elif reachable is False:
        status = "fail"
    elif reachable is True:
        status = "pass"
    else:
        status = "configured_not_contacted"

    capability = None
    inventory = None
    endpoint_probe = None
    response = None
    if configured:
        endpoint_probe = probe_openai_compatible_endpoint(
            provider_id="lmstudio",
            endpoint=endpoint,
            supports_models_list=True,
            supports_chat_completions=True,
            configured=configured,
            allow_external=bool(config.get("allow_external")),
            control=control,
        )
        capability = record_capability(
            {
                "provider_id": "lmstudio",
                "kind": "lmstudio",
                "supports_models_list": True,
                "supports_chat_completions": True,
                "supports_load": True,
                "supports_unload": True,
                "quirks": ["openai_compatible", "lms_cli_load_unload"],
            },
            control=control,
        )
        if listed_models is not None:
            inventory = record_inventory({"provider_id": "lmstudio", "models": listed_models}, control=control)

    if status == "pass":
        if not model_id:
            raise LocalProviderSmokeError("lmstudio_real_smoke_requires_tiny_model_id")
        # Validate the tiny model and the harmless prompt before recording a response.
        build_smoke_prompt(model_id=model_id, control=control)
        text = smoke_response_text if smoke_response_text is not None else ""
        response = record_smoke_response(provider_id="lmstudio", model_id=model_id, response_text=text, control=control)
        if not response["endpoint_compatible"]:
            status = "fail"

    record = {
        "schema": LMSTUDIO_SMOKE_RECORD_SCHEMA,
        "provider_id": "lmstudio",
        "endpoint": endpoint,
        "configured": configured,
        "enable_real": enable_real,
        "real_call_made": bool(enable_real and reachable is not None),
        "dry_run": not enable_real,
        "status": status,
        "health_probe": health,
        "endpoint_probe": endpoint_probe,
        "capability": capability,
        "inventory": inventory,
        "smoke_response": response,
        "planned_load_disabled_by_default": contract.dry_run,
        **neutral_flags(),
    }
    record["smoke_hash"] = canonical_hash(record)
    return record


__all__ = ["lmstudio_smoke"]
