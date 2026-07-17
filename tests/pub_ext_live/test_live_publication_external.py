"""PUB-EXT-LIVE governed live publication external action tests."""

from __future__ import annotations

import pytest

from hg_core.iam.registry import clear_registry_cache, load_registry
from hg_core.iam.types import reset_iam_event_ledger
from hg_core.pub_ext_live.errors import (
    PUB_EXT_RELEASE_CANDIDATE_BOUND,
    PubExtValidationError,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_IRREVERSIBLE_WITHOUT_ACK,
    REFUSED_MISSING_DISCLOSURE_POLICY,
    REFUSED_MISSING_GPP_PERMIT,
    REFUSED_MISSING_IAM,
    REFUSED_MISSING_OPERATOR_APPROVAL,
    REFUSED_MISSING_ROLLBACK_PLAN,
    REFUSED_MISSING_TIM_FRESHNESS,
    REFUSED_MISSING_UEAK_ADMISSION,
    REFUSED_MISSING_WITHDRAWAL_PLAN,
    REFUSED_STALE_APPROVAL,
    REFUSED_STALE_TIM,
)
from hg_runtime.live_publication_external import (
    FIXTURE_CLOCK,
    FUTURE_EXPIRY,
    PAST_EXPIRY,
    analyze_pub_ext_fixtures,
    commit_to_fake_sink,
    load_pub_ext_fixtures,
    process_pub_ext_bundle,
    process_publication_release,
    refuse_pub_as_authority,
    replay_fixture_stream,
    request_from_fixture,
    run_publication_external_fixture,
    stage_to_fake_sink,
    validate_publication_request,
    withdrawal_record,
)
from hg_runtime.live_publication_external.types import PublicationCandidate, PublicationReceipt


@pytest.fixture(autouse=True)
def _reset_iam() -> None:
    clear_registry_cache()
    reset_iam_event_ledger()
    load_registry()


def _release_fixture(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "request_id": "pub-ext-test-release",
        "release_kind": "publish",
        "content_digest": "digest:test",
        "operator_ref": "op:local",
        "freshness_ref": "tim:approval_window_ok",
        "approval_expires_at": FUTURE_EXPIRY,
        "scope": "approve_change",
        "disclosure_policy_ref": "disclosure:test",
        "redaction_policy_ref": "redaction:test",
        "rollback_plan_ref": "rollback:plan:test",
        "withdrawal_plan_ref": "withdrawal:plan:test",
        "observed_at": FIXTURE_CLOCK,
    }
    base.update(overrides)
    return base


def test_valid_release_fixture_path() -> None:
    result = process_publication_release(_release_fixture(), observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["evidence_admissible"] is True
    assert result["permission_granted"] is False
    assert result["live_external_action"] is False
    assert result["committed_sink"]["live_external_action"] is False


def test_missing_operator_approval_refusal() -> None:
    request = request_from_fixture(_release_fixture(operator_ref=None))
    result = validate_publication_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_OPERATOR_APPROVAL


def test_stale_approval_refusal() -> None:
    request = request_from_fixture(_release_fixture(approval_expires_at=PAST_EXPIRY))
    result = validate_publication_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_STALE_APPROVAL


def test_missing_iam_refusal() -> None:
    request = request_from_fixture(_release_fixture(operator_ref="bob"))
    result = validate_publication_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_IAM


def test_missing_tim_freshness_refusal() -> None:
    request = request_from_fixture(_release_fixture(freshness_ref="tim:missing"))
    result = validate_publication_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_TIM_FRESHNESS


def test_stale_tim_refusal() -> None:
    request = request_from_fixture(_release_fixture(freshness_ref="tim:stale"))
    result = validate_publication_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_STALE_TIM


def test_missing_gpp_permit_refusal() -> None:
    request = request_from_fixture(_release_fixture(requires_gpp=True))
    result = validate_publication_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_GPP_PERMIT


def test_missing_ueak_admission_refusal() -> None:
    request = request_from_fixture(_release_fixture(requires_ueak=True))
    result = validate_publication_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_UEAK_ADMISSION


def test_missing_disclosure_policy_refusal() -> None:
    request = request_from_fixture(_release_fixture(disclosure_policy_ref=None))
    result = validate_publication_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_DISCLOSURE_POLICY


def test_missing_rollback_plan_refusal() -> None:
    request = request_from_fixture(_release_fixture(rollback_plan_ref=None))
    result = validate_publication_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_ROLLBACK_PLAN


def test_missing_withdrawal_plan_refusal() -> None:
    request = request_from_fixture(_release_fixture(withdrawal_plan_ref=None))
    result = validate_publication_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_WITHDRAWAL_PLAN


def test_irreversible_without_ack_refusal() -> None:
    request = request_from_fixture(_release_fixture(irreversible=True, irreversible_ack=False))
    result = validate_publication_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_IRREVERSIBLE_WITHOUT_ACK


def test_authority_conversion_refusal() -> None:
    bundle = next(b for b in load_pub_ext_fixtures() if b["bundle_id"] == "pub-ext-authority-conversion")
    result = process_pub_ext_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_AUTHORITY_CONVERSION


def test_secret_redaction() -> None:
    with pytest.raises(PubExtValidationError):
        request_from_fixture(_release_fixture(content_digest="password=secret123"))


def test_deterministic_replay_hash() -> None:
    bundles = list(load_pub_ext_fixtures()[:6])
    _, h1 = replay_fixture_stream(bundles, observed_at=FIXTURE_CLOCK)
    _, h2 = replay_fixture_stream(bundles, observed_at=FIXTURE_CLOCK)
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_withdrawal_recorded() -> None:
    bundle = next(b for b in load_pub_ext_fixtures() if b["bundle_id"] == "pub-ext-valid-withdrawal")
    result = process_pub_ext_bundle(bundle, observed_at=FIXTURE_CLOCK)
    withdrawal = result.get("withdrawal_result")
    assert isinstance(withdrawal, dict)
    assert withdrawal.get("status") == "recorded"
    assert result["permission_granted"] is False


def test_compensation_from_withdrawal() -> None:
    bundle = next(b for b in load_pub_ext_fixtures() if b["bundle_id"] == "pub-ext-valid-withdrawal")
    result = process_pub_ext_bundle(bundle, observed_at=FIXTURE_CLOCK)
    compensation = result.get("compensation_result")
    assert isinstance(compensation, dict)
    assert compensation.get("status") == "recorded"
    assert result["live_external_action"] is False


def test_no_out_of_scope_live_action() -> None:
    bundle = next(b for b in load_pub_ext_fixtures() if b["bundle_id"] == "pub-ext-out-of-scope-live")
    result = process_pub_ext_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["permission_granted"] is False
    assert result["live_action_performed"] is False
    assert result["live_external_action"] is False


def test_fake_sink_never_live_external() -> None:
    candidate = PublicationCandidate(
        candidate_id="pub-cand-sink",
        request_id="pub-req-sink",
        release_kind="publish",
        content_digest="digest:sink",
        disclosure_tier="tier:test",
        operator_ref="op:local",
    )
    staged = stage_to_fake_sink(candidate, observed_at=FIXTURE_CLOCK)
    assert staged["live_external_action"] is False
    assert staged["sink_type"] == "fake"
    receipt = PublicationReceipt(
        receipt_id="pub-rcpt-sink",
        request_id="pub-req-sink",
        candidate_id="pub-cand-sink",
        release_kind="publish",
        status="recorded",
        reason_code=PUB_EXT_RELEASE_CANDIDATE_BOUND,
        operator_ref="op:local",
    )
    committed = commit_to_fake_sink(receipt, observed_at=FIXTURE_CLOCK)
    assert committed["live_external_action"] is False
    assert committed["sink_type"] == "fake"


def test_tep_wrapped_candidate() -> None:
    result = process_publication_release(_release_fixture(), observed_at=FIXTURE_CLOCK)
    tep = result.get("tep_wrapped")
    assert isinstance(tep, dict)
    candidate = result.get("candidate")
    assert isinstance(candidate, dict)
    assert candidate.get("authority_created") is False
    assert candidate.get("permission_granted") is False


def test_release_adapter_fixture() -> None:
    adapter = run_publication_external_fixture(observed_at=FIXTURE_CLOCK)
    assert adapter["live_external_action"] is False
    assert "tep_emission" in adapter


def test_refuse_pub_as_authority_raises() -> None:
    with pytest.raises(ValueError):
        refuse_pub_as_authority(treat_as_authority=True)


def test_analyze_fixtures_all_advisory() -> None:
    analysis = analyze_pub_ext_fixtures(observed_at=FIXTURE_CLOCK)
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert analysis["no_live_external_action"] is True


def test_withdrawal_helper() -> None:
    receipt = PublicationReceipt(
        receipt_id="pub-rcpt-wdr",
        request_id="pub-req-wdr",
        candidate_id="pub-cand-wdr",
        release_kind="publish",
        status="recorded",
        reason_code=PUB_EXT_RELEASE_CANDIDATE_BOUND,
        operator_ref="op:local",
    )
    w = withdrawal_record(receipt, content_digest="digest:wdr", observed_at=FIXTURE_CLOCK)
    assert w["status"] == "recorded"
    assert w["live_external_action"] is False
