"""Static guards protecting the hermetic-CI curation invariants.

These run inside `pytest_and_policy` itself, so a change that would silently
regress the hermetic setup (drop HG_CI_HERMETIC, reorder validators after pytest,
remove the quarantine escape hatch, add an unreasoned quarantine line) fails CI
loudly. They read repo files only — no services, fully hermetic.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CI_YML = ROOT / ".gitlab-ci.yml"
QUARANTINE = ROOT / "tests" / "quarantine.txt"
PYPROJECT = ROOT / "pyproject.toml"
CONFTEST = ROOT / "tests" / "conftest.py"


def _ci_text() -> str:
    return CI_YML.read_text(encoding="utf-8")


def test_import_mode_importlib_configured():
    assert '--import-mode=importlib' in PYPROJECT.read_text(encoding="utf-8")


def test_pytest_job_is_hermetic():
    assert 'HG_CI_HERMETIC: "1"' in _ci_text()


def test_pytest_job_uses_signal_timeout():
    # thread-method can't interrupt C-level hangs; signal is required for a
    # completing run on the Linux runner.
    assert '--timeout-method=signal' in _ci_text()


def test_validators_run_before_pytest():
    """validate_proof_links etc. must run on the pristine tree, before pytest,
    so they don't trip over ephemeral proof bundles the suite writes."""
    txt = _ci_text()
    pytest_pos = txt.find('pytest -m "not integration"')
    proof_pos = txt.find('scripts/validate_proof_links.py')
    assert pytest_pos != -1 and proof_pos != -1
    assert proof_pos < pytest_pos, "validate_proof_links must run before pytest"


def test_quarantine_file_exists_and_is_reasoned():
    assert QUARANTINE.exists(), "tests/quarantine.txt must exist"
    lines = QUARANTINE.read_text(encoding="utf-8").splitlines()
    entries = [l for l in lines if l.strip() and not l.lstrip().startswith("#")]
    comments = [l for l in lines if l.lstrip().startswith("#")]
    assert entries, "quarantine has entries"
    # The file must carry human-readable reasons + point at the inventory doc.
    joined = "\n".join(comments)
    assert "HERMETIC_UNIT_SUITE_INVENTORY" in joined
    assert "HG_RUN_QUARANTINE=1" in joined, "escape hatch must be documented in-file"


def test_run_quarantine_escape_hatch_present():
    assert "HG_RUN_QUARANTINE" in CONFTEST.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "marker",
    ["requires_postgres", "requires_redis", "requires_docker", "quarantined"],
)
def test_service_and_quarantine_markers_registered(marker):
    assert marker in PYPROJECT.read_text(encoding="utf-8") or marker in CONFTEST.read_text(encoding="utf-8")
