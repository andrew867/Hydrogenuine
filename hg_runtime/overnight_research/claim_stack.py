"""Claim stack extractor from model outputs.

Parses model summaries to extract structured claims.
No promotion. Operator review required. Model output is not truth.
"""

from __future__ import annotations

import hashlib
import json
import os
import re


def extract_claims(*, model_outputs: list[dict], question: str, risk_mode: str = "normal") -> dict:
    claims = []
    for mo in model_outputs:
        text = mo.get("text", "")
        source_ref = mo.get("source_candidate_id", "")
        model_ref = mo.get("prompt_id", "")

        for line in text.split("\n"):
            line = line.strip()
            if not line or len(line) < 20:
                continue
            if line.startswith("#") or line.startswith("---"):
                continue

            claim_type = _classify_claim_line(line)
            if claim_type:
                claims.append({
                    "claim_id": hashlib.sha256(line.encode()).hexdigest()[:12],
                    "source_ref": source_ref,
                    "model_ref": model_ref,
                    "claim_text": line[:500],
                    "claim_type": claim_type,
                    "risk_tags": _risk_tags(line, risk_mode),
                    "promotion_allowed": False,
                    "operator_review_required": True,
                })

    return {
        "schema_version": "claim_stack_v1",
        "question": question,
        "risk_mode": risk_mode,
        "claims": claims,
        "total_claims": len(claims),
        "promotion_allowed": False,
        "model_output_is_truth": False,
    }


def _classify_claim_line(line: str) -> str:
    lower = line.lower()
    if any(w in lower for w in ["the source states", "explicitly", "directly claim"]):
        return "direct"
    if any(w in lower for w in ["infer", "suggest", "imply", "appears to"]):
        return "inferred"
    if any(w in lower for w in ["speculative", "speculat", "hypothe"]):
        return "speculative"
    if any(w in lower for w in ["theorem", "proof", "axiom", "formal", "equation"]):
        return "formal"
    if any(w in lower for w in ["metaphysical", "ontolog", "consciousness", "reality"]):
        return "metaphysical"
    if any(w in lower for w in ["empirical", "experiment", "measur", "observ"]):
        return "empirical"
    if len(line) > 40 and not line.startswith("*"):
        return "unclassified"
    return ""


def _risk_tags(line: str, risk_mode: str) -> list[str]:
    tags = []
    lower = line.lower()
    if any(w in lower for w in ["consciousness", "sentien", "aware"]):
        tags.append("consciousness_claim")
    if any(w in lower for w in ["proves", "proven", "establishes truth"]):
        tags.append("truth_claim")
    if any(w in lower for w in ["physics", "quantum"]):
        tags.append("physics_claim")
    if risk_mode == "high_risk_speculative":
        tags.append("high_risk_speculative")
    return tags


def write_claim_stack(claims_data: dict, out_dir: str) -> str:
    path = os.path.join(out_dir, "claim_stack.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(claims_data, f, indent=2)
    return path
