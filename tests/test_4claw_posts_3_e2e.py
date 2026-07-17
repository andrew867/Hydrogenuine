"""
E2E tests for 4claw_posts_3: REAL HTTP, real production code path. No mocks.
Primary: real code path (use_fake=False). Offline/CI fallback: use_fake=True only when real 4claw unavailable.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def test_4claw_posts_3_real_http_real_code_path(tmp_path: Path) -> None:
    """PRIMARY: Real HTTP to server (fake or real 4claw), use_fake=False (production path). INTEGRATION_MODE=REAL_SANDBOX."""
    server_proc = subprocess.Popen(
        [sys.executable, "-m", "scripts.proofs.fourclaw_fake_server", "--port", "5099"],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(0.5)
        from scripts.proofs.fourclaw_posts_3 import run

        run(tmp_path, fourclaw_base_url="http://127.0.0.1:5099", use_fake=False)
        assert (tmp_path / "summary.json").exists()
        summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
        assert summary.get("checks_passed") is True
        assert len(summary.get("post_ids", [])) == 3
        assert (tmp_path / "INTEGRATION_MODE.txt").read_text(encoding="utf-8").strip() == "REAL_SANDBOX"
        assert (tmp_path / "APPROVAL_EVIDENCE.json").exists()
        assert (tmp_path / "4CLAW_POSTS_EVIDENCE.md").exists()
    finally:
        server_proc.terminate()
        server_proc.wait(timeout=5)


@pytest.mark.offline
def test_4claw_posts_3_fake_ci_fallback_only(tmp_path: Path) -> None:
    """OFFLINE FALLBACK: use_fake=True only when real 4claw unavailable. Records FAKE_CI_ONLY."""
    server_proc = subprocess.Popen(
        [sys.executable, "-m", "scripts.proofs.fourclaw_fake_server", "--port", "5099"],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(0.5)
        from scripts.proofs.fourclaw_posts_3 import run

        run(tmp_path, fourclaw_base_url="http://127.0.0.1:5099", use_fake=True)
        assert (tmp_path / "summary.json").exists()
        summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
        assert summary.get("checks_passed") is True
        assert len(summary.get("post_ids", [])) == 3
        assert (tmp_path / "INTEGRATION_MODE.txt").read_text(encoding="utf-8").strip() == "FAKE_CI_ONLY"
        assert (tmp_path / "APPROVAL_EVIDENCE.json").exists()
        ev = json.loads((tmp_path / "APPROVAL_EVIDENCE.json").read_text(encoding="utf-8"))
        assert ev.get("match") is True
    finally:
        server_proc.terminate()
        server_proc.wait(timeout=5)


def test_4claw_via_run_proofs_real_code_path(tmp_path: Path) -> None:
    """PRIMARY: run_proofs.py 4claw_posts_3 WITHOUT --use-fixtures (real production path). Server started here."""
    server_proc = subprocess.Popen(
        [sys.executable, "-m", "scripts.proofs.fourclaw_fake_server", "--port", "5099"],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(0.5)
        r = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "run_proofs.py"),
                "--label",
                "4claw_posts_3",
                "--base-url",
                "http://localhost:8080",
                "--api-key",
                "test-key",
                "--fourclaw-base-url",
                "http://127.0.0.1:5099",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
            env={**__import__("os").environ, "HG_API_KEY": "test-key"},
        )
        assert r.returncode == 0, (r.stdout, r.stderr)
        idx = json.loads((REPO_ROOT / "docs" / "proofs" / "index.json").read_text(encoding="utf-8"))
        folder = idx.get("latest", {}).get("4claw_posts_3")
        assert folder
        bundle_dir = Path(folder)
        assert (bundle_dir / "summary.json").exists()
        summary = json.loads((bundle_dir / "summary.json").read_text(encoding="utf-8"))
        assert summary.get("checks_passed") is True
        assert (bundle_dir / "INTEGRATION_MODE.txt").read_text(encoding="utf-8").strip() == "REAL_SANDBOX"
        assert (bundle_dir / "4CLAW_POSTS_EVIDENCE.md").exists()
    finally:
        server_proc.terminate()
        server_proc.wait(timeout=5)
