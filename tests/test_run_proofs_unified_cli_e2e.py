"""
E2E for unified proof runner CLI: --list-scenarios, --scenario all. No mocks.
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

sys.path.insert(0, str(REPO_ROOT / "docs" / "proofs"))
from validate_proof_bundle import validate_bundle  # noqa: E402

RUN_PROOFS = REPO_ROOT / "scripts" / "run_proofs.py"
INDEX_PATH = REPO_ROOT / "docs" / "proofs" / "index.json"

ALL_SCENARIOS = [
    "health",
    "weather_sweep_10",
    "4claw_posts_3",
    "ticket_triage_5",
    "persona_hopper_factcheck",
    "investor_demo",
    "drift_quarantine_demo",
    "prompt_injection_hardening_demo",
    "soak_trust_demo",
]


def test_run_proofs_list_scenarios() -> None:
    """--list-scenarios prints all scenario names and 'all', exits 0."""
    r = subprocess.run(
        [sys.executable, str(RUN_PROOFS), "--list-scenarios"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert r.returncode == 0, (r.stdout, r.stderr)
    out = r.stdout.strip().splitlines()
    for s in ALL_SCENARIOS:
        assert s in out, "Expected %r in --list-scenarios output" % s
    assert "all" in out


def test_run_proofs_scenario_all_creates_bundles_and_index() -> None:
    """--scenario all runs all scenarios, updates index for each; offline bundles validate."""
    r = subprocess.run(
        [
            sys.executable,
            str(RUN_PROOFS),
            "--scenario",
            "all",
            "--base-url",
            "http://localhost:8080",
            "--api-key",
            "test-key",
            "--use-fixtures",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
        env={**__import__("os").environ, "HG_API_KEY": "test-key"},
    )
    assert INDEX_PATH.exists(), "index.json should exist after run"
    idx = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    latest = idx.get("latest", {})
    for label in ALL_SCENARIOS:
        assert label in latest, "Index latest should contain %r after --scenario all" % label
        folder = Path(latest[label])
        assert folder.is_dir(), "Bundle folder should exist: %s" % folder
        assert (folder / "summary.json").exists()
        assert (folder / "checks.json").exists()
        assert (folder / "ENVIRONMENT.json").exists()
        assert (folder / "VERSIONS.txt").exists()

    # Offline scenarios must pass and validate (no gateway required for their content).
    for label in ("ticket_triage_5", "persona_hopper_factcheck"):
        bundle_dir = Path(latest[label])
        ok, msg = validate_bundle(bundle_dir)
        assert ok, "Bundle %s should validate: %s" % (label, msg)
        summary = json.loads((bundle_dir / "summary.json").read_text(encoding="utf-8"))
        assert summary.get("checks_passed") is True, "Offline scenario %s should have checks_passed true" % label
