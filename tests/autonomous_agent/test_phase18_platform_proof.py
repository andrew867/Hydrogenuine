"""Phase 18 platform proof tests."""
from __future__ import annotations

from hg_runtime.external_write_authority.live_smoke import Phase18Verdict
from hg_runtime.external_write_authority.platform_proof import (
    Phase18LiveDispatchResult,
    PlatformVisibilityProof,
    verify_platform_proof,
)
from hg_runtime.external_write_authority.schema import new_id, now_iso


def test_platform_proof_required_for_green():
    result = Phase18LiveDispatchResult(
        live_dispatch_result_id=new_id("p18-test"),
        live_permit_ref="lp",
        platform="moltbook",
        action_type="publish_post",
        content_sha256="abc",
        external_side_effect=True,
        platform_object_id="post-1",
        platform_url="https://www.moltbook.com/post/post-1",
        visibility_status="published",
        dispatched_at=now_iso(),
        verdict=Phase18Verdict.GREEN,
    )
    assert result.platform_url
    assert result.platform_object_id


def test_missing_platform_url_blocks_green():
    result = Phase18LiveDispatchResult(
        live_dispatch_result_id=new_id("p18-test2"),
        live_permit_ref="lp",
        platform="moltbook",
        action_type="publish_post",
        content_sha256="abc",
        external_side_effect=True,
        dispatched_at=now_iso(),
        verdict=Phase18Verdict.YELLOW_VISIBILITY,
    )
    assert not result.platform_url


def test_visibility_delayed_yellow():
    proof = PlatformVisibilityProof(
        platform_proof_id=new_id("proof"),
        live_dispatch_result_ref="r1",
        platform="moltbook",
        platform_object_id="p1",
        platform_url="https://example.com/p1",
        observed_at=now_iso(),
        visibility_status="visibility_delayed",
        proof_method="api_readback",
        verdict=Phase18Verdict.YELLOW_VISIBILITY,
    )
    assert proof.verdict == Phase18Verdict.YELLOW_VISIBILITY
