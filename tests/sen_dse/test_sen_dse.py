"""Tests for SEN_DSE."""

from __future__ import annotations

from hg_runtime.durable_side_effect.sensor_sink import FIXTURE_CLOCK, load_sen_dse_fixtures, process_sen_dse_bundle


def test_valid_approved_durable_sink() -> None:
    bundle = next(b for b in load_sen_dse_fixtures() if b["bundle_id"] == "sen-dse-valid-fixture")
    result = process_sen_dse_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["durable_write_performed"] is True
    assert result["permission_granted"] is False


def test_missing_operator_approval_refusal() -> None:
    bundle = next(b for b in load_sen_dse_fixtures() if "missing-approval" in b["bundle_id"])
    result = process_sen_dse_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result.get("admission", {}).get("admitted") is False or result.get("status") == "refused"
