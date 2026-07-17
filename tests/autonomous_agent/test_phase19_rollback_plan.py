"""Phase 19 rollback plan tests."""
from __future__ import annotations

from hg_runtime.external_write_authority.action_ledger import Phase19Verdict
from hg_runtime.external_write_authority.rollback import RollbackAttempt, RollbackPlan, dry_run_rollback
from hg_runtime.external_write_authority.schema import new_id, now_iso


def test_rollback_plan_required_fields():
    plan = RollbackPlan(
        rollback_plan_id=new_id("rp"),
        ledger_entry_ref="led-1",
        platform="moltbook",
        action_type="publish_post",
        rollback_supported=True,
        rollback_method="platform_delete",
        created_at=now_iso(),
    ).with_hash()
    assert plan.rollback_supported is True
    assert plan.hash


def test_live_rollback_blocked_by_default():
    from hg_runtime.external_write_authority.rollback import ROLLBACK_DIR
    import json

    plan = RollbackPlan(
        rollback_plan_id="test-plan-dry",
        ledger_entry_ref="led-1",
        platform="moltbook",
        action_type="publish_post",
        rollback_supported=True,
        rollback_method="platform_delete",
        created_at=now_iso(),
    ).with_hash()
    ROLLBACK_DIR.mkdir(parents=True, exist_ok=True)
    (ROLLBACK_DIR / "test-plan-dry.json").write_text(json.dumps(plan.to_payload(), indent=2), encoding="utf-8")
    attempt = dry_run_rollback(rollback_plan_id="test-plan-dry")
    assert attempt is not None
    assert attempt.external_side_effect is False
    assert attempt.dry_run_only is True
    assert attempt.verdict == Phase19Verdict.YELLOW_ROLLBACK_DRY
