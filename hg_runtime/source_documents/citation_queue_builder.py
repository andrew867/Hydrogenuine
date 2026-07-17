"""Citation queue builder — creates candidate source queue from citations.

Citation candidates are not fetched by default. Fetch requires explicit flag.
Citation is not proof. No promotion.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from hg_runtime.source_documents.citation_extractor import CitationCandidate


def build_citation_queue(
    candidates: list[CitationCandidate],
    *,
    max_candidates: int = 20,
    out_dir: str = "",
) -> dict:
    safe = [c for c in candidates if c.safe_for_read]
    unsafe = [c for c in candidates if not c.safe_for_read]

    queue_entries = []
    for c in safe[:max_candidates]:
        queue_entries.append(c.to_dict())

    result = {
        "schema_version": "citation_queue_v1",
        "total_candidates": len(candidates),
        "safe_candidates": len(safe),
        "unsafe_rejected": len(unsafe),
        "queued": len(queue_entries),
        "max_candidates": max_candidates,
        "fetch_enabled": False,
        "fetch_requires_explicit_flag": True,
        "entries": queue_entries,
        "citation_is_not_proof": True,
        "promotion_allowed": False,
        "operator_review_required": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, "citation_candidates.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for entry in queue_entries:
                f.write(json.dumps(entry) + "\n")

    return result
