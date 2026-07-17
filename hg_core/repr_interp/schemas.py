# Layer 8: Representation Interpretability - schemas
from __future__ import annotations

from typing import Any, Dict, List, Optional

InspectionRequest = Dict[str, Any]
InspectionResult = Dict[str, Any]
InspectionPromptRegistryEntry = Dict[str, Any]


def inspection_request(
    prompt_id: str,
    model_id: str = "",
    context_ref: Optional[Dict[str, Any]] = None,
    layer_range: Optional[Dict[str, int]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> InspectionRequest:
    out: InspectionRequest = {"prompt_id": prompt_id, "model_id": model_id}
    if context_ref is not None:
        out["context_ref"] = context_ref
    if layer_range is not None:
        out["layer_range"] = layer_range
    if options is not None:
        out["options"] = options
    return out


def inspection_result(
    prompt_id: str,
    request_id: str,
    output_text: str,
    captured_layers: Optional[List[Any]] = None,
    artifact_ref: Optional[str] = None,
    ts: Optional[str] = None,
) -> InspectionResult:
    out: InspectionResult = {
        "prompt_id": prompt_id,
        "request_id": request_id,
        "output_text": output_text,
    }
    if captured_layers is not None:
        out["captured_layers"] = captured_layers
    if artifact_ref is not None:
        out["artifact_ref"] = artifact_ref
    if ts is not None:
        out["ts"] = ts
    return out


def registry_entry(
    id: str,
    name: str,
    description: str,
    prompt_template: str,
    default_options: Optional[Dict[str, Any]] = None,
) -> InspectionPromptRegistryEntry:
    out: InspectionPromptRegistryEntry = {
        "id": id,
        "name": name,
        "description": description,
        "prompt_template": prompt_template,
    }
    if default_options is not None:
        out["default_options"] = default_options
    return out


# --- Layer 8 Phase 5: Backward-patching under governance ---

PatchProposal = Dict[str, Any]
PatchRecord = Dict[str, Any]

PATCH_STATUS_PROPOSED = "proposed"
PATCH_STATUS_APPROVED = "approved"
PATCH_STATUS_APPLIED = "applied"
PATCH_STATUS_REJECTED = "rejected"


def patch_proposal(
    decision_id: str,
    patch_type: str,
    proposed_output: str,
    rationale: str,
    requester_id: str = "",
    options: Optional[Dict[str, Any]] = None,
) -> PatchProposal:
    """Minimal proposal for a backward patch (override/correction) on a decision."""
    out: PatchProposal = {
        "decision_id": decision_id,
        "patch_type": patch_type,
        "proposed_output": proposed_output,
        "rationale": rationale,
        "requester_id": requester_id or "",
    }
    if options is not None:
        out["options"] = options
    return out


def patch_record(
    patch_id: str,
    decision_id: str,
    patch_type: str,
    proposed_output: str,
    rationale: str,
    requester_id: str = "",
    status: str = PATCH_STATUS_PROPOSED,
    ts: Optional[str] = None,
    applied_at: Optional[str] = None,
) -> PatchRecord:
    """Record of a patch proposal and its status (proposed | approved | applied | rejected)."""
    from datetime import datetime, timezone
    _ts = ts or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    out: PatchRecord = {
        "patch_id": patch_id,
        "decision_id": decision_id,
        "patch_type": patch_type,
        "proposed_output": proposed_output,
        "rationale": rationale,
        "requester_id": requester_id or "",
        "status": status,
        "ts": _ts,
    }
    if applied_at is not None:
        out["applied_at"] = applied_at
    return out
