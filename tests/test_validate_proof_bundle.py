"""
Tests for docs/proofs/validate_proof_bundle.py (Pack 7/8 and legacy proof bundles).
No mocks: uses real file I/O and real validation logic.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Add repo root for imports when running tests from workspace
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import from the script under test (same module interface)
sys.path.insert(0, str(REPO_ROOT / "docs" / "proofs"))
from validate_proof_bundle import validate_bundle  # noqa: E402


def test_legacy_demo_bundle_passes():
    """Legacy investor_demo shape (chat_id, approval_id, timestamp, success) is valid."""
    bundle_dir = REPO_ROOT / "docs" / "proofs" / "out" / "test_bundle"
    if not bundle_dir.is_dir():
        pytest.skip("test_bundle not present")
    ok, msg = validate_bundle(bundle_dir)
    assert ok, msg
    assert msg == "ok"


def test_pack78_bundle_passes(tmp_path):
    """Pack 7/8 bundle with summary, checks, ENVIRONMENT, VERSIONS is valid."""
    (tmp_path / "summary.json").write_text(
        json.dumps({
            "label": "test",
            "started_at": "2026-03-04T12:00:00Z",
            "ended_at": "2026-03-04T12:00:01Z",
            "checks_passed": True,
        }),
        encoding="utf-8",
    )
    (tmp_path / "checks.json").write_text(json.dumps([{"name": "c1", "pass": True}]), encoding="utf-8")
    (tmp_path / "ENVIRONMENT.json").write_text(json.dumps({"git_commit_hash": "abc"}), encoding="utf-8")
    (tmp_path / "VERSIONS.txt").write_text("gateway: 0.1\n", encoding="utf-8")
    ok, msg = validate_bundle(tmp_path)
    assert ok, msg
    assert msg == "ok"


def test_pack78_fails_without_environment(tmp_path):
    """Pack 7/8 bundle without ENVIRONMENT.json fails."""
    (tmp_path / "summary.json").write_text(
        json.dumps({
            "label": "test",
            "started_at": "2026-03-04T12:00:00Z",
            "ended_at": "2026-03-04T12:00:01Z",
            "checks_passed": True,
        }),
        encoding="utf-8",
    )
    (tmp_path / "checks.json").write_text("[]", encoding="utf-8")
    (tmp_path / "VERSIONS.txt").write_text("x: 1\n", encoding="utf-8")
    ok, msg = validate_bundle(tmp_path)
    assert not ok
    assert "ENVIRONMENT.json" in msg


def test_pack78_fails_when_checks_passed_false(tmp_path):
    """Pack 7/8 bundle with checks_passed false fails."""
    (tmp_path / "summary.json").write_text(
        json.dumps({
            "label": "test",
            "started_at": "2026-03-04T12:00:00Z",
            "ended_at": "2026-03-04T12:00:01Z",
            "checks_passed": False,
        }),
        encoding="utf-8",
    )
    (tmp_path / "checks.json").write_text("[]", encoding="utf-8")
    (tmp_path / "ENVIRONMENT.json").write_text('{"git_commit_hash": "x"}', encoding="utf-8")
    (tmp_path / "VERSIONS.txt").write_text("x\n", encoding="utf-8")
    ok, msg = validate_bundle(tmp_path)
    assert not ok
    assert "checks_passed" in msg


def test_not_a_directory_fails():
    """Non-directory path fails."""
    ok, msg = validate_bundle(REPO_ROOT / "docs" / "proofs" / "validate_proof_bundle.py")
    assert not ok
    assert "not a directory" in msg


def test_missing_summary_fails(tmp_path):
    """Directory without summary.json fails."""
    ok, msg = validate_bundle(tmp_path)
    assert not ok
    assert "summary.json" in msg
