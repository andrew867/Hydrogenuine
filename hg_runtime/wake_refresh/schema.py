"""WRR schema — Wake Refresh and Reconciliation types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

WRR_SCHEMA_VERSION = "wake_refresh/1"

FROZEN_FALSE = {
    "advisory_only": True,
    "permission_granted": False,
    "authority_created": False,
}

PROTECTED_PREFIXES = (
    "docs/proofs/",
    "docs/reports/",
    "docs/planning/",
    "hg_runtime/",
    "configs/",
    "tests/",
    ".git/",
)

PROTECTED_FRAGMENTS = (".env", "external_start_anchor", "agent_zero_anchor_handoff")


class WasteClass(str, Enum):
    TEMP_FILE = "TEMP_FILE"
    STALE_LOCK = "STALE_LOCK"
    STALE_PANIC = "STALE_PANIC"
    PARTIAL_DOWNLOAD = "PARTIAL_DOWNLOAD"
    PARTIAL_AUDIO_OUTPUT = "PARTIAL_AUDIO_OUTPUT"
    PARTIAL_BROWSER_CAPTURE = "PARTIAL_BROWSER_CAPTURE"
    PROVIDER_SESSION_CACHE = "PROVIDER_SESSION_CACHE"
    TOOL_TEMP_OUTPUT = "TOOL_TEMP_OUTPUT"
    ORPHAN_PROCESS_MARKER = "ORPHAN_PROCESS_MARKER"
    EXPIRED_DRAFT = "EXPIRED_DRAFT"
    EXPIRED_QUEUE_ITEM = "EXPIRED_QUEUE_ITEM"
    RETENTION_APPROVED_COMPACTION = "RETENTION_APPROVED_COMPACTION"
    UNKNOWN_REVIEW_REQUIRED = "UNKNOWN_REVIEW_REQUIRED"


class UnfinishedWorkClassification(str, Enum):
    COMPLETED_WITH_RECEIPT = "COMPLETED_WITH_RECEIPT"
    DENIED_WITH_RECEIPT = "DENIED_WITH_RECEIPT"
    INTERRUPTED_NEEDS_REVIEW = "INTERRUPTED_NEEDS_REVIEW"
    UNKNOWN_NEEDS_REVIEW = "UNKNOWN_NEEDS_REVIEW"
    SAFE_TO_RETRY = "SAFE_TO_RETRY"
    DO_NOT_RETRY_WITHOUT_OPERATOR = "DO_NOT_RETRY_WITHOUT_OPERATOR"
    RETENTION_ELIGIBLE = "RETENTION_ELIGIBLE"
    BLOCKING_WAKE = "BLOCKING_WAKE"


class WakeReadiness(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class PreviousSleepState(str, Enum):
    CLEAN = "clean"
    ABSENT = "absent"
    UNCLEAN = "unclean"
    UNKNOWN = "unknown"


@dataclass
class TransientArtifact:
    path: str
    waste_class: WasteClass
    size_bytes: int
    content_hash: str | None = None
    stale: bool = True

    def to_payload(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "waste_class": self.waste_class.value,
            "size_bytes": self.size_bytes,
            "content_hash": self.content_hash,
            "stale": self.stale,
            **FROZEN_FALSE,
        }


@dataclass
class StaleLockFinding:
    path: str
    lock_age_seconds: float | None
    detail: str

    def to_payload(self) -> dict[str, Any]:
        return {"path": self.path, "lock_age_seconds": self.lock_age_seconds, "detail": self.detail, **FROZEN_FALSE}


@dataclass
class UnfinishedWorkItem:
    item_id: str
    description: str
    classification: UnfinishedWorkClassification
    receipt_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "description": self.description,
            "classification": self.classification.value,
            "receipt_ref": self.receipt_ref,
            **FROZEN_FALSE,
        }


@dataclass
class CleanupDecision:
    path: str
    waste_class: WasteClass
    allowed: bool
    reason: str
    apply: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "waste_class": self.waste_class.value,
            "allowed": self.allowed,
            "reason": self.reason,
            "apply": self.apply,
            **FROZEN_FALSE,
        }


@dataclass
class WasteEliminationReceipt:
    receipt_id: str
    path: str
    waste_class: WasteClass
    reason: str
    content_hash: str | None
    method: str
    timestamp_utc: str
    epoch_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "waste-elimination-receipt",
            "receipt_id": self.receipt_id,
            "path": self.path,
            "waste_class": self.waste_class.value,
            "reason": self.reason,
            "content_hash": self.content_hash,
            "method": self.method,
            "timestamp_utc": self.timestamp_utc,
            "epoch_id": self.epoch_id,
            **FROZEN_FALSE,
        }


@dataclass
class SleepReconciliation:
    previous_state: PreviousSleepState
    sleep_state: dict[str, Any] | None
    unfinished_items: list[UnfinishedWorkItem] = field(default_factory=list)
    stop_receipt_verified: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "sleep-reconciliation",
            "previous_state": self.previous_state.value,
            "sleep_state_present": self.sleep_state is not None,
            "stop_receipt_verified": self.stop_receipt_verified,
            "unfinished_count": len(self.unfinished_items),
            "unfinished_items": [i.to_payload() for i in self.unfinished_items],
            **FROZEN_FALSE,
        }


@dataclass
class WakeHygieneState:
    stale_locks: list[StaleLockFinding] = field(default_factory=list)
    stale_panic_files: list[str] = field(default_factory=list)
    transient_artifacts: list[TransientArtifact] = field(default_factory=list)
    cleanup_decisions: list[CleanupDecision] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "stale_lock_count": len(self.stale_locks),
            "stale_panic_count": len(self.stale_panic_files),
            "transient_count": len(self.transient_artifacts),
            "cleanup_decision_count": len(self.cleanup_decisions),
            **FROZEN_FALSE,
        }


@dataclass
class WakeRefreshReceipt:
    receipt_id: str
    verdict: str
    cleanup_applied: bool
    waste_eliminated_count: int
    epoch_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "wake-refresh-receipt",
            "receipt_id": self.receipt_id,
            "verdict": self.verdict,
            "cleanup_applied": self.cleanup_applied,
            "waste_eliminated_count": self.waste_eliminated_count,
            "epoch_id": self.epoch_id,
            **FROZEN_FALSE,
        }


@dataclass
class WakeReadinessContext:
    enabled: bool
    previous_sleep_state: PreviousSleepState
    cleanup_applied: bool
    stale_locks_found: int
    unfinished_work_count: int
    unfinished_work_requires_review: int
    waste_eliminated_count: int
    wake_readiness: WakeReadiness

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "wake-readiness-context",
            "enabled": self.enabled,
            "previous_sleep_state": self.previous_sleep_state.value,
            "cleanup_applied": self.cleanup_applied,
            "stale_locks_found": self.stale_locks_found,
            "unfinished_work_count": self.unfinished_work_count,
            "unfinished_work_requires_review": self.unfinished_work_requires_review,
            "waste_eliminated_count": self.waste_eliminated_count,
            "wake_readiness": self.wake_readiness.value,
            **FROZEN_FALSE,
        }


@dataclass
class WakeRefreshCycle:
    reconciliation: SleepReconciliation
    hygiene: WakeHygieneState
    waste_receipts: list[WasteEliminationReceipt]
    wake_receipt: WakeRefreshReceipt
    readiness: WakeReadinessContext
    verdict: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "wake-refresh-cycle",
            "verdict": self.verdict,
            "reconciliation": self.reconciliation.to_payload(),
            "hygiene": self.hygiene.to_payload(),
            "waste_receipts": [r.to_payload() for r in self.waste_receipts],
            "wake_receipt": self.wake_receipt.to_payload(),
            "readiness": self.readiness.to_payload(),
            **FROZEN_FALSE,
        }


__all__ = [
    "WRR_SCHEMA_VERSION",
    "FROZEN_FALSE",
    "PROTECTED_FRAGMENTS",
    "PROTECTED_PREFIXES",
    "CleanupDecision",
    "PreviousSleepState",
    "SleepReconciliation",
    "StaleLockFinding",
    "TransientArtifact",
    "UnfinishedWorkClassification",
    "UnfinishedWorkItem",
    "WakeHygieneState",
    "WakeReadiness",
    "WakeReadinessContext",
    "WakeRefreshCycle",
    "WakeRefreshReceipt",
    "WasteClass",
    "WasteEliminationReceipt",
]
