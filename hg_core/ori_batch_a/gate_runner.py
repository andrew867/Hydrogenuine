"""Shared proof gate runner for Batch ORI-A."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_core.ori_batch_a.checks import ORI_A_SLICES, run_ori_batch_a_checks
from hg_core.proof.command_log import record_command

SLICE_TEST_TARGETS: dict[str, list[str]] = {
    "ori": ["tests/ori", "tests/ori_batch_a/test_all_slices.py::test_each_slice_green"],
    "ori_audit": ["tests/ori/test_operator_review_intake.py::test_passive_review_audit"],
    "ori_digest": ["tests/ori/test_operator_review_intake.py::test_operator_digest_fixture"],
    "ori_integration": ["tests/ori/test_operator_review_intake.py::test_fixture_route_integration"],
    "all": ["tests/ori", "tests/ori_batch_a"],
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


def run_ori_iam_binding_checks() -> dict[str, object]:
    from hg_core.iam.registry import clear_registry_cache, load_registry
    from hg_runtime.operator_review_intake import FIXTURE_CLOCK, receipt_from_fixture
    from hg_runtime.operator_review_intake.validator import evaluate_operator_review_receipt

    clear_registry_cache()
    load_registry()
    checks: list[dict[str, object]] = []
    future_expiry = "2026-06-15T12:00:00.000000Z"
    past_expiry = "2026-06-13T12:00:00.000000Z"

    valid = receipt_from_fixture(
        {
            "receipt_id": "gate-valid",
            "operator_action": "approved",
            "operator_ref": "op:local",
            "approval_scope": "approve_change",
            "approval_expires_at": future_expiry,
        }
    )
    valid_result = evaluate_operator_review_receipt(valid, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "iam_valid_approval_bound",
            "ok": valid_result.get("evidence_admissible") is True,
            "detail": valid_result.get("reason_code"),
        }
    )

    bare = receipt_from_fixture(
        {
            "receipt_id": "gate-bare",
            "operator_action": "approved",
            "operator_ref": "bob",
            "approval_scope": "approve_change",
            "approval_expires_at": future_expiry,
        }
    )
    bare_result = evaluate_operator_review_receipt(bare, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "iam_bare_operator_inert",
            "ok": bare_result.get("status") == "inert",
            "detail": bare_result.get("reason_code"),
        }
    )

    stale = receipt_from_fixture(
        {
            "receipt_id": "gate-stale",
            "operator_action": "approved",
            "operator_ref": "op:local",
            "approval_scope": "approve_change",
            "approval_expires_at": past_expiry,
        }
    )
    stale_result = evaluate_operator_review_receipt(stale, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "iam_stale_approval_inert",
            "ok": stale_result.get("status") == "inert",
            "detail": stale_result.get("reason_code"),
        }
    )

    critical_failures = [c["check_id"] for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks}


def run_ori_full_scope_checks() -> dict[str, object]:
    from hg_runtime.operator_review_intake.audit import audit_review_events
    from hg_runtime.operator_review_intake.digest import render_operator_digest_fixture
    from hg_runtime.operator_review_intake.integration import integrate_fixture_routes

    checks: list[dict[str, object]] = []

    audit = audit_review_events()
    checks.append(
        {
            "check_id": "passive_review_audit",
            "ok": audit.get("passive_audit_only") is True and audit.get("permission_granted") is False,
            "detail": audit.get("event_count"),
        }
    )

    digest = render_operator_digest_fixture()
    checks.append(
        {
            "check_id": "digest_is_not_approval",
            "ok": digest.get("digest_is_not_approval") is True and digest.get("permission_granted") is False,
            "detail": digest.get("digest_item_count"),
        }
    )

    integration = integrate_fixture_routes()
    checks.append(
        {
            "check_id": "fixture_routes_integrated",
            "ok": integration.get("all_receipts_non_authority") is True,
            "detail": integration.get("route_count"),
        }
    )

    critical_failures = [c["check_id"] for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks}


def run_ori_intake_checks() -> dict[str, object]:
    from hg_core.iam.registry import clear_registry_cache, load_registry
    from hg_core.ori_cluster.no_authority import check_ori_import_fences
    from hg_runtime.operator_review_intake import (
        FIXTURE_CLOCK,
        analyze_fixture_bundle,
        evaluate_expired_review,
        evaluate_silence_policy,
        load_static_fixture_requests,
        ori_receipt_is_not_permit_authority,
        process_review_queue,
        receipt_from_fixture,
        record_operator_response,
        review_request_from_fixture,
        verify_ori_approval_evidence,
    )

    clear_registry_cache()
    load_registry()
    checks: list[dict[str, object]] = []

    bundle = analyze_fixture_bundle(observed_at=FIXTURE_CLOCK)
    queue = bundle.get("queue", {})
    if isinstance(queue, dict):
        checks.append(
            {
                "check_id": "fixture_sources_opb_ipb_arb_egi",
                "ok": all(bundle.get(k) for k in ("has_opb", "has_ipb", "has_arb", "has_egi")),
                "detail": bundle.get("source_modules"),
            }
        )
        dedupe = queue.get("dedupe", {})
        if isinstance(dedupe, dict):
            checks.append(
                {
                    "check_id": "dedupe_suppresses_duplicates",
                    "ok": int(dedupe.get("suppressed_count", 0)) >= 1,
                    "detail": dedupe.get("suppressed_count"),
                }
            )
            checks.append(
                {
                    "check_id": "critical_never_suppressed",
                    "ok": dedupe.get("critical_never_suppressed") is True,
                    "detail": dedupe.get("critical_never_suppressed"),
                }
            )
        batching = queue.get("batching", {})
        if isinstance(batching, dict):
            batches = batching.get("batches", [])
            checks.append(
                {
                    "check_id": "low_priority_batched",
                    "ok": isinstance(batches, list) and len(batches) >= 1,
                    "detail": len(batches) if isinstance(batches, list) else 0,
                }
            )
        priority = queue.get("priority", {})
        if isinstance(priority, dict):
            checks.append(
                {
                    "check_id": "critical_escalated",
                    "ok": int(priority.get("critical_count", 0)) >= 1,
                    "detail": priority.get("critical_count"),
                }
            )
            checks.append(
                {
                    "check_id": "priority_not_permission",
                    "ok": priority.get("permission_granted") is False,
                    "detail": priority.get("reason_code_priority_marker"),
                }
            )
        overload = queue.get("overload", {})
        if isinstance(overload, dict):
            checks.append(
                {
                    "check_id": "overload_signal_recorded",
                    "ok": overload.get("overload_signal") is not None,
                    "detail": overload.get("overload_level"),
                }
            )

    requests = load_static_fixture_requests()
    silence = evaluate_silence_policy(requests[0], observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "silence_not_approval",
            "ok": silence.get("approval_implied") is False and silence.get("permission_granted") is False,
            "detail": silence.get("reason_code"),
        }
    )

    expired_req = review_request_from_fixture(
        {
            "review_request_id": "ori-expired",
            "source_module": "IPB",
            "review_type": "clarification",
            "summary": "expired review fixture",
            "expires_at": "2026-06-13T12:00:00.000000Z",
        }
    )
    expired = evaluate_expired_review(expired_req, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "expiry_not_approval",
            "ok": expired.get("approval_implied") is False and expired.get("permission_granted") is False,
            "detail": expired.get("reason_code"),
        }
    )

    bare_receipt = receipt_from_fixture(
        {
            "receipt_id": "gate-bare",
            "operator_action": "approved",
            "operator_ref": "bob",
            "approval_scope": "approve_change",
            "approval_expires_at": "2026-06-15T12:00:00.000000Z",
        }
    )
    downstream = verify_ori_approval_evidence(bare_receipt, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "receipt_not_permit",
            "ok": downstream.get("permission_granted") is False
            and ori_receipt_is_not_permit_authority(bare_receipt, observed_at=FIXTURE_CLOCK),
            "detail": downstream.get("reason_code"),
        }
    )

    response = record_operator_response(
        receipt_from_fixture({"receipt_id": "gate-defer", "operator_action": "deferred"}),
        observed_at=FIXTURE_CLOCK,
    )
    checks.append(
        {
            "check_id": "explicit_operator_response_recorded",
            "ok": response.get("status") == "recorded" and response.get("permission_granted") is False,
            "detail": response.get("reason_code"),
        }
    )

    queue_direct = process_review_queue(requests, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "queue_all_advisory",
            "ok": queue_direct.get("permission_granted") is False,
            "detail": queue_direct.get("reason_code"),
        }
    )

    fences_ok, fence_detail = check_ori_import_fences()
    checks.append(
        {
            "check_id": "import_fences",
            "ok": fences_ok,
            "detail": fence_detail if not fences_ok else "clean",
        }
    )

    critical_failures = [c["check_id"] for c in checks if not c["ok"]]
    return {
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": checks,
    }


def run_ori_a_gate(workspace: Path, *, slice: str, gate_id: str, proof_subpath: str) -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "operator_review" / proof_subpath / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    batch_checks = run_ori_batch_a_checks(workspace, slice=slice)
    intake_checks = run_ori_intake_checks()
    iam_checks = run_ori_iam_binding_checks()
    full_scope_checks = run_ori_full_scope_checks()
    combined = {
        "ok": batch_checks["ok"]
        and intake_checks["ok"]
        and iam_checks["ok"]
        and full_scope_checks["ok"],
        "batch_checks": batch_checks,
        "intake_checks": intake_checks,
        "iam_checks": iam_checks,
        "full_scope_checks": full_scope_checks,
        "critical_failures": list(batch_checks.get("critical_failures", []))
        + list(intake_checks.get("critical_failures", []))
        + list(iam_checks.get("critical_failures", []))
        + list(full_scope_checks.get("critical_failures", [])),
    }
    (artifacts_dir / "ori_batch_checks.json").write_text(
        json.dumps(batch_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (artifacts_dir / "ori_intake_checks.json").write_text(
        json.dumps(intake_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (artifacts_dir / "ori_iam_binding_checks.json").write_text(
        json.dumps(iam_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (artifacts_dir / "ori_full_scope_checks.json").write_text(
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
        "slices": list(ORI_A_SLICES) if slice == "all" else [slice],
        "verdicts": [
            {
                "check": "ori_batch_checks",
                "verdict": "pass" if batch_checks["ok"] else "fail",
                "ok": batch_checks["ok"],
                "detail": batch_checks,
            },
            {
                "check": "ori_intake_checks",
                "verdict": "pass" if intake_checks["ok"] else "fail",
                "ok": intake_checks["ok"],
                "detail": intake_checks,
            },
            {
                "check": "ori_iam_binding_checks",
                "verdict": "pass" if iam_checks["ok"] else "fail",
                "ok": iam_checks["ok"],
                "detail": iam_checks,
            },
            {
                "check": "ori_full_scope_checks",
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
                "pack": "ORI-A",
                "gate": gate_id,
                "slice": slice,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": f"operator_review/{proof_subpath}",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/ori_batch_checks.json": sha256_file(artifacts_dir / "ori_batch_checks.json"),
                    "artifacts/ori_intake_checks.json": sha256_file(artifacts_dir / "ori_intake_checks.json"),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status_lines = [
        f"# ORI-A Operator Review Intake — {slice} — {ts}",
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


__all__ = [
    "SLICE_TEST_TARGETS",
    "run_ori_a_gate",
    "run_ori_full_scope_checks",
    "run_ori_iam_binding_checks",
    "run_ori_intake_checks",
]
