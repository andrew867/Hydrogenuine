"""Evidence gap ledger for overnight research.

No promotion. Model output is not truth.
"""

from __future__ import annotations

import hashlib
import json
import os


def build_evidence_gaps(*, model_outputs: list[dict], claims: dict, question: str) -> list[dict]:
    gaps = []
    claim_list = claims.get("claims", [])

    for claim in claim_list:
        if claim.get("claim_type") in ("speculative", "metaphysical", "formal"):
            gaps.append({
                "gap_id": hashlib.sha256(claim["claim_text"].encode()).hexdigest()[:12],
                "related_claim_id": claim["claim_id"],
                "gap_type": _gap_type(claim),
                "source_needed": "peer-reviewed empirical study or formal proof",
                "priority": "high" if "truth_claim" in claim.get("risk_tags", []) else "medium",
                "no_promotion_reason": "evidence gap unresolved",
            })

    return gaps


def _gap_type(claim: dict) -> str:
    ct = claim.get("claim_type", "")
    if ct == "formal":
        return "formal_proof_missing"
    if ct == "metaphysical":
        return "empirical_bridge_missing"
    if ct == "speculative":
        return "evidence_missing"
    return "general_gap"


def write_evidence_gaps(gaps: list[dict], out_dir: str) -> str:
    path = os.path.join(out_dir, "evidence_gap_ledger.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for gap in gaps:
            f.write(json.dumps(gap) + "\n")
    return path
