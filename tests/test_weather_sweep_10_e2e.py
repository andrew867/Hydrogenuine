"""
E2E tests for weather_sweep_10: REAL Open-Meteo API is the primary path. No mocks.
Fixture path exists only as offline fallback when network is unavailable.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

EXPECTED_PROVINCES = {"BC", "AB", "SK", "MB", "ON", "QC", "NB", "NS", "PE", "NL"}


def _assert_weather_bundle_valid(bundle_dir: Path, md_required: bool = True) -> None:
    assert (bundle_dir / "summary.json").exists()
    assert (bundle_dir / "checks.json").exists()
    summary = json.loads((bundle_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary.get("label") == "weather_sweep_10"
    assert summary.get("checks_passed") is True
    assert set(summary.get("provinces", [])) == EXPECTED_PROVINCES
    assistant_summary = summary.get("assistant_summary")
    assert isinstance(assistant_summary, str) and assistant_summary.strip()
    assert assistant_summary.startswith("It looks like the weather across the ten provinces")
    if md_required:
        md_path = bundle_dir / "WEATHER_SUMMARY_10_PROVINCES.md"
        assert md_path.exists(), f"Missing {md_path}"
        md_text = md_path.read_text(encoding="utf-8")
        assert "## Executive summary" in md_text
        assert assistant_summary in md_text
        for prov in EXPECTED_PROVINCES:
            assert prov in md_text, f"WEATHER_SUMMARY_10_PROVINCES.md must list province {prov}"
    assert (bundle_dir / "tool_outputs.jsonl").exists()
    lines = (bundle_dir / "tool_outputs.jsonl").read_text().strip().split("\n")
    assert len(lines) == 10


def test_weather_sweep_10_real_open_meteo(tmp_path: Path) -> None:
    """PRIMARY: Run weather_sweep_10 against REAL Open-Meteo API. No fixtures. Fails if API unreachable."""
    from scripts.proofs.weather_sweep_10 import run

    summary = run(tmp_path, use_fixtures=False)
    assert summary.get("checks_passed") is True
    assert set(summary.get("provinces", [])) == EXPECTED_PROVINCES
    _assert_weather_bundle_valid(tmp_path, md_required=True)
    lines = (tmp_path / "tool_outputs.jsonl").read_text().strip().split("\n")
    for line in lines:
        record = json.loads(line)
        assert record.get("source") == "open-meteo", "Production path must use real Open-Meteo"
        assert "fetched_at" in record


def test_weather_sweep_10_via_run_proofs_real_api(tmp_path: Path) -> None:
    """PRIMARY: Run scripts/run_proofs.py weather_sweep_10 WITHOUT --use-fixtures (real Open-Meteo). Fails if API down."""
    run_proofs = REPO_ROOT / "scripts" / "run_proofs.py"
    r = subprocess.run(
        [
            sys.executable,
            str(run_proofs),
            "--label",
            "weather_sweep_10",
            "--base-url",
            "http://localhost:8080",
            "--api-key",
            "test-key",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
        env={**__import__("os").environ, "HG_API_KEY": "test-key"},
    )
    assert r.returncode == 0, f"run_proofs must succeed with real API. stdout={r.stdout} stderr={r.stderr}"
    index_path = REPO_ROOT / "docs" / "proofs" / "index.json"
    assert index_path.exists()
    idx = json.loads(index_path.read_text(encoding="utf-8"))
    folder = idx.get("latest", {}).get("weather_sweep_10")
    assert folder
    bundle_dir = Path(folder)
    assert bundle_dir.is_dir()
    _assert_weather_bundle_valid(bundle_dir, md_required=True)
    assert (bundle_dir / "ENVIRONMENT.json").exists()
    assert (bundle_dir / "VERSIONS.txt").exists()
    lines = (bundle_dir / "tool_outputs.jsonl").read_text().strip().split("\n")
    first = json.loads(lines[0])
    assert first.get("source") == "open-meteo", "Production run must use real Open-Meteo"


@pytest.mark.offline
def test_weather_sweep_10_fixtures_offline_fallback_only(tmp_path: Path) -> None:
    """OFFLINE FALLBACK ONLY: Use fixtures when real Open-Meteo is unavailable. Not a substitute for real API tests."""
    from scripts.proofs.weather_sweep_10 import run

    summary = run(tmp_path, use_fixtures=True)
    assert summary.get("checks_passed") is True
    assert set(summary.get("provinces", [])) == EXPECTED_PROVINCES
    _assert_weather_bundle_valid(tmp_path, md_required=True)
