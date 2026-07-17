"""Source upgrade planner — suggests primary/better sources.

Suggestions only. No authority granted. Primary source is not
automatically true. Source upgrade is review priority, not authority.
No promotion.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone


SOURCE_CLASSIFICATIONS = {
    "primary_paper": 1,
    "preprint": 2,
    "journal": 2,
    "academic": 3,
    "documentation": 3,
    "code": 4,
    "wiki": 5,
    "news": 5,
    "blog": 6,
    "web": 7,
    "unknown": 8,
}


def classify_source_type(url: str) -> str:
    lower = url.lower()
    if "arxiv.org" in lower:
        return "preprint"
    if "doi.org" in lower:
        return "primary_paper"
    if any(x in lower for x in ["nature.com", "science.org", "springer.com",
                                  "wiley.com", "aps.org", "ieee.org"]):
        return "journal"
    if ".edu" in lower or "scholar.google" in lower:
        return "academic"
    if "wikipedia.org" in lower or "wiki" in lower:
        return "wiki"
    if "github.com" in lower or "gitlab.com" in lower:
        return "code"
    if any(x in lower for x in ["news", "press", "bbc.", "cnn.",
                                  "nytimes.", "reuters.", "apnews."]):
        return "news"
    if any(x in lower for x in ["blog", "medium.com", "substack.com",
                                  "wordpress."]):
        return "blog"
    if any(x in lower for x in ["readthedocs", "docs.", "documentation"]):
        return "documentation"
    return "web"


def suggest_upgrades(sources: list[dict]) -> list[dict]:
    suggestions = []

    for src in sources:
        url = src.get("url", "") or src.get("candidate_url", "")
        source_type = classify_source_type(url)
        rank = SOURCE_CLASSIFICATIONS.get(source_type, 8)

        suggestion = {
            "original_url": url,
            "current_type": source_type,
            "current_rank": rank,
            "upgrade_suggestion": "",
            "upgrade_reason": "",
            "advisory_only": True,
            "authority_granted": False,
            "promotion_allowed": False,
            "operator_review_required": True,
        }

        if source_type == "wiki":
            suggestion["upgrade_suggestion"] = "Check cited references for primary papers"
            suggestion["upgrade_reason"] = "Wikipedia is secondary; cited sources may be primary"
        elif source_type == "news":
            suggestion["upgrade_suggestion"] = "Find the original paper or press release"
            suggestion["upgrade_reason"] = "News articles summarize; original source has more detail"
        elif source_type == "blog":
            suggestion["upgrade_suggestion"] = "Find referenced papers or standards"
            suggestion["upgrade_reason"] = "Blogs interpret; primary sources are more authoritative"
        elif source_type == "preprint":
            suggestion["upgrade_suggestion"] = "Check if a published version exists"
            suggestion["upgrade_reason"] = "Published version may have peer review corrections"

        if suggestion["upgrade_suggestion"]:
            suggestions.append(suggestion)

    return suggestions


def write_upgrade_suggestions(suggestions: list[dict], out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "source_upgrade_suggestions.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for s in suggestions:
            f.write(json.dumps(s) + "\n")
    return path
