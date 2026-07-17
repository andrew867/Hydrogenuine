"""
Pack 21: Pair sampler — uncertainty scoring and tag-stratified selection.
Pure module: no DB, no network.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

# Outcome: dict with outcome_id (or id) and tags (list of str)
# mu: optional dict outcome_id -> float for uncertainty


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def select_pairs(
    outcomes: List[Dict[str, Any]],
    budget: int,
    mu: Optional[Dict[str, float]] = None,
    *,
    include_tags: Optional[List[str]] = None,
    exclude_tags: Optional[List[str]] = None,
    exclude_severity: Optional[str] = None,
    random_seed: Optional[int] = 42,
) -> List[Tuple[str, str]]:
    """
    Select up to `budget` outcome pairs. Prefer pairs where p_ij is near 0.5 (uncertainty).
    Optionally stratify by include_tags. outcomes: list of {outcome_id, tags, severity?}.
    Returns list of (a_id, b_id).
    """
    import random
    rng = random.Random(random_seed)

    oids = []
    for o in outcomes:
        oid = o.get("outcome_id") or o.get("id")
        if not oid:
            continue
        tags = o.get("tags") or o.get("tags_json")
        if isinstance(tags, str):
            try:
                import json
                tags = json.loads(tags)
            except Exception:
                tags = []
        if not isinstance(tags, list):
            tags = []
        sev = o.get("severity")
        if include_tags and not any(t in tags for t in include_tags):
            continue
        if exclude_tags and any(t in tags for t in exclude_tags):
            continue
        if exclude_severity and sev == exclude_severity:
            continue
        oids.append(str(oid))

    if len(oids) < 2:
        return []

    mu = mu or {x: 0.0 for x in oids}
    pairs: List[Tuple[float, str, str]] = []  # (uncertainty_score, a, b)
    for i in range(len(oids)):
        for j in range(i + 1, len(oids)):
            a, b = oids[i], oids[j]
            diff = mu.get(a, 0) - mu.get(b, 0)
            p = _sigmoid(diff)
            # uncertainty: 1 - 2*|p - 0.5| in [0,1], higher = more uncertain
            u = 1.0 - 2 * abs(p - 0.5)
            pairs.append((u, a, b))

    # Sort by uncertainty descending, then sample up to budget (with optional tag stratification)
    pairs.sort(key=lambda x: -x[0])
    chosen: List[Tuple[str, str]] = []
    used = set()
    for u, a, b in pairs:
        if len(chosen) >= budget:
            break
        key = (min(a, b), max(a, b))
        if key in used:
            continue
        used.add(key)
        chosen.append((a, b))

    rng.shuffle(chosen)
    return chosen
