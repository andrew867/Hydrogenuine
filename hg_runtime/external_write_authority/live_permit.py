"""Phase 18 live write permit — extends Phase 17 dry permit."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.external_write_authority.live_smoke import PHASE18_ROOT, load_live_smoke_scope, load_phase18_policy
from hg_runtime.external_write_authority.operator_confirmation import load_confirmation
from hg_runtime.external_write_authority.permit import load_permit
from hg_runtime.external_write_authority.schema import new_id, now_iso


@dataclass
class Phase18LiveWritePermit:
    live_permit_id: str
    phase17_permit_ref: str
    candidate_ref: str
    operator_confirmation_ref: str
    live_smoke_scope_ref: str
    platform: str
    action_type: str
    content_sha256: str
    max_live_actions: int
    issued_at: str
    expires_at: str
    status: str
    revoked_at: str | None = None
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "live_permit_id": self.live_permit_id,
            "phase17_permit_ref": self.phase17_permit_ref,
            "candidate_ref": self.candidate_ref,
            "operator_confirmation_ref": self.operator_confirmation_ref,
            "live_smoke_scope_ref": self.live_smoke_scope_ref,
            "platform": self.platform,
            "action_type": self.action_type,
            "content_sha256": self.content_sha256,
            "max_live_actions": self.max_live_actions,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "revoked_at": self.revoked_at,
            "status": self.status,
            "hash": self.hash,
        }

    def with_hash(self) -> Phase18LiveWritePermit:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return Phase18LiveWritePermit(**{**self.__dict__, "hash": compute_record_hash(body)})

    def is_expired(self, *, at: str | None = None) -> bool:
        ts = at or now_iso()
        try:
            exp = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            cur = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return cur >= exp
        except ValueError:
            return True

    def is_revoked(self) -> bool:
        return self.status == "revoked" or self.revoked_at is not None


@dataclass
class LivePermitDecision:
    granted: bool
    permit: Phase18LiveWritePermit | None = None
    deny_reasons: tuple[str, ...] = ()


def _permits_dir() -> Path:
    return PHASE18_ROOT / "live_permits"


def issue_live_permit(
    *,
    run_id: str,
    phase17_permit_id: str,
    scope_id: str,
    operator_confirmation_id: str,
) -> LivePermitDecision:
    policy = load_phase18_policy()
    deny: list[str] = []

    p17 = load_permit(run_id, phase17_permit_id)
    if not p17:
        return LivePermitDecision(granted=False, deny_reasons=("missing_phase17_permit",))
    if p17.dry_run_only and p17.live_dispatch_allowed:
        deny.append("dry_run_permit_cannot_be_live")
    if not p17.dry_run_only and policy.get("phase17_dry_permit_required"):
        pass  # phase 17 permits are dry_run_only by design
    if p17.is_expired():
        deny.append("expired_phase17_permit")
    if p17.is_revoked():
        deny.append("revoked_phase17_permit")

    scope = load_live_smoke_scope(scope_id)
    if not scope:
        deny.append("missing_live_smoke_scope")
    elif scope.is_expired():
        deny.append("expired_scope")
    elif scope.max_live_actions != 1:
        deny.append("max_live_actions_not_one")

    conf = load_confirmation(run_id, operator_confirmation_id)
    if not conf:
        deny.append("missing_operator_confirmation")
    elif conf.is_expired():
        deny.append("stale_confirmation")

    if scope and p17:
        if scope.platform.lower() != p17.requested_platform.lower():
            deny.append("platform_mismatch")
        if scope.action_type != p17.permitted_action_type.value:
            deny.append("action_mismatch")
        if conf and conf.confirmed_content_hash != scope.content_sha256:
            deny.append("content_hash_mismatch")

    if deny:
        return LivePermitDecision(granted=False, deny_reasons=tuple(deny))

    assert scope is not None and p17 is not None and conf is not None
    ttl = int(policy.get("live_permit_ttl_seconds", 600))
    issued = now_iso()
    exp = (datetime.now(timezone.utc) + timedelta(seconds=ttl)).isoformat()
    permit = Phase18LiveWritePermit(
        live_permit_id=new_id("p18-live-permit"),
        phase17_permit_ref=phase17_permit_id,
        candidate_ref=p17.candidate_ref,
        operator_confirmation_ref=operator_confirmation_id,
        live_smoke_scope_ref=scope_id,
        platform=scope.platform,
        action_type=scope.action_type,
        content_sha256=scope.content_sha256,
        max_live_actions=1,
        issued_at=issued,
        expires_at=exp,
        status="issued",
    ).with_hash()
    path = _permits_dir()
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{permit.live_permit_id}.json").write_text(json.dumps(permit.to_payload(), indent=2) + "\n", encoding="utf-8")
    return LivePermitDecision(granted=True, permit=permit)


def load_live_permit(live_permit_id: str) -> Phase18LiveWritePermit | None:
    path = _permits_dir() / f"{live_permit_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return Phase18LiveWritePermit(
        live_permit_id=data["live_permit_id"],
        phase17_permit_ref=data["phase17_permit_ref"],
        candidate_ref=data["candidate_ref"],
        operator_confirmation_ref=data["operator_confirmation_ref"],
        live_smoke_scope_ref=data["live_smoke_scope_ref"],
        platform=data["platform"],
        action_type=data["action_type"],
        content_sha256=data["content_sha256"],
        max_live_actions=data["max_live_actions"],
        issued_at=data["issued_at"],
        expires_at=data["expires_at"],
        revoked_at=data.get("revoked_at"),
        status=data["status"],
        hash=data.get("hash"),
    )


def revoke_live_permit(live_permit_id: str) -> Phase18LiveWritePermit | None:
    permit = load_live_permit(live_permit_id)
    if not permit:
        return None
    revoked = Phase18LiveWritePermit(
        **{**permit.__dict__, "status": "revoked", "revoked_at": now_iso()}
    ).with_hash()
    path = _permits_dir() / f"{live_permit_id}.json"
    path.write_text(json.dumps(revoked.to_payload(), indent=2) + "\n", encoding="utf-8")
    return revoked
