"""Mainstream-adjacent comparison table builder.

No promotion. Model output is not truth. Operator review required.
"""

from __future__ import annotations

import json
import os

COMPARISON_BUCKETS = [
    "fixed_point_logic_self_reference",
    "formal_language_theory",
    "information_theory",
    "cybernetics",
    "dynamical_systems",
    "active_inference_predictive_processing",
    "quantum_like_cognition",
    "philosophy_of_mind",
    "process_philosophy",
]

BUCKET_LABELS = {
    "fixed_point_logic_self_reference": "Fixed-Point Logic / Self-Reference",
    "formal_language_theory": "Formal Language Theory",
    "information_theory": "Information Theory",
    "cybernetics": "Cybernetics",
    "dynamical_systems": "Dynamical Systems",
    "active_inference_predictive_processing": "Active Inference / Predictive Processing",
    "quantum_like_cognition": "Quantum-Like Cognition",
    "philosophy_of_mind": "Philosophy of Mind",
    "process_philosophy": "Process Philosophy",
}


def build_comparison(*, model_outputs: list[dict], question: str, risk_mode: str = "normal") -> dict:
    buckets = []
    all_text = "\n".join(mo.get("text", "") for mo in model_outputs).lower()

    for bucket_id in COMPARISON_BUCKETS:
        label = BUCKET_LABELS[bucket_id]
        keywords = bucket_id.replace("_", " ").split()
        relevance = sum(1 for kw in keywords if kw in all_text)

        buckets.append({
            "bucket_id": bucket_id,
            "label": label,
            "possible_relationship": "to be determined by operator review" if relevance > 0 else "no signal in retrieved sources",
            "evidence_strength": "weak" if relevance > 0 else "none",
            "unsupported_leaps": [],
            "sources_needed": [],
            "operator_review_required": True,
        })

    return {
        "schema_version": "mainstream_comparison_v1",
        "question": question,
        "risk_mode": risk_mode,
        "buckets": buckets,
        "total_buckets": len(buckets),
        "model_output_is_truth": False,
        "comparison_is_not_endorsement": True,
    }


def write_comparison(comparison_data: dict, out_dir: str) -> str:
    path = os.path.join(out_dir, "mainstream_comparison.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(comparison_data, f, indent=2)
    return path
