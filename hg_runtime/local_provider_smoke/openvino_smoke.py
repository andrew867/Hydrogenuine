"""OpenVINO local smoke.

OpenVINO is treated as a configured OpenAI-style chat endpoint, not an automatic GGUF
loader. When OpenVINO is not configured, that state is recorded honestly (never hidden
or treated as a pass). A GGUF model is never assumed directly loadable by OpenVINO.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.model_router.openvino import OpenVINOProviderContract
from hg_runtime.local_provider_smoke.capabilities import (
    record_capability,
    record_incompatibility,
    record_inventory,
    reject_openvino_gguf_assumption,
)
from hg_runtime.local_provider_smoke.model_smoke import build_smoke_prompt, record_smoke_response
from hg_runtime.local_provider_smoke.probes import probe_health, probe_openai_compatible_endpoint
from hg_runtime.local_provider_smoke.schemas import (
    OPENVINO_SMOKE_RECORD_SCHEMA,
    LocalProviderSmokeError,
    is_security_model,
    neutral_flags,
    preempt_if_needed,
)


def openvino_smoke(
    config: Mapping[str, Any],
    *,
    reachable: bool | None = None,
    listed_models: list[str] | None = None,
    smoke_response_text: str | None = None,
    control=None,
) -> dict[str, Any]:
    preempt_if_needed(control)
    configured = bool(config.get("openvino_configured"))
    enable_real = bool(config.get("enable_real"))
    endpoint = config.get("openvino_base_url", "")
    model_id = config.get("openvino_tiny_model", "")

    contract = OpenVINOProviderContract(dry_run=not enable_real)
    health = probe_health(
        provider_id="openvino",
        kind="openvino",
        endpoint=endpoint,
        configured=configured,
        reachable=reachable if (enable_real and configured) else None,
        allow_external=bool(config.get("allow_external")),
        control=control,
    )

    incompatibility = None
    if not configured:
        status = "not_configured"
        # Honest record that the OpenVINO server/config is absent.
        incompatibility = record_incompatibility(
            {
                "provider_id": "openvino",
                "reason": "openvino_not_configured",
                "detail": "OpenVINO base URL not set; server/configuration absent",
            },
            control=control,
        )
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
            provider_id="openvino",
            endpoint=endpoint,
            supports_models_list=bool(config.get("openvino_supports_models_list", False)),
            supports_chat_completions=True,
            configured=configured,
            allow_external=bool(config.get("allow_external")),
            control=control,
        )
        capability = record_capability(
            {
                "provider_id": "openvino",
                "kind": "openvino",
                "supports_models_list": bool(config.get("openvino_supports_models_list", False)),
                "supports_chat_completions": True,
                "supports_load": False,
                "supports_unload": False,
                "quirks": ["v3_chat_completions", "not_a_gguf_loader"],
            },
            control=control,
        )
        if listed_models is not None:
            inventory = record_inventory({"provider_id": "openvino", "models": listed_models}, control=control)
        # If a GGUF model was named for OpenVINO, record the incompatibility honestly.
        if model_id and "gguf" in str(model_id).lower():
            incompatibility = reject_openvino_gguf_assumption(provider_kind="openvino", model_id=model_id, control=control)

    if status == "pass":
        if not model_id:
            raise LocalProviderSmokeError("openvino_real_smoke_requires_tiny_model_id")
        if is_security_model(model_id):
            raise LocalProviderSmokeError("security_model_smoke_refused_by_default")
        build_smoke_prompt(model_id=model_id, control=control)
        text = smoke_response_text if smoke_response_text is not None else ""
        response = record_smoke_response(provider_id="openvino", model_id=model_id, response_text=text, control=control)
        if not response["endpoint_compatible"]:
            status = "fail"

    record = {
        "schema": OPENVINO_SMOKE_RECORD_SCHEMA,
        "provider_id": "openvino",
        "endpoint": endpoint,
        "configured": configured,
        "enable_real": enable_real,
        "real_call_made": bool(enable_real and configured and reachable is not None),
        "dry_run": not enable_real,
        "status": status,
        "health_probe": health,
        "endpoint_probe": endpoint_probe,
        "capability": capability,
        "inventory": inventory,
        "incompatibility": incompatibility,
        "smoke_response": response,
        "gguf_loader_assumed": False,
        "planned_load_disabled_by_default": contract.dry_run,
        **neutral_flags(),
    }
    record["smoke_hash"] = canonical_hash(record)
    return record


__all__ = ["openvino_smoke"]
