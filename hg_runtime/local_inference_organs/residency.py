"""Residency policy and owned-instance load/unload receipts."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.local_inference_organs.schemas import (
    LocalInferenceOrganError,
    ORGAN_LOAD_RECEIPT_SCHEMA,
    ORGAN_RESIDENCY_REQUEST_SCHEMA,
    ORGAN_UNLOAD_RECEIPT_SCHEMA,
    classify_model,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    require_fields,
)

DEFAULT_MAX_LOADED_MODELS = 3


class OrganResidencyManager:
    def __init__(self, *, max_loaded_models: int = DEFAULT_MAX_LOADED_MODELS) -> None:
        if max_loaded_models < 1:
            raise LocalInferenceOrganError("max_loaded_models_must_be_positive")
        self.max_loaded_models = max_loaded_models
        self.loaded: dict[str, dict[str, Any]] = {}

    def request_load(
        self,
        payload: Mapping[str, Any],
        *,
        operator_permission: bool,
        memory_estimate: Mapping[str, Any] | None = None,
        load_called: bool = False,
        already_resident: bool = False,
        control: OperationControl | None = None,
    ) -> dict[str, Any]:
        preempt_if_needed(control)
        require_fields(payload, ("load_id", "model_id", "role"))
        data = dict(payload)
        reject_authority_payload(data)
        if not operator_permission:
            raise LocalInferenceOrganError("organ_load_requires_operator_permission")
        size_class, requires_memory = classify_model(str(data["model_id"]))
        if requires_memory and not memory_estimate:
            raise LocalInferenceOrganError("organ_load_requires_memory_estimate_for_7b")
        for instance in self.loaded.values():
            if instance["model_id"] == str(data["model_id"]):
                role = str(data["role"])
                if role not in instance["roles"]:
                    instance["roles"].append(role)
                receipt = {
                    "schema": ORGAN_LOAD_RECEIPT_SCHEMA,
                    "request_schema": ORGAN_RESIDENCY_REQUEST_SCHEMA,
                    "action": "shared_model_role_binding",
                    "instance_id": instance["instance_id"],
                    "model_id": str(data["model_id"]),
                    "role": role,
                    "roles_bound_to_instance": list(instance["roles"]),
                    "model_size_class": size_class,
                    "load_endpoint_called": False,
                    "shared_model_role_binding": True,
                    "operator_permission_ref": data.get("operator_permission_ref", "phase33.6_prompt"),
                    "memory_estimate_ref": (memory_estimate or {}).get("estimate_hash", ""),
                    "is_permission": False,
                    **neutral_flags(),
                }
                receipt["receipt_hash"] = canonical_hash(receipt)
                return receipt
        if len(self.loaded) >= self.max_loaded_models and str(data["model_id"]) not in {
            item["model_id"] for item in self.loaded.values()
        }:
            raise LocalInferenceOrganError("organ_max_loaded_models_enforced")
        instance_id = "organ-inst-" + canonical_hash({"load_id": data["load_id"], "model": data["model_id"]}).removeprefix("sha256:")[:16]
        instance = {
            "instance_id": instance_id,
            "model_id": str(data["model_id"]),
            "role": str(data["role"]),
            "roles": [str(data["role"])],
            "size_class": size_class,
            "active_invocation": False,
            "owned_by_this_pass": bool(load_called),
            "already_resident": bool(already_resident),
        }
        self.loaded[instance_id] = instance
        receipt = {
            "schema": ORGAN_LOAD_RECEIPT_SCHEMA,
            "request_schema": ORGAN_RESIDENCY_REQUEST_SCHEMA,
            "action": "already_resident" if already_resident else "load",
            "instance_id": instance_id,
            "model_id": str(data["model_id"]),
            "role": str(data["role"]),
            "roles_bound_to_instance": list(instance["roles"]),
            "model_size_class": size_class,
            "load_endpoint_called": bool(load_called),
            "shared_model_role_binding": False,
            "operator_permission_ref": data.get("operator_permission_ref", "phase33.6_prompt"),
            "memory_estimate_ref": (memory_estimate or {}).get("estimate_hash", ""),
            "is_permission": False,
            **neutral_flags(),
        }
        receipt["receipt_hash"] = canonical_hash(receipt)
        return receipt

    def mark_active(self, instance_id: str) -> None:
        self.loaded[instance_id]["active_invocation"] = True

    def mark_idle(self, instance_id: str) -> None:
        self.loaded[instance_id]["active_invocation"] = False

    def request_unload(
        self,
        instance_id: str,
        *,
        unload_called: bool,
        control: OperationControl | None = None,
    ) -> dict[str, Any]:
        preempt_if_needed(control)
        inst = self.loaded.get(instance_id)
        if not inst:
            raise LocalInferenceOrganError("organ_unload_requires_owned_instance")
        if inst.get("active_invocation"):
            raise LocalInferenceOrganError("organ_unload_rejects_active_invocation")
        self.loaded.pop(instance_id)
        receipt = {
            "schema": ORGAN_UNLOAD_RECEIPT_SCHEMA,
            "instance_id": instance_id,
            "model_id": inst["model_id"],
            "role": inst["role"],
            "unload_endpoint_called": bool(unload_called),
            "owned_by_this_pass": bool(inst.get("owned_by_this_pass")),
            "is_permission": False,
            **neutral_flags(),
        }
        receipt["receipt_hash"] = canonical_hash(receipt)
        return receipt


__all__ = ["DEFAULT_MAX_LOADED_MODELS", "OrganResidencyManager"]
