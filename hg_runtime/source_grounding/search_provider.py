"""Controlled search interface — search ranking is not authority.

Search results are candidates, not facts. Snippets are not source truth.
Every search creates a receipt. No autonomous authority from search.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

SCHEMA_VERSION = "search_receipt_v1"


def create_search_receipt(*, query: str, provider: str = "web_search",
                          result_count: int = 0,
                          results: list[dict] | None = None,
                          run_id: str = "",
                          seed_ids: list[str] | None = None) -> dict:
    receipt = {
        "schema": SCHEMA_VERSION,
        "search_receipt_id": "",
        "query": query,
        "provider": provider,
        "searched_at": datetime.now(timezone.utc).isoformat(),
        "result_count": result_count,
        "results": results or [],
        "run_id": run_id,
        "seed_ids": seed_ids or [],
        "search_ranking_is_authority": False,
        "snippets_are_truth": False,
        "source_treated_as_truth": False,
        "external_effect_created": False,
    }
    raw = json.dumps(receipt, sort_keys=True)
    receipt["search_receipt_id"] = hashlib.sha256(raw.encode()).hexdigest()[:24]
    return receipt


def create_search_result(*, url: str, title: str = "",
                         snippet: str = "", rank: int = 0,
                         source_type: str = "unknown") -> dict:
    return {
        "url": url,
        "canonical_url": url.split("?")[0].split("#")[0],
        "title": title,
        "snippet": snippet,
        "rank": rank,
        "source_type": source_type,
        "snippet_is_truth": False,
        "ranking_is_evidence_quality": False,
    }


def validate_search_receipt(receipt: dict) -> list[str]:
    errors = []
    if receipt.get("schema") != SCHEMA_VERSION:
        errors.append(f"wrong schema: {receipt.get('schema')}")
    if receipt.get("search_ranking_is_authority"):
        errors.append("search_ranking_is_authority must be False")
    if receipt.get("snippets_are_truth"):
        errors.append("snippets_are_truth must be False")
    if receipt.get("source_treated_as_truth"):
        errors.append("source_treated_as_truth must be False")
    if receipt.get("external_effect_created"):
        errors.append("external_effect_created must be False")
    for r in receipt.get("results", []):
        if r.get("snippet_is_truth"):
            errors.append(f"result snippet_is_truth must be False: {r.get('url')}")
        if r.get("ranking_is_evidence_quality"):
            errors.append(f"result ranking_is_evidence_quality must be False: {r.get('url')}")
    return errors
