"""Public copy safety checker for dashboard-generated text.

Scans for unsafe affirmative claims in dashboard HTML. Respects
per-line negation context. No mutation. No external network.
"""

from __future__ import annotations

import json
import os
import re

UNSAFE_TERMS = [
    "AGI", "artificial general intelligence",
    "conscious", "consciousness", "sentient", "sentience",
    "sovereign AI", "sovereignty",
    "truth engine", "proven true",
    "establishes truth", "proves that", "has been proven",
    "this proves", "scientifically proven",
    "autonomous authority",
]

NEGATION_MARKERS = [
    "not ", "no ", "cannot ", "does not ", "do not ", "never ",
    "is not ", "!=", "without ", "what was not ",
    "what this does not ", "does not prove",
]


def check_public_copy(*, dashboard_dir: str) -> dict:
    index_path = os.path.join(dashboard_dir, "index.html")
    if not os.path.isfile(index_path):
        return {"error": "index.html not found", "flagged": [], "clean": True}

    with open(index_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    flagged = []
    for i, line in enumerate(lines, 1):
        lower = line.lower()
        for term in UNSAFE_TERMS:
            if term.lower() in lower:
                idx = lower.find(term.lower())
                context_start = max(0, idx - 80)
                context = lower[context_start:idx]
                negated = any(neg in context for neg in NEGATION_MARKERS)
                if not negated:
                    flagged.append({
                        "term": term,
                        "line": i,
                        "text": line.strip()[:150],
                        "negated": False,
                    })

    return {
        "flagged": flagged,
        "flagged_count": len(flagged),
        "clean": len(flagged) == 0,
        "total_lines": len(lines),
        "dashboard_dir": dashboard_dir,
    }
