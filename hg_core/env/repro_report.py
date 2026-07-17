"""Reproducibility report with versions and hashes (CT-16 ENV)."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_core.env.deps import lockfile_hash
from hg_core.env.doctor import run_env_doctor
from hg_core.env.manifest import load_manifest


def _git_head(workspace: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def build_repro_report(workspace: Path, *, mode: str = "baseline") -> dict[str, Any]:
    manifest = load_manifest(workspace=workspace)
    doctor = run_env_doctor(workspace, mode=mode, manifest=manifest)
    lock_path = workspace / manifest.package_lock_path
    report = {
        "schema": "env_repro_report_v1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "head": _git_head(workspace),
        "manifest_hash": manifest.manifest_hash,
        "package_lock": {
            "path": manifest.package_lock_path,
            "hash": lockfile_hash(lock_path) if lock_path.exists() else "missing",
        },
        "python": {
            "version": sys.version.split()[0],
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
        "doctor_ok": doctor.ok,
        "doctor_detail": doctor.detail,
        "baseline_commands": list(manifest.baseline_commands),
        "doctor_report": doctor.report,
    }
    body = json.dumps(report, sort_keys=True)
    report["report_hash"] = f"sha256:{hashlib.sha256(body.encode('utf-8')).hexdigest()}"
    return report


__all__ = ["build_repro_report"]
