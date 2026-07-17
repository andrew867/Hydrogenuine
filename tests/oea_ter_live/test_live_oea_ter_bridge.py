"""OEA-TER-LIVE governed live OEA/TER bridge tests."""

from __future__ import annotations

import pytest

from hg_core.iam.registry import clear_registry_cache, load_registry
from hg_core.iam.types import reset_iam_event_ledger
from hg_core.oea_ter_live.errors import (
    OEA_TER_DISPATCH_CANDIDATE_BOUND,
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_KILL_SWITCH_ACTIVE,
    REFUSED_MISSING_GPP_PERMIT,
    REFUSED_MISSING_IAM,
    REFUSED_MISSING_OPERATOR_APPROVAL,
    REFUSED_MISSING_TIM_FRESHNESS,
    REFUSED_MISSING_UEAK_ADMISSION,
    REFUSED_STALE_APPROVAL,
    REFUSED_STALE_TIM,
    OeaTerValidationError,
)
from hg_runtime.live_oea_ter_bridge import (
    FIXTURE_CLOCK,
    FUTURE_EXPIRY,
    PAST_EXPIRY,
    analyze_oea_ter_fixtures,
    commit_to_fake_sink,
    compensate_from_rollback,
    load_oea_ter_fixtures,
    process_oea_ter_bundle,
    process_live_dispatch,
    refuse_oea_as_authority,
    replay_fixture_stream,
    request_from_fixture,
    request_to_fake_sink,
    rollback_live_action,
    run_oea_ter_bridge_fixture,
    validate_dispatch_request,
)
from hg_runtime.live_oea_ter_bridge.types import LiveActionCandidate, LiveActionReceipt


@pytest.fixture(autouse=True)
def _reset_iam() -> None:
    clear_registry_cache()
    reset_iam_event_ledger()
    load_registry()


def _dispatch_fixture(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "request_id": "oea-test-dispatch",
        "external_surface": "fake",
        "action_digest": "digest:test",
        "operator_ref": "op:local",
        "freshness_ref": "tim:approval_window_ok",
        "approval_expires_at": FUTURE_EXPIRY,
        "scope": "approve_change",
        "gpp_permit_ref": "gpp:permit:test",
        "ueak_admission_ref": "ueak:admission:test",
        "rollback_plan_ref": "rollback:plan:test",
        "control_kind": "dispatch",
        "observed_at": FIXTURE_CLOCK,
    }
    base.update(overrides)
    return base


def test_valid_dispatch_fixture_path() -> None:
    result = process_live_dispatch(_dispatch_fixture(), observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["evidence_admissible"] is True
    assert result["permission_granted"] is False
    assert result["live_action_performed"] is False
    assert result["oea_ter_called"] is False
    assert result["committed_sink"]["live_action_performed"] is False


def test_missing_operator_approval_refusal() -> None:
    request = request_from_fixture(_dispatch_fixture(operator_ref=None))
    result = validate_dispatch_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_OPERATOR_APPROVAL


def test_stale_approval_refusal() -> None:
    request = request_from_fixture(_dispatch_fixture(approval_expires_at=PAST_EXPIRY))
    result = validate_dispatch_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_STALE_APPROVAL


def test_missing_iam_refusal() -> None:
    request = request_from_fixture(_dispatch_fixture(operator_ref="bob"))
    result = validate_dispatch_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_IAM


def test_missing_tim_freshness_refusal() -> None:
    request = request_from_fixture(_dispatch_fixture(freshness_ref="tim:missing"))
    result = validate_dispatch_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_TIM_FRESHNESS


def test_stale_tim_refusal() -> None:
    request = request_from_fixture(_dispatch_fixture(freshness_ref="tim:stale"))
    result = validate_dispatch_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_STALE_TIM


def test_missing_gpp_permit_refusal() -> None:
    request = request_from_fixture(_dispatch_fixture(gpp_permit_ref=None))
    result = validate_dispatch_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_GPP_PERMIT


def test_missing_ueak_admission_refusal() -> None:
    request = request_from_fixture(_dispatch_fixture(ueak_admission_ref=None))
    result = validate_dispatch_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_UEAK_ADMISSION


def test_kill_switch_refusal() -> None:
    bundle = next(b for b in load_oea_ter_fixtures() if b["bundle_id"] == "oea-kill-switch")
    result = process_oea_ter_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_KILL_SWITCH_ACTIVE
    assert result["kill_switch_active"] is True


def test_authority_conversion_refusal() -> None:
    bundle = next(b for b in load_oea_ter_fixtures() if b["bundle_id"] == "oea-authority-conversion")
    result = process_oea_ter_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_AUTHORITY_CONVERSION


def test_secret_redaction() -> None:
    with pytest.raises(OeaTerValidationError):
        request_from_fixture(_dispatch_fixture(action_digest="password=secret123"))


def test_deterministic_replay_hash() -> None:
    bundles = list(load_oea_ter_fixtures()[:6])
    _, h1 = replay_fixture_stream(bundles, observed_at=FIXTURE_CLOCK)
    _, h2 = replay_fixture_stream(bundles, observed_at=FIXTURE_CLOCK)
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_rollback_recorded() -> None:
    bundle = next(b for b in load_oea_ter_fixtures() if b["bundle_id"] == "oea-valid-rollback")
    result = process_oea_ter_bundle(bundle, observed_at=FIXTURE_CLOCK)
    rollback = result.get("rollback_result")
    assert isinstance(rollback, dict)
    assert rollback.get("rollback_acknowledged") is True
    assert result["permission_granted"] is False


def test_compensation_from_rollback() -> None:
    bundle = next(b for b in load_oea_ter_fixtures() if b["bundle_id"] == "oea-valid-compensation")
    result = process_oea_ter_bundle(bundle, observed_at=FIXTURE_CLOCK)
    compensation = result.get("compensation_result")
    assert isinstance(compensation, dict)
    assert compensation.get("compensation_available") is True
    assert result["live_action_performed"] is False


def test_no_out_of_scope_live_action() -> None:
    bundle = next(b for b in load_oea_ter_fixtures() if b["bundle_id"] == "oea-out-of-scope-live")
    result = process_oea_ter_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["permission_granted"] is False
    assert result["live_action_performed"] is False
    assert result["oea_ter_called"] is False


def test_fake_sink_never_live() -> None:
    candidate = LiveActionCandidate(
        candidate_id="oea-cand-sink",
        request_id="oea-req-sink",
        external_surface="fake",
        action_digest="digest:sink",
        operator_ref="op:local",
        gpp_permit_ref="gpp:permit:sink",
        ueak_admission_ref="ueak:admission:sink",
    )
    staged = request_to_fake_sink(candidate, observed_at=FIXTURE_CLOCK)
    assert staged["live_action_performed"] is False
    assert staged["oea_ter_called"] is False
    assert staged["sink_type"] == "fake"
    receipt = LiveActionReceipt(
        receipt_id="oea-rcpt-sink",
        request_id="oea-req-sink",
        candidate_id="oea-cand-sink",
        external_surface="fake",
        status="recorded",
        reason_code=OEA_TER_DISPATCH_CANDIDATE_BOUND,
        operator_ref="op:local",
        permit_bound=True,
        admission_bound=True,
    )
    committed = commit_to_fake_sink(receipt, observed_at=FIXTURE_CLOCK)
    assert committed["live_action_performed"] is False
    assert committed["oea_ter_called"] is False
    assert committed["sink_type"] == "fake"


def test_tep_wrapped_candidate() -> None:
    result = process_live_dispatch(_dispatch_fixture(), observed_at=FIXTURE_CLOCK)
    tep = result.get("tep_wrapped")
    assert isinstance(tep, dict)
    candidate = result.get("candidate")
    assert isinstance(candidate, dict)
    assert candidate.get("authority_created") is False
    assert candidate.get("permission_granted") is False


def test_gpp_permit_binding() -> None:
    result = process_live_dispatch(_dispatch_fixture(), observed_at=FIXTURE_CLOCK)
    receipt = result.get("receipt")
    assert isinstance(receipt, dict)
    assert receipt.get("permit_bound") is True


def test_ueak_admission_binding() -> None:
    result = process_live_dispatch(_dispatch_fixture(), observed_at=FIXTURE_CLOCK)
    receipt = result.get("receipt")
    assert isinstance(receipt, dict)
    assert receipt.get("admission_bound") is True


def test_bridge_adapter_fixture() -> None:
    adapter = run_oea_ter_bridge_fixture(observed_at=FIXTURE_CLOCK)
    assert adapter["live_action_performed"] is False
    assert adapter["oea_ter_called"] is False
    assert "tep_emission" in adapter


def test_refuse_oea_as_authority_raises() -> None:
    with pytest.raises(ValueError):
        refuse_oea_as_authority(treat_as_authority=True)


def test_analyze_fixtures_all_advisory() -> None:
    analysis = analyze_oea_ter_fixtures(observed_at=FIXTURE_CLOCK)
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert analysis["no_live_actions"] is True


def test_rollback_helper() -> None:
    receipt = LiveActionReceipt(
        receipt_id="oea-rcpt-rbk",
        request_id="oea-req-rbk",
        candidate_id="oea-cand-rbk",
        external_surface="fake",
        status="recorded",
        reason_code=OEA_TER_DISPATCH_CANDIDATE_BOUND,
        operator_ref="op:local",
    )
    rb = rollback_live_action(
        receipt,
        action_digest="digest:rbk",
        prior_digest="digest:prior",
        observed_at=FIXTURE_CLOCK,
    )
    assert rb["rollback_acknowledged"] is True
    assert rb["live_action_performed"] is False
    assert rb["oea_ter_called"] is False


def test_compensation_helper() -> None:
    cmp = compensate_from_rollback(
        {"rollback_id": "oea-rbk-test", "action_digest": "digest:cmp"},
        compensation_digest="digest:compensated",
        observed_at=FIXTURE_CLOCK,
    )
    assert cmp["compensation_available"] is True
    assert cmp["live_action_performed"] is False
    assert cmp["oea_ter_called"] is False
