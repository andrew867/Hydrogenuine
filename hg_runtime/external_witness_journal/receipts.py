"""Witness journal receipts."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from hg_runtime.external_witness_journal.schema import FROZEN_FALSE, WitnessAppendDecision


def new_id(prefix: str = "ewj") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


@dataclass
class AnchorWriterReceipt:
    receipt_id: str
    run_id: str
    event_class: str
    event_sequence: int
    journal_event_sha256: str
    decision: WitnessAppendDecision
    pushed: bool
    dry_run: bool
    github_commit_sha: str | None = None
    queue_path: str | None = None
    created_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    advisory_only: bool = True
    permission_granted: bool = False
    authority_created: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "anchor-writer-receipt",
            "receipt_id": self.receipt_id,
            "run_id": self.run_id,
            "event_class": self.event_class,
            "event_sequence": self.event_sequence,
            "journal_event_sha256": self.journal_event_sha256,
            "decision": self.decision.value,
            "pushed": self.pushed,
            "dry_run": self.dry_run,
            "github_commit_sha": self.github_commit_sha,
            "queue_path": self.queue_path,
            "created_utc": self.created_utc,
            **FROZEN_FALSE,
        }


@dataclass
class WitnessJournalVerificationReceipt:
    receipt_id: str
    chain_verified: bool
    event_count: int
    latest_sequence: int
    failures: list[str] = field(default_factory=list)
    created_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "witness-journal-verification-receipt",
            "receipt_id": self.receipt_id,
            "chain_verified": self.chain_verified,
            "event_count": self.event_count,
            "latest_sequence": self.latest_sequence,
            "failures": self.failures,
            "created_utc": self.created_utc,
            **FROZEN_FALSE,
        }


__all__ = ["AnchorWriterReceipt", "WitnessJournalVerificationReceipt", "new_id"]
