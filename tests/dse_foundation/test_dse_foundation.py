"""Tests for DSE-FOUNDATION."""

from __future__ import annotations

from hg_core.dse.admission import AdmissionRequest, evaluate_sink_admission
from hg_core.dse.policy import RealSinkPolicy, SinkClass
from hg_runtime.durable_side_effect.foundation import (
    FIXTURE_CLOCK,
    FUTURE_EXPIRY,
    load_foundation_fixtures,
    process_foundation_bundle,
)


def test_all_sink_classes_in_foundation_scope() -> None:
    for sink_class in SinkClass:
        policy = RealSinkPolicy(sink_class=sink_class, tranche_id="DSE-FOUNDATION")
        assert policy.is_in_scope()


def test_valid_approved_durable_sink() -> None:
    bundle = next(b for b in load_foundation_fixtures() if b["bundle_id"] == "dse-valid-file-sink")
    result = process_foundation_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["durable_write_performed"] is True
    assert result["permission_granted"] is False
    assert result["receipt"]["receipt_hash"]


def test_missing_operator_approval_refusal() -> None:
    bundle = next(b for b in load_foundation_fixtures() if b["bundle_id"] == "dse-missing-operator-approval")
    result = process_foundation_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["admission"]["admitted"] is False


def test_stale_approval_refusal() -> None:
    bundle = next(b for b in load_foundation_fixtures() if b["bundle_id"] == "dse-stale-approval")
    result = process_foundation_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["admission"]["admitted"] is False


def test_missing_iam_refusal() -> None:
    bundle = next(b for b in load_foundation_fixtures() if b["bundle_id"] == "dse-missing-iam")
    result = process_foundation_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["admission"]["admitted"] is False


def test_missing_tim_refusal() -> None:
    bundle = next(b for b in load_foundation_fixtures() if b["bundle_id"] == "dse-missing-tim")
    result = process_foundation_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["admission"]["admitted"] is False


def test_unauthorized_path_refusal() -> None:
    bundle = next(b for b in load_foundation_fixtures() if b["bundle_id"] == "dse-unauthorized-path")
    result = process_foundation_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result.get("durable_write_performed") is False


def test_secret_leak_refusal() -> None:
    bundle = next(b for b in load_foundation_fixtures() if b["bundle_id"] == "dse-secret-leak")
    result = process_foundation_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["admission"]["admitted"] is False


def test_rollback_record_present() -> None:
    bundle = next(b for b in load_foundation_fixtures() if b["bundle_id"] == "dse-valid-file-sink")
    result = process_foundation_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert isinstance(result.get("rollback"), dict)


def test_no_authority_conversion() -> None:
    req = AdmissionRequest(
        request_id="dse-auth-conv",
        tranche_id="DSE-FOUNDATION",
        sink_class=SinkClass.DURABLE_LOCAL_FILE_SINK,
        operator_ref="op:local",
        freshness_ref="tim:approval_window_ok",
        approval_expires_at=FUTURE_EXPIRY,
        scope="approve_change",
        treat_as_authority=True,
    )
    decision = evaluate_sink_admission(req, observed_at=FIXTURE_CLOCK)
    assert decision.admitted is False
    assert decision.permission_granted is False
