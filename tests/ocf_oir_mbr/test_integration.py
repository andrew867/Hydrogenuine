"""OCF/OIR/MBR integration tests."""

from __future__ import annotations

from hg_runtime.organ_control_and_many_body_safety import (
    FIXTURE_CLOCK_INTEGRATION,
    load_integration_fixtures,
    process_integration_fixture,
    replay_integration,
)


def test_integration_fixture_recorded() -> None:
    fixture = next(f for f in load_integration_fixtures() if f["bundle_id"] == "integration-baseline")
    result = process_integration_fixture(fixture, observed_at=FIXTURE_CLOCK_INTEGRATION)
    assert result["status"] == "recorded"
    assert result["permission_granted"] is False


def test_dse_sink_pressure_drives_mbr() -> None:
    fixture = next(f for f in load_integration_fixtures() if f["bundle_id"] == "integration-dse-mbr")
    result = process_integration_fixture(fixture, observed_at=FIXTURE_CLOCK_INTEGRATION)
    assert "dse_sink_pressure_observed" in result["snapshot"]["recommendations"]


def test_exciton_fixture_display_only() -> None:
    fixture = next(f for f in load_integration_fixtures() if f["bundle_id"] == "integration-high-risk")
    result = process_integration_fixture(fixture, observed_at=FIXTURE_CLOCK_INTEGRATION)
    assert result["exciton_fixture"]["display_only"] is True


def test_no_durable_sink() -> None:
    fixture = next(f for f in load_integration_fixtures() if f["bundle_id"] == "integration-adversarial-sink")
    assert process_integration_fixture(fixture, observed_at=FIXTURE_CLOCK_INTEGRATION)["status"] == "refused"


def test_replay_determinism() -> None:
    fixtures = load_integration_fixtures()[:3]
    assert replay_integration(fixtures, observed_at=FIXTURE_CLOCK_INTEGRATION) == replay_integration(fixtures, observed_at=FIXTURE_CLOCK_INTEGRATION)
