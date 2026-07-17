"""External action candidate tests."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from hg_runtime.external_write_authority.action_candidate import create_candidate, load_candidate
from hg_runtime.external_write_authority.schema import CandidateStatus


def test_candidate_hash_deterministic():
    c1 = create_candidate(
        run_id="test-hash",
        platform="moltbook",
        action_type="publish_post",
        content="hello",
        scope="platform:moltbook:draft-only",
        ttl_seconds=3600,
    )
    c2 = load_candidate("test-hash", c1.candidate_id)
    assert c2 is not None
    assert c2.hash == c1.hash


def test_candidate_requires_platform_action_scope():
    try:
        create_candidate(run_id="x", platform="", action_type="publish_post", content="a", scope="s")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_candidate_expires():
    c = create_candidate(
        run_id="test-expire",
        platform="moltbook",
        action_type="publish_post",
        content="x",
        scope="platform:moltbook:draft-only",
        ttl_seconds=1,
    )
    future = (datetime.now(timezone.utc) + timedelta(seconds=10)).isoformat()
    assert c.is_expired(at=future)


def test_candidate_is_not_permission():
    c = create_candidate(
        run_id="test-not-perm",
        platform="moltbook",
        action_type="publish_post",
        content="draft",
        scope="platform:moltbook:draft-only",
    )
    assert c.status == CandidateStatus.CANDIDATE_CREATED
    assert "permission" not in c.status.value
