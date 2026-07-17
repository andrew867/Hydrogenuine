"""Source candidate schema — canonical fields for harvested source candidates.

URL existence is not truth. Source candidate is not source proof.
Source is not truth. Operator-provided URL is not authority.
"""

from __future__ import annotations

import hashlib
import json

SCHEMA_VERSION = "source_candidate_v1"

SOURCE_CANDIDATE_TYPES = frozenset({
    "primary_paper",
    "preprint",
    "press_release",
    "science_news_article",
    "documentation",
    "dataset",
    "constants_reference",
    "pdf",
    "unknown",
})

RESEARCH_BUCKETS = frozenset({
    "subjective_time",
    "quantum_like_cognition",
    "quantum_measurement",
    "higgs_proper_time",
    "collider_reference",
    "quantum_materials",
    "entanglement_metric",
    "signal_processing_metaphor",
    "active_matter_information_bottleneck",
    "measurement_metrology",
    "other",
})


def _candidate_id(canonical_url: str) -> str:
    return hashlib.sha256(canonical_url.encode()).hexdigest()[:24]


def normalize_url(url: str) -> str:
    url = url.strip().rstrip("/")
    url = url.split("#")[0]
    url = url.split("?")[0]
    if url.startswith("http://"):
        url = "https://" + url[7:]
    return url


def create_source_candidate(
    *,
    canonical_url: str,
    original_urls: list[str] | None = None,
    first_seen_path: str = "",
    first_seen_line_or_offset: int = -1,
    all_occurrences: list[dict] | None = None,
    source_candidate_type: str = "unknown",
    research_bucket: str = "other",
    operator_provided: bool = False,
    retrieval_allowed: bool = True,
    retrieval_mode: str = "read_only",
    login_required_known: str = "unknown",
    paywall_possible: str = "unknown",
    notes: str = "",
) -> dict:
    if source_candidate_type not in SOURCE_CANDIDATE_TYPES:
        raise ValueError(f"invalid source_candidate_type: {source_candidate_type}")
    if research_bucket not in RESEARCH_BUCKETS:
        raise ValueError(f"invalid research_bucket: {research_bucket}")

    return {
        "schema": SCHEMA_VERSION,
        "source_candidate_id": _candidate_id(canonical_url),
        "canonical_url": canonical_url,
        "original_urls": original_urls or [canonical_url],
        "first_seen_path": first_seen_path,
        "first_seen_line_or_offset": first_seen_line_or_offset,
        "all_occurrences": all_occurrences or [],
        "source_candidate_type": source_candidate_type,
        "research_bucket": research_bucket,
        "operator_provided": operator_provided,
        "retrieval_allowed": retrieval_allowed,
        "retrieval_mode": retrieval_mode,
        "login_required_known": login_required_known,
        "paywall_possible": paywall_possible,
        "promotion_allowed": False,
        "operator_review_required": True,
        "notes": notes,
    }


def validate_source_candidate(candidate: dict) -> list[str]:
    violations = []
    if candidate.get("promotion_allowed"):
        violations.append("promotion_allowed_true")
    if not candidate.get("operator_review_required"):
        violations.append("operator_review_not_required")
    if candidate.get("source_candidate_type") not in SOURCE_CANDIDATE_TYPES:
        violations.append(f"invalid_type:{candidate.get('source_candidate_type')}")
    if candidate.get("research_bucket") not in RESEARCH_BUCKETS:
        violations.append(f"invalid_bucket:{candidate.get('research_bucket')}")
    if candidate.get("retrieval_mode") != "read_only":
        violations.append("retrieval_mode_not_read_only")
    if not candidate.get("canonical_url"):
        violations.append("missing_canonical_url")
    return violations
