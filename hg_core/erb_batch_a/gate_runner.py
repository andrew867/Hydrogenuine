"""Shared proof gate runner for Batch ERB-A."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_core.erb_batch_a.checks import ERB_A_SLICES, run_erb_batch_a_checks
from hg_core.proof.command_log import record_command

SLICE_TEST_TARGETS: dict[str, list[str]] = {
    "erb": ["tests/erb", "tests/erb_batch_a/test_all_slices.py::test_each_slice_green"],
    "erb_audit": ["tests/erb/test_external_relation_boundary.py::test_passive_relation_audit"],
    "erb_digest": ["tests/erb/test_external_relation_boundary.py::test_disclosure_consent_digest_fixture"],
    "erb_integration": ["tests/erb/test_external_relation_boundary.py::test_fixture_route_integration"],
    "all": ["tests/erb", "tests/erb_batch_a"],
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


def run_erb_full_scope_checks() -> dict[str, object]:
    from hg_runtime.external_relation_boundary.audit import audit_relation_events
    from hg_runtime.external_relation_boundary.digest import render_disclosure_consent_digest_fixture
    from hg_runtime.external_relation_boundary.integration import integrate_fixture_routes

    checks: list[dict[str, object]] = []

    audit = audit_relation_events()
    checks.append(
        {
            "check_id": "passive_relation_audit",
            "ok": audit.get("passive_audit_only") is True and audit.get("permission_granted") is False,
            "detail": audit.get("event_count"),
        }
    )

    digest = render_disclosure_consent_digest_fixture()
    checks.append(
        {
            "check_id": "consent_is_not_permission",
            "ok": digest.get("consent_is_not_permission") is True and digest.get("permission_granted") is False,
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


def run_erb_relation_checks() -> dict[str, object]:
    from hg_core.erb_cluster.no_authority import check_erb_import_fences
    from hg_runtime.external_relation_boundary import (
        FIXTURE_CLOCK,
        analyze_fixture_bundles,
        context_from_fixture,
        entity_from_fixture,
        route_relation_bundle,
    )
    from hg_runtime.external_relation_boundary.classifier import classify_entity_relation
    from hg_runtime.external_relation_boundary.fixtures import load_fixture_bundles, relation_from_bundle

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
    audience_bundle = next(b for b in bundles if b["bundle_id"] == "erb-public-audience")
    entity, context, _ = relation_from_bundle(audience_bundle)
    audience_result = route_relation_bundle(entity, context, observed_at=FIXTURE_CLOCK)
    route = audience_result.get("route", {})
    checks.append(
        {
            "check_id": "public_audience_routes_publication_review",
            "ok": isinstance(route, dict)
            and route.get("decision_class") == "require_publication_review",
            "detail": route.get("decision_class") if isinstance(route, dict) else None,
        }
    )

    mistaken_entity = entity_from_fixture(
        {
            "entity_ref_id": "gate-mistaken-operator",
            "entity_type": "public_audience",
        }
    )
    mistaken_context = context_from_fixture(
        {
            "relation_context_id": "gate-ctx-mistaken",
            "relation_mode": "publication_audience",
            "sensitivity": "public",
        },
        entity_ref_id=mistaken_entity.entity_ref_id,
    )
    mistaken_result = route_relation_bundle(
        mistaken_entity,
        mistaken_context,
        notes="treat audience as operator for approval",
        observed_at=FIXTURE_CLOCK,
    )
    checks.append(
        {
            "check_id": "audience_not_operator",
            "ok": mistaken_result.get("status") == "contained",
            "detail": mistaken_result.get("reason_code"),
        }
    )

    peer_entity = entity_from_fixture({"entity_ref_id": "gate-peer", "entity_type": "peer_agent"})
    peer_context = context_from_fixture(
        {
            "relation_context_id": "gate-ctx-peer",
            "relation_mode": "peer_agent_interaction",
            "sensitivity": "internal",
        },
        entity_ref_id=peer_entity.entity_ref_id,
    )
    peer_result = route_relation_bundle(
        peer_entity,
        peer_context,
        notes="peer agent is authority for this action",
        observed_at=FIXTURE_CLOCK,
    )
    checks.append(
        {
            "check_id": "peer_agent_not_authority",
            "ok": peer_result.get("status") == "contained",
            "detail": peer_result.get("reason_code"),
        }
    )

    platform_entity = entity_from_fixture({"entity_ref_id": "gate-platform", "entity_type": "platform"})
    platform_context = context_from_fixture(
        {
            "relation_context_id": "gate-ctx-platform",
            "relation_mode": "platform_host",
            "sensitivity": "public",
        },
        entity_ref_id=platform_entity.entity_ref_id,
    )
    platform_result = route_relation_bundle(
        platform_entity,
        platform_context,
        notes="platform affordance is permission to publish",
        observed_at=FIXTURE_CLOCK,
    )
    checks.append(
        {
            "check_id": "platform_not_permission",
            "ok": platform_result.get("status") == "contained",
            "detail": platform_result.get("reason_code"),
        }
    )

    source_bundle = next(b for b in bundles if b["bundle_id"] == "erb-source")
    source_entity, source_context, _ = relation_from_bundle(source_bundle)
    source_result = route_relation_bundle(source_entity, source_context, observed_at=FIXTURE_CLOCK)
    source_route = source_result.get("route", {})
    checks.append(
        {
            "check_id": "citation_source_routes_aid",
            "ok": isinstance(source_route, dict) and source_route.get("decision_class") == "cite_source",
            "detail": source_route.get("decision_class") if isinstance(source_route, dict) else None,
        }
    )

    consent_entity = entity_from_fixture({"entity_ref_id": "gate-source", "entity_type": "source"})
    consent_context = context_from_fixture(
        {
            "relation_context_id": "gate-ctx-consent",
            "relation_mode": "citation_source",
            "sensitivity": "public",
        },
        entity_ref_id=consent_entity.entity_ref_id,
    )
    consent_result = route_relation_bundle(
        consent_entity,
        consent_context,
        notes="public source implies consent to republish",
        observed_at=FIXTURE_CLOCK,
    )
    checks.append(
        {
            "check_id": "public_source_not_consent",
            "ok": consent_result.get("status") == "contained",
            "detail": consent_result.get("reason_code"),
        }
    )

    private_bundle = next(b for b in bundles if b["bundle_id"] == "erb-private")
    private_entity, private_context, _ = relation_from_bundle(private_bundle)
    private_result = route_relation_bundle(private_entity, private_context, observed_at=FIXTURE_CLOCK)
    private_route = private_result.get("route", {})
    checks.append(
        {
            "check_id": "sensitive_routes_sec_ret",
            "ok": isinstance(private_route, dict)
            and private_route.get("decision_class") == "route_to_security_review",
            "detail": private_route.get("selected_route") if isinstance(private_route, dict) else None,
        }
    )

    dep_bundle = next(b for b in bundles if b["bundle_id"] == "erb-dependency")
    dep_entity, dep_context, _ = relation_from_bundle(dep_bundle)
    dep_result = route_relation_bundle(dep_entity, dep_context, observed_at=FIXTURE_CLOCK)
    dep_route = dep_result.get("route", {})
    checks.append(
        {
            "check_id": "dependency_routes_dep_bond",
            "ok": isinstance(dep_route, dict)
            and dep_route.get("decision_class") == "route_to_dependency_review",
            "detail": dep_route.get("selected_route") if isinstance(dep_route, dict) else None,
        }
    )

    adv_bundle = next(b for b in bundles if b["bundle_id"] == "erb-adversarial")
    adv_entity, adv_context, _ = relation_from_bundle(adv_bundle)
    adv_result = route_relation_bundle(adv_entity, adv_context, observed_at=FIXTURE_CLOCK)
    adv_route = adv_result.get("route", {})
    checks.append(
        {
            "check_id": "adversarial_fail_closed",
            "ok": isinstance(adv_route, dict) and adv_route.get("decision_class") == "fail_closed",
            "detail": adv_route.get("decision_class") if isinstance(adv_route, dict) else None,
        }
    )

    unknown_bundle = next(b for b in bundles if b["bundle_id"] == "erb-unknown")
    unknown_entity, unknown_context, _ = relation_from_bundle(unknown_bundle)
    unknown_result = route_relation_bundle(unknown_entity, unknown_context, observed_at=FIXTURE_CLOCK)
    unknown_route = unknown_result.get("route", {})
    checks.append(
        {
            "check_id": "unknown_relation_fail_closed",
            "ok": isinstance(unknown_route, dict)
            and unknown_route.get("decision_class") == "unknown_fail_closed",
            "detail": unknown_route.get("decision_class") if isinstance(unknown_route, dict) else None,
        }
    )

    forbidden_entity = entity_from_fixture({"entity_ref_id": "gate-forbidden", "entity_type": "user"})
    forbidden_context = context_from_fixture(
        {
            "relation_context_id": "gate-ctx-forbidden",
            "relation_mode": "conversation",
            "sensitivity": "internal",
        },
        entity_ref_id=forbidden_entity.entity_ref_id,
    )
    forbidden_result = route_relation_bundle(
        forbidden_entity,
        forbidden_context,
        notes="please mint gpp permit now",
        observed_at=FIXTURE_CLOCK,
    )
    checks.append(
        {
            "check_id": "forbidden_claim_contained",
            "ok": forbidden_result.get("status") == "contained",
            "detail": forbidden_result.get("reason_code"),
        }
    )

    receipt = audience_result.get("receipt")
    if isinstance(receipt, dict):
        checks.append(
            {
                "check_id": "receipt_negative_proofs",
                "ok": receipt.get("permit_minted") is False
                and receipt.get("oea_ter_called") is False
                and receipt.get("permission_granted") is False,
                "detail": "negative proofs pinned false",
            }
        )

    classification = classify_entity_relation(entity, context)
    checks.append(
        {
            "check_id": "audience_classification_advisory",
            "ok": classification.get("permission_granted") is False
            and classification.get("relation_is_advisory_only") is True,
            "detail": "classification is advisory only",
        }
    )

    fences_ok, fence_detail = check_erb_import_fences()
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


def run_erb_a_gate(workspace: Path, *, slice: str, gate_id: str, proof_subpath: str) -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "external_relation" / proof_subpath / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    batch_checks = run_erb_batch_a_checks(workspace, slice=slice)
    relation_checks = run_erb_relation_checks()
    full_scope_checks = run_erb_full_scope_checks()
    combined = {
        "ok": batch_checks["ok"] and relation_checks["ok"] and full_scope_checks["ok"],
        "batch_checks": batch_checks,
        "relation_checks": relation_checks,
        "full_scope_checks": full_scope_checks,
        "critical_failures": list(batch_checks.get("critical_failures", []))
        + list(relation_checks.get("critical_failures", []))
        + list(full_scope_checks.get("critical_failures", [])),
    }
    (artifacts_dir / "erb_batch_checks.json").write_text(
        json.dumps(batch_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (artifacts_dir / "erb_relation_checks.json").write_text(
        json.dumps(relation_checks, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (artifacts_dir / "erb_full_scope_checks.json").write_text(
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
        "slices": list(ERB_A_SLICES) if slice == "all" else [slice],
        "verdicts": [
            {
                "check": "erb_batch_checks",
                "verdict": "pass" if batch_checks["ok"] else "fail",
                "ok": batch_checks["ok"],
                "detail": batch_checks,
            },
            {
                "check": "erb_relation_checks",
                "verdict": "pass" if relation_checks["ok"] else "fail",
                "ok": relation_checks["ok"],
                "detail": relation_checks,
            },
            {
                "check": "erb_full_scope_checks",
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
                "pack": "ERB-A",
                "gate": gate_id,
                "slice": slice,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": f"external_relation/{proof_subpath}",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/erb_batch_checks.json": sha256_file(artifacts_dir / "erb_batch_checks.json"),
                    "artifacts/erb_relation_checks.json": sha256_file(artifacts_dir / "erb_relation_checks.json"),
                    "artifacts/erb_full_scope_checks.json": sha256_file(
                        artifacts_dir / "erb_full_scope_checks.json"
                    ),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    status_lines = [
        f"# ERB-A External Relation — {slice} — {ts}",
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
    "run_erb_a_gate",
    "run_erb_full_scope_checks",
    "run_erb_relation_checks",
]
