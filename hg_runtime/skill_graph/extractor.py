"""Extract advisory skill nodes from Phase 26 experience entries."""

from __future__ import annotations

from typing import Any

from hg_runtime.memory_ledger.ledger import LedgerEntry
from hg_runtime.memory_ledger.schemas import EXPERIENCE_ENTRY_SCHEMA
from hg_runtime.skill_graph.schemas import SkillGraphError, validate_skill_node


def extract_skill_from_experience(entry: LedgerEntry, *, name: str, domain: str) -> dict[str, Any]:
    payload = entry.to_dict()["payload"]
    if entry.schema != EXPERIENCE_ENTRY_SCHEMA:
        raise SkillGraphError("schema_violation:phase26_experience_entry_required")
    if not payload.get("receipt_refs"):
        raise SkillGraphError("receipt_backed_experience_required")
    if str(payload.get("result", "")).lower() != "success" or payload.get("promotion_status") != "promoted":
        raise SkillGraphError("receipt_backed_experience_required")
    return validate_skill_node(
        {
            "name": name,
            "domain": domain,
            "procedure": payload["procedure"],
            "phase26_entry_ref": entry.entry_id,
            "provenance_refs": [entry.chain_hash],
            "evidence_refs": list(payload.get("receipt_refs", [])) + list(payload.get("proof_refs", [])),
            "receipt_refs": list(payload.get("receipt_refs", [])),
            "authority_refs": list(payload.get("authority_refs", [])),
            "claim_boundary": "advisory_only",
            "status": "draft",
        }
    )


__all__ = ["extract_skill_from_experience"]
