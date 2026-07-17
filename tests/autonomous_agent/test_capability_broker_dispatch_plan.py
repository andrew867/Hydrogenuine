"""Dispatch plan tests."""
from __future__ import annotations
import sys
from pathlib import Path
WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))
from hg_runtime.capability_broker.dispatch_plan import DispatchVerdict, create_dispatch_plan

def test_dispatch_plan_never_executes():
    plan = create_dispatch_plan(decision_id="dec-1", action_id="observe_social", required_receipts=["live-1"])
    assert plan.execution_allowed is False
    assert plan.verdict == DispatchVerdict.GREEN_INTERNAL_DISPATCH_PLAN_CREATED

def test_dispatch_plan_has_execution_allowed_false():
    plan = create_dispatch_plan(decision_id="dec-2", action_id="synthesize_notes")
    assert plan.execution_allowed is False
    assert plan.external_side_effect is False
    assert plan.internal_only is True
