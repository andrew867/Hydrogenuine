"""Shared OCF/OIR/MBR gate runner."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

from hg_core.dse.command_log_adapter import record_command
from hg_core.ocf_oir_mbr.proof_bundle import emit_proof_bundle, new_proof_dir


def git_head(workspace: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def run_feature_gate(
    workspace: Path,
    *,
    pack: str,
    gate_id: str,
    feature_check_fn: Callable[[], dict[str, object]],
    test_dirs: list[str],
) -> int:
    proof_dir = new_proof_dir(workspace, pack)
    proof_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    feature_checks = feature_check_fn()
    t0 = time.monotonic()
    test_cmd = subprocess.run(
        [sys.executable, "-m", "pytest", *test_dirs, "-q", "--timeout=180"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    record_command(
        command_log,
        argv=["pytest", *test_dirs, "-q"],
        cwd=workspace,
        exit_code=test_cmd.returncode,
        duration_s=time.monotonic() - t0,
        stdout=test_cmd.stdout,
        stderr=test_cmd.stderr,
    )

    gate_ok = bool(feature_checks.get("ok")) and test_cmd.returncode == 0
    emit_proof_bundle(
        proof_dir,
        pack=pack,
        gate=gate_id,
        head=git_head(workspace),
        artifacts={f"{pack.lower().replace('/', '_')}_checks.json": feature_checks},
        gate_ok=gate_ok,
    )
    gate_result: dict[str, Any] = {
        "gate": gate_id,
        "ok": gate_ok,
        "critical_failures": feature_checks.get("critical_failures", []),
        "proof_dir": str(proof_dir),
    }
    print(json.dumps(gate_result, indent=2))
    return 0 if gate_ok else 1


__all__ = ["run_feature_gate"]
