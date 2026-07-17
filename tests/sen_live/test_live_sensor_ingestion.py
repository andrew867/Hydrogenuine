"""SEN-LIVE governed live sensor ingestion tests."""

from __future__ import annotations

import pytest

from hg_core.iam.registry import clear_registry_cache, load_registry
from hg_core.iam.types import reset_iam_event_ledger
from hg_core.sen_live.errors import (
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_MISSING_CONSENT,
    REFUSED_MISSING_GPP_PERMIT,
    REFUSED_MISSING_IAM,
    REFUSED_MISSING_OPERATOR_APPROVAL,
    REFUSED_MISSING_REDACTION_POLICY,
    REFUSED_MISSING_TIM_FRESHNESS,
    REFUSED_MISSING_UEAK_ADMISSION,
    REFUSED_SCALAR_AS_TRUTH,
    REFUSED_STALE_APPROVAL,
    REFUSED_STALE_TIM,
    SEN_OBSERVATION_CANDIDATE_BOUND,
    SenValidationError,
)
from hg_runtime.live_sensor_ingestion import (
    FIXTURE_CLOCK,
    FUTURE_EXPIRY,
    PAST_EXPIRY,
    analyze_sen_fixtures,
    commit_to_fake_sink,
    load_sen_fixtures,
    process_sen_bundle,
    process_sensor_ingestion,
    quarantine_observation,
    refuse_sen_as_authority,
    replay_fixture_stream,
    request_from_fixture,
    run_sensor_ingestion_fixture,
    stage_to_fake_sink,
    validate_sensor_ingest_request,
    withdraw_from_quarantine,
)
from hg_runtime.live_sensor_ingestion.types import SensorIngestReceipt, SensorObservationCandidate


@pytest.fixture(autouse=True)
def _reset_iam() -> None:
    clear_registry_cache()
    reset_iam_event_ledger()
    load_registry()


def _ingest_fixture(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "request_id": "sen-test-ingest",
        "modality": "text",
        "observation_digest": "digest:test",
        "operator_ref": "op:local",
        "freshness_ref": "tim:approval_window_ok",
        "approval_expires_at": FUTURE_EXPIRY,
        "scope": "approve_change",
        "consent_ref": "consent:test",
        "redaction_policy_ref": "redaction:test",
        "observed_at": FIXTURE_CLOCK,
    }
    base.update(overrides)
    return base


def test_valid_ingest_fixture_path() -> None:
    result = process_sensor_ingestion(_ingest_fixture(), observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["evidence_admissible"] is True
    assert result["permission_granted"] is False
    assert result["live_sensor_connection"] is False
    assert result["committed_sink"]["live_sensor_connection"] is False


def test_missing_operator_approval_refusal() -> None:
    request = request_from_fixture(_ingest_fixture(operator_ref=None))
    result = validate_sensor_ingest_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_OPERATOR_APPROVAL


def test_stale_approval_refusal() -> None:
    request = request_from_fixture(_ingest_fixture(approval_expires_at=PAST_EXPIRY))
    result = validate_sensor_ingest_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_STALE_APPROVAL


def test_missing_iam_refusal() -> None:
    request = request_from_fixture(_ingest_fixture(operator_ref="bob"))
    result = validate_sensor_ingest_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_IAM


def test_missing_tim_freshness_refusal() -> None:
    request = request_from_fixture(_ingest_fixture(freshness_ref="tim:missing"))
    result = validate_sensor_ingest_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_TIM_FRESHNESS


def test_stale_tim_refusal() -> None:
    request = request_from_fixture(_ingest_fixture(freshness_ref="tim:stale"))
    result = validate_sensor_ingest_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_STALE_TIM


def test_missing_gpp_permit_refusal() -> None:
    request = request_from_fixture(_ingest_fixture(requires_gpp=True))
    result = validate_sensor_ingest_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_GPP_PERMIT


def test_missing_ueak_admission_refusal() -> None:
    request = request_from_fixture(_ingest_fixture(requires_ueak=True))
    result = validate_sensor_ingest_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_UEAK_ADMISSION


def test_missing_consent_refusal() -> None:
    request = request_from_fixture(_ingest_fixture(consent_ref=None))
    result = validate_sensor_ingest_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_CONSENT


def test_missing_redaction_policy_refusal() -> None:
    request = request_from_fixture(_ingest_fixture(redaction_policy_ref=None))
    result = validate_sensor_ingest_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_REDACTION_POLICY


def test_scalar_not_truth_refusal() -> None:
    request = request_from_fixture(
        _ingest_fixture(modality="scalar", observation_digest="scalar:truth:reading")
    )
    result = validate_sensor_ingest_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_SCALAR_AS_TRUTH


def test_authority_conversion_refusal() -> None:
    bundle = next(b for b in load_sen_fixtures() if b["bundle_id"] == "sen-authority-conversion")
    result = process_sen_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_AUTHORITY_CONVERSION


def test_secret_redaction() -> None:
    with pytest.raises(SenValidationError):
        request_from_fixture(_ingest_fixture(observation_digest="password=secret123"))


def test_deterministic_replay_hash() -> None:
    bundles = list(load_sen_fixtures()[:6])
    _, h1 = replay_fixture_stream(bundles, observed_at=FIXTURE_CLOCK)
    _, h2 = replay_fixture_stream(bundles, observed_at=FIXTURE_CLOCK)
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_quarantine_recorded() -> None:
    bundle = next(b for b in load_sen_fixtures() if b["bundle_id"] == "sen-valid-quarantine")
    result = process_sen_bundle(bundle, observed_at=FIXTURE_CLOCK)
    quarantine = result.get("quarantine_result")
    assert isinstance(quarantine, dict)
    assert quarantine.get("status") == "recorded"
    assert result["permission_granted"] is False


def test_withdrawal_from_quarantine() -> None:
    bundle = next(b for b in load_sen_fixtures() if b["bundle_id"] == "sen-valid-quarantine")
    result = process_sen_bundle(bundle, observed_at=FIXTURE_CLOCK)
    withdrawal = result.get("withdrawal_result")
    assert isinstance(withdrawal, dict)
    assert withdrawal.get("status") == "recorded"
    assert result["live_sensor_connection"] is False


def test_no_out_of_scope_live_action() -> None:
    bundle = next(b for b in load_sen_fixtures() if b["bundle_id"] == "sen-out-of-scope-live")
    result = process_sen_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["permission_granted"] is False
    assert result["live_action_performed"] is False
    assert result["live_sensor_connection"] is False


def test_fake_sink_never_live_sensor() -> None:
    candidate = SensorObservationCandidate(
        candidate_id="sen-cand-sink",
        request_id="sen-req-sink",
        modality="text",
        observation_digest="digest:sink",
        privacy_tier="tier:test",
        operator_ref="op:local",
    )
    staged = stage_to_fake_sink(candidate, observed_at=FIXTURE_CLOCK)
    assert staged["live_sensor_connection"] is False
    assert staged["sink_type"] == "fake"
    receipt = SensorIngestReceipt(
        receipt_id="sen-rcpt-sink",
        request_id="sen-req-sink",
        candidate_id="sen-cand-sink",
        modality="text",
        status="recorded",
        reason_code=SEN_OBSERVATION_CANDIDATE_BOUND,
        operator_ref="op:local",
    )
    committed = commit_to_fake_sink(receipt, observed_at=FIXTURE_CLOCK)
    assert committed["live_sensor_connection"] is False
    assert committed["sink_type"] == "fake"


def test_tep_wrapped_candidate() -> None:
    result = process_sensor_ingestion(_ingest_fixture(), observed_at=FIXTURE_CLOCK)
    tep = result.get("tep_wrapped")
    assert isinstance(tep, dict)
    candidate = result.get("candidate")
    assert isinstance(candidate, dict)
    assert candidate.get("authority_created") is False
    assert candidate.get("permission_granted") is False


def test_ingestion_adapter_fixture() -> None:
    adapter = run_sensor_ingestion_fixture(observed_at=FIXTURE_CLOCK)
    assert adapter["live_sensor_connection"] is False
    assert "tep_emission" in adapter


def test_refuse_sen_as_authority_raises() -> None:
    with pytest.raises(ValueError):
        refuse_sen_as_authority(treat_as_authority=True)


def test_analyze_fixtures_all_advisory() -> None:
    analysis = analyze_sen_fixtures(observed_at=FIXTURE_CLOCK)
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert analysis["no_live_sensor_connection"] is True


def test_quarantine_helper() -> None:
    receipt = SensorIngestReceipt(
        receipt_id="sen-rcpt-qtn",
        request_id="sen-req-qtn",
        candidate_id="sen-cand-qtn",
        modality="text",
        status="recorded",
        reason_code=SEN_OBSERVATION_CANDIDATE_BOUND,
        operator_ref="op:local",
    )
    q = quarantine_observation(receipt, observation_digest="digest:qtn", observed_at=FIXTURE_CLOCK)
    assert q["status"] == "recorded"
    assert q["live_sensor_connection"] is False


def test_withdrawal_helper() -> None:
    w = withdraw_from_quarantine(
        {"quarantine_id": "sen-qtn-test", "observation_digest": "digest:wdr"},
        observed_at=FIXTURE_CLOCK,
    )
    assert w["status"] == "recorded"
    assert w["live_sensor_connection"] is False
