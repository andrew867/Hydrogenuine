"""OCF organ control fields tests."""

from __future__ import annotations

from hg_runtime.organ_control_fields import FIXTURE_CLOCK, load_ocf_fixtures, process_ocf_bundle, replay_ocf_bundles


def test_valid_damp_control_field() -> None:
    bundle = next(b for b in load_ocf_fixtures() if b["bundle_id"] == "ocf-valid-damp")
    result = process_ocf_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_valid_dark_transition() -> None:
    bundle = next(b for b in load_ocf_fixtures() if b["bundle_id"] == "ocf-valid-dark")
    result = process_ocf_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["transition"]["to_posture"] == "DARK"


def test_valid_probe_only_transition() -> None:
    bundle = next(b for b in load_ocf_fixtures() if b["bundle_id"] == "ocf-valid-probe")
    result = process_ocf_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["transition"]["to_posture"] == "PROBE_ONLY"


def test_valid_decoupling_transition() -> None:
    bundle = next(b for b in load_ocf_fixtures() if b["bundle_id"] == "ocf-valid-decouple")
    result = process_ocf_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert "decoupling_plan" in result


def test_recoupling_requires_explicit_audit() -> None:
    bundle = next(b for b in load_ocf_fixtures() if b["bundle_id"] == "ocf-recouple-no-audit")
    result = process_ocf_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"


def test_panic_dark_restrict_only() -> None:
    bundle = next(b for b in load_ocf_fixtures() if b["bundle_id"] == "ocf-panic-dark")
    result = process_ocf_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["panic_dark_receipt"]["restrict_only"] is True


def test_control_field_cannot_grant_permission() -> None:
    bundle = next(b for b in load_ocf_fixtures() if b["bundle_id"] == "ocf-adversarial-auth")
    result = process_ocf_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["permission_granted"] is False


def test_sideband_receipt_emitted() -> None:
    bundle = next(b for b in load_ocf_fixtures() if b["bundle_id"] == "ocf-valid-damp")
    result = process_ocf_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["sideband_receipt"]["receipt_hash"]


def test_deterministic_posture_replay() -> None:
    bundles = load_ocf_fixtures()[:5]
    assert replay_ocf_bundles(bundles, observed_at=FIXTURE_CLOCK) == replay_ocf_bundles(bundles, observed_at=FIXTURE_CLOCK)


def test_unknown_posture_fails_closed() -> None:
    bundle = next(b for b in load_ocf_fixtures() if b["bundle_id"] == "ocf-unknown-posture")
    result = process_ocf_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["status"] == "refused"
