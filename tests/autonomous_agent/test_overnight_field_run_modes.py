"""Field run mode tests."""
from __future__ import annotations

from hg_runtime.overnight_field_run.field_run_config import build_default_field_run_config, build_smoke_config
from hg_runtime.overnight_field_run.schema import FieldRunMode, OvernightFieldRunVerdict


def test_infrastructure_smoke_cannot_claim_overnight_complete():
    c = build_smoke_config(field_run_id="m1", observed_turns=2)
    assert c.mode == FieldRunMode.INFRASTRUCTURE_SMOKE.value
    assert c.test_only_stop_after_observed_turns == 2
    assert OvernightFieldRunVerdict.GREEN_FIELD_RUN_COMPLETE.value != OvernightFieldRunVerdict.GREEN_INFRASTRUCTURE_READY.value


def test_operator_field_run_no_test_cap():
    c = build_default_field_run_config(field_run_id="op1", mode=FieldRunMode.OPERATOR_FIELD_RUN.value)
    assert c.test_only_stop_after_observed_turns is None
    assert c.fixed_turn_cap is None
