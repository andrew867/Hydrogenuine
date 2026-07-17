"""Write PROOF_SCHEMA-compliant bundles for quantum/robotics E2E scenarios."""
from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _git_commit() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except Exception:
        return "unknown"


def write_proof_bundle(
    out_dir: Path,
    *,
    label: str,
    checks: List[Dict[str, Any]],
    summary_extra: Optional[Dict[str, Any]] = None,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    all_pass = all(bool(c.get("pass")) for c in checks)
    summary = {
        "label": label,
        "started_at": started.isoformat().replace("+00:00", "Z"),
        "ended_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "checks_passed": all_pass,
        "track": "quantum_robotics_e2e",
    }
    if summary_extra:
        summary.update(summary_extra)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "checks.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
    (out_dir / "ENVIRONMENT.json").write_text(
        json.dumps(
            {
                "git_commit_hash": _git_commit(),
                "feature_flags": {
                    "HG_EMBODIED_MOCK_MODE": "1",
                    "HG_QUANTUM_SYMMETRY_BREAKING_ENABLED": "true",
                    "HG_QUANTUM_LDPC_VERIFICATION_ENABLED": "true",
                },
                "api_base_urls": "local_pytest",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (out_dir / "VERSIONS.txt").write_text(
        "hg_quantum=tranche9\nhg_embodied=tranche9\npytest=e2e\n",
        encoding="utf-8",
    )
    return out_dir
