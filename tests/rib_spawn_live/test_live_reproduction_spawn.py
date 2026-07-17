"""RIB-SPAWN-LIVE governed reproduction spawn tests."""

from __future__ import annotations

import pytest

from hg_core.iam.registry import clear_registry_cache, load_registry
from hg_core.iam.types import reset_iam_event_ledger
from hg_core.rib_spawn_live.errors import (
    REFUSED_AUTHORITY_CONVERSION,
    REFUSED_CHILD_IDENTITY_COLLISION,
    REFUSED_INHERITED_AUTHORITY,
    REFUSED_MISSING_IAM,
    REFUSED_MISSING_OPERATOR_APPROVAL,
    REFUSED_MISSING_TIM_FRESHNESS,
    REFUSED_STALE_APPROVAL,
    RibSpawnValidationError,
)
from hg_runtime.live_reproduction_spawn import (
    FIXTURE_CLOCK,
    FUTURE_EXPIRY,
    PAST_EXPIRY,
    ChildIdentityProfile,
    ChildSpawnReceipt,
    analyze_rib_spawn_fixtures,
    child_identity_distinct,
    commit_to_fake_sink,
    load_rib_spawn_fixtures,
    plan_to_fake_sink,
    process_reproduction_spawn,
    process_rib_spawn_bundle,
    refuse_rib_spawn_as_authority,
    replay_fixture_stream,
    request_from_fixture,
    rollback_spawn_plan,
    run_reproduction_spawn_fixture,
    validate_spawn_request,
)


@pytest.fixture(autouse=True)
def _reset_iam() -> None:
    clear_registry_cache()
    reset_iam_event_ledger()
    load_registry()


def _spawn_fixture(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "request_id": "rib-test-spawn",
        "parent_iam_ref": "iam:parent:fixture",
        "child_iam_ref": "iam:child:fixture-distinct",
        "bootstrap_digest": "digest:test",
        "operator_ref": "op:local",
        "freshness_ref": "tim:approval_window_ok",
        "approval_expires_at": FUTURE_EXPIRY,
        "scope": "approve_change",
        "rollback_plan_ref": "rollback:plan:test",
        "observed_at": FIXTURE_CLOCK,
    }
    base.update(overrides)
    return base


def test_valid_spawn_fixture_path() -> None:
    result = process_reproduction_spawn(_spawn_fixture(), observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["evidence_admissible"] is True
    assert result["permission_granted"] is False
    assert result["live_spawn_performed"] is False
    assert result["child_inherits_authority"] is False
    assert result["committed_sink"]["live_spawn_performed"] is False


def test_child_identity_distinct() -> None:
    assert child_identity_distinct("iam:parent:a", "iam:child:b") is True
    assert child_identity_distinct("iam:parent:a", "iam:parent:a") is False


def test_missing_operator_approval_refusal() -> None:
    request = request_from_fixture(_spawn_fixture(operator_ref=None))
    result = validate_spawn_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_OPERATOR_APPROVAL


def test_stale_approval_refusal() -> None:
    request = request_from_fixture(_spawn_fixture(approval_expires_at=PAST_EXPIRY))
    result = validate_spawn_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_STALE_APPROVAL


def test_missing_iam_refusal() -> None:
    request = request_from_fixture(_spawn_fixture(operator_ref="bob"))
    result = validate_spawn_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_IAM


def test_missing_tim_freshness_refusal() -> None:
    request = request_from_fixture(_spawn_fixture(freshness_ref="tim:missing"))
    result = validate_spawn_request(request, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
    assert result["reason_code"] == REFUSED_MISSING_TIM_FRESHNESS


def test_child_identity_collision_refusal() -> None:
    with pytest.raises(RibSpawnValidationError):
        request_from_fixture(_spawn_fixture(child_iam_ref="iam:parent:fixture"))


def test_authority_conversion_refusal() -> None:
    bundle = next(b for b in load_rib_spawn_fixtures() if b["bundle_id"] == "rib-authority-conversion")
    result = process_rib_spawn_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_AUTHORITY_CONVERSION


def test_inherited_authority_refusal() -> None:
    bundle = next(b for b in load_rib_spawn_fixtures() if b["bundle_id"] == "rib-inherited-authority")
    result = process_rib_spawn_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "contained"
    assert result["reason_code"] == REFUSED_INHERITED_AUTHORITY


def test_secret_redaction() -> None:
    with pytest.raises(RibSpawnValidationError):
        request_from_fixture(_spawn_fixture(bootstrap_digest="password=secret123"))


def test_deterministic_replay_hash() -> None:
    bundles = list(load_rib_spawn_fixtures()[:8])
    _, h1 = replay_fixture_stream(bundles, observed_at=FIXTURE_CLOCK)
    _, h2 = replay_fixture_stream(bundles, observed_at=FIXTURE_CLOCK)
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_rollback_recorded() -> None:
    bundle = next(b for b in load_rib_spawn_fixtures() if b["bundle_id"] == "rib-valid-rollback")
    result = process_rib_spawn_bundle(bundle, observed_at=FIXTURE_CLOCK)
    rollback = result.get("rollback_result")
    assert isinstance(rollback, dict)
    assert rollback.get("rollback_acknowledged") is True
    assert result["live_spawn_performed"] is False


def test_fake_sink_never_live() -> None:
    identity = ChildIdentityProfile(
        child_iam_ref="iam:child:test",
        parent_iam_ref="iam:parent:test",
    )
    staged = plan_to_fake_sink(identity, observed_at=FIXTURE_CLOCK)
    assert staged["live_spawn_performed"] is False
    receipt = ChildSpawnReceipt(
        receipt_id="rib-rcpt-sink",
        request_id="rib-test-sink",
        child_iam_ref="iam:child:test",
        parent_iam_ref="iam:parent:test",
        status="recorded",
        reason_code="rib_spawn.advisory.spawn_fake_sink",
        operator_ref="op:local",
    )
    committed = commit_to_fake_sink(receipt, observed_at=FIXTURE_CLOCK)
    assert committed["live_spawn_performed"] is False
    assert committed["sink_type"] == "fake"


def test_tep_wrapped_plan() -> None:
    result = process_reproduction_spawn(_spawn_fixture(), observed_at=FIXTURE_CLOCK)
    tep = result.get("tep_wrapped")
    assert isinstance(tep, dict)
    receipt = result.get("receipt")
    assert isinstance(receipt, dict)
    assert receipt.get("authority_created") is False
    assert receipt.get("live_spawn_performed") is False


def test_spawn_adapter_fixture() -> None:
    adapter = run_reproduction_spawn_fixture(observed_at=FIXTURE_CLOCK)
    assert adapter["live_spawn_performed"] is False
    assert "tep_emission" in adapter


def test_refuse_spawn_as_authority_raises() -> None:
    with pytest.raises(ValueError):
        refuse_rib_spawn_as_authority(treat_as_authority=True)


def test_analyze_fixtures_all_advisory() -> None:
    analysis = analyze_rib_spawn_fixtures(observed_at=FIXTURE_CLOCK)
    assert analysis["all_advisory"] is True
    assert analysis["no_authority_created"] is True
    assert analysis["no_live_spawn"] is True
    assert analysis["no_inherited_authority"] is True


def test_rollback_helper() -> None:
    receipt = ChildSpawnReceipt(
        receipt_id="rib-rcpt-rbk",
        request_id="rib-req-rbk",
        child_iam_ref="iam:child:rbk",
        parent_iam_ref="iam:parent:rbk",
        status="recorded",
        reason_code="rib_spawn.advisory.spawn_fake_sink",
        operator_ref="op:local",
    )
    rb = rollback_spawn_plan(receipt, observed_at=FIXTURE_CLOCK)
    assert rb["rollback_acknowledged"] is True
    assert rb["live_spawn_performed"] is False
