"""Phase 18 live smoke scope — max one live action."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.external_write_authority.schema import STORE_ROOT, new_id, now_iso

PHASE18_ROOT = STORE_ROOT / "phase18"
POLICY_PATH = Path(__file__).resolve().parents[2] / "configs/agent_zero/phase18_live_smoke_policy.json"


class Phase18Verdict:
    GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_18_OPERATOR_APPROVED_LIVE_SMOKE_COMPLETE"
    YELLOW_READY = "YELLOW_AUTONOMOUS_AGENT_ZERO_PHASE_18_READY_FOR_OPERATOR_LIVE_SCOPE"
    YELLOW_CREDS = "YELLOW_PLATFORM_WRITE_CREDENTIALS_MISSING"
    YELLOW_SCOPE = "YELLOW_OPERATOR_LIVE_SCOPE_NOT_PROVIDED"
    YELLOW_VISIBILITY = "YELLOW_PLATFORM_VISIBILITY_DELAYED"


def load_phase18_policy() -> dict[str, Any]:
    if not POLICY_PATH.is_file():
        return {}
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def phase18_env_configured() -> dict[str, Any]:
    return {
        "allow_live_smoke": os.environ.get("HG_PHASE18_ALLOW_LIVE_SMOKE", "").lower() in ("1", "true", "yes"),
        "operator_confirmed": os.environ.get("HG_PHASE18_OPERATOR_CONFIRMED", "").lower() in ("1", "true", "yes"),
        "platform": os.environ.get("HG_PHASE18_PLATFORM", "").strip(),
        "action_type": os.environ.get("HG_PHASE18_ACTION_TYPE", "").strip(),
        "content_file": os.environ.get("HG_PHASE18_CONTENT_FILE", "").strip(),
        "expected_content_sha256": os.environ.get("HG_PHASE18_EXPECTED_CONTENT_SHA256", "").strip(),
        "live_writes_enabled": os.environ.get("HG_ENABLE_LIVE_SOCIAL_WRITES", "").lower() in ("1", "true", "yes"),
    }


def stop_panic_active() -> bool:
    return os.environ.get("HG_STOP_ACTIVE", "").lower() in ("1", "true", "yes") or os.environ.get(
        "HG_PANIC_ACTIVE", ""
    ).lower() in ("1", "true", "yes")


@dataclass
class Phase18LiveSmokeScope:
    scope_id: str
    operator_ref: str
    platform: str
    action_type: str
    content_file_ref: str
    content_sha256: str
    max_live_actions: int
    credential_scope_ref: str
    created_at: str
    expires_at: str
    status: str
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "scope_id": self.scope_id,
            "operator_ref": self.operator_ref,
            "platform": self.platform,
            "action_type": self.action_type,
            "content_file_ref": self.content_file_ref,
            "content_sha256": self.content_sha256,
            "max_live_actions": self.max_live_actions,
            "credential_scope_ref": self.credential_scope_ref,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status,
            "hash": self.hash,
        }

    def with_hash(self) -> Phase18LiveSmokeScope:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return Phase18LiveSmokeScope(**{**self.__dict__, "hash": compute_record_hash(body)})

    def is_expired(self, *, at: str | None = None) -> bool:
        ts = at or now_iso()
        try:
            exp = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            cur = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return cur >= exp
        except ValueError:
            return True


def _scopes_dir() -> Path:
    return PHASE18_ROOT / "scopes"


def create_live_smoke_scope(
    *,
    operator_ref: str,
    platform: str,
    action_type: str,
    content_file: Path,
    credential_scope_ref: str = "operator-local-social",
) -> Phase18LiveSmokeScope | None:
    policy = load_phase18_policy()
    env = phase18_env_configured()
    if not env["allow_live_smoke"] or not env["operator_confirmed"]:
        return None
    if not content_file.is_file():
        return None
    sha = file_sha256(content_file)
    if env["expected_content_sha256"] and sha != env["expected_content_sha256"]:
        return None
    if env["platform"] and platform != env["platform"]:
        return None
    if env["action_type"] and action_type != env["action_type"]:
        return None
    max_actions = int(policy.get("max_live_actions", 1))
    if max_actions != 1:
        return None
    ttl = int(policy.get("scope_ttl_seconds", 3600))
    created = now_iso()
    exp = (datetime.now(timezone.utc) + timedelta(seconds=ttl)).isoformat()
    scope = Phase18LiveSmokeScope(
        scope_id=new_id("p18-scope"),
        operator_ref=operator_ref,
        platform=platform,
        action_type=action_type,
        content_file_ref=str(content_file),
        content_sha256=sha,
        max_live_actions=1,
        credential_scope_ref=credential_scope_ref,
        created_at=created,
        expires_at=exp,
        status="active",
    ).with_hash()
    path = _scopes_dir()
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{scope.scope_id}.json").write_text(json.dumps(scope.to_payload(), indent=2) + "\n", encoding="utf-8")
    return scope


def load_live_smoke_scope(scope_id: str) -> Phase18LiveSmokeScope | None:
    path = _scopes_dir() / f"{scope_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return Phase18LiveSmokeScope(
        scope_id=data["scope_id"],
        operator_ref=data["operator_ref"],
        platform=data["platform"],
        action_type=data["action_type"],
        content_file_ref=data["content_file_ref"],
        content_sha256=data["content_sha256"],
        max_live_actions=data["max_live_actions"],
        credential_scope_ref=data["credential_scope_ref"],
        created_at=data["created_at"],
        expires_at=data["expires_at"],
        status=data["status"],
        hash=data.get("hash"),
    )


def get_live_dispatch_count() -> int:
    counter = PHASE18_ROOT / "live_dispatch_count.json"
    if not counter.is_file():
        return 0
    return int(json.loads(counter.read_text(encoding="utf-8")).get("count", 0))


def increment_live_dispatch_count() -> int:
    PHASE18_ROOT.mkdir(parents=True, exist_ok=True)
    count = get_live_dispatch_count() + 1
    (PHASE18_ROOT / "live_dispatch_count.json").write_text(json.dumps({"count": count}) + "\n", encoding="utf-8")
    return count


def reset_live_dispatch_count() -> None:
    counter = PHASE18_ROOT / "live_dispatch_count.json"
    if counter.is_file():
        counter.unlink()
