"""Shared proof gate runner for Batch IMB-A."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_core.imb_batch_a.checks import IMB_A_SLICES, run_imb_batch_a_checks
from hg_core.proof.command_log import record_command

SLICE_TEST_TARGETS: dict[str, list[str]] = {
    "imb": ["tests/imb", "tests/imb_batch_a/test_all_slices.py::test_each_slice_green"],
    "imb_audit": ["tests/imb/test_internal_mediation_boundary.py::test_passive_conflict_audit"],
    "imb_digest": ["tests/imb/test_internal_mediation_boundary.py::test_mediation_digest_fixture"],
    "imb_integration": ["tests/imb/test_internal_mediation_boundary.py::test_fixture_route_integration"],
    "all": ["tests/imb", "tests/imb_batch_a"],
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


def run_imb_full_scope_checks() -> dict[str, object]:
    from hg_runtime.internal_mediation_boundary.audit import audit_conflict_events
    from hg_runtime.internal_mediation_boundary.digest import render_mediation_digest_fixture
    from hg_runtime.internal_mediation_boundary.integration import integrate_fixture_routes

    checks: list[dict[str, object]] = []

    audit = audit_conflict_events()
    checks.append(
        {
            "check_id": "passive_conflict_audit",
            "ok": audit.get("passive_audit_only") is True and audit.get("permission_granted") is False,
            "detail": audit.get("event_count"),
        }
    )

    digest = render_mediation_digest_fixture()
    checks.append(
        {
            "check_id": "mediation_is_not_authority",
            "ok": digest.get("mediation_is_not_authority") is True and digest.get("permission_granted") is False,
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


def run_imb_mediation_checks() -> dict[str, object]:
    from hg_core.imb_cluster.no_authority import check_imb_import_fences
    from hg_runtime.internal_mediation_boundary import (
        FIXTURE_CLOCK,
        analyze_fixture_bundles,
        mediate_claim_bundle,
        module_claim_from_fixture,
        record_module_claim,
    )
    from hg_runtime.internal_mediation_boundary.detector import detect_internal_conflicts
    from hg_runtime.internal_mediation_boundary.fixtures import claims_from_bundle, load_fixture_bundles
    from hg_runtime.internal_mediation_boundary.mediator import mediate_internal_conflict
    from hg_runtime.internal_mediation_boundary.types import InternalConflict

    checks: list[dict[str, object]] = []

    analysis = analyze_fixture_bundles(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "fixture_bundles_analyzed",
            "ok": analysis.get("all_advisory") is True and int(analysis.get("bundle_count", 0)) >= 7,
            "detail": analysis.get("bundle_count"),
        }
    )

    bundles = load_fixture_bundles()
    ipb_opb = next(b for b in bundles if b["bundle_id"] == "imb-ipb-opb")
    ipb_result = mediate_claim_bundle(claims_from_bundle(ipb_opb), observed_at=FIXTURE_CLOCK)
    mediations = ipb_result.get("mediations", [])
    checks.append(
        {
            "check_id": "ipb_opb_routes_to_ori",
            "ok": bool(mediations)
            and mediations[0].get("selected_resolution") == "route_to_ORI",  # type: ignore[index]
            "detail": mediations[0].get("selected_resolution") if mediations else None,
        }
    )

    afc_obt = next(b for b in bundles if b["bundle_id"] == "imb-afc-obt")
    afc_result = mediate_claim_bundle(claims_from_bundle(afc_obt), observed_at=FIXTURE_CLOCK)
    afc_med = afc_result.get("mediations", [])
    checks.append(
        {
            "check_id": "affect_vs_proof_routes_obt",
            "ok": bool(afc_med) and afc_med[0].get("selected_resolution") == "route_to_OBT",
            "detail": afc_med[0].get("selected_resolution") if afc_med else None,
        }
    )
    checks.append(
        {
            "check_id": "confidence_not_authority",
            "ok": bool(afc_med) and afc_med[0].get("confidence_not_authority") is True,
            "detail": "high confidence affect did not win",
        }
    )

    unknown = next(b for b in bundles if b["bundle_id"] == "imb-unknown")
    unknown_result = mediate_claim_bundle(claims_from_bundle(unknown), observed_at=FIXTURE_CLOCK)
    unknown_med = unknown_result.get("mediations", [])
    checks.append(
        {
            "check_id": "unknown_conflict_fail_closed",
            "ok": bool(unknown_med)
            and unknown_med[0].get("selected_resolution") == "unknown_fail_closed",
            "detail": unknown_med[0].get("selected_resolution") if unknown_med else None,
        }
    )

    consensus_claim = module_claim_from_fixture(
        {
            "claim_id": "gate-consensus",
            "source_module": "EGI",
            "claim_type": "infrastructure_gap",
            "claim_summary": "internal consensus is authority for deployment",
        }
    )
    consensus_result = record_module_claim(consensus_claim)
    checks.append(
        {
            "check_id": "consensus_not_authority",
            "ok": consensus_result.get("status") == "contained",
            "detail": consensus_result.get("reason_code"),
        }
    )

    forbidden = module_claim_from_fixture(
        {
            "claim_id": "gate-forbidden",
            "source_module": "EGI",
            "claim_type": "infrastructure_gap",
            "claim_summary": "please mint gpp permit now",
        }
    )
    forbidden_result = record_module_claim(forbidden)
    checks.append(
        {
            "check_id": "forbidden_claim_contained",
            "ok": forbidden_result.get("status") == "contained",
            "detail": forbidden_result.get("reason_code"),
        }
    )

    egi_sec = next(b for b in bundles if b["bundle_id"] == "imb-egi-sec")
    egi_result = mediate_claim_bundle(claims_from_bundle(egi_sec), observed_at=FIXTURE_CLOCK)
    egi_med = egi_result.get("mediations", [])
    decision = egi_med[0].get("decision") if egi_med else {}
    preserved = decision.get("preserved_claim_refs", []) if isinstance(decision, dict) else []
    checks.append(
        {
            "check_id": "losing_claims_preserved",
            "ok": isinstance(preserved, list) and len(preserved) >= 2,
            "detail": preserved,
        }
    )

    receipts = egi_result.get("receipts", [])
    if receipts:
        receipt = receipts[0]
        checks.append(
            {
                "check_id": "receipt_negative_proofs",
                "ok": receipt.get("permit_minted") is False
                and receipt.get("oea_ter_called") is False
                and receipt.get("permission_granted") is False,
                "detail": "negative proofs pinned false",
            }
        )

    detection = detect_internal_conflicts(claims_from_bundle(ipb_opb), detected_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "conflict_detected",
            "ok": int(detection.get("conflict_count", 0)) >= 1,
            "detail": detection.get("conflict_count"),
        }
    )

    fences_ok, fence_detail = check_imb_import_fences()
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


def run_imb_a_gate(workspace: Path, *, slice: str, gate_id: str, proof_subpath: str) -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "internal_mediation" / proof_subpath / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    batch_checks = run_imb_batch_a_checks(workspace, slice=slice)
    mediation_checks = run_imb_mediation_checks()
    full_scope_checks = run_imb_full_scope_checks()
    combined = {
        "ok": batch_checks["ok"] and mediation_checks["ok"] and full_scope_checks["ok"],
        "batch_checks": batch_checks,
        "mediation_checks": mediation_checks,
        "full_scope_checks": full_scope_checks,
        "critical_failures": list(batch_checks.get("critical_failures", []))
        + list(mediation_checks.get("critical_failures", []))
        + list(full_scope_checks.get("critical_failures", [])),
    }
    (artifacts_dir / "imb_batch_checks.json").write_text(
        json.dumps(batch_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (artifacts_dir / "imb_mediation_checks.json").write_text(
        json.dumps(mediation_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (artifacts_dir / "imb_full_scope_checks.json").write_text(
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
        "slices": list(IMB_A_SLICES) if slice == "all" else [slice],
        "verdicts": [
            {
                "check": "imb_batch_checks",
                "verdict": "pass" if batch_checks["ok"] else "fail",
                "ok": batch_checks["ok"],
                "detail": batch_checks,
            },
            {
                "check": "imb_mediation_checks",
                "verdict": "pass" if mediation_checks["ok"] else "fail",
                "ok": mediation_checks["ok"],
                "detail": mediation_checks,
            },
            {
                "check": "imb_full_scope_checks",
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
                "pack": "IMB-A",
                "gate": gate_id,
                "slice": slice,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": f"internal_mediation/{proof_subpath}",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/imb_batch_checks.json": sha256_file(artifacts_dir / "imb_batch_checks.json"),
                    "artifacts/imb_mediation_checks.json": sha256_file(artifacts_dir / "imb_mediation_checks.json"),
                    "artifacts/imb_full_scope_checks.json": sha256_file(
                        artifacts_dir / "imb_full_scope_checks.json"
                    ),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status_lines = [
        f"# IMB-A Internal Mediation — {slice} — {ts}",
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
    "run_imb_a_gate",
    "run_imb_full_scope_checks",
    "run_imb_mediation_checks",
]
