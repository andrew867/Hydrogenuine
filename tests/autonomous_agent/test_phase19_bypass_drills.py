"""Phase 19 bypass drill tests."""
from __future__ import annotations

from hg_runtime.external_write_authority.incident_audit import all_drills_passed, run_bypass_drills


def test_bypass_drills_run():
    drills = run_bypass_drills()
    assert len(drills) >= 4
    assert all_drills_passed(drills)


def test_review_not_approval_drill():
    drills = run_bypass_drills()
    review = next(d for d in drills if d.drill_name == "review_queue_not_approval")
    assert review.passed


def test_model_output_not_permission_drill():
    drills = run_bypass_drills()
    model = next(d for d in drills if d.drill_name == "model_output_not_permission")
    assert model.passed
