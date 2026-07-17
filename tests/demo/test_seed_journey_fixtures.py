from pathlib import Path

from demo.seed_journey_fixtures import seed_journey_fixtures


def test_seed_journey_fixtures_writes_brief_and_marker(tmp_path: Path) -> None:
    result = seed_journey_fixtures(tmp_path)
    assert result["files_written"] >= 1
    assert (tmp_path / "knowledge" / "current_events" / "brief-journey-demo.md").exists()
    assert (tmp_path / "memory" / "ux_journey_seed.json").exists()

    # idempotent
    again = seed_journey_fixtures(tmp_path)
    assert again["files_written"] >= 1
