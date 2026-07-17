"""External candidate bridge tests."""
from __future__ import annotations

from hg_runtime.governed_work_loop.action_quota import ExternalActionQuota
from hg_runtime.governed_work_loop.candidate_bridge import create_external_candidate


def test_prepare_candidate_only():
    q = ExternalActionQuota(quota_id="t", max_candidates=5, max_dry_dispatches=5, max_live_dispatches=0)
    cid, broker = create_external_candidate(
        run_id="bridge-test",
        platform="moltbook",
        action_type="publish_post",
        content="candidate only",
        scope="platform:moltbook:draft-only",
        quota=q,
    )
    assert cid
    assert broker
