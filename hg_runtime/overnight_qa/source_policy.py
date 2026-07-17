"""Source retrieval policy for governed overnight runs."""

from __future__ import annotations

from .schemas import SourceRecord


ALLOWED_SOURCE_CATEGORIES = (
    "public_reference_docs",
    "open_access_research",
    "official_standards",
    "public_documentation",
    "fixture_corpus",
)

BLOCKED_SOURCE_CATEGORIES = (
    "paywalled",
    "credentialed_portals",
    "private_user_data",
    "social_media_posting_endpoints",
    "executable_downloads",
    "forms_requiring_submission",
    "login_required",
)

POLICY_RULES = {
    "no_paywall_bypass": True,
    "no_credentialed_browsing_by_default": True,
    "no_forms_submitted": True,
    "no_comments_posts_messages": True,
    "no_downloads_except_explicit_allowed_docs": True,
    "no_executable_downloads": True,
    "polite_manual_like_fetch_only": True,
    "browsing_disabled_by_default": True,
}


def category_allowed(category: str) -> bool:
    return category in ALLOWED_SOURCE_CATEGORIES and category not in BLOCKED_SOURCE_CATEGORIES


def make_source_record(
    *,
    source_id: str,
    url_or_fixture_id: str,
    retrieval_time: str,
    retrieval_performed: bool,
    retrieval_method: str,
    title: str,
    claim_support: str = "",
    uncertainty: str = "",
) -> SourceRecord:
    return SourceRecord(
        source_id=source_id,
        url_or_fixture_id=url_or_fixture_id,
        retrieval_time=retrieval_time,
        retrieval_performed=retrieval_performed,
        retrieval_method=retrieval_method,
        title=title,
        claim_support=claim_support,
        uncertainty=uncertainty,
        operator_review_required=True,
        is_truth=False,
    )


def source_is_truth(record: SourceRecord) -> bool:
    """Sources are never truth."""
    return False


def policy_snapshot() -> dict:
    return {
        "allowed_categories": list(ALLOWED_SOURCE_CATEGORIES),
        "blocked_categories": list(BLOCKED_SOURCE_CATEGORIES),
        "rules": dict(POLICY_RULES),
        "browsing_disabled_by_default": True,
    }
