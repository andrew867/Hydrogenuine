"""MBR tests."""

from __future__ import annotations

from hg_runtime.many_body_renormalization import FIXTURE_CLOCK, load_mbr_fixtures, process_mbr_bundle, replay_mbr_bundles


def test_coherent_many_body_state() -> None:
    bundle = next(b for b in load_mbr_fixtures() if b["bundle_id"] == "mbr-coherent")
    assert process_mbr_bundle(bundle, observed_at=FIXTURE_CLOCK)["state"] == "coherent"


def test_hidden_proof_pressure_not_safe() -> None:
    bundle = next(b for b in load_mbr_fixtures() if b["bundle_id"] == "mbr-hidden-proof-pressure")
    result = process_mbr_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["hidden_proof_risk"] is True


def test_no_direct_action() -> None:
    bundle = next(b for b in load_mbr_fixtures() if b["bundle_id"] == "mbr-adversarial-action")
    assert process_mbr_bundle(bundle, observed_at=FIXTURE_CLOCK)["status"] == "refused"


def test_replay_determinism() -> None:
    bundles = load_mbr_fixtures()[:4]
    assert replay_mbr_bundles(bundles, observed_at=FIXTURE_CLOCK) == replay_mbr_bundles(bundles, observed_at=FIXTURE_CLOCK)
