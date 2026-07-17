"""Phase 29 workbench schemas and authority guardrails."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from hg_runtime.memory_ledger.schemas import OperationControl

TOOL_CAPABILITY_SCHEMA = "tool_capability_v1"
TOOL_REGISTRY_ENTRY_SCHEMA = "tool_registry_entry_v1"
WORKBENCH_REQUEST_SCHEMA = "workbench_request_v1"
WORKBENCH_RESULT_SCHEMA = "workbench_result_v1"
TOOL_INVOCATION_RECEIPT_SCHEMA = "tool_invocation_receipt_v1"
ARTIFACT_RECEIPT_SCHEMA = "artifact_receipt_v1"
PATCH_CANDIDATE_RECEIPT_SCHEMA = "patch_candidate_receipt_v1"
WORKSPACE_MUTATION_POLICY_SCHEMA = "workspace_mutation_policy_v1"

READ_ONLY_KINDS = {"read_file", "inspect_log", "compare_outputs"}
MUTATING_KINDS = {"write_artifact", "patch_candidate", "build_artifact", "test_run"}
FORBIDDEN_KINDS = {"shell", "network", "package_install", "credential_read"}
ALLOWED_KINDS = READ_ONLY_KINDS | MUTATING_KINDS | FORBIDDEN_KINDS


class WorkbenchError(ValueError):
    """Phase 29 validation or operation refusal."""


@dataclass(frozen=True)
class WorkbenchExecutionDecision:
    allowed: bool
    reason: str


def _require_fields(payload: Mapping[str, Any], fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if field not in payload]
    if missing:
        raise WorkbenchError(f"schema_violation:missing:{','.join(missing)}")


def _as_list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise WorkbenchError(f"schema_violation:{key}_must_be_list")
    return value


def _reject_authority_payload(payload: Mapping[str, Any]) -> None:
    forbidden = {
        "authority_created",
        "permission_granted",
        "tool_authorized",
        "live_side_effects_created",
        "grants_authority",
        "grant_authority",
        "authorizes_tool",
        "authorize_tool",
        "authorizes_live_action",
        "permits_live_action",
        "widens_scope",
        "override_gpp",
        "override_hal",
        "override_ueak",
        "override_oea",
        "memory_as_permission",
        "skill_as_permission",
        "domain_pack_as_permission",
        "unrestricted_shell",
        "unrestricted_file_write",
    }
    for key, value in payload.items():
        if key in forbidden and value:
            raise WorkbenchError(f"authority_bypass_attempt:{key}")
        if isinstance(value, Mapping):
            _reject_authority_payload(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    _reject_authority_payload(item)


def validate_tool_capability(payload: Mapping[str, Any]) -> dict[str, Any]:
    _require_fields(payload, ("capability_id", "tool_kind", "description", "scope", "authority_refs", "receipt_required"))
    data = dict(payload)
    _reject_authority_payload(data)
    if data.get("schema") not in {None, TOOL_CAPABILITY_SCHEMA}:
        raise WorkbenchError("schema_violation:tool_capability_schema")
    if data["tool_kind"] not in ALLOWED_KINDS:
        raise WorkbenchError("schema_violation:unknown_tool_kind")
    if data["tool_kind"] in FORBIDDEN_KINDS:
        data["disabled_by_default"] = True
    if data.get("default_mode", "dry_run") != "dry_run":
        raise WorkbenchError("schema_violation:workbench_default_must_be_dry_run")
    if not data.get("receipt_required"):
        raise WorkbenchError("receipt_required:tool_capability_schema_required")
    _as_list(data, "authority_refs")
    data.setdefault("schema", TOOL_CAPABILITY_SCHEMA)
    data["authority_created"] = False
    data["permission_granted"] = False
    data["tool_authorized"] = False
    data["live_side_effects_created"] = False
    return data


def validate_tool_registry_entry(payload: Mapping[str, Any]) -> dict[str, Any]:
    _require_fields(payload, ("tool_id", "capability", "registry_hash"))
    data = dict(payload)
    _reject_authority_payload(data)
    capability = validate_tool_capability(data["capability"])
    if data.get("schema") not in {None, TOOL_REGISTRY_ENTRY_SCHEMA}:
        raise WorkbenchError("schema_violation:tool_registry_entry_schema")
    data["capability"] = capability
    data.setdefault("schema", TOOL_REGISTRY_ENTRY_SCHEMA)
    data["authority_created"] = False
    data["permission_granted"] = False
    data["tool_authorized"] = False
    return data


def validate_workbench_request(payload: Mapping[str, Any]) -> dict[str, Any]:
    _require_fields(payload, ("request_id", "tool_id", "operation", "mode", "inputs", "receipt_refs", "claim_boundary"))
    data = dict(payload)
    _reject_authority_payload(data)
    if data.get("schema") not in {None, WORKBENCH_REQUEST_SCHEMA}:
        raise WorkbenchError("schema_violation:workbench_request_schema")
    if data["mode"] not in {"dry_run", "mutating", "live"}:
        raise WorkbenchError("schema_violation:invalid_mode")
    if data["mode"] != "dry_run" and not _as_list(data, "receipt_refs"):
        raise WorkbenchError("receipt_required:mutating_or_live_request")
    if data.get("claim_boundary") != "workbench_governed_dry_run_default":
        raise WorkbenchError("schema_violation:workbench_claim_boundary")
    data.setdefault("schema", WORKBENCH_REQUEST_SCHEMA)
    data["authority_created"] = False
    data["permission_granted"] = False
    data["tool_authorized"] = False
    data["live_side_effects_created"] = False
    return data


def preempt_if_needed(control: OperationControl | None, *, stop_blocks: bool = True) -> None:
    reason = (control or OperationControl()).refuse_reason(stop_blocks=stop_blocks)
    if reason:
        raise WorkbenchError(reason)


__all__ = [
    "ARTIFACT_RECEIPT_SCHEMA",
    "PATCH_CANDIDATE_RECEIPT_SCHEMA",
    "TOOL_CAPABILITY_SCHEMA",
    "TOOL_INVOCATION_RECEIPT_SCHEMA",
    "TOOL_REGISTRY_ENTRY_SCHEMA",
    "WORKBENCH_REQUEST_SCHEMA",
    "WORKBENCH_RESULT_SCHEMA",
    "WORKSPACE_MUTATION_POLICY_SCHEMA",
    "WorkbenchError",
    "WorkbenchExecutionDecision",
    "preempt_if_needed",
    "validate_tool_capability",
    "validate_tool_registry_entry",
    "validate_workbench_request",
]
