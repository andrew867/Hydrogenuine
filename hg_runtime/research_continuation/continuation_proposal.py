"""Continuation proposal — a structured next-step recommendation."""

from __future__ import annotations

import hashlib
import json

SCHEMA_VERSION = "continuation_proposal_v1"


def create_proposal(*, seed_id: str, decision: str, model_id: str,
                    suggested_model: str = "", suggested_mode: str = "",
                    rationale: str = "", evidence_gaps: list[str] | None = None,
                    operator_action_needed: bool = False) -> dict:
    proposal = {
        "schema": SCHEMA_VERSION,
        "proposal_id": "",
        "seed_id": seed_id,
        "decision": decision,
        "current_model_id": model_id,
        "suggested_model": suggested_model or model_id,
        "suggested_mode": suggested_mode,
        "rationale": rationale,
        "evidence_gaps": evidence_gaps or [],
        "operator_action_needed": operator_action_needed,
        "proposal_grants_authority": False,
        "proposal_promotes_to_truth": False,
    }
    raw = json.dumps(proposal, sort_keys=True)
    proposal["proposal_id"] = hashlib.sha256(raw.encode()).hexdigest()[:24]
    return proposal
