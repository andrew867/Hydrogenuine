"""Unsupported leap audit extractor.

No promotion. Model output is not truth.
"""

from __future__ import annotations

import hashlib
import json
import os


def extract_leaps(*, model_outputs: list[dict], question: str, risk_mode: str = "normal") -> dict:
    leaps = []
    for mo in model_outputs:
        text = mo.get("text", "")
        prompt_id = mo.get("prompt_id", "")
        if "unsupported" not in prompt_id.lower() and "skeptical" not in prompt_id.lower():
            continue
        for line in text.split("\n"):
            line = line.strip()
            if not line or len(line) < 20:
                continue
            lower = line.lower()
            if any(w in lower for w in ["unsupported", "leap", "gap", "missing", "no evidence", "without proof", "unsubstantiated"]):
                severity = "HIGH" if any(w in lower for w in ["no evidence", "unsubstantiated"]) else "MEDIUM"
                leaps.append({
                    "leap_id": hashlib.sha256(line.encode()).hexdigest()[:12],
                    "text": line[:500],
                    "category": _categorize_leap(line),
                    "severity": severity,
                    "why_unsupported": "identified by skeptical review",
                    "what_evidence_would_be_needed": "empirical or formal proof required",
                })

    return {
        "schema_version": "unsupported_leap_audit_v1",
        "question": question,
        "risk_mode": risk_mode,
        "leaps": leaps,
        "total_leaps": len(leaps),
        "model_output_is_truth": False,
    }


def _categorize_leap(line: str) -> str:
    lower = line.lower()
    if any(w in lower for w in ["physics", "quantum", "empirical"]):
        return "empirical_overreach"
    if any(w in lower for w in ["consciousness", "sentien", "aware"]):
        return "consciousness_claim"
    if any(w in lower for w in ["math", "theorem", "proof", "formal"]):
        return "formal_overreach"
    return "general_unsupported"


def write_leap_audit(leaps_data: dict, out_dir: str) -> str:
    path = os.path.join(out_dir, "unsupported_leap_audit.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(leaps_data, f, indent=2)
    return path
