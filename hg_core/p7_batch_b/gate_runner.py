"""Shared proof gate runner for Batch P7-B."""

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
from hg_core.p7_batch_b.checks import P7_B_SLICES, run_p7_batch_b_checks

SLICE_TEST_TARGETS: dict[str, list[str]] = {
    "embodiment": [
        "tests/embodiment_oea_growth",
        "tests/p7_batch_b/test_all_slices.py::test_each_slice_green",
    ],
    "embodiment_audit": [
        "tests/embodiment_oea_growth/test_embodiment_growth.py::test_passive_embodiment_growth_audit"
    ],
    "embodiment_queue": [
        "tests/embodiment_oea_growth/test_embodiment_growth.py::test_fake_embodiment_growth_queue"
    ],
    "embodiment_proposal": [
        "tests/embodiment_oea_growth/test_embodiment_growth.py::test_authority_chain_fake_proposal"
    ],
    "oea_growth": [
        "tests/embodiment_oea_growth/test_embodiment_growth.py::test_oea_catalog_growth_descriptors"
    ],
    "all": ["tests/embodiment_oea_growth", "tests/p7_batch_b"],
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


def run_eog_growth_checks(workspace: Path) -> dict[str, object]:
    from hg_core.embodiment_oea_cluster.errors import (
        REFUSED_EOG_AS_AUTHORITY,
        REFUSED_HARDWARE_OFF_BACKBURNER,
        EogValidationError,
    )
    from hg_core.embodiment_oea_cluster.no_authority import check_eog_import_fences
    from hg_runtime.embodiment_oea_growth import (
        FIXTURE_CLOCK,
        analyze_fixture_bundles,
        assert_eog_backburner_boundary,
        audit_embodiment_growth_claims,
        enqueue_fixture_queue,
        load_fixture_bundles,
        load_oea_catalog_growth_descriptors,
        load_pro_body_fixtures,
        link_pro_body_state,
        refuse_growth_as_permission,
        refuse_hardware_off_backburner,
        route_growth_bundle,
    )
    from hg_runtime.embodiment_oea_growth.classifier import classify_growth_risk
    from hg_runtime.embodiment_oea_growth.redaction import redact_growth_text
    from hg_runtime.embodiment_oea_growth.types import integration_from_fixture

    checks: list[dict[str, object]] = []

    fences_ok, fence_detail = check_eog_import_fences()
    checks.append(
        {
            "check_id": "import_fences",
            "ok": fences_ok,
            "detail": fence_detail if not fences_ok else "clean",
        }
    )

    backburner = assert_eog_backburner_boundary()
    checks.append(
        {
            "check_id": "backburner_guard_active",
            "ok": backburner.get("backburner_guard_active") is True
            and backburner.get("hardware_embodiment_deferred") is True,
            "detail": backburner,
        }
    )

    hardware_refused = False
    try:
        refuse_hardware_off_backburner(allow_hardware=True)
    except EogValidationError as exc:
        hardware_refused = exc.code == REFUSED_HARDWARE_OFF_BACKBURNER
    checks.append(
        {
            "check_id": "hardware_refused_off_backburner",
            "ok": hardware_refused,
            "detail": REFUSED_HARDWARE_OFF_BACKBURNER,
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
    android = next(b for b in bundles if b["bundle_id"] == "eog-android-body-fixture")
    android_result = route_growth_bundle(android, observed_at=FIXTURE_CLOCK)
    decision = android_result.get("route", {}).get("growth_decision", {})  # type: ignore[union-attr]
    checks.append(
        {
            "check_id": "android_observe_advisory",
            "ok": isinstance(decision, dict) and decision.get("decision") == "advisory_recorded",
            "detail": decision.get("decision") if isinstance(decision, dict) else None,
        }
    )

    stale = next(b for b in bundles if b["bundle_id"] == "eog-stale-growth-request")
    stale_result = route_growth_bundle(stale, observed_at=FIXTURE_CLOCK)
    stale_decision = stale_result.get("route", {}).get("growth_decision", {})  # type: ignore[union-attr]
    checks.append(
        {
            "check_id": "stale_growth_refused",
            "ok": stale_result.get("status") == "refused"
            and isinstance(stale_decision, dict)
            and stale_decision.get("decision") == "fail_closed",
            "detail": stale_decision.get("reason") if isinstance(stale_decision, dict) else None,
        }
    )

    consent = next(b for b in bundles if b["bundle_id"] == "eog-embodiment-consent-claim")
    consent_result = route_growth_bundle(consent, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "embodiment_implies_consent_contained",
            "ok": consent_result.get("status") == "contained",
            "detail": consent_result.get("containment", {}).get("growth_risk"),  # type: ignore[union-attr]
        }
    )

    hardware_real = next(b for b in bundles if b["bundle_id"] == "eog-hardware-not-real")
    hardware_result = route_growth_bundle(hardware_real, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "hardware_not_real_contained",
            "ok": hardware_result.get("status") == "contained",
            "detail": hardware_result.get("containment", {}).get("growth_risk"),  # type: ignore[union-attr]
        }
    )

    catalog = next(b for b in bundles if b["bundle_id"] == "eog-oea-growth-proposal")
    catalog_result = route_growth_bundle(catalog, observed_at=FIXTURE_CLOCK)
    catalog_decision = catalog_result.get("route", {}).get("growth_decision", {})  # type: ignore[union-attr]
    checks.append(
        {
            "check_id": "catalog_growth_requires_authority_chain",
            "ok": isinstance(catalog_decision, dict)
            and catalog_decision.get("decision") == "require_authority_chain",
            "detail": catalog_decision.get("decision") if isinstance(catalog_decision, dict) else None,
        }
    )

    proposal = catalog_result.get("authority_chain_proposal")
    checks.append(
        {
            "check_id": "fake_authority_chain_proposal",
            "ok": isinstance(proposal, dict)
            and proposal.get("fake_dispatch_only") is True
            and proposal.get("proposal", {}).get("permit_minted") is False,  # type: ignore[union-attr]
            "detail": "fake_dispatch_only",
        }
    )

    audit = audit_embodiment_growth_claims(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "passive_embodiment_growth_audit",
            "ok": audit.get("passive_audit_only") is True and int(audit.get("event_count", 0)) >= 9,
            "detail": audit.get("event_count"),
        }
    )

    queue_result = enqueue_fixture_queue()
    checks.append(
        {
            "check_id": "fake_embodiment_growth_queue",
            "ok": queue_result.get("fake_queue_only") is True and int(queue_result.get("queue_depth", 0)) >= 3,
            "detail": queue_result.get("queue_depth"),
        }
    )

    oea_result = load_oea_catalog_growth_descriptors()
    checks.append(
        {
            "check_id": "oea_catalog_growth_descriptors",
            "ok": oea_result.get("bounded_by_gpp_ueak_all") is True
            and int(oea_result.get("entry_count", 0)) >= 5,
            "detail": oea_result.get("entry_count"),
        }
    )

    pro_link = link_pro_body_state(load_pro_body_fixtures()[0], observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "pro_body_state_link_advisory",
            "ok": pro_link.get("link_only") is True and pro_link.get("permission_granted") is False,
            "detail": pro_link.get("status"),
        }
    )

    redacted = redact_growth_text("token api_key=secret-value here")
    checks.append(
        {
            "check_id": "secret_redaction",
            "ok": "api_key=" not in redacted and "[REDACTED]" in redacted,
            "detail": redacted,
        }
    )

    descriptor = integration_from_fixture(
        {
            "integration_id": "eog-risk-test",
            "title": "Embodiment presence implies consent panel",
            "hardware_scope_real": "false",
        }
    )
    checks.append(
        {
            "check_id": "growth_risk_classifier",
            "ok": classify_growth_risk(descriptor) == "embodiment_implies_consent",
            "detail": classify_growth_risk(descriptor),
        }
    )

    growth_refused = False
    try:
        refuse_growth_as_permission(treat_as_authority=True)
    except EogValidationError as exc:
        growth_refused = exc.code == REFUSED_EOG_AS_AUTHORITY
    checks.append(
        {
            "check_id": "growth_not_authority",
            "ok": growth_refused,
            "detail": REFUSED_EOG_AS_AUTHORITY,
        }
    )

    critical_failures = [c["check_id"] for c in checks if not c["ok"]]
    return {
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": checks,
    }


def run_p7_b_gate(workspace: Path, *, slice: str, gate_id: str, proof_subpath: str) -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "embodiment_oea_growth" / proof_subpath / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    batch_checks = run_p7_batch_b_checks(workspace, slice=slice)
    growth_checks = run_eog_growth_checks(workspace)
    combined = {
        "ok": batch_checks["ok"] and growth_checks["ok"],
        "batch_checks": batch_checks,
        "growth_checks": growth_checks,
        "critical_failures": list(batch_checks.get("critical_failures", []))
        + list(growth_checks.get("critical_failures", [])),
    }
    (artifacts_dir / "p7_batch_checks.json").write_text(
        json.dumps(batch_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (artifacts_dir / "eog_growth_checks.json").write_text(
        json.dumps(growth_checks, indent=2, sort_keys=True) + "\n",
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
        "slices": list(P7_B_SLICES) if slice == "all" else [slice],
        "verdicts": [
            {
                "check": "p7_batch_checks",
                "verdict": "pass" if batch_checks["ok"] else "fail",
                "ok": batch_checks["ok"],
                "detail": batch_checks,
            },
            {
                "check": "eog_growth_checks",
                "verdict": "pass" if growth_checks["ok"] else "fail",
                "ok": growth_checks["ok"],
                "detail": growth_checks,
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
                "pack": "P7-B",
                "gate": gate_id,
                "slice": slice,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": f"embodiment_oea_growth/{proof_subpath}",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/p7_batch_checks.json": sha256_file(artifacts_dir / "p7_batch_checks.json"),
                    "artifacts/eog_growth_checks.json": sha256_file(artifacts_dir / "eog_growth_checks.json"),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status_lines = [
        f"# P7-B Embodiment / OEA Growth — {slice} — {ts}",
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


__all__ = ["SLICE_TEST_TARGETS", "run_eog_growth_checks", "run_p7_b_gate"]
