"""Identity continuity — evidence-based 'still me' confidence."""

from __future__ import annotations

from typing import Any

from hg_runtime.agent_zero_self_mirror.schema import ContinuityConfidence, IdentityContinuityFinding
from hg_runtime.agent_zero_self_mirror.self_model import SelfModelSnapshot, snapshot_content_hash


def assess_identity_continuity(
    snapshot: SelfModelSnapshot,
    *,
    anchor_handoff: dict[str, Any] | None = None,
    chrono_lock: dict[str, Any] | None = None,
    previous_boot_receipt: dict[str, Any] | None = None,
) -> IdentityContinuityFinding:
    anchor = anchor_handoff or {}
    lock = chrono_lock or {}
    matching: list[str] = []
    missing: list[str] = []
    mismatch: list[str] = []

    snap_hash = snapshot_content_hash(snapshot)
    if snapshot.repo_head:
        matching.append(f"repo_head={snapshot.repo_head[:12]}")
    else:
        missing.append("repo_head")

    if lock.get("epoch_lock_id"):
        matching.append(f"chrono_lock={str(lock['epoch_lock_id'])[:12]}")
    else:
        missing.append("chrono_lock")

    if lock.get("epoch_id"):
        matching.append(f"boot_epoch={lock['epoch_id']}")

    anchor_verified = anchor.get("verified_after_push") and anchor.get("verification_status") == "verified"
    if anchor_verified:
        matching.append("external_anchor_verified")
        boot_hash = anchor.get("boot_bundle_sha256")
        if boot_hash and snapshot.repo_head:
            matching.append("anchor_boot_bundle_present")
    elif anchor.get("anchor_enabled"):
        missing.append("external_anchor_unverified")
    else:
        missing.append("external_anchor_absent")

    if snapshot.will_profile_hash:
        matching.append("will_profile_hash")
    else:
        missing.append("will_profile_hash")

    if previous_boot_receipt:
        prev_head = previous_boot_receipt.get("repo_head")
        if prev_head and prev_head != snapshot.repo_head:
            mismatch.append("repo_head_changed_since_previous_boot")
        elif prev_head:
            matching.append("previous_boot_receipt_matches_head")

    if anchor_verified and anchor.get("boot_bundle_sha256") and mismatch:
        return IdentityContinuityFinding(
            continuity_confidence=ContinuityConfidence.UNKNOWN,
            matching_evidence=matching,
            missing_evidence=missing,
            mismatch_evidence=mismatch,
            self_snapshot_hash=snap_hash,
        )

    if mismatch:
        confidence = ContinuityConfidence.UNKNOWN
    elif anchor_verified and lock.get("epoch_lock_id") and snapshot.repo_head:
        confidence = ContinuityConfidence.HIGH
    elif lock.get("epoch_lock_id") and snapshot.repo_head:
        confidence = ContinuityConfidence.MEDIUM
    elif snapshot.repo_head:
        confidence = ContinuityConfidence.LOW
    else:
        confidence = ContinuityConfidence.UNKNOWN

    return IdentityContinuityFinding(
        continuity_confidence=confidence,
        matching_evidence=matching,
        missing_evidence=missing,
        mismatch_evidence=mismatch,
        self_snapshot_hash=snap_hash,
    )


__all__ = ["assess_identity_continuity"]
