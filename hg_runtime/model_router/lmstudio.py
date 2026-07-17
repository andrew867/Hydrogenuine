"""LM Studio provider adapter contract.

Dry-run by default. This adapter NEVER calls the real LM Studio server, never runs
`lms load`/`lms unload`, and never makes a REST load/unload call unless a later,
explicit operator-enabled local-provider smoke test passes ``allow_real=True``.
By default every method emits a planned (non-executed) record only.
"""

from __future__ import annotations

from typing import Any

from hg_runtime.model_router.schemas import ModelRouterError


class LMStudioProviderContract:
    kind = "lmstudio"

    def __init__(self, provider_id: str = "lmstudio-contract", *, dry_run: bool = True) -> None:
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
            "note": "planned only; real lms call disabled by default",
        }

    def plan_load(self, model_id: str) -> dict[str, Any]:
        return self._planned("load", model_id)

    def plan_unload(self, model_id: str) -> dict[str, Any]:
        return self._planned("unload", model_id)

    def load(self, model_id: str, *, allow_real: bool = False) -> dict[str, Any]:
        if not allow_real:
            return self._planned("load", model_id)
        raise ModelRouterError("lmstudio_real_call_requires_operator_smoke_test")

    def unload(self, model_id: str, *, allow_real: bool = False) -> dict[str, Any]:
        if not allow_real:
            return self._planned("unload", model_id)
        raise ModelRouterError("lmstudio_real_call_requires_operator_smoke_test")


__all__ = ["LMStudioProviderContract"]
