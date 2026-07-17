from __future__ import annotations

from hg_runtime.bounded_soak.supervisor import SupervisorConfig, run_soak
from hg_runtime.bounded_soak.schema import BoundedSoakProfile
from hg_runtime.social_capability.schema import SocialPublishDecision


def test_dry_run_soak_queues_draft_no_live_post():
    profile = BoundedSoakProfile(
        profile_id="dry", duration_minutes=15, allow_live_social_read=False,
        allow_live_social_publish=False, max_posts=0, operator_approval_required=True, tool_dry_run=True,
    )
    receipt = run_soak(SupervisorConfig(profile=profile))
    social_results = [r for r in receipt.task_results if r.kind == "queue_social_post"]
    assert social_results
    assert not any("PUBLISHED" in r.detail and "live" in r.detail.lower() for r in social_results)
