"""Social capability schema — cargo in, governed publish out.

Social content is cargo, not instruction. Posting is external action requiring a scoped
``SocialPublishPermit``. Agent Zero may request; it may not seize.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

SOCIAL_SCHEMA_VERSION = "social-capability/1"
FIXTURE_UTC = "2026-06-15T04:00:00+00:00"


def _frozen() -> dict[str, Any]:
    return {
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


def social_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class SocialSurface(str, Enum):
    FIXTURE = "fixture"
    LOCAL_TEXT = "local_text"
    MOLTBOOK = "moltbook"
    FOURCLAW = "fourclaw"
    BROWSER_READ_ONLY = "browser_read_only"
    MASTODON_LIKE = "mastodon_like"
    TWITTER_X_LIKE = "twitter_x_like"
    BLUESKY_LIKE = "bluesky_like"
    CUSTOM_MANUAL_POST = "custom_manual_post"


class SocialCredentialStatus(str, Enum):
    ABSENT = "ABSENT"
    CONFIGURED = "CONFIGURED"
    EXPIRED = "EXPIRED"
    INVALID = "INVALID"


class SocialForbiddenAction(str, Enum):
    DM = "dm"
    REPLY = "reply"
    FOLLOW = "follow"
    UNFOLLOW = "unfollow"
    DELETE = "delete"
    ACCOUNT_EDIT = "account_edit"
    ACCOUNT_CREATE = "account_create"
    LOGIN_AUTOMATION = "login_automation"
    SCRAPE_PRIVATE = "scrape_private"
    UNBOUNDED_THREAD = "unbounded_thread"
    DIRECT_PUBLISH = "direct_publish"


class SocialPublishDecision(str, Enum):
    QUEUED = "QUEUED"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    PUBLISHED = "PUBLISHED"
    REFUSED = "REFUSED"


@dataclass
class SocialReadRequest:
    request_id: str
    surface: SocialSurface
    operator: str = "local-operator"
    live: bool = False
    limit: int = 20

    def to_payload(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "surface": self.surface.value,
            "operator": self.operator,
            "live": self.live,
            "limit": self.limit,
            **_frozen(),
        }


@dataclass
class SocialReadItem:
    item_id: str
    surface: SocialSurface
    author: str
    text: str
    retrieved_at: str
    is_cargo: bool = True

    def to_payload(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "surface": self.surface.value,
            "author": self.author,
            "text": self.text[:2000],
            "retrieved_at": self.retrieved_at,
            "is_cargo": self.is_cargo,
            **_frozen(),
        }


@dataclass
class SocialReadResult:
    request_id: str
    surface: SocialSurface
    items: list[SocialReadItem]
    trust_ok: bool
    trust_disposition: str
    credential_status: SocialCredentialStatus

    def to_payload(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "surface": self.surface.value,
            "items": [i.to_payload() for i in self.items],
            "trust_ok": self.trust_ok,
            "trust_disposition": self.trust_disposition,
            "credential_status": self.credential_status.value,
            **_frozen(),
        }


@dataclass
class SocialDraftRequest:
    request_id: str
    surface: SocialSurface
    source_context: str
    topic: str
    confidence: float = 0.5
    operator: str = "local-operator"

    def to_payload(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "surface": self.surface.value,
            "source_context": self.source_context[:1000],
            "topic": self.topic[:500],
            "confidence": self.confidence,
            "operator": self.operator,
            **_frozen(),
        }


@dataclass
class SocialDraft:
    draft_id: str
    surface: SocialSurface
    body: str
    source_context: str
    confidence: float
    no_authority_claim: bool
    no_personhood_claim: bool
    no_coercion: bool
    trust_ok: bool
    opb_ok: bool
    created_at: str
    internal_only: bool = True
    publishable: bool = False
    topic: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "draft_id": self.draft_id,
            "surface": self.surface.value,
            "body": self.body[:2000],
            "source_context": self.source_context[:500],
            "confidence": self.confidence,
            "no_authority_claim": self.no_authority_claim,
            "no_personhood_claim": self.no_personhood_claim,
            "no_coercion": self.no_coercion,
            "trust_ok": self.trust_ok,
            "opb_ok": self.opb_ok,
            "created_at": self.created_at,
            "internal_only": self.internal_only,
            "publishable": self.publishable,
            "topic": self.topic[:200],
            **_frozen(),
        }


@dataclass
class SocialPublishRequest:
    request_id: str
    draft_id: str
    surface: SocialSurface
    operator: str = "local-operator"
    operator_approved: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "draft_id": self.draft_id,
            "surface": self.surface.value,
            "operator": self.operator,
            "operator_approved": self.operator_approved,
            **_frozen(),
        }


@dataclass
class SocialPublishPermit:
    permit_id: str
    draft_id: str
    surface: SocialSurface
    scope: str
    max_posts: int
    expires_at: str
    operator: str
    live_publish_enabled: bool

    def to_payload(self) -> dict[str, Any]:
        return {
            "permit_id": self.permit_id,
            "draft_id": self.draft_id,
            "surface": self.surface.value,
            "scope": self.scope,
            "max_posts": self.max_posts,
            "expires_at": self.expires_at,
            "operator": self.operator,
            "live_publish_enabled": self.live_publish_enabled,
            **_frozen(),
        }


@dataclass
class SocialPublishReceipt:
    receipt_id: str
    permit_id: str
    draft_id: str
    surface: SocialSurface
    decision: SocialPublishDecision
    published: bool
    fixture_mode: bool
    created_at: str
    ewj_event_ref: str | None = None
    external_visibility: dict | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema": "social-publish-receipt",
            "version": SOCIAL_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "permit_id": self.permit_id,
            "draft_id": self.draft_id,
            "surface": self.surface.value,
            "decision": self.decision.value,
            "published": self.published,
            "fixture_mode": self.fixture_mode,
            "created_at": self.created_at,
            "ewj_event_ref": self.ewj_event_ref,
            **_frozen(),
        }
        if self.external_visibility:
            payload.update(self.external_visibility)
        payload["content_hash"] = social_hash(payload)
        return payload


@dataclass
class SocialSoakTask:
    task_id: str
    kind: str
    description: str
    allowed: bool = True

    def to_payload(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "kind": self.kind,
            "description": self.description,
            "allowed": self.allowed,
            **_frozen(),
        }


__all__ = [
    "FIXTURE_UTC",
    "SOCIAL_SCHEMA_VERSION",
    "SocialCredentialStatus",
    "SocialDraft",
    "SocialDraftRequest",
    "SocialForbiddenAction",
    "SocialPublishDecision",
    "SocialPublishPermit",
    "SocialPublishReceipt",
    "SocialPublishRequest",
    "SocialReadItem",
    "SocialReadRequest",
    "SocialReadResult",
    "SocialSoakTask",
    "SocialSurface",
    "new_id",
    "social_hash",
]
