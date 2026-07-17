"""External write authority schemas."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash

WORKSPACE = Path(__file__).resolve().parents[2]
POLICY_PATH = WORKSPACE / "configs/agent_zero/external_write_authority_policy.json"
STORE_ROOT = WORKSPACE / ".hg-local/external_write_authority"


class ExternalActionType(str, Enum):
    PUBLISH_POST = "publish_post"
    SEND_MESSAGE = "send_message"
    REPLY = "reply"
    COMMENT = "comment"
    UPDATE_PROFILE = "update_profile"
    EXTERNAL_WEBHOOK = "external_webhook"


class CandidateStatus(str, Enum):
    CANDIDATE_CREATED = "candidate_created"
    AWAITING_AUTHORITY = "awaiting_authority"
    AUTHORITY_DENIED = "authority_denied"
    DRY_RUN_PLANNED = "dry_run_planned"
    DRY_RUN_COMPLETED = "dry_run_completed"
    EXPIRED = "expired"
    REVOKED = "revoked"
    INVALID = "invalid"


class PermitStatus(str, Enum):
    ISSUED = "issued"
    DENIED = "denied"
    EXPIRED = "expired"
    REVOKED = "revoked"


class PermitDenyReason(str, Enum):
    MISSING_CANDIDATE = "missing_candidate"
    STALE_CANDIDATE = "stale_candidate"
    EXPIRED_CANDIDATE = "expired_candidate"
    MISSING_CAPABILITY_DECISION = "missing_capability_decision"
    CAPABILITY_MISMATCH = "capability_mismatch"
    SCOPE_EXPANSION = "scope_expansion"
    PLATFORM_MISMATCH = "platform_mismatch"
    ACTION_MISMATCH = "action_mismatch"
    EXPIRED_PERMIT = "expired_permit"
    REVOKED_PERMIT = "revoked_permit"
    MISSING_OPERATOR_CONFIRMATION = "missing_operator_confirmation"
    STALE_CONFIRMATION = "stale_confirmation"
    CONTENT_HASH_MISMATCH = "content_hash_mismatch"
    APPROVE_ALL_PHRASE = "approve_all_phrase"
    REVIEW_NOT_APPROVAL = "review_not_approval"
    MODEL_OUTPUT_NOT_AUTHORITY = "model_output_not_authority"
    MISSING_PERMIT = "missing_permit"
    LIVE_DISPATCH_FORBIDDEN = "live_dispatch_forbidden"


class ExternalWriteAuthorityVerdict(str, Enum):
    GREEN_EXTERNAL_WRITE_AUTHORITY_BOUNDARY_COMPLETE = "GREEN_EXTERNAL_WRITE_AUTHORITY_BOUNDARY_COMPLETE"
    YELLOW_EXTERNAL_WRITE_DRY_RUN_ONLY = "YELLOW_EXTERNAL_WRITE_DRY_RUN_ONLY"
    RED_LIVE_DISPATCH_FORBIDDEN = "RED_LIVE_DISPATCH_FORBIDDEN"
    RED_MISSING_PERMIT = "RED_MISSING_PERMIT"
    RED_REVIEW_QUEUE_TREATED_AS_APPROVAL = "RED_REVIEW_QUEUE_TREATED_AS_APPROVAL"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def load_policy(*, path: Path | None = None) -> dict[str, Any]:
    p = path or POLICY_PATH
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def content_hash(content: str) -> str:
    return compute_record_hash({"content": content})
