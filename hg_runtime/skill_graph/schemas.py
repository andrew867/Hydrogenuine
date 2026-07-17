"""Phase 27 skill graph and transfer schemas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from hg_runtime.memory_ledger.schemas import OperationControl

SKILL_NODE_SCHEMA = "skill_node_v1"
SKILL_EDGE_SCHEMA = "skill_edge_v1"
SKILL_VERSION_SCHEMA = "skill_version_v1"
TRANSFER_CANDIDATE_SCHEMA = "transfer_candidate_v1"
TRANSFER_EVIDENCE_SCHEMA = "transfer_evidence_v1"
NEGATIVE_TRANSFER_SCHEMA = "negative_transfer_record_v1"


class SkillGraphError(ValueError):
    """Phase 27 validation or operation refusal."""


@dataclass(frozen=True)
class TransferExecutionDecision:
    allowed: bool
    reason: str


def _require_fields(payload: Mapping[str, Any], fields: tuple[str, ...]) -> None:
    missing = [field for field in fields if field not in payload]
    if missing:
        raise SkillGraphError(f"schema_violation:missing:{','.join(missing)}")


def _as_list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise SkillGraphError(f"schema_violation:{key}_must_be_list")
    return value


def _reject_authority_refs(authority_refs: list[Any]) -> None:
    forbidden = {
        "grants_authority",
        "grant_authority",
        "authorizes_tool",
        "authorize_tool",
        "authorizes_live_action",
        "permits_live_action",
        "widens_scope",
        "executes_tool",
    }
    for ref in authority_refs:
        if isinstance(ref, Mapping):
            if any(ref.get(key) for key in forbidden):
                raise SkillGraphError("authority_bypass_attempt:skill_refs_are_reference_only")
        elif not isinstance(ref, str):
            raise SkillGraphError("schema_violation:authority_ref_must_be_string_or_object")


def _require_evidence(payload: Mapping[str, Any]) -> None:
    if not _as_list(payload, "evidence_refs"):
        raise SkillGraphError("evidence_required:transfer_or_skill_requires_evidence")


def _require_receipt(payload: Mapping[str, Any]) -> None:
    if not _as_list(payload, "receipt_refs"):
        raise SkillGraphError("receipt_required:successful_transfer_requires_receipt")


def validate_skill_node(payload: Mapping[str, Any]) -> dict[str, Any]:
    _require_fields(
        payload,
        (
            "name",
            "domain",
            "procedure",
            "phase26_entry_ref",
            "provenance_refs",
            "evidence_refs",
            "receipt_refs",
            "authority_refs",
            "claim_boundary",
            "status",
        ),
    )
    data = dict(payload)
    if not _as_list(data, "provenance_refs"):
        raise SkillGraphError("provenance_required:skill_node_requires_phase26_ledger_provenance")
    _require_evidence(data)
    _require_receipt(data)
    _reject_authority_refs(_as_list(data, "authority_refs"))
    if data.get("claim_boundary") not in {"advisory_only", "evidence_only"}:
        raise SkillGraphError("schema_violation:skill_claim_boundary_must_be_advisory")
    data.setdefault("schema", SKILL_NODE_SCHEMA)
    data["advisory_only"] = True
    data["authority_created"] = False
    data["permission_granted"] = False
    data["tool_authorized"] = False
    data["live_side_effects_created"] = False
    return data


def validate_skill_edge(payload: Mapping[str, Any]) -> dict[str, Any]:
    _require_fields(payload, ("source_id", "target_id", "edge_type", "evidence_refs", "receipt_refs"))
    data = dict(payload)
    _require_evidence(data)
    _require_receipt(data)
    data.setdefault("schema", SKILL_EDGE_SCHEMA)
    data["advisory_only"] = True
    data["authority_created"] = False
    return data


def validate_skill_version(payload: Mapping[str, Any]) -> dict[str, Any]:
    _require_fields(payload, ("skill_id", "parent_refs", "change_summary", "evidence_refs", "receipt_refs"))
    data = dict(payload)
    if not _as_list(data, "parent_refs"):
        raise SkillGraphError("provenance_required:skill_version_requires_parent_refs")
    _require_evidence(data)
    _require_receipt(data)
    data.setdefault("schema", SKILL_VERSION_SCHEMA)
    data["advisory_only"] = True
    data["authority_created"] = False
    return data


def validate_transfer_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    _require_fields(
        payload,
        (
            "source_skill_id",
            "source_domain",
            "target_domain",
            "analogy",
            "evidence_refs",
            "verification_requirements",
            "negative_transfer_refs",
            "status",
            "claim_boundary",
            "authority_refs",
        ),
    )
    data = dict(payload)
    _require_evidence(data)
    if not _as_list(data, "verification_requirements"):
        raise SkillGraphError("evidence_required:verification_requirements_required")
    _reject_authority_refs(_as_list(data, "authority_refs"))
    if data.get("claim_boundary") != "advisory_only":
        raise SkillGraphError("schema_violation:transfer_claim_boundary_must_be_advisory")
    if data.get("status") in {"success", "green", "passed"}:
        raise SkillGraphError("fake_green_rejected:transfer_candidate_is_not_proof")
    data.setdefault("schema", TRANSFER_CANDIDATE_SCHEMA)
    data["advisory_only"] = True
    data["authority_created"] = False
    data["permission_granted"] = False
    data["tool_authorized"] = False
    data["live_side_effects_created"] = False
    return data


def validate_transfer_evidence(payload: Mapping[str, Any]) -> dict[str, Any]:
    _require_fields(payload, ("skill_id", "result", "evidence_refs", "receipt_refs", "claim_boundary"))
    data = dict(payload)
    if str(data.get("result", "")).lower() in {"success", "green", "passed"}:
        try:
            _require_evidence(data)
            _require_receipt(data)
        except SkillGraphError as exc:
            raise SkillGraphError("fake_green_rejected:receipt_required:transfer_success_requires_evidence") from exc
    data.setdefault("schema", TRANSFER_EVIDENCE_SCHEMA)
    data["advisory_only"] = True
    data["authority_created"] = False
    return data


def validate_negative_transfer(payload: Mapping[str, Any]) -> dict[str, Any]:
    _require_fields(payload, ("source_skill_id", "target_domain", "reason", "evidence_refs", "receipt_refs"))
    data = dict(payload)
    _require_evidence(data)
    _require_receipt(data)
    data.setdefault("schema", NEGATIVE_TRANSFER_SCHEMA)
    data["status"] = "rejected"
    data["advisory_only"] = True
    data["authority_created"] = False
    return data


def evaluate_transfer_execution(payload: Mapping[str, Any], control: OperationControl | None = None) -> TransferExecutionDecision:
    state = control or OperationControl()
    reason = state.refuse_reason(stop_blocks=True)
    if reason:
        return TransferExecutionDecision(False, reason)
    return TransferExecutionDecision(False, "SKILL_GRAPH_ADVISORY_ONLY")


__all__ = [
    "NEGATIVE_TRANSFER_SCHEMA",
    "SKILL_EDGE_SCHEMA",
    "SKILL_NODE_SCHEMA",
    "SKILL_VERSION_SCHEMA",
    "TRANSFER_CANDIDATE_SCHEMA",
    "TRANSFER_EVIDENCE_SCHEMA",
    "SkillGraphError",
    "TransferExecutionDecision",
    "evaluate_transfer_execution",
    "validate_negative_transfer",
    "validate_skill_edge",
    "validate_skill_node",
    "validate_skill_version",
    "validate_transfer_candidate",
    "validate_transfer_evidence",
]
