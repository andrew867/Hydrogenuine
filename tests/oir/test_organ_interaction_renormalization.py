"""OIR tests."""

from __future__ import annotations

from hg_runtime.organ_interaction_renormalization import FIXTURE_CLOCK, load_oir_fixtures, process_oir_bundle, replay_oir_bundles


def test_low_density_cooperative() -> None:
    bundle = next(b for b in load_oir_fixtures() if b["bundle_id"] == "oir-low-density-cooperative")
    result = process_oir_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["interaction"]["regime"] == "cooperative"


def test_high_density_screened() -> None:
    bundle = next(b for b in load_oir_fixtures() if b["bundle_id"] == "oir-high-density-screened")
    result = process_oir_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["interaction"]["regime"] in ("screened", "saturated")


def test_interaction_score_not_permission() -> None:
    bundle = next(b for b in load_oir_fixtures() if b["bundle_id"] == "oir-low-density-cooperative")
    result = process_oir_bundle(bundle, observed_at=FIXTURE_CLOCK)
    assert result["permission_granted"] is False


def test_unknown_fails_closed() -> None:
    bundle = next(b for b in load_oir_fixtures() if b["bundle_id"] == "oir-unknown-regime")
    assert process_oir_bundle(bundle, observed_at=FIXTURE_CLOCK)["status"] == "refused"


def test_replay_determinism() -> None:
    bundles = load_oir_fixtures()[:5]
    assert replay_oir_bundles(bundles, observed_at=FIXTURE_CLOCK) == replay_oir_bundles(bundles, observed_at=FIXTURE_CLOCK)
