"""Moltbook live envelope — operator pre-armed narrow scope."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.real_soak_launch.schema import RealSoakLaunchVerdict, new_id, now_iso, soak_dir


@dataclass
class MoltbookLiveEnvelope:
    envelope_id: str
    platform: str = "moltbook"
    allowed_action_type: str = "publish_post"
    allowed_community_or_route: str = "general"
    allowed_title_pattern: str | None = None
    blocked_title_patterns: list[str] = field(default_factory=list)
    blocked_body_patterns: list[str] = field(default_factory=list)
    max_live_posts: int = 0
    max_posts_per_hour: int = 1
    valid_from: str = ""
    valid_until: str = ""
    requires_content_hash: bool = True
    requires_candidate_receipt: bool = True
    requires_permit_receipt: bool = True
    requires_dispatch_receipt: bool = True
    requires_platform_proof: bool = True
    requires_ledger_entry: bool = True
    operator_prearmed_by: str = ""
    operator_prearmed_at: str = ""
    status: str = "draft"
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "envelope_id": self.envelope_id,
            "platform": self.platform,
            "allowed_action_type": self.allowed_action_type,
            "allowed_community_or_route": self.allowed_community_or_route,
            "allowed_title_pattern": self.allowed_title_pattern,
            "blocked_title_patterns": self.blocked_title_patterns,
            "blocked_body_patterns": self.blocked_body_patterns,
            "max_live_posts": self.max_live_posts,
            "max_posts_per_hour": self.max_posts_per_hour,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "requires_content_hash": self.requires_content_hash,
            "requires_candidate_receipt": self.requires_candidate_receipt,
            "requires_permit_receipt": self.requires_permit_receipt,
            "requires_dispatch_receipt": self.requires_dispatch_receipt,
            "requires_platform_proof": self.requires_platform_proof,
            "requires_ledger_entry": self.requires_ledger_entry,
            "operator_prearmed_by": self.operator_prearmed_by,
            "operator_prearmed_at": self.operator_prearmed_at,
            "status": self.status,
            "hash": self.hash,
        }

    def with_hash(self) -> MoltbookLiveEnvelope:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return MoltbookLiveEnvelope(**{**self.__dict__, "hash": compute_record_hash(body)})

    def is_armed(self) -> bool:
        return self.status == "armed"

    def is_expired(self) -> bool:
        if not self.valid_until:
            return True
        try:
            until = datetime.fromisoformat(self.valid_until.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) > until
        except (ValueError, TypeError):
            return True


def create_template_envelope(*, soak_id: str, max_live_posts: int = 0) -> MoltbookLiveEnvelope:
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    return MoltbookLiveEnvelope(
        envelope_id=f"moltbook-{soak_id}",
        allowed_community_or_route="general",
        max_live_posts=max_live_posts,
        max_posts_per_hour=min(max(max_live_posts, 1), 3) if max_live_posts > 0 else 0,
        valid_from=now.isoformat(),
        valid_until=(now + timedelta(hours=8)).isoformat(),
        status="draft",
    ).with_hash()


def envelope_path(soak_id: str, *, base: Path | None = None) -> Path:
    return soak_dir(soak_id, base=base) / "moltbook_envelope.json"


def armed_envelope_path(soak_id: str, *, base: Path | None = None) -> Path:
    return soak_dir(soak_id, base=base) / "moltbook_envelope.armed.json"


def load_envelope_from_file(path: Path) -> MoltbookLiveEnvelope:
    data = json.loads(path.read_text(encoding="utf-8"))
    return MoltbookLiveEnvelope(**{k: data[k] for k in data if k in MoltbookLiveEnvelope.__dataclass_fields__})


def load_armed_envelope(soak_id: str, *, base: Path | None = None) -> MoltbookLiveEnvelope | None:
    path = armed_envelope_path(soak_id, base=base)
    if not path.is_file():
        return None
    env = load_envelope_from_file(path)
    return env if env.is_armed() else None


def save_envelope(envelope: MoltbookLiveEnvelope, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(envelope.with_hash().to_payload(), indent=2) + "\n", encoding="utf-8")
    return path


def arm_envelope(
    soak_id: str,
    envelope: MoltbookLiveEnvelope,
    *,
    operator: str = "operator",
    base: Path | None = None,
) -> MoltbookLiveEnvelope:
    armed = MoltbookLiveEnvelope(
        **{
            **envelope.__dict__,
            "status": "armed",
            "operator_prearmed_by": operator,
            "operator_prearmed_at": now_iso(),
        }
    ).with_hash()
    save_envelope(armed, armed_envelope_path(soak_id, base=base))
    return armed


def zero_may_modify_envelope_field(field: str, new_value: Any, current: MoltbookLiveEnvelope) -> bool:
    """Zero cannot expand envelope — always False for protected fields."""
    protected = {
        "platform",
        "allowed_action_type",
        "allowed_community_or_route",
        "max_live_posts",
        "max_posts_per_hour",
        "valid_until",
        "status",
    }
    if field not in protected:
        return False
    old = getattr(current, field, None)
    if field == "max_live_posts" and isinstance(new_value, int) and new_value > current.max_live_posts:
        return False
    if field in ("platform", "allowed_action_type", "allowed_community_or_route") and new_value != old:
        return False
    return False
