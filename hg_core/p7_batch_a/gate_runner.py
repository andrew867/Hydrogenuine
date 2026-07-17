"""Shared proof gate runner for Batch P7-A."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_core.proof.command_log import record_command
from hg_core.p7_batch_a.checks import P7_A_SLICES, run_p7_batch_a_checks

SLICE_TEST_TARGETS: dict[str, list[str]] = {
    "exciton": ["tests/operator_product_surface", "tests/p7_batch_a/test_all_slices.py::test_each_slice_green"],
    "exciton_audit": ["tests/operator_product_surface/test_operator_surface.py::test_passive_surface_polish_audit"],
    "exciton_queue": ["tests/operator_product_surface/test_operator_surface.py::test_fake_operator_action_queue"],
    "exciton_proposal": [
        "tests/operator_product_surface/test_operator_surface.py::test_authority_chain_fake_proposal"
    ],
    "plt": ["tests/operator_product_surface/test_operator_surface.py::test_plt_surface_polish_descriptors"],
    "all": ["tests/operator_product_surface", "tests/p7_batch_a"],
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


def run_exciton_surface_checks(workspace: Path) -> dict[str, object]:
    from hg_core.exciton_cluster.errors import (
        REFUSED_EXCITON_AS_AUTHORITY,
        REFUSED_NATIVE_UI_OFF_BACKBURNER,
        REFUSED_STALE_APPROVAL,
        ExcitonValidationError,
    )
    from hg_core.exciton_cluster.no_authority import check_exciton_import_fences
    from hg_runtime.operator_product_surface import (
        FIXTURE_CLOCK,
        analyze_fixture_bundles,
        assert_exciton_backburner_boundary,
        audit_surface_polish_claims,
        enqueue_fixture_queue,
        load_fixture_bundles,
        load_plt_polish_descriptors,
        refuse_action_as_permission,
        refuse_native_ui_off_backburner,
        route_operator_bundle,
    )
    from hg_runtime.operator_product_surface.classifier import classify_polish_risk
    from hg_runtime.operator_product_surface.redaction import redact_surface_text
    from hg_runtime.operator_product_surface.types import surface_descriptor_from_fixture

    checks: list[dict[str, object]] = []

    fences_ok, fence_detail = check_exciton_import_fences()
    checks.append(
        {
            "check_id": "import_fences",
            "ok": fences_ok,
            "detail": fence_detail if not fences_ok else "clean",
        }
    )

    backburner = assert_exciton_backburner_boundary()
    checks.append(
        {
            "check_id": "backburner_guard_active",
            "ok": backburner.get("backburner_guard_active") is True
            and backburner.get("native_ui_deferred") is True,
            "detail": backburner,
        }
    )

    native_refused = False
    try:
        refuse_native_ui_off_backburner(allow_native=True)
    except ExcitonValidationError as exc:
        native_refused = exc.code == REFUSED_NATIVE_UI_OFF_BACKBURNER
    checks.append(
        {
            "check_id": "native_ui_refused_off_backburner",
            "ok": native_refused,
            "detail": REFUSED_NATIVE_UI_OFF_BACKBURNER,
        }
    )

    analysis = analyze_fixture_bundles(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "fixture_bundles_analyzed",
            "ok": analysis.get("all_advisory") is True and int(analysis.get("bundle_count", 0)) >= 9,
            "detail": analysis.get("bundle_count"),
        }
    )

    bundles = load_fixture_bundles()
    observe = next(b for b in bundles if b["bundle_id"] == "ops-exciton-observe-pulse")
    observe_result = route_operator_bundle(observe, observed_at=FIXTURE_CLOCK)
    decision = observe_result.get("route", {}).get("action_decision", {})  # type: ignore[union-attr]
    checks.append(
        {
            "check_id": "observe_pulse_advisory_display",
            "ok": isinstance(decision, dict) and decision.get("decision") == "advisory_display_only",
            "detail": decision.get("decision") if isinstance(decision, dict) else None,
        }
    )

    pause = next(b for b in bundles if b["bundle_id"] == "ops-exciton-hash-bound-pause")
    pause_result = route_operator_bundle(pause, observed_at=FIXTURE_CLOCK)
    pause_decision = pause_result.get("route", {}).get("action_decision", {})  # type: ignore[union-attr]
    checks.append(
        {
            "check_id": "hash_bound_pause_recorded",
            "ok": isinstance(pause_decision, dict)
            and pause_decision.get("decision") == "hash_bound_request_recorded",
            "detail": pause_decision.get("decision") if isinstance(pause_decision, dict) else None,
        }
    )

    stale = next(b for b in bundles if b["bundle_id"] == "ops-exciton-stale-approval")
    stale_result = route_operator_bundle(stale, observed_at=FIXTURE_CLOCK)
    stale_decision = stale_result.get("route", {}).get("action_decision", {})  # type: ignore[union-attr]
    checks.append(
        {
            "check_id": "stale_approval_refused",
            "ok": stale_result.get("status") == "refused"
            and isinstance(stale_decision, dict)
            and stale_decision.get("decision") == "fail_closed",
            "detail": stale_decision.get("reason") if isinstance(stale_decision, dict) else None,
        }
    )

    polish = next(b for b in bundles if b["bundle_id"] == "ops-polish-safety-claim")
    polish_result = route_operator_bundle(polish, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "polish_implies_safety_contained",
            "ok": polish_result.get("status") == "contained",
            "detail": polish_result.get("containment", {}).get("polish_risk"),  # type: ignore[union-attr]
        }
    )

    approve = next(b for b in bundles if b["bundle_id"] == "ops-approve-authority-chain")
    approve_result = route_operator_bundle(approve, observed_at=FIXTURE_CLOCK)
    approve_decision = approve_result.get("route", {}).get("action_decision", {})  # type: ignore[union-attr]
    checks.append(
        {
            "check_id": "approve_requires_authority_chain",
            "ok": isinstance(approve_decision, dict)
            and approve_decision.get("decision") == "require_authority_chain",
            "detail": approve_decision.get("decision") if isinstance(approve_decision, dict) else None,
        }
    )

    proposal = approve_result.get("authority_chain_proposal")
    checks.append(
        {
            "check_id": "fake_authority_chain_proposal",
            "ok": isinstance(proposal, dict)
            and proposal.get("fake_dispatch_only") is True
            and proposal.get("proposal", {}).get("permit_minted") is False,  # type: ignore[union-attr]
            "detail": "fake_dispatch_only",
        }
    )

    audit = audit_surface_polish_claims(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "passive_surface_polish_audit",
            "ok": audit.get("passive_audit_only") is True and int(audit.get("event_count", 0)) >= 9,
            "detail": audit.get("event_count"),
        }
    )

    queue_result = enqueue_fixture_queue()
    checks.append(
        {
            "check_id": "fake_operator_action_queue",
            "ok": queue_result.get("fake_queue_only") is True and int(queue_result.get("queue_depth", 0)) >= 3,
            "detail": queue_result.get("queue_depth"),
        }
    )

    plt_result = load_plt_polish_descriptors()
    checks.append(
        {
            "check_id": "plt_surface_polish_descriptors",
            "ok": plt_result.get("writes_events_only") is True
            and int(plt_result.get("surface_count", 0)) >= 5,
            "detail": plt_result.get("surface_count"),
        }
    )

    redacted = redact_surface_text("token api_key=secret-value here")
    checks.append(
        {
            "check_id": "secret_redaction",
            "ok": "api_key=" not in redacted and "[REDACTED]" in redacted,
            "detail": redacted,
        }
    )

    descriptor = surface_descriptor_from_fixture(
        {
            "surface_descriptor_id": "ops-surf-risk-test",
            "title": "Friendly green UI means safe panel",
            "safety_disclaimer_visible": "true",
        }
    )
    checks.append(
        {
            "check_id": "polish_risk_classifier",
            "ok": classify_polish_risk(descriptor) == "polish_implies_safety",
            "detail": classify_polish_risk(descriptor),
        }
    )

    action_refused = False
    try:
        refuse_action_as_permission(treat_as_authority=True)
    except ExcitonValidationError as exc:
        action_refused = exc.code == REFUSED_EXCITON_AS_AUTHORITY
    checks.append(
        {
            "check_id": "surface_not_authority",
            "ok": action_refused,
            "detail": REFUSED_EXCITON_AS_AUTHORITY,
        }
    )

    critical_failures = [c["check_id"] for c in checks if not c["ok"]]
    return {
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": checks,
    }


def run_p7_a_gate(workspace: Path, *, slice: str, gate_id: str, proof_subpath: str) -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "operator_product_surface" / proof_subpath / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    batch_checks = run_p7_batch_a_checks(workspace, slice=slice)
    surface_checks = run_exciton_surface_checks(workspace)
    combined = {
        "ok": batch_checks["ok"] and surface_checks["ok"],
        "batch_checks": batch_checks,
        "surface_checks": surface_checks,
        "critical_failures": list(batch_checks.get("critical_failures", []))
        + list(surface_checks.get("critical_failures", [])),
    }
    (artifacts_dir / "p7_batch_checks.json").write_text(
        json.dumps(batch_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (artifacts_dir / "exciton_surface_checks.json").write_text(
        json.dumps(surface_checks, indent=2, sort_keys=True) + "\n",
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
        "slices": list(P7_A_SLICES) if slice == "all" else [slice],
        "verdicts": [
            {
                "check": "p7_batch_checks",
                "verdict": "pass" if batch_checks["ok"] else "fail",
                "ok": batch_checks["ok"],
                "detail": batch_checks,
            },
            {
                "check": "exciton_surface_checks",
                "verdict": "pass" if surface_checks["ok"] else "fail",
                "ok": surface_checks["ok"],
                "detail": surface_checks,
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
                "pack": "P7-A",
                "gate": gate_id,
                "slice": slice,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": f"operator_product_surface/{proof_subpath}",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/p7_batch_checks.json": sha256_file(artifacts_dir / "p7_batch_checks.json"),
                    "artifacts/exciton_surface_checks.json": sha256_file(
                        artifacts_dir / "exciton_surface_checks.json"
                    ),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status_lines = [
        f"# P7-A Operator Product Surface — {slice} — {ts}",
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


__all__ = ["SLICE_TEST_TARGETS", "run_exciton_surface_checks", "run_p7_a_gate"]
