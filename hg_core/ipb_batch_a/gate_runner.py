"""Shared proof gate runner for Batch IPB-A — full slice scope."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_core.ipb_batch_a.checks import IPB_A_SLICES, run_ipb_batch_a_checks
from hg_core.proof.command_log import record_command

SLICE_TEST_TARGETS: dict[str, list[str]] = {
    "ipb": ["tests/ipb", "tests/ipb_batch_a/test_all_slices.py::test_each_slice_green"],
    "ipb_audit": ["tests/ipb/test_internal_power_boundary.py::test_passive_internal_decision_audit"],
    "ipb_advisory": ["tests/ipb/test_internal_power_boundary.py::test_bounded_wait_silence_retry_recommendations"],
    "ipb_policy": ["tests/ipb/test_internal_power_boundary.py::test_authority_chain_fake_proposal"],
    "ipb_extras": ["tests/ipb/test_internal_power_boundary.py::test_neighbor_fixture_integration"],
    "all": ["tests/ipb", "tests/ipb_batch_a"],
}


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


def run_ipb_full_scope_checks() -> dict[str, object]:
    from hg_runtime.internal_power_boundary.advisory import record_bounded_recommendations
    from hg_runtime.internal_power_boundary.audit import audit_internal_decisions
    from hg_runtime.internal_power_boundary.evaluator import evaluate_internal_decision
    from hg_runtime.internal_power_boundary.neighbor_integration import integrate_neighbor_fixture_routes
    from hg_runtime.internal_power_boundary.proposal import dispatch_local_decision_proposal
    from hg_runtime.internal_power_boundary.types import FIXTURE_CLOCK, internal_decision_from_fixture

    checks: list[dict[str, object]] = []

    audit = audit_internal_decisions(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "passive_internal_decision_audit",
            "ok": audit.get("passive_audit_only") is True
            and audit.get("permission_granted") is False
            and int(audit.get("event_count", 0)) >= 6,
            "detail": audit.get("event_count"),
        }
    )

    advisory = record_bounded_recommendations(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "bounded_recommendations_recorded",
            "ok": advisory.get("runtime_action_taken") is False
            and advisory.get("permission_granted") is False
            and int(advisory.get("recommendation_count", 0)) >= 3,
            "detail": advisory.get("recommendation_count"),
        }
    )

    decision = internal_decision_from_fixture(
        {"decision_id": "ipb-gate-proposal", "decision_class": "local_observe"}
    )
    evaluation = evaluate_internal_decision(decision, observed_at=FIXTURE_CLOCK)
    proposal = dispatch_local_decision_proposal(decision, evaluation)
    checks.append(
        {
            "check_id": "fake_authority_chain_proposal",
            "ok": isinstance(proposal, dict)
            and proposal.get("fake_dispatch_only") is True
            and proposal.get("proposal", {}).get("permit_minted") is False,  # type: ignore[union-attr]
            "detail": "fake_dispatch_only",
        }
    )

    integration = integrate_neighbor_fixture_routes(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "neighbor_fixture_routes_integrated",
            "ok": integration.get("all_integrations_non_authority") is True,
            "detail": integration.get("integration_count"),
        }
    )

    critical_failures = [c["check_id"] for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks}


def run_ipb_a_gate(workspace: Path, *, slice: str, gate_id: str, proof_subpath: str) -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "internal_power" / proof_subpath / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    batch_checks = run_ipb_batch_a_checks(workspace, slice=slice)
    full_scope_checks = run_ipb_full_scope_checks() if slice == "all" else {"ok": True, "critical_failures": [], "checks": []}
    combined = {
        "ok": batch_checks["ok"] and full_scope_checks["ok"],
        "batch_checks": batch_checks,
        "full_scope_checks": full_scope_checks,
        "critical_failures": list(batch_checks.get("critical_failures", []))
        + list(full_scope_checks.get("critical_failures", [])),
    }
    (artifacts_dir / "ipb_batch_checks.json").write_text(
        json.dumps(batch_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (artifacts_dir / "ipb_full_scope_checks.json").write_text(
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

    gate_ok = combined["ok"] and test_cmd.returncode == 0
    gate_result: dict[str, Any] = {
        "gate": gate_id,
        "slice": slice,
        "ok": gate_ok,
        "slices": list(IPB_A_SLICES) if slice == "all" else [slice],
        "verdicts": [
            {
                "check": "ipb_batch_checks",
                "verdict": "pass" if batch_checks["ok"] else "fail",
                "ok": batch_checks["ok"],
                "detail": batch_checks,
            },
            {
                "check": "ipb_full_scope_checks",
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
                "pack": "IPB-A",
                "gate": gate_id,
                "slice": slice,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": f"internal_power/{proof_subpath}",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/ipb_batch_checks.json": sha256_file(artifacts_dir / "ipb_batch_checks.json"),
                    "artifacts/ipb_full_scope_checks.json": sha256_file(
                        artifacts_dir / "ipb_full_scope_checks.json"
                    ),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status_lines = [
        f"# IPB-A Internal Power — {slice} — {ts}",
        "",
        f"**Verdict:** {'GREEN' if gate_ok else 'RED'}",
        f"**HEAD:** `{git_head(workspace)}`",
        "",
        "## Checks",
    ]
    if slice == "all":
        for name, slice_result in batch_checks.get("slices", {}).items():
            status_lines.append(f"### {name}")
            for check in slice_result.get("checks", []):
                status_lines.append(
                    f"- {check['check_id']}: {'pass' if check['ok'] else 'fail'} — {check['detail']}"
                )
            status_lines.append("")
    else:
        for check in batch_checks.get("checks", []):
            status_lines.append(
                f"- {check['check_id']}: {'pass' if check['ok'] else 'fail'} — {check['detail']}"
            )
        status_lines.append("")
    (proof_dir / "status.md").write_text("\n".join(status_lines) + "\n", encoding="utf-8")
    print(json.dumps(gate_result, indent=2))
    return 0 if gate_ok else 1


__all__ = ["SLICE_TEST_TARGETS", "run_ipb_a_gate", "run_ipb_full_scope_checks"]
