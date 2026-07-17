"""
E2E for ticket_triage_5 and persona_hopper_factcheck: run scenarios, validate bundles. No mocks.
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


def test_ticket_triage_5_run_and_validate(tmp_path: Path) -> None:
    """Run ticket_triage_5; assert 5 tickets, triage, approval payload; validate bundle (with ENVIRONMENT/VERSIONS from runner)."""
    from scripts.proofs.ticket_triage_5 import run

    summary = run(tmp_path)
    assert summary.get("checks_passed") is True
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "checks.json").exists()
    assert (tmp_path / "triage.json").exists()
    assert (tmp_path / "approval_payload_example.json").exists()
    triage = json.loads((tmp_path / "triage.json").read_text(encoding="utf-8"))
    assert len(triage.get("triage", [])) == 5
    for x in triage["triage"]:
        assert x.get("needs_approval_to_send") is True


def test_persona_hopper_factcheck_run_and_validate(tmp_path: Path) -> None:
    """Run persona_hopper_factcheck; assert factcheck ok, simulation labeled; validate bundle."""
    from scripts.proofs.persona_hopper_factcheck import run

    summary = run(tmp_path)
    assert summary.get("checks_passed") is True
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "checks.json").exists()
    assert (tmp_path / "answer.json").exists()
    assert (tmp_path / "factcheck.json").exists()


def test_ticket_triage_5_via_run_proofs_and_validate() -> None:
    """Run run_proofs.py --label ticket_triage_5; validate bundle (ENVIRONMENT/VERSIONS written by runner)."""
    run_proofs = REPO_ROOT / "scripts" / "run_proofs.py"
    r = subprocess.run(
        [
            sys.executable,
            str(run_proofs),
            "--label",
            "ticket_triage_5",
            "--base-url",
            "http://localhost:8080",
            "--api-key",
            "test-key",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
        env={**__import__("os").environ, "HG_API_KEY": "test-key"},
    )
    assert r.returncode == 0, (r.stdout, r.stderr)
    idx = json.loads((REPO_ROOT / "docs" / "proofs" / "index.json").read_text(encoding="utf-8"))
    folder = idx.get("latest", {}).get("ticket_triage_5")
    assert folder
    bundle_dir = Path(folder)
    ok, msg = validate_bundle(bundle_dir)
    assert ok, msg
    summary = json.loads((bundle_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary.get("checks_passed") is True
    assert (bundle_dir / "ENVIRONMENT.json").exists()
    assert (bundle_dir / "VERSIONS.txt").exists()


def test_persona_hopper_factcheck_via_run_proofs_and_validate() -> None:
    """Run run_proofs.py --label persona_hopper_factcheck; validate bundle."""
    run_proofs = REPO_ROOT / "scripts" / "run_proofs.py"
    r = subprocess.run(
        [
            sys.executable,
            str(run_proofs),
            "--label",
            "persona_hopper_factcheck",
            "--base-url",
            "http://localhost:8080",
            "--api-key",
            "test-key",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
        env={**__import__("os").environ, "HG_API_KEY": "test-key"},
    )
    assert r.returncode == 0, (r.stdout, r.stderr)
    idx = json.loads((REPO_ROOT / "docs" / "proofs" / "index.json").read_text(encoding="utf-8"))
    folder = idx.get("latest", {}).get("persona_hopper_factcheck")
    assert folder
    bundle_dir = Path(folder)
    ok, msg = validate_bundle(bundle_dir)
    assert ok, msg
    summary = json.loads((bundle_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary.get("checks_passed") is True
