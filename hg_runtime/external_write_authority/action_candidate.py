"""External action candidate — not permission, not dispatch."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.external_write_authority.schema import (
    CandidateStatus,
    ExternalActionType,
    STORE_ROOT,
    content_hash,
    load_policy,
    new_id,
    now_iso,
)


@dataclass
class ExternalActionCandidate:
    candidate_id: str
    run_id: str
    requested_platform: str
    requested_action_type: ExternalActionType
    content_hash: str
    risk_class: str
    scope: str
    data_tier: str
    status: CandidateStatus
    created_at: str
    expires_at: str
    turn_id: str | None = None
    artifact_ref: str | None = None
    review_item_ref: str | None = None
    provider_receipt_ref: str | None = None
    live_read_receipt_refs: tuple[str, ...] = ()
    requested_target_ref: str | None = None
    draft_content_ref: str | None = None
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "run_id": self.run_id,
            "turn_id": self.turn_id,
            "artifact_ref": self.artifact_ref,
            "review_item_ref": self.review_item_ref,
            "provider_receipt_ref": self.provider_receipt_ref,
            "live_read_receipt_refs": list(self.live_read_receipt_refs),
            "requested_platform": self.requested_platform,
            "requested_action_type": self.requested_action_type.value,
            "requested_target_ref": self.requested_target_ref,
            "draft_content_ref": self.draft_content_ref,
            "content_hash": self.content_hash,
            "risk_class": self.risk_class,
            "scope": self.scope,
            "data_tier": self.data_tier,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status.value,
            "hash": self.hash,
        }

    def with_hash(self) -> ExternalActionCandidate:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        from hg_core.policy_safety.hashing import compute_record_hash

        return ExternalActionCandidate(**{**self.__dict__, "hash": compute_record_hash(body)})

    def is_expired(self, *, at: str | None = None) -> bool:
        ts = at or now_iso()
        try:
            exp = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            cur = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return cur >= exp
        except ValueError:
            return True


def _store(run_id: str) -> Path:
    return STORE_ROOT / run_id / "candidates"


def create_candidate(
    *,
    run_id: str,
    platform: str,
    action_type: str | ExternalActionType,
    content: str,
    scope: str,
    risk_class: str = "medium",
    data_tier: str = "internal",
    ttl_seconds: int | None = None,
    content_sha256: str | None = None,
    **refs: Any,
) -> ExternalActionCandidate:
    policy = load_policy()
    if not platform or not scope:
        raise ValueError("platform and scope required")
    action = ExternalActionType(action_type) if isinstance(action_type, str) else action_type
    ttl = ttl_seconds or int(policy.get("candidate_ttl_seconds", 3600))
    created = now_iso()
    from datetime import timedelta

    exp = (datetime.now(timezone.utc) + timedelta(seconds=ttl)).isoformat()
    candidate = ExternalActionCandidate(
        candidate_id=new_id("ext-cand"),
        run_id=run_id,
        turn_id=refs.get("turn_id"),
        artifact_ref=refs.get("artifact_ref"),
        review_item_ref=refs.get("review_item_ref"),
        provider_receipt_ref=refs.get("provider_receipt_ref"),
        live_read_receipt_refs=tuple(refs.get("live_read_receipt_refs") or ()),
        requested_platform=platform,
        requested_action_type=action,
        requested_target_ref=refs.get("requested_target_ref"),
        draft_content_ref=refs.get("draft_content_ref"),
        content_hash=content_sha256 or content_hash(content),
        risk_class=risk_class,
        scope=scope,
        data_tier=data_tier,
        created_at=created,
        expires_at=exp,
        status=CandidateStatus.CANDIDATE_CREATED,
    ).with_hash()
    path = _store(run_id)
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{candidate.candidate_id}.json").write_text(
        json.dumps(candidate.to_payload(), indent=2) + "\n", encoding="utf-8"
    )
    return candidate


def load_candidate(run_id: str, candidate_id: str) -> ExternalActionCandidate | None:
    path = _store(run_id) / f"{candidate_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return ExternalActionCandidate(
        candidate_id=data["candidate_id"],
        run_id=data["run_id"],
        turn_id=data.get("turn_id"),
        artifact_ref=data.get("artifact_ref"),
        review_item_ref=data.get("review_item_ref"),
        provider_receipt_ref=data.get("provider_receipt_ref"),
        live_read_receipt_refs=tuple(data.get("live_read_receipt_refs") or ()),
        requested_platform=data["requested_platform"],
        requested_action_type=ExternalActionType(data["requested_action_type"]),
        requested_target_ref=data.get("requested_target_ref"),
        draft_content_ref=data.get("draft_content_ref"),
        content_hash=data["content_hash"],
        risk_class=data["risk_class"],
        scope=data["scope"],
        data_tier=data.get("data_tier", "internal"),
        created_at=data["created_at"],
        expires_at=data["expires_at"],
        status=CandidateStatus(data["status"]),
        hash=data.get("hash"),
    )


def update_candidate_status(run_id: str, candidate_id: str, status: CandidateStatus) -> None:
    cand = load_candidate(run_id, candidate_id)
    if not cand:
        return
    updated = ExternalActionCandidate(**{**cand.__dict__, "status": status}).with_hash()
    path = _store(run_id) / f"{candidate_id}.json"
    path.write_text(json.dumps(updated.to_payload(), indent=2) + "\n", encoding="utf-8")
