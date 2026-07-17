"""Social draft generation — governed, advisory, no authority claims."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from hg_runtime.fixture_policy import FixtureUseDenied, require_fixture_allowed
from hg_runtime.social_capability.content_policy import is_internal_operational_content
from hg_runtime.social_capability.schema import (
    FIXTURE_UTC,
    SocialDraft,
    SocialDraftRequest,
    SocialSurface,
    new_id,
)
from hg_runtime.social_capability.trust_boundary import check_draft_policy, ingest_social_cargo

WORKSPACE = Path(__file__).resolve().parents[2]
CURATED_POSTS = WORKSPACE / "configs" / "social" / "curated_public_posts.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _opb_check(body: str) -> bool:
    low = body.lower()
    pressure = ("please respond", "waiting for you", "don't ignore", "urgent approval needed")
    return not any(p in low for p in pressure)


def create_draft(request: SocialDraftRequest, *, allow_publish: bool = False) -> SocialDraft:
    """Create an internal probe/audit draft. Never publishable unless explicitly testing."""
    trust = ingest_social_cargo(request.source_context + " " + request.topic)
    body = (
        f"[INTERNAL AUDIT — NOT FOR PUBLISH]\n"
        f"topic={request.topic}\n"
        f"context={request.source_context[:200]}\n"
        f"confidence={request.confidence:.2f}"
    )
    policy_ok, issues = check_draft_policy(body)
    opb_ok = _opb_check(body)
    publishable = bool(allow_publish) and not is_internal_operational_content(body, topic=request.topic)
    return SocialDraft(
        draft_id=new_id("draft"),
        surface=request.surface,
        body=body,
        source_context=request.source_context[:500],
        confidence=request.confidence,
        topic=request.topic,
        no_authority_claim="authority" not in issues,
        no_personhood_claim="personhood" not in issues,
        no_coercion="coercion" not in issues,
        trust_ok=trust.ok and policy_ok,
        opb_ok=opb_ok,
        created_at=_now_iso(),
        internal_only=not publishable,
        publishable=publishable,
    )


def create_curated_draft(*, post_id: str, surface: SocialSurface, body: str, topic: str) -> SocialDraft:
    """Create a public-safe curated draft — fixture rehearsal only."""
    require_fixture_allowed(operation="create_curated_draft")
    if is_internal_operational_content(body, topic=topic):
        raise ValueError("curated draft rejected: internal operational content")
    trust = ingest_social_cargo(body)
    policy_ok, issues = check_draft_policy(body)
    opb_ok = _opb_check(body)
    return SocialDraft(
        draft_id=new_id("draft"),
        surface=surface,
        body=body.strip(),
        source_context=f"curated:{post_id}",
        confidence=0.85,
        topic=topic,
        no_authority_claim="authority" not in issues,
        no_personhood_claim="personhood" not in issues,
        no_coercion="coercion" not in issues,
        trust_ok=trust.ok and policy_ok,
        opb_ok=opb_ok,
        created_at=_now_iso(),
        internal_only=False,
        publishable=True,
    )


def load_curated_posts() -> list[dict]:
    require_fixture_allowed(operation="load_curated_posts")
    if not CURATED_POSTS.exists():
        return []
    import json

    data = json.loads(CURATED_POSTS.read_text(encoding="utf-8"))
    return list(data.get("posts", []))


__all__ = ["create_curated_draft", "create_draft", "load_curated_posts"]
