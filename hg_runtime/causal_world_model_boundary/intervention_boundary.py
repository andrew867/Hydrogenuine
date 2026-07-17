"""Intervention proposals — proposed, never executed.

An intervention proposal is not an action. Every proposal is
PROPOSED_NOT_AUTHORIZED and authorizes no action, tool, or live effect. Any
attempt to authorize an intervention is rejected.
"""

from __future__ import annotations

from hg_runtime.causal_world_model_boundary.schemas import (
    INTERVENTION_PROPOSAL_SCHEMA,
    CausalBoundaryError,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def build_intervention_proposal(*, hypothesis: dict, status: str = "PROPOSED_NOT_AUTHORIZED") -> dict:
    text = f"[intervention proposal for {hypothesis['hypothesis_id']} — NOT authorized]"
    record = {
        "schema": INTERVENTION_PROPOSAL_SCHEMA,
        "intervention_id": f"intv-{hypothesis['hypothesis_id']}",
        "hypothesis_id": hypothesis["hypothesis_id"],
        "intervention_text_hash": canonical_hash({"text": text}),
        "intervention_text_redacted": text,
        "intervention_status": status,
        "intervention_authorized": False,
        "action_authorized": False,
        "tools_authorized": False,
        "live_effects_created": False,
        **neutral_flags(),
    }
    record["record_hash"] = canonical_hash(record)
    return record


def validate_intervention_proposal(record: dict) -> None:
    """Refuse any intervention that claims authorization to act."""
    if record.get("intervention_authorized"):
        raise CausalBoundaryError("intervention_authorized")
    if record.get("action_authorized"):
        raise CausalBoundaryError("action_authorized")
    if record.get("tools_authorized") or record.get("tool_authorized"):
        raise CausalBoundaryError("tools_authorized")
    if record.get("live_effects_created") or record.get("live_external_side_effects_created"):
        raise CausalBoundaryError("live_effect_created")
    if record.get("intervention_status") not in ("PROPOSED_NOT_AUTHORIZED", "REJECTED_REQUIRES_OPERATOR_AUTHORITY"):
        raise CausalBoundaryError("intervention_status_invalid")
