"""CHRONO Agent Zero boot context — time sync + boot epoch lock."""

from __future__ import annotations

import time
from typing import Any

from hg_runtime.chrono.agent0 import AGENT0_TIME_INSTRUCTION, build_agent0_time_context
from hg_runtime.chrono.epoch import EpochConfidence
from hg_runtime.chrono.lock import CHRONO_LOCK_BOOT_INSTRUCTION, ChronoLock, ChronoLockOutcome, create_chrono_lock
from hg_runtime.chrono.receipts import ChronoReceipt, create_epoch_receipt
from hg_runtime.chrono.sync import ChronoConfig, SyncOutcome


def build_chrono_lock_boot_context(outcome: ChronoLockOutcome) -> dict[str, Any]:
    lock = outcome.lock
    return {
        "schema": "chrono-lock-context",
        "epoch_id": lock.epoch_id,
        "epoch_lock_id": lock.epoch_lock_id,
        "epoch_lock_id_short": lock.epoch_lock_id[:12],
        "agent_code_id": lock.agent_code_id,
        "system_utc_at_lock": lock.system_utc_at_lock,
        "ntp_utc_at_lock": lock.ntp_utc_at_lock,
        "ntp_host": lock.ntp_host,
        "ntp_offset_seconds": lock.ntp_offset_seconds,
        "monotonic_origin_ns": lock.monotonic_origin_ns,
        "time_confidence": lock.time_confidence.value,
        "time_uncertain": lock.time_uncertain,
        "boot_bundle_sha256": lock.boot_bundle_sha256,
        "external_anchor_commit_sha": lock.external_anchor_commit_sha,
        "external_anchor_verified": lock.external_anchor_verified,
        "source_quorum_status": lock.source_quorum_status,
        "drift_window_seconds": lock.drift_window_seconds,
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
        "time_instruction": AGENT0_TIME_INSTRUCTION,
        "lock_instruction": CHRONO_LOCK_BOOT_INSTRUCTION,
    }


def chrono_lock_on_wake(
    *,
    config: ChronoConfig | None = None,
    boot_bundle_sha256: str | None = None,
    external_anchor_commit_sha: str | None = None,
    external_anchor_verified: bool = False,
    agent_code_id: str = "agent0",
) -> tuple[dict[str, Any], dict[str, Any], ChronoReceipt, ChronoLockOutcome]:
    """Create boot epoch lock and Agent Zero contexts before boot."""
    outcome = create_chrono_lock(
        agent_code_id=agent_code_id,
        config=config,
        boot_bundle_sha256=boot_bundle_sha256,
        external_anchor_commit_sha=external_anchor_commit_sha,
        external_anchor_verified=external_anchor_verified,
    )
    time_ctx = build_agent0_time_context(outcome.sync_outcome)
    lock_ctx = build_chrono_lock_boot_context(outcome)
    receipt = create_epoch_receipt(
        outcome.sync_outcome.result,
        epoch_id=outcome.lock.epoch_id,
        epoch_lock_id=outcome.lock.epoch_lock_id,
        receipt_sequence=0,
    )
    return time_ctx.to_payload(), lock_ctx, receipt, outcome


def answer_chrono_lock_status_query(lock: ChronoLock | dict[str, Any]) -> str:
    if isinstance(lock, dict):
        conf = lock.get("time_confidence", "UNKNOWN")
        epoch_id = lock.get("epoch_id", "unknown")
        lock_short = (lock.get("epoch_lock_id") or lock.get("epoch_lock_id_short") or "")[:12]
        uncertain = lock.get("time_uncertain", True)
    else:
        conf = lock.time_confidence.value
        epoch_id = lock.epoch_id
        lock_short = lock.epoch_lock_id[:12]
        uncertain = lock.time_uncertain
    uncertain_note = " Time is uncertain." if uncertain else ""
    return (
        f"I am in boot epoch {epoch_id}. "
        f"My epoch lock ID is {lock_short}... "
        f"My time confidence is {conf}.{uncertain_note} "
        "I have a CHRONO lock for this boot epoch. "
        "My local monotonic clock, NTP sample, boot bundle hash, and external witness anchor "
        "are bound as continuity evidence. I treat this as continuity evidence, not authority. "
        "The lock does not grant permission."
    )


def monotonic_ns_since_lock(lock: ChronoLock) -> int:
    return time.monotonic_ns() - lock.monotonic_origin_ns


def next_receipt_sequence(previous: int) -> int:
    return previous + 1


__all__ = [
    "answer_chrono_lock_status_query",
    "build_chrono_lock_boot_context",
    "chrono_lock_on_wake",
    "monotonic_ns_since_lock",
    "next_receipt_sequence",
]
