"""Identity continuity tests."""

from __future__ import annotations

from hg_runtime.agent_zero_self_mirror.identity_continuity import assess_identity_continuity
from hg_runtime.agent_zero_self_mirror.schema import ContinuityConfidence
from hg_runtime.agent_zero_self_mirror.self_model import build_self_snapshot


def test_identity_medium_without_anchor():
    snap = build_self_snapshot()
    snap.repo_head = "abc"
    finding = assess_identity_continuity(snap, chrono_lock={"epoch_lock_id": "lock123"})
    assert finding.continuity_confidence == ContinuityConfidence.MEDIUM


def test_identity_high_with_verified_anchor():
    snap = build_self_snapshot()
    snap.repo_head = "abc"
    finding = assess_identity_continuity(
        snap,
        chrono_lock={"epoch_lock_id": "lock123"},
        anchor_handoff={"verified_after_push": True, "verification_status": "verified", "boot_bundle_sha256": "x"},
    )
    assert finding.continuity_confidence == ContinuityConfidence.HIGH


def test_identity_low_repo_only():
    snap = build_self_snapshot()
    snap.repo_head = "abc"
    finding = assess_identity_continuity(snap)
    assert finding.continuity_confidence == ContinuityConfidence.LOW
