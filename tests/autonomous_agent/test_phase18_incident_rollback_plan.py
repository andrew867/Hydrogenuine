"""Phase 18 incident rollback plan tests."""
from __future__ import annotations

from hg_runtime.external_write_authority.incident_plan import create_incident_plan, find_incident_plan_for_scope


def test_incident_plan_required_fields():
    plan = create_incident_plan(
        scope_ref="scope-1",
        candidate_ref="cand-1",
        platform="moltbook",
        action_type="publish_post",
    )
    assert plan.rollback_method
    assert find_incident_plan_for_scope("scope-1") is not None
