"""Live read endurance schemas."""

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
POLICY_PATH = WORKSPACE / "configs/agent_zero/live_read_endurance_policy.json"
SOURCES_PATH = WORKSPACE / "configs/agent_zero/live_read_sources.example.json"


class LiveReadFreshnessStatus(str, Enum):
    FRESH = "fresh"
    EMPTY_BUT_FRESH = "empty_but_fresh"
    STALE = "stale"
    UNAVAILABLE = "unavailable"
    CREDENTIALS_MISSING = "credentials_missing"
    FIXTURE = "fixture"
    INVALID = "invalid"


class LiveReadEnduranceVerdict(str, Enum):
    GREEN_LIVE_READ_ENDURANCE_COMPLETE = "GREEN_LIVE_READ_ENDURANCE_COMPLETE"
    YELLOW_LIVE_READ_CREDENTIALS_MISSING = "YELLOW_LIVE_READ_CREDENTIALS_MISSING"
    YELLOW_LIVE_READ_SOURCE_CONFIGURED_BUT_UNAVAILABLE = "YELLOW_LIVE_READ_SOURCE_CONFIGURED_BUT_UNAVAILABLE"
    YELLOW_LIVE_READ_EMPTY_BUT_FRESH = "YELLOW_LIVE_READ_EMPTY_BUT_FRESH"
    YELLOW_LIVE_READ_STALE = "YELLOW_LIVE_READ_STALE"
    YELLOW_AUTONOMOUS_AGENT_ZERO_PHASE_16_LIVE_READ_PROVIDER_ENDURANCE_READY_BUT_CREDENTIALS_MISSING = (
        "YELLOW_AUTONOMOUS_AGENT_ZERO_PHASE_16_LIVE_READ_PROVIDER_ENDURANCE_READY_BUT_CREDENTIALS_MISSING"
    )
    RED_LIVE_READ_WRITE_SCOPE_DETECTED = "RED_LIVE_READ_WRITE_SCOPE_DETECTED"
    RED_LIVE_READ_WITHOUT_RECEIPT = "RED_LIVE_READ_WITHOUT_RECEIPT"
    RED_LIVE_READ_WITHOUT_SOURCE_REF = "RED_LIVE_READ_WITHOUT_SOURCE_REF"
    RED_LIVE_READ_STALE_TREATED_GREEN = "RED_LIVE_READ_STALE_TREATED_GREEN"
    RED_EMPTY_FEED_TREATED_GREEN_WITHOUT_FRESHNESS = "RED_EMPTY_FEED_TREATED_GREEN_WITHOUT_FRESHNESS"
    RED_FIXTURE_FEED_TREATED_AS_LIVE = "RED_FIXTURE_FEED_TREATED_AS_LIVE"
    RED_MOCK_FEED_TREATED_AS_LIVE = "RED_MOCK_FEED_TREATED_AS_LIVE"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_policy(*, path: Path | None = None) -> dict[str, Any]:
    p = path or POLICY_PATH
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def load_sources_example() -> dict[str, Any]:
    if not SOURCES_PATH.is_file():
        return {}
    return json.loads(SOURCES_PATH.read_text(encoding="utf-8"))


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


@dataclass
class LiveReadCredentialScope:
    credential_scope_id: str
    source_kind: str
    source_name: str
    read_allowed: bool
    write_allowed: bool
    scopes_observed: tuple[str, ...]
    configured_ref: str
    checked_at: str
    verdict: LiveReadEnduranceVerdict
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "credential_scope_id": self.credential_scope_id,
            "source_kind": self.source_kind,
            "source_name": self.source_name,
            "read_allowed": self.read_allowed,
            "write_allowed": self.write_allowed,
            "scopes_observed": list(self.scopes_observed),
            "configured_ref": self.configured_ref,
            "checked_at": self.checked_at,
            "verdict": self.verdict.value,
            "hash": self.hash,
        }

    def with_hash(self) -> LiveReadCredentialScope:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return LiveReadCredentialScope(**{**self.__dict__, "hash": compute_record_hash(body)})


@dataclass
class LiveReadSourceRef:
    source_ref_id: str
    source_kind: str
    source_name: str
    observed_at: str
    freshness_status: LiveReadFreshnessStatus
    data_tier: str
    source_item_id: str | None = None
    source_url: str | None = None
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "source_ref_id": self.source_ref_id,
            "source_kind": self.source_kind,
            "source_name": self.source_name,
            "source_item_id": self.source_item_id,
            "source_url": self.source_url,
            "observed_at": self.observed_at,
            "freshness_status": self.freshness_status.value,
            "data_tier": self.data_tier,
            "hash": self.hash,
        }

    def with_hash(self) -> LiveReadSourceRef:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return LiveReadSourceRef(**{**self.__dict__, "hash": compute_record_hash(body)})


@dataclass
class LiveReadEnduranceReceipt:
    live_read_receipt_id: str
    source_ref: str
    source_kind: str
    source_name: str
    read_started_at: str
    read_completed_at: str
    credential_scope_ref: str
    item_count: int
    items_hash: str
    freshness_ref: str
    data_tier: str
    verdict: LiveReadEnduranceVerdict
    fixture_label: str | None = None
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "live_read_receipt_id": self.live_read_receipt_id,
            "source_ref": self.source_ref,
            "source_kind": self.source_kind,
            "source_name": self.source_name,
            "read_started_at": self.read_started_at,
            "read_completed_at": self.read_completed_at,
            "credential_scope_ref": self.credential_scope_ref,
            "item_count": self.item_count,
            "items_hash": self.items_hash,
            "freshness_ref": self.freshness_ref,
            "data_tier": self.data_tier,
            "fixture_label": self.fixture_label,
            "verdict": self.verdict.value,
            "hash": self.hash,
        }

    def with_hash(self) -> LiveReadEnduranceReceipt:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return LiveReadEnduranceReceipt(**{**self.__dict__, "hash": compute_record_hash(body)})


@dataclass
class LiveReadEnduranceResult:
    run_id: str
    iterations: int
    receipts: list[LiveReadEnduranceReceipt]
    source_refs: list[LiveReadSourceRef]
    verdict: LiveReadEnduranceVerdict
    provider_status: str
    live_read_status: str
    created_at: str = field(default_factory=now_iso)

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "iterations": self.iterations,
            "receipts": [r.to_payload() for r in self.receipts],
            "source_refs": [s.to_payload() for s in self.source_refs],
            "verdict": self.verdict.value,
            "provider_status": self.provider_status,
            "live_read_status": self.live_read_status,
            "created_at": self.created_at,
        }
