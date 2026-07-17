"""
Tests for Pack 8 proof helpers and fixtures. No mocks: real file I/O and fixture content.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FIXTURES = REPO_ROOT / "scripts" / "proofs" / "fixtures"

# Expected provinces (10) for weather_sweep_10
EXPECTED_PROVINCES = {"BC", "AB", "SK", "MB", "ON", "QC", "NB", "NS", "PE", "NL"}


def test_weather_locations_fixture_exists_and_has_10_provinces():
    """weather_locations.json exists and contains exactly 10 provinces."""
    path = FIXTURES / "weather_locations.json"
    assert path.exists(), f"Fixture missing: {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "locations" in data
    locations = data["locations"]
    assert len(locations) == 10
    provinces = {loc["province"] for loc in locations}
    assert provinces == EXPECTED_PROVINCES
    for loc in locations:
        assert "name" in loc and "lat" in loc and "lon" in loc


def test_tickets_fixture_exists_and_has_5_tickets():
    """tickets/tickets.json exists and contains exactly 5 tickets."""
    path = FIXTURES / "tickets" / "tickets.json"
    assert path.exists(), f"Fixture missing: {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "tickets" in data
    tickets = data["tickets"]
    assert len(tickets) == 5
    for t in tickets:
        assert "ticket_id" in t and "subject" in t and "priority" in t


def test_persona_grace_hopper_fixtures_exist():
    """Grace Hopper reference and answer fixtures exist and are loadable."""
    ref_path = FIXTURES / "personas" / "grace_hopper_reference.json"
    ans_path = FIXTURES / "personas" / "hopper_answer_example.txt"
    assert ref_path.exists(), f"Fixture missing: {ref_path}"
    assert ans_path.exists(), f"Fixture missing: {ans_path}"
    ref = json.loads(ref_path.read_text(encoding="utf-8"))
    assert ref.get("persona_id") == "grace_hopper"
    assert "facts" in ref and "forbidden_patterns" in ref
    answer = ans_path.read_text(encoding="utf-8")
    assert len(answer.strip()) > 0


def test_common_helpers_write_json_and_append_jsonl(tmp_path):
    """Helpers write_json and append_jsonl write real files."""
    from scripts.proofs.common import write_json, append_jsonl, utc_iso, record_check

    write_json(tmp_path / "out.json", {"a": 1})
    assert (tmp_path / "out.json").exists()
    assert json.loads((tmp_path / "out.json").read_text()) == {"a": 1}

    append_jsonl(tmp_path / "lines.jsonl", {"b": 2})
    append_jsonl(tmp_path / "lines.jsonl", {"c": 3})
    lines = (tmp_path / "lines.jsonl").read_text().strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"b": 2}
    assert json.loads(lines[1]) == {"c": 3}

    ts = utc_iso()
    assert "T" in ts and ("Z" in ts or "+" in ts or "Z" in ts)

    checks = []
    record_check(checks, "one", True, {"x": 1})
    record_check(checks, "two", False, {"y": 2})
    assert len(checks) == 2
    assert checks[0]["name"] == "one" and checks[0]["pass"] is True
    assert checks[1]["name"] == "two" and checks[1]["pass"] is False


def test_persona_hopper_factcheck_run_produces_valid_bundle(tmp_path):
    """persona_hopper_factcheck run produces summary.json and checks.json with checks_passed."""
    from scripts.proofs.persona_hopper_factcheck import run

    meta = run(tmp_path)
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "checks.json").exists()
    assert (tmp_path / "answer.json").exists()
    assert (tmp_path / "factcheck.json").exists()
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["label"] == "persona_hopper_factcheck"
    assert summary["checks_passed"] is True
    assert "started_at" in summary and "ended_at" in summary
