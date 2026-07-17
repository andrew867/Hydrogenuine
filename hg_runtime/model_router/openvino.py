"""OpenVINO provider adapter contract (and the refusing vLLM contract).

OpenVINO is a dry-run contract boundary only: no real hot reload is required for
Phase 33 GREEN, and no real device call is made by default. The future vLLM
contract refuses by default -- it is a schema placeholder, not a usable provider.
"""

from __future__ import annotations

from typing import Any

from hg_runtime.model_router.schemas import ModelRouterError


class OpenVINOProviderContract:
    kind = "openvino"

    def __init__(self, provider_id: str = "openvino-contract", *, dry_run: bool = True) -> None:
        self.provider_id = provider_id
        self.dry_run = dry_run

    def _planned(self, action: str, model_id: str) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "action": action,
            "model_id": model_id,
            "executed": False,
            "dry_run": True,
            "real_call": False,
            "network": False,
            "note": "planned only; real OpenVINO device call disabled by default",
        }

    def plan_load(self, model_id: str) -> dict[str, Any]:
        return self._planned("load", model_id)

    def plan_unload(self, model_id: str) -> dict[str, Any]:
        return self._planned("unload", model_id)

    def hot_reload(self, model_id: str, *, allow_real: bool = False) -> dict[str, Any]:
        if not allow_real:
            return self._planned("hot_reload", model_id)
        raise ModelRouterError("openvino_real_call_requires_operator_smoke_test")


class FutureVLLMProviderContract:
    kind = "vllm"

    def __init__(self, provider_id: str = "vllm-future") -> None:
        self.provider_id = provider_id

    def plan_load(self, model_id: str) -> dict[str, Any]:
        raise ModelRouterError("provider_contract_refuses_by_default:vllm")


__all__ = ["FutureVLLMProviderContract", "OpenVINOProviderContract"]
