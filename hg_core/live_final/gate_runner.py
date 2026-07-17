"""Shared proof gate runner for LIVE-FINAL go/no-go review."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_core.live_final.registry import LIVE_SCOPE_PRIOR_GATES, load_feature_check
from hg_core.proof.command_log import record_command


def git_head(workspace: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def run_live_final_feature_checks(workspace: Path) -> dict[str, object]:
    checks: list[dict[str, object]] = []
    deferred: list[str] = []
    implemented_count = 0

    for entry in LIVE_SCOPE_PRIOR_GATES:
        gate_path = workspace / entry.gate_script
        audit_path = workspace / entry.audit_doc
        gate_exists = gate_path.is_file()
        audit_exists = audit_path.is_file()

        if not gate_exists:
            if entry.required_for_final:
                checks.append(
                    {
                        "check_id": f"gate_exists_{entry.tranche_id}",
                        "ok": False,
                        "detail": f"missing gate script: {entry.gate_script}",
                    }
                )
            else:
                deferred.append(entry.tranche_id)
                checks.append(
                    {
                        "check_id": f"gate_deferred_{entry.tranche_id}",
                        "ok": True,
                        "detail": f"deferred (not yet implemented): {entry.gate_script}",
                    }
                )
            continue

        implemented_count += 1
        checks.append(
            {
                "check_id": f"gate_exists_{entry.tranche_id}",
                "ok": True,
                "detail": entry.gate_script,
            }
        )
        checks.append(
            {
                "check_id": f"audit_exists_{entry.tranche_id}",
                "ok": audit_exists,
                "detail": entry.audit_doc if audit_exists else f"missing audit: {entry.audit_doc}",
            }
        )

        try:
            feature_fn = load_feature_check(entry)
            feature_result = feature_fn()
            checks.append(
                {
                    "check_id": f"feature_checks_{entry.tranche_id}",
                    "ok": feature_result.get("ok") is True,
                    "detail": feature_result.get("critical_failures", []),
                }
            )
        except Exception as exc:
            checks.append(
                {
                    "check_id": f"feature_checks_{entry.tranche_id}",
                    "ok": False,
                    "detail": str(exc),
                }
            )

    checks.append(
        {
            "check_id": "implemented_gate_count",
            "ok": implemented_count >= 8,
            "detail": implemented_count,
        }
    )
    checks.append(
        {
            "check_id": "registry_complete",
            "ok": len(LIVE_SCOPE_PRIOR_GATES) == 11,
            "detail": len(LIVE_SCOPE_PRIOR_GATES),
        }
    )

    critical_failures = [str(c["check_id"]) for c in checks if not c["ok"]]
    return {
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": checks,
        "implemented_count": implemented_count,
        "deferred_tranches": deferred,
    }


def run_live_final_gate(workspace: Path, *, gate_id: str = "live_scope_final_go_no_go_v1") -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "live_final" / "LIVE-FINAL" / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    feature_checks = run_live_final_feature_checks(workspace)
    (artifacts_dir / "live_final_feature_checks.json").write_text(
        json.dumps(feature_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    gate_ok = feature_checks["ok"]
    gate_result: dict[str, Any] = {
        "gate": gate_id,
        "ok": gate_ok,
        "verdicts": [
            {
                "check": "live_final_feature_checks",
                "verdict": "pass" if feature_checks["ok"] else "fail",
                "ok": feature_checks["ok"],
                "detail": feature_checks,
            },
        ],
        "critical_failures": feature_checks.get("critical_failures", []),
        "deferred_tranches": feature_checks.get("deferred_tranches", []),
        "proof_dir": str(proof_dir),
    }
    (proof_dir / "gate_result.json").write_text(json.dumps(gate_result, indent=2), encoding="utf-8")
    (proof_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "ct_proof_bundle_v1",
                "pack": "LIVE-FINAL",
                "gate": gate_id,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": "live_final/LIVE-FINAL",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/live_final_feature_checks.json": sha256_file(
                        artifacts_dir / "live_final_feature_checks.json"
                    ),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status_lines = [
        f"# LIVE-FINAL Go/No-Go Review — {ts}",
        "",
        f"**Verdict:** {'GREEN' if gate_ok else 'RED'}",
        f"**HEAD:** `{git_head(workspace)}`",
        f"**Implemented gates:** {feature_checks.get('implemented_count', 0)}",
        "",
        "## Checks",
    ]
    for check in feature_checks.get("checks", []):
        status_lines.append(
            f"- {check['check_id']}: {'pass' if check['ok'] else 'fail'} — {check['detail']}"
        )
    deferred = feature_checks.get("deferred_tranches", [])
    if deferred:
        status_lines.extend(["", "## Deferred tranches", ", ".join(deferred)])
    (proof_dir / "status.md").write_text("\n".join(status_lines) + "\n", encoding="utf-8")

    print(json.dumps(gate_result, indent=2))
    return 0 if gate_ok else 1


__all__ = ["run_live_final_feature_checks", "run_live_final_gate"]
