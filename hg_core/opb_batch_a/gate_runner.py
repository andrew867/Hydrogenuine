"""Shared proof gate runner for Batch OPB-A."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_core.opb_batch_a.checks import OPB_A_SLICES, run_opb_batch_a_checks
from hg_core.proof.command_log import record_command

SLICE_TEST_TARGETS: dict[str, list[str]] = {
    "opb": ["tests/opb", "tests/opb_batch_a/test_all_slices.py::test_each_slice_green"],
    "opb_audit": ["tests/opb/test_operator_power_boundary.py::test_passive_operator_audit"],
    "opb_labels": ["tests/opb/test_operator_power_boundary.py::test_destructive_action_labels_static"],
    "opb_lifecycle": [
        "tests/opb/test_operator_power_boundary.py::test_shutdown_lifecycle_fixture_integration",
        "tests/opb/test_operator_power_boundary.py::test_neighbor_advisory_manifest_static",
    ],
    "all": ["tests/opb", "tests/opb_batch_a"],
}


def run_opb_full_scope_checks() -> dict[str, object]:
    from hg_runtime.operator_power_boundary.advisory_routes import load_neighbor_advisory_manifest
    from hg_runtime.operator_power_boundary.audit import audit_operator_action_events, redact_operator_audit_text
    from hg_runtime.operator_power_boundary.labels import render_destructive_action_labels
    from hg_runtime.operator_power_boundary.lifecycle import integrate_shutdown_packets_fixture

    checks: list[dict[str, object]] = []

    audit = audit_operator_action_events()
    checks.append(
        {
            "check_id": "passive_operator_audit",
            "ok": audit.get("passive_audit_only") is True and audit.get("permission_granted") is False,
            "detail": audit.get("event_count"),
        }
    )
    checks.append(
        {
            "check_id": "privacy_redaction_applied",
            "ok": redact_operator_audit_text("api_key=leaked") == "[REDACTED]",
            "detail": "redact_operator_audit_text",
        }
    )

    labels = render_destructive_action_labels()
    checks.append(
        {
            "check_id": "destructive_labels_static",
            "ok": labels.get("operator_authority_preserved") is True
            and all(item.get("live_plt_dispatch") is False for item in labels.get("labels", [])),
            "detail": labels.get("label_count"),
        }
    )

    lifecycle = integrate_shutdown_packets_fixture()
    checks.append(
        {
            "check_id": "shutdown_non_blockable",
            "ok": lifecycle.get("shutdown_non_blockable") is True
            and lifecycle.get("shutdown_block_refused") is True,
            "detail": lifecycle.get("reason_code"),
        }
    )

    manifest = load_neighbor_advisory_manifest()
    checks.append(
        {
            "check_id": "neighbor_advisory_manifest",
            "ok": manifest.get("permission_granted") is False
            and manifest.get("retention_recommendation_only") == "retention_snapshot_recommendation",
            "detail": manifest.get("route_count"),
        }
    )

    critical_failures = [c["check_id"] for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks}


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


def run_opb_a_gate(workspace: Path, *, slice: str, gate_id: str, proof_subpath: str) -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "operator_power" / proof_subpath / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    checks = run_opb_batch_a_checks(workspace, slice=slice)
    full_scope_checks = run_opb_full_scope_checks()
    combined_ok = checks["ok"] and full_scope_checks["ok"]
    (artifacts_dir / "opb_batch_checks.json").write_text(
        json.dumps(checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (artifacts_dir / "opb_full_scope_checks.json").write_text(
        json.dumps(full_scope_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    test_targets = SLICE_TEST_TARGETS[slice]
    t0 = time.monotonic()
    test_cmd = subprocess.run(
        [sys.executable, "-m", "pytest", *test_targets, "-q", "--timeout=180"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    record_command(
        command_log,
        argv=["pytest", *test_targets, "-q"],
        cwd=workspace,
        exit_code=test_cmd.returncode,
        duration_s=time.monotonic() - t0,
        stdout=test_cmd.stdout,
        stderr=test_cmd.stderr,
    )

    gate_ok = combined_ok and test_cmd.returncode == 0
    gate_result: dict[str, Any] = {
        "gate": gate_id,
        "slice": slice,
        "ok": gate_ok,
        "slices": list(OPB_A_SLICES) if slice == "all" else [slice],
        "verdicts": [
            {
                "check": "opb_batch_checks",
                "verdict": "pass" if checks["ok"] else "fail",
                "ok": checks["ok"],
                "detail": checks,
            },
            {
                "check": "opb_full_scope_checks",
                "verdict": "pass" if full_scope_checks["ok"] else "fail",
                "ok": full_scope_checks["ok"],
                "detail": full_scope_checks,
            },
            {
                "check": "focused_unit_tests",
                "verdict": "pass" if test_cmd.returncode == 0 else "fail",
                "ok": test_cmd.returncode == 0,
            },
        ],
    }
    (proof_dir / "gate_result.json").write_text(json.dumps(gate_result, indent=2), encoding="utf-8")
    (proof_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "ct_proof_bundle_v1",
                "pack": "OPB-A",
                "gate": gate_id,
                "slice": slice,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": f"operator_power/{proof_subpath}",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/opb_batch_checks.json": sha256_file(artifacts_dir / "opb_batch_checks.json"),
                    "artifacts/opb_full_scope_checks.json": sha256_file(
                        artifacts_dir / "opb_full_scope_checks.json"
                    ),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status_lines = [
        f"# OPB-A Operator Power — {slice} — {ts}",
        "",
        f"**Verdict:** {'GREEN' if gate_ok else 'RED'}",
        f"**HEAD:** `{git_head(workspace)}`",
        "",
        "## Checks",
    ]
    if slice == "all":
        for name, slice_result in checks.get("slices", {}).items():
            status_lines.append(f"### {name}")
            for check in slice_result.get("checks", []):
                status_lines.append(
                    f"- {check['check_id']}: {'pass' if check['ok'] else 'fail'} — {check['detail']}"
                )
            status_lines.append("")
    else:
        for check in checks.get("checks", []):
            status_lines.append(
                f"- {check['check_id']}: {'pass' if check['ok'] else 'fail'} — {check['detail']}"
            )
        status_lines.append("")
    (proof_dir / "status.md").write_text("\n".join(status_lines) + "\n", encoding="utf-8")
    print(json.dumps(gate_result, indent=2))
    return 0 if gate_ok else 1


__all__ = ["SLICE_TEST_TARGETS", "run_opb_a_gate", "run_opb_full_scope_checks"]
