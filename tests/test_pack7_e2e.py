"""
E2E for Pack 7: run proof, validate bundle, run doc embed.
Requires HG_API_KEY. Skips if gateway unreachable. No mocks.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(scope="module")
def api_key():
    key = os.environ.get("HG_API_KEY")
    if not key:
        pytest.skip("HG_API_KEY not set")
    return key


def test_pack7_e2e_run_proof_validate_embed(api_key: str) -> None:
    """Run health proof, validate bundle from index, run embed script."""
    run_proofs = REPO_ROOT / "scripts" / "run_proofs.py"
    validator = REPO_ROOT / "docs" / "proofs" / "validate_proof_bundle.py"
    embed = REPO_ROOT / "scripts" / "embed_proofs_into_docs.py"
    index_path = REPO_ROOT / "docs" / "proofs" / "index.json"

    r = subprocess.run(
        [
            sys.executable,
            str(run_proofs),
            "--label",
            "health",
            "--base-url",
            "http://localhost:8080",
            "--api-key",
            api_key,
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    # 0 = passed, 2 = checks_passed false (e.g. gateway down)
    assert r.returncode in (0, 2), (r.stdout, r.stderr)

    assert index_path.exists(), "index.json should exist after run"
    idx = json.loads(index_path.read_text(encoding="utf-8"))
    assert "latest" in idx and "health" in idx["latest"]
    folder = idx["latest"]["health"]
    bundle_dir = Path(folder)
    assert bundle_dir.is_dir(), f"Bundle dir should exist: {folder}"

    r2 = subprocess.run(
        [sys.executable, str(validator), str(bundle_dir)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=10,
    )
    # Validator passes only when checks_passed is true (gateway was up)
    if r.returncode == 0:
        assert r2.returncode == 0, f"Bundle should be valid when proof passed: {r2.stderr}"

    r3 = subprocess.run(
        [sys.executable, str(embed), "--latest", "health"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert r3.returncode == 0, f"Embed should succeed: {r3.stderr}"
