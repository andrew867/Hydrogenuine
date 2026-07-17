#!/usr/bin/env python3
"""
Pack 5: E2E harness entry point. Run after compose is up.
Calls demo_smoke, validates proof bundle, writes proof dir for CI artifact upload.
Usage: python tests/e2e/run_e2e.py [--proof-dir DIR] [--gateway-url URL]
Env E2E_PROOF_BUNDLE_DIR overrides --proof-dir for CI.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--proof-dir", default=os.environ.get("E2E_PROOF_BUNDLE_DIR"), help="Proof bundle output dir")
    ap.add_argument("--gateway-url", default="http://localhost:8000")
    args = ap.parse_args()

    if not args.proof_dir:
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        args.proof_dir = str(REPO_ROOT / "docs" / "proofs" / "out" / f"e2e_{ts}")
    proof_dir = Path(args.proof_dir)
    proof_dir.mkdir(parents=True, exist_ok=True)

    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    r = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "demo_smoke.py"),
            str(proof_dir),
            "--gateway-url", args.gateway_url,
            "--workspace", str(REPO_ROOT),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        timeout=120,
    )
    if r.returncode != 0:
        print("E2E demo_smoke failed", file=sys.stderr)
        return r.returncode

    r2 = subprocess.run(
        [sys.executable, str(REPO_ROOT / "docs" / "proofs" / "validate_proof_bundle.py"), str(proof_dir)],
        cwd=str(REPO_ROOT),
        env=env,
    )
    if r2.returncode != 0:
        print("E2E proof bundle validation failed", file=sys.stderr)
        return r2.returncode
    print("E2E proof bundle:", proof_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
