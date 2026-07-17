"""Source planner for overnight research mode.

Creates a source plan and source queue from the question contract.
Operator-provided URLs appear first. No autonomous search by default.
No promotion. Source is not truth.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

from hg_runtime.overnight_research.question_contract import ResearchQuestion

try:
    from hg_runtime.source_grounding.read_only_web_retriever import is_url_safe_for_read
except ImportError:
    def is_url_safe_for_read(url: str) -> tuple[bool, str]:
        if any(x in url for x in ["127.0.0.1", "localhost", "192.168.", "10.", "172.16."]):
            return False, "private/internal URL"
        return True, ""


def build_source_plan(q: ResearchQuestion, out_dir: str) -> dict:
    entries = []
    for i, url in enumerate(q.source_urls):
        safe, reason = is_url_safe_for_read(url)
        entries.append({
            "source_candidate_id": hashlib.sha256(url.encode()).hexdigest()[:16],
            "url": url,
            "origin": "operator_provided",
            "priority": i,
            "safe_for_read": safe,
            "rejection_reason": reason if not safe else "",
            "source_type": _classify_url(url),
            "operator_review_required": True,
            "source_is_truth": False,
        })

    plan = {
        "schema_version": "overnight_research_source_plan_v1",
        "question": q.question,
        "risk_mode": q.risk_mode,
        "entries": entries,
        "total_sources": len(entries),
        "max_sources": q.max_sources,
        "autonomous_search_enabled": False,
        "source_ranking_is_not_authority": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    plan_path = os.path.join(out_dir, "source_plan.json")
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)

    queue_path = os.path.join(out_dir, "source_queue.jsonl")
    with open(queue_path, "w", encoding="utf-8") as f:
        for entry in entries[:q.max_sources]:
            if entry["safe_for_read"]:
                f.write(json.dumps(entry) + "\n")

    return plan


def _classify_url(url: str) -> str:
    lower = url.lower()
    if "arxiv.org" in lower:
        return "preprint"
    if "wiki" in lower:
        return "wiki"
    if "nature.com" in lower or "science.org" in lower:
        return "journal"
    if ".edu" in lower:
        return "academic"
    if "github.com" in lower:
        return "code"
    return "web"
