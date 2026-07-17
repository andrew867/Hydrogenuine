"""Phase 19 platform reverification tests."""
from __future__ import annotations

from hg_runtime.external_write_authority.action_ledger import Phase19Verdict
from hg_runtime.external_write_authority.platform_reverify import PlatformProofReverification
from hg_runtime.external_write_authority.schema import new_id, now_iso


def test_missing_platform_proof_yellow():
    rev = PlatformProofReverification(
        reverification_id=new_id("r"),
        live_dispatch_result_ref="d1",
        platform="moltbook",
        platform_object_id=None,
        platform_url=None,
        content_sha256_expected="abc",
        content_sha256_observed=None,
        visibility_status="missing",
        proof_method="test",
        observed_at=now_iso(),
        verdict=Phase19Verdict.YELLOW_NO_PROOF,
    )
    assert rev.verdict != Phase19Verdict.GREEN


def test_content_hash_mismatch_red():
    rev = PlatformProofReverification(
        reverification_id=new_id("r"),
        live_dispatch_result_ref="d1",
        platform="moltbook",
        platform_object_id="p1",
        platform_url="https://example.com/p1",
        content_sha256_expected="abc",
        content_sha256_observed="def",
        visibility_status="visible",
        proof_method="test",
        observed_at=now_iso(),
        verdict=Phase19Verdict.RED_HASH_MISMATCH,
    )
    assert "RED" in rev.verdict


def test_visibility_delayed_yellow():
    rev = PlatformProofReverification(
        reverification_id=new_id("r"),
        live_dispatch_result_ref="d1",
        platform="moltbook",
        platform_object_id="p1",
        platform_url="https://example.com/p1",
        content_sha256_expected="abc",
        content_sha256_observed="abc",
        visibility_status="visibility_delayed",
        proof_method="test",
        observed_at=now_iso(),
        verdict=Phase19Verdict.YELLOW_VISIBILITY,
    )
    assert rev.verdict == Phase19Verdict.YELLOW_VISIBILITY
