"""Extract candidate claims from WMBR-01A matrix cells.

A candidate claim is a *description* of something a model included. It is always
UNVERIFIED and NOT_PROMOTED. Extraction never marks a claim true or false and
never promotes a model output into a belief.
"""

from __future__ import annotations

from hg_runtime.belief_verification_queue.schemas import (
    BELIEF_STATUS_NOT_PROMOTED,
    CANDIDATE_CLAIM_RECORD_SCHEMA,
    TRUTH_STATUS_UNVERIFIED,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def _claim_kind(claim_tag: str, prompt_id: str, moral_tags: list[str]) -> str:
    tag = claim_tag.lower()
    prompt = prompt_id.lower()
    if moral_tags or "moral" in tag or "moral" in prompt:
        return "MORAL"
    if "historical" in tag or "historical" in prompt:
        return "HISTORICAL"
    if "policy" in tag or "policy" in prompt:
        return "POLICY"
    if "repair" in tag or "technical" in prompt or "fixture" in tag:
        return "TECHNICAL"
    if "standard" in tag or "fact" in tag or "summary" in tag:
        return "FACTUAL"
    return "UNCERTAIN"


def extract_candidate_claims(bundle: dict) -> list[dict]:
    pm = bundle["perspective_matrix"]
    # Map claim_tag -> set of participants that included it (for consensus detection).
    tag_holders: dict[str, set[str]] = {}
    for cell in pm["cells"]:
        for tag in cell.get("included_claim_tags", []):
            tag_holders.setdefault((cell["prompt_id"], tag), set()).add(cell["participant_id"])

    # claim_tags involved in any divergence record => MODEL_DIVERGENCE.
    diverging_tags: set[tuple[str, str]] = set()
    for record in bundle["divergence_matrix"].get("records", []):
        if record.get("divergence_type") == "factual_claim_divergence":
            prompt_id = record.get("prompt_id")
            for participant_claims in record.get("observations", {}).values():
                for tag in participant_claims or []:
                    diverging_tags.add((prompt_id, tag))

    claims: list[dict] = []
    for cell in sorted(pm["cells"], key=lambda c: (c["prompt_id"], c["participant_id"])):
        moral_tags = cell.get("moral_principle_tags", [])
        for tag in sorted(cell.get("included_claim_tags", [])):
            key = (cell["prompt_id"], tag)
            holders = tag_holders.get(key, set())
            if key in diverging_tags:
                confidence_source = "MODEL_DIVERGENCE"
            elif len(holders) >= 2 and not cell.get("sourced", False):
                confidence_source = "MODEL_CONSENSUS"
            else:
                confidence_source = "MODEL_ASSERTION"
            claim = {
                "schema": CANDIDATE_CLAIM_RECORD_SCHEMA,
                "claim_id": f"claim-{cell['receipt_id']}-{tag.replace(':', '_')}",
                "source_receipt_id": cell["receipt_id"],
                "source_prompt_id": cell["prompt_id"],
                "participant_id": cell["participant_id"],
                "claim_tag": tag,
                "claim_hash": canonical_hash({"receipt_id": cell["receipt_id"], "claim_tag": tag}),
                "claim_text_redacted": f"[claim:{tag} included by {cell['participant_id']} on {cell['prompt_id']}]",
                "claim_kind": _claim_kind(tag, cell["prompt_id"], moral_tags),
                "confidence_source": confidence_source,
                "truth_status": TRUTH_STATUS_UNVERIFIED,
                "belief_status": BELIEF_STATUS_NOT_PROMOTED,
                "evidence_required": True,
                **neutral_flags(),
            }
            claim["record_hash"] = canonical_hash(claim)
            claims.append(claim)
    return claims
