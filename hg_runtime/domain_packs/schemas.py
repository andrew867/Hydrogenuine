"""Phase 28 domain pack schemas and guardrails."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from hg_runtime.memory_ledger.schemas import OperationControl

DOMAIN_PACK_SCHEMA = "domain_pack_v1"
DOMAIN_TASK_TEMPLATE_SCHEMA = "domain_task_template_v1"
DOMAIN_QUALITY_CRITERIA_SCHEMA = "domain_quality_criteria_v1"
DOMAIN_TOOL_REF_SCHEMA = "domain_tool_ref_v1"
DOMAIN_FORBIDDEN_CLAIM_SCHEMA = "domain_forbidden_claim_v1"
DOMAIN_PROOF_EXPECTATION_SCHEMA = "domain_proof_expectation_v1"
DOMAIN_PACK_ACTIVATION_RECEIPT_SCHEMA = "domain_pack_activation_receipt_v1"


class DomainPackError(ValueError):
    """Phase 28 validation or operation refusal."""


@dataclass(frozen=True)
class DomainPackExecutionDecision:
    allowed: bool
    reason: str


def _require_fields(payload: Mapping[str, Any], fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if field not in payload]
    if missing:
        raise DomainPackError(f"schema_violation:missing:{','.join(missing)}")


def _as_list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise DomainPackError(f"schema_violation:{key}_must_be_list")
    return value


def _reject_authority_payload(payload: Mapping[str, Any]) -> None:
    forbidden_keys = {
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
        "treat_skill_as_permission",
        "treat_memory_as_permission",
        "executes_tool",
        "entrypoint",
        "module",
        "python",
        "code",
    }
    for key, value in payload.items():
        if key in forbidden_keys and value:
            raise DomainPackError(f"authority_bypass_attempt:{key}")
        if isinstance(value, Mapping):
            _reject_authority_payload(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    _reject_authority_payload(item)


def _validate_tool_refs(data: Mapping[str, Any], known_tool_refs: set[str] | None) -> None:
    for ref in _as_list(data, "allowed_tool_refs"):
        if not isinstance(ref, Mapping):
            raise DomainPackError("schema_violation:tool_ref_must_be_object")
        _require_fields(ref, ("tool_ref", "purpose"))
        if ref.get("schema") not in {None, DOMAIN_TOOL_REF_SCHEMA}:
            raise DomainPackError("schema_violation:tool_ref_schema")
        if ref.get("authorize") or ref.get("permission_granted"):
            raise DomainPackError("authority_bypass_attempt:domain_pack_cannot_authorize_tools")
        tool_ref = str(ref["tool_ref"])
        if known_tool_refs is None or tool_ref not in known_tool_refs:
            raise DomainPackError("unknown_tool_ref:pack_tool_reference_requires_registry_match")


def _validate_known_refs(data: Mapping[str, Any], key: str, known_refs: set[str] | None) -> None:
    refs = _as_list(data, key)
    if known_refs is None:
        if refs:
            raise DomainPackError(f"unknown_{key}:registry_required")
        return
    unknown = [str(ref) for ref in refs if str(ref) not in known_refs]
    if unknown:
        raise DomainPackError(f"unknown_{key}:{unknown[0]}")


def validate_domain_pack(
    payload: Mapping[str, Any],
    *,
    expected_hash: str | None = None,
    known_tool_refs: set[str] | None = None,
    known_skill_refs: set[str] | None = None,
    known_memory_refs: set[str] | None = None,
) -> dict[str, Any]:
    _require_fields(
        payload,
        (
            "domain_id",
            "version",
            "task_templates",
            "quality_criteria",
            "allowed_tool_refs",
            "forbidden_claims",
            "proof_expectations",
            "schema_refs",
            "fixture_refs",
            "skill_refs",
            "memory_refs",
            "evaluation_refs",
            "claim_boundary",
            "authority_refs",
            "pack_hash",
            "signature_ref",
        ),
    )
    data = dict(payload)
    _reject_authority_payload(data)
    if data.get("schema") not in {None, DOMAIN_PACK_SCHEMA}:
        raise DomainPackError("schema_violation:domain_pack_schema")
    if not str(data.get("domain_id", "")).strip():
        raise DomainPackError("schema_violation:domain_id_required")
    if not str(data.get("version", "")).strip():
        raise DomainPackError("schema_violation:version_required")
    if data.get("claim_boundary") != "declarative_advisory_only":
        raise DomainPackError("schema_violation:domain_pack_claim_boundary_must_be_declarative")
    if not _as_list(data, "task_templates"):
        raise DomainPackError("schema_violation:task_templates_required")
    if not _as_list(data, "quality_criteria"):
        raise DomainPackError("quality_criteria_required")
    if not _as_list(data, "proof_expectations"):
        raise DomainPackError("proof_expectations_required")
    if not _as_list(data, "forbidden_claims"):
        raise DomainPackError("schema_violation:forbidden_claims_required")
    if not str(data.get("signature_ref", "")).strip():
        raise DomainPackError("unsigned_pack_rejected")
    if expected_hash and data.get("pack_hash") != expected_hash:
        raise DomainPackError("pack_hash_mismatch")
    _validate_tool_refs(data, known_tool_refs)
    _validate_known_refs(data, "skill_refs", known_skill_refs)
    _validate_known_refs(data, "memory_refs", known_memory_refs)
    data.setdefault("schema", DOMAIN_PACK_SCHEMA)
    data["declarative_only"] = True
    data["authority_created"] = False
    data["permission_granted"] = False
    data["tool_authorized"] = False
    data["live_side_effects_created"] = False
    return data


def validate_activation_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    _require_fields(payload, ("domain_id", "version", "pack_hash", "phase26_verdict", "phase27_verdict", "receipt_refs", "claim_boundary"))
    data = dict(payload)
    if not _as_list(data, "receipt_refs"):
        raise DomainPackError("receipt_required:domain_pack_activation_requires_receipts")
    if data.get("claim_boundary") != "activation_is_advisory_only":
        raise DomainPackError("schema_violation:activation_claim_boundary")
    data.setdefault("schema", DOMAIN_PACK_ACTIVATION_RECEIPT_SCHEMA)
    data["authority_created"] = False
    data["permission_granted"] = False
    data["tool_authorized"] = False
    data["live_side_effects_created"] = False
    return data


def evaluate_pack_execution(payload: Mapping[str, Any], control: OperationControl | None = None) -> DomainPackExecutionDecision:
    state = control or OperationControl()
    reason = state.refuse_reason(stop_blocks=True)
    if reason:
        return DomainPackExecutionDecision(False, reason)
    return DomainPackExecutionDecision(False, "DOMAIN_PACK_DECLARATIVE_ONLY")


__all__ = [
    "DOMAIN_FORBIDDEN_CLAIM_SCHEMA",
    "DOMAIN_PACK_ACTIVATION_RECEIPT_SCHEMA",
    "DOMAIN_PACK_SCHEMA",
    "DOMAIN_PROOF_EXPECTATION_SCHEMA",
    "DOMAIN_QUALITY_CRITERIA_SCHEMA",
    "DOMAIN_TASK_TEMPLATE_SCHEMA",
    "DOMAIN_TOOL_REF_SCHEMA",
    "DomainPackError",
    "DomainPackExecutionDecision",
    "evaluate_pack_execution",
    "validate_activation_receipt",
    "validate_domain_pack",
]
