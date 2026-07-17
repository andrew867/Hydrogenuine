"""Shared proof gate runner for Batch ARB-A."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_core.arb_batch_a.checks import ARB_A_SLICES, run_arb_batch_a_checks
from hg_core.proof.command_log import record_command

SLICE_TEST_TARGETS: dict[str, list[str]] = {
    "arb": ["tests/arb", "tests/arb_batch_a/test_all_slices.py::test_each_slice_green"],
    "arb_audit": ["tests/arb/test_agency_routing_boundary.py::test_passive_route_audit"],
    "arb_integration": ["tests/arb/test_agency_routing_boundary.py::test_fixture_bridge_queues"],
    "arb_proposal": ["tests/arb/test_agency_routing_boundary.py::test_authority_chain_fake_proposal"],
    "all": ["tests/arb", "tests/arb_batch_a"],
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


def run_arb_routing_checks(workspace: Path) -> dict[str, object]:
    from hg_core.arb_cluster.no_authority import check_arb_import_fences
    from hg_runtime.agency_routing_boundary.audit import audit_route_events
    from hg_runtime.agency_routing_boundary.evaluator import (
        analyze_fixture_bundle,
        refuse_arb_as_authority,
        route_agent_signal,
    )
    from hg_runtime.agency_routing_boundary.fixtures import authority_chain_fixture_signals, load_fixture_signals
    from hg_runtime.agency_routing_boundary.integration import bridge_fixture_queues
    from hg_runtime.agency_routing_boundary.proposal import dispatch_authority_chain_routing_receipt
    from hg_runtime.agency_routing_boundary.types import (
        FIXTURE_CLOCK,
        AgencyRouteDecision,
        AgencyRoutingReceipt,
        agent0_signal_from_fixture,
    )

    checks: list[dict[str, object]] = []

    fences_ok, fence_detail = check_arb_import_fences()
    checks.append(
        {
            "check_id": "import_fences",
            "ok": fences_ok,
            "detail": fence_detail if not fences_ok else "clean",
        }
    )

    fixtures = load_fixture_signals()
    checks.append(
        {
            "check_id": "fixture_signals_loaded",
            "ok": len(fixtures) >= 20,
            "detail": len(fixtures),
        }
    )

    l1_signal = agent0_signal_from_fixture(
        {"signal_id": "arb-gate-l1", "source_layer": "L1_DNI", "signal_type": "desire", "risk_hint": "low"}
    )
    l1_result = route_agent_signal(l1_signal, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "l1_desire_routes_to_ipb",
            "ok": l1_result.get("route_class") == "local_ipb",
            "detail": l1_result.get("route_class"),
        }
    )

    soar_signal = agent0_signal_from_fixture(
        {
            "signal_id": "arb-gate-soar",
            "source_layer": "SOAR",
            "signal_type": "external_action_request",
            "risk_hint": "high",
        }
    )
    soar_result = route_agent_signal(soar_signal, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "external_action_routes_to_authority_chain",
            "ok": soar_result.get("route_class") in (
                "authority_chain_soar_hal_gpp_ueak",
                "operator_review",
            ),
            "detail": soar_result.get("route_class"),
        }
    )

    unknown_signal = agent0_signal_from_fixture(
        {"signal_id": "arb-gate-unknown", "source_layer": "unknown", "signal_type": "unknown"}
    )
    unknown_result = route_agent_signal(unknown_signal, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "unknown_signal_fails_closed",
            "ok": unknown_result.get("route_class") == "unknown_fail_closed",
            "detail": unknown_result.get("route_class"),
        }
    )

    bundle = {
        "signals": [
            {"signal_id": "arb-gate-bundle-1", "source_layer": "L1_DNI", "signal_type": "desire"},
            {"signal_id": "arb-gate-bundle-2", "source_layer": "SOAR", "signal_type": "external_action_request"},
        ]
    }
    analysis = analyze_fixture_bundle(bundle, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "fixture_bundle_all_advisory",
            "ok": analysis.get("all_advisory") is True,
            "detail": analysis.get("permission_granted"),
        }
    )

    arb_authority_refused = False
    try:
        refuse_arb_as_authority(treat_as_authority=True)
    except Exception as exc:
        arb_authority_refused = getattr(exc, "code", "") == "arb.refused.agency_routing_as_authority"
    checks.append(
        {
            "check_id": "arb_not_authority",
            "ok": arb_authority_refused,
            "detail": "arb.refused.agency_routing_as_authority",
        }
    )

    audit = audit_route_events(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "passive_route_audit",
            "ok": audit.get("passive_audit_only") is True and int(audit.get("event_count", 0)) >= 20,
            "detail": audit.get("event_count"),
        }
    )

    bridge = bridge_fixture_queues(observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "fixture_bridge_queues",
            "ok": bridge.get("fixture_bridge_only") is True and int(bridge.get("queue_depth", 0)) >= 3,
            "detail": bridge.get("queue_depth"),
        }
    )

    proposal_fixture = authority_chain_fixture_signals()[0]
    proposal_signal = agent0_signal_from_fixture(proposal_fixture)
    proposal_route = route_agent_signal(proposal_signal, observed_at=FIXTURE_CLOCK)
    decision_payload = proposal_route.get("decision")
    receipt_payload = proposal_route.get("receipt")
    proposal = None
    if isinstance(decision_payload, dict):
        decision = AgencyRouteDecision(
            route_decision_id=str(decision_payload["route_decision_id"]),
            signal_ref=str(decision_payload["signal_ref"]),
            route_class=decision_payload["route_class"],  # type: ignore[arg-type]
            reason=str(decision_payload["reason"]),
            evidence_refs=tuple(decision_payload["evidence_refs"]),
            required_next_refs=tuple(decision_payload["required_next_refs"]),
            forbidden_next_refs=tuple(decision_payload["forbidden_next_refs"]),
        )
        receipt = None
        if isinstance(receipt_payload, dict):
            receipt = AgencyRoutingReceipt(
                receipt_id=str(receipt_payload["receipt_id"]),
                signal_ref=str(receipt_payload["signal_ref"]),
                route_decision_ref=str(receipt_payload["route_decision_ref"]),
                policy_ref=str(receipt_payload.get("policy_ref", "")),
                conflict_refs=tuple(receipt_payload.get("conflict_refs", ())),
                emitted_events=tuple(receipt_payload.get("emitted_events", ())),
            )
        proposal = dispatch_authority_chain_routing_receipt(proposal_signal, decision, receipt)
    checks.append(
        {
            "check_id": "fake_authority_chain_proposal",
            "ok": isinstance(proposal, dict)
            and proposal.get("fake_dispatch_only") is True
            and proposal.get("proposal", {}).get("permit_minted") is False,  # type: ignore[union-attr]
            "detail": "fake_dispatch_only",
        }
    )

    critical_failures = [c["check_id"] for c in checks if not c["ok"]]
    return {
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": checks,
    }


def run_arb_a_gate(workspace: Path, *, slice: str, gate_id: str, proof_subpath: str) -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "agency_routing" / proof_subpath / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    batch_checks = run_arb_batch_a_checks(workspace, slice=slice)
    routing_checks = run_arb_routing_checks(workspace)
    combined = {
        "ok": batch_checks["ok"] and routing_checks["ok"],
        "batch_checks": batch_checks,
        "routing_checks": routing_checks,
        "critical_failures": list(batch_checks.get("critical_failures", []))
        + list(routing_checks.get("critical_failures", [])),
    }
    (artifacts_dir / "arb_batch_checks.json").write_text(
        json.dumps(batch_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (artifacts_dir / "arb_routing_checks.json").write_text(
        json.dumps(routing_checks, indent=2, sort_keys=True) + "\n",
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
        "slices": list(ARB_A_SLICES) if slice == "all" else [slice],
        "verdicts": [
            {
                "check": "arb_batch_checks",
                "verdict": "pass" if batch_checks["ok"] else "fail",
                "ok": batch_checks["ok"],
                "detail": batch_checks,
            },
            {
                "check": "arb_routing_checks",
                "verdict": "pass" if routing_checks["ok"] else "fail",
                "ok": routing_checks["ok"],
                "detail": routing_checks,
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
                "pack": "ARB-A",
                "gate": gate_id,
                "slice": slice,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": f"agency_routing/{proof_subpath}",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/arb_batch_checks.json": sha256_file(artifacts_dir / "arb_batch_checks.json"),
                    "artifacts/arb_routing_checks.json": sha256_file(artifacts_dir / "arb_routing_checks.json"),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status_lines = [
        f"# ARB-A Agency Routing — {slice} — {ts}",
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


__all__ = ["SLICE_TEST_TARGETS", "run_arb_a_gate", "run_arb_routing_checks"]
