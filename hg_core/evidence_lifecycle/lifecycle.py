"""Artifact lifecycle decisions — deletion and expiry (CT-10 RET)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from hg_core.evidence_lifecycle.policy import RetentionPolicy, classify_path

REASON_UNAUTHORIZED = "retention.refused.unauthorized_deletion"
REASON_IMMUTABLE = "retention.refused.immutable_tier"
REASON_NOT_EXPIRED = "retention.refused.not_expired"
REASON_MISSING_SEC = "retention.refused.missing_sec_handling"


@dataclass(frozen=True)
class ArtifactDescriptor:
    artifact_id: str
    path: str
    artifact_class: str
    owner_subsystem: str
    created_at: datetime
    sec_handled: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "path": self.path,
            "artifact_class": self.artifact_class,
            "owner_subsystem": self.owner_subsystem,
            "created_at": self.created_at.isoformat(),
            "sec_handled": self.sec_handled,
        }


@dataclass(frozen=True)
class DeletionDecision:
    allowed: bool
    reason_code: str | None
    receipt_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason_code": self.reason_code,
            "receipt_id": self.receipt_id,
        }


def is_temp_expired(
    descriptor: ArtifactDescriptor,
    policy: RetentionPolicy,
    *,
    now: datetime | None = None,
) -> bool:
    entry = policy.class_policy(descriptor.artifact_class)
    if entry is None or entry.tier != "temporary":
        return False
    ttl = entry.ttl_hours or 24
    current = now or datetime.now(timezone.utc)
    created = descriptor.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return current - created >= timedelta(hours=ttl)


def evaluate_deletion(
    descriptor: ArtifactDescriptor,
    requestor_subsystem: str,
    policy: RetentionPolicy,
    *,
    now: datetime | None = None,
) -> DeletionDecision:
    entry = policy.class_policy(descriptor.artifact_class)
    if entry is None:
        return DeletionDecision(False, REASON_UNAUTHORIZED)
    if requestor_subsystem != entry.owner_subsystem:
        return DeletionDecision(False, REASON_UNAUTHORIZED)
    if entry.tier == "immutable":
        return DeletionDecision(False, REASON_IMMUTABLE)
    if entry.tier == "sensitive" and not descriptor.sec_handled:
        return DeletionDecision(False, REASON_MISSING_SEC)
    if entry.tier == "temporary":
        if is_temp_expired(descriptor, policy, now=now):
            return DeletionDecision(True, None, receipt_id=f"ret-del-{descriptor.artifact_id}")
        return DeletionDecision(False, REASON_NOT_EXPIRED)
    if entry.tier in {"archivable", "compactable", "append_only"}:
        return DeletionDecision(False, REASON_UNAUTHORIZED)
    return DeletionDecision(False, REASON_UNAUTHORIZED)


def descriptor_from_path(
    path: str,
    policy: RetentionPolicy,
    *,
    artifact_id: str = "artifact",
    owner_subsystem: str | None = None,
    created_at: datetime | None = None,
) -> ArtifactDescriptor | None:
    artifact_class = classify_path(path, policy)
    if artifact_class is None:
        return None
    entry = policy.class_policy(artifact_class)
    owner = owner_subsystem or (entry.owner_subsystem if entry else "unknown")
    return ArtifactDescriptor(
        artifact_id=artifact_id,
        path=path,
        artifact_class=artifact_class,
        owner_subsystem=owner,
        created_at=created_at or datetime.now(timezone.utc),
    )


__all__ = [
    "ArtifactDescriptor",
    "DeletionDecision",
    "REASON_IMMUTABLE",
    "REASON_MISSING_SEC",
    "REASON_NOT_EXPIRED",
    "REASON_UNAUTHORIZED",
    "descriptor_from_path",
    "evaluate_deletion",
    "is_temp_expired",
]
