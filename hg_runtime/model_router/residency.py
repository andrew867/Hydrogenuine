"""Local model residency: policy, load/unload requests, and a residency manager.

The residency manager keeps at most ``max_loaded_models`` local models warm
(default 3). Loading requires a residency receipt. An active invocation protects a
model from being unloaded. When the budget is exhausted, an idle low-priority model
is evicted by policy, or the load is refused -- never an active model. Idle models
past their TTL are unloaded.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.model_router.schemas import (
    LOADED_MODEL_INSTANCE_SCHEMA,
    MODEL_LOAD_REQUEST_SCHEMA,
    MODEL_RESIDENCY_POLICY_SCHEMA,
    MODEL_RESIDENCY_RECEIPT_SCHEMA,
    MODEL_UNLOAD_REQUEST_SCHEMA,
    ModelRouterError,
    as_list,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    require_fields,
)

DEFAULT_MAX_LOADED_MODELS = 3


def define_residency_policy(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_fields(payload, ("policy_id",))
    data = dict(payload)
    reject_authority_payload(data)
    max_loaded = int(data.get("max_loaded_models", DEFAULT_MAX_LOADED_MODELS))
    if max_loaded < 1:
        raise ModelRouterError("residency_policy_max_loaded_must_be_positive")
    return {
        "schema": MODEL_RESIDENCY_POLICY_SCHEMA,
        "policy_id": data["policy_id"],
        "max_loaded_models": max_loaded,
        "default_roles": as_list(data, "default_roles")
        or ["tiny_summarizer_or_router_helper", "small_coder", "critic_or_writer"],
        "load_on_demand_roles": as_list(data, "load_on_demand_roles") or ["large_coder", "security_reviewer"],
        "gpu_budget_mb": data.get("gpu_budget_mb"),
        "ttl_ticks": int(data.get("ttl_ticks", 100)),
        **neutral_flags(),
    }


def create_load_request(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_fields(payload, ("load_id", "model_ref", "role"))
    data = dict(payload)
    reject_authority_payload(data)
    if not str(data.get("provider_ref", "")):
        raise ModelRouterError("loaded_instance_requires_provider_ref")
    mode = "live" if data.get("live") else "dry"
    if mode == "live" and not as_list(data, "operator_permit_refs"):
        raise ModelRouterError("dry_live_boundary_enforced:real_load_requires_operator_permit")
    return {
        "schema": MODEL_LOAD_REQUEST_SCHEMA,
        "load_id": data["load_id"],
        "model_ref": data["model_ref"],
        "provider_ref": data["provider_ref"],
        "role": str(data["role"]).strip().lower(),
        "priority": str(data.get("priority", "normal")),
        "size_mb": int(data.get("size_mb", 0)),
        "mode": mode,
        "is_permission": False,
        **neutral_flags(),
    }


def create_unload_request(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_fields(payload, ("unload_id", "instance_ref"))
    data = dict(payload)
    reject_authority_payload(data)
    return {
        "schema": MODEL_UNLOAD_REQUEST_SCHEMA,
        "unload_id": data["unload_id"],
        "instance_ref": data["instance_ref"],
        **neutral_flags(),
    }


def _residency_receipt(action: str, instance: Mapping[str, Any]) -> dict[str, Any]:
    receipt = {
        "schema": MODEL_RESIDENCY_RECEIPT_SCHEMA,
        "action": action,
        "instance_id": instance.get("instance_id"),
        "model_ref": instance.get("model_ref"),
        "provider_ref": instance.get("provider_ref"),
        "is_permission": False,
        **neutral_flags(),
    }
    receipt["receipt_hash"] = canonical_hash(receipt)
    return receipt


class ResidencyManager:
    """In-memory residency registry enforcing max-loaded, budget, TTL, and active-invocation rules."""

    def __init__(self, policy: Mapping[str, Any]) -> None:
        self.policy = dict(policy)
        self.max_loaded = int(self.policy.get("max_loaded_models", DEFAULT_MAX_LOADED_MODELS))
        self.gpu_budget_mb = self.policy.get("gpu_budget_mb")
        self.ttl_ticks = int(self.policy.get("ttl_ticks", 100))
        self.loaded: dict[str, dict[str, Any]] = {}

    def _used_mb(self) -> int:
        return sum(int(inst.get("size_mb", 0)) for inst in self.loaded.values())

    def _evictable(self) -> list[str]:
        # Idle, low/normal-priority instances are evictable; active or high-priority are not.
        return [
            iid
            for iid, inst in self.loaded.items()
            if not inst.get("active_invocation") and str(inst.get("priority", "normal")) != "high"
        ]

    def request_load(
        self,
        load_request: Mapping[str, Any],
        *,
        now_tick: int = 0,
        control: OperationControl | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
        """Load a model, evicting an idle low-priority model if needed. Returns (instance, receipt, evictions)."""
        preempt_if_needed(control, stop_blocks=True)
        require_fields(load_request, ("load_id", "model_ref", "provider_ref", "role"))
        evictions: list[dict[str, Any]] = []

        # First evict TTL-expired idle models so the slot/budget frees up.
        evictions.extend(self.evict_idle(now_tick))

        size_mb = int(load_request.get("size_mb", 0))
        budget_exhausted = self.gpu_budget_mb is not None and self._used_mb() + size_mb > int(self.gpu_budget_mb)
        slots_full = len(self.loaded) >= self.max_loaded

        while slots_full or budget_exhausted:
            evictable = self._evictable()
            if not evictable:
                if slots_full:
                    raise ModelRouterError("max_loaded_models_enforced")
                raise ModelRouterError("gpu_budget_exhausted_no_evictable_model")
            victim = evictable[0]
            evictions.append(self._unload_instance(victim, reason="evicted_for_budget_or_slot"))
            slots_full = len(self.loaded) >= self.max_loaded
            budget_exhausted = self.gpu_budget_mb is not None and self._used_mb() + size_mb > int(self.gpu_budget_mb)

        instance = {
            "schema": LOADED_MODEL_INSTANCE_SCHEMA,
            "instance_id": "inst-" + canonical_hash({"load_id": load_request["load_id"], "tick": now_tick}).removeprefix("sha256:")[:16],
            "model_ref": load_request["model_ref"],
            "provider_ref": load_request["provider_ref"],
            "role": load_request["role"],
            "priority": str(load_request.get("priority", "normal")),
            "size_mb": size_mb,
            "loaded_at_tick": now_tick,
            "last_used_tick": now_tick,
            "active_invocation": False,
            **neutral_flags(),
        }
        self.loaded[instance["instance_id"]] = instance
        return instance, _residency_receipt("load", instance), evictions

    def mark_active(self, instance_id: str) -> None:
        self.loaded[instance_id]["active_invocation"] = True

    def mark_idle(self, instance_id: str, *, now_tick: int) -> None:
        inst = self.loaded[instance_id]
        inst["active_invocation"] = False
        inst["last_used_tick"] = now_tick

    def _unload_instance(self, instance_id: str, *, reason: str) -> dict[str, Any]:
        inst = self.loaded.pop(instance_id)
        receipt = _residency_receipt("unload", inst)
        receipt["reason"] = reason
        return receipt

    def request_unload(
        self,
        unload_request: Mapping[str, Any],
        *,
        control: OperationControl | None = None,
    ) -> dict[str, Any]:
        preempt_if_needed(control, stop_blocks=True)
        instance_id = str(unload_request.get("instance_ref"))
        inst = self.loaded.get(instance_id)
        if inst is None:
            raise ModelRouterError("schema_violation:unknown_instance")
        if inst.get("active_invocation"):
            raise ModelRouterError("model_unload_requires_no_active_invocation")
        return self._unload_instance(instance_id, reason="operator_unload")

    def evict_idle(self, now_tick: int) -> list[dict[str, Any]]:
        """Unload idle instances whose TTL has expired."""
        expired = [
            iid
            for iid, inst in self.loaded.items()
            if not inst.get("active_invocation") and (now_tick - int(inst.get("last_used_tick", 0))) >= self.ttl_ticks
        ]
        return [self._unload_instance(iid, reason="ttl_expiry") for iid in expired]


__all__ = [
    "DEFAULT_MAX_LOADED_MODELS",
    "ResidencyManager",
    "create_load_request",
    "create_unload_request",
    "define_residency_policy",
]
