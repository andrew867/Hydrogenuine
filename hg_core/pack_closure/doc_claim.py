"""Pack 17 DOC claim chain closure — source-linked claims, not fake readiness."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_core.docs_freshness.scanner import run_claim_check
from hg_core.pack_closure.proof_bundles import find_latest_green_gate_bundle
from hg_core.pack_closure.types import PackClosureCheck


def run_doc_claim_closure_checks(workspace: Path) -> dict[str, Any]:
    checks: list[PackClosureCheck] = []

    gate_path = workspace / "scripts" / "evals" / "ct17_doc_claim_check_gate.py"
    checks.append(
        PackClosureCheck(
            "ct17_doc_gate_present",
            gate_path.is_file(),
            str(gate_path.relative_to(workspace)).replace("\\", "/"),
        )
    )

    test_path = workspace / "tests" / "doc" / "test_docs_freshness.py"
    checks.append(
        PackClosureCheck(
            "doc_freshness_tests_present",
            test_path.is_file(),
            str(test_path.relative_to(workspace)).replace("\\", "/"),
        )
    )

    registry_path = workspace / "config" / "doc_registry_v1.yaml"
    rules_path = workspace / "config" / "doc_claim_rules_v1.yaml"
    checks.append(
        PackClosureCheck(
            "doc_registry_and_rules_present",
            registry_path.is_file() and rules_path.is_file(),
            "doc_registry_v1 + doc_claim_rules_v1",
        )
    )

    report = run_claim_check(workspace)
    checks.append(
        PackClosureCheck(
            "live_claim_check_green",
            report.ok,
            f"docs_scanned={report.docs_scanned} findings={len(report.findings)}",
        )
    )

    citation_ok = bool(report.citation_lint.get("ok", False))
    checks.append(
        PackClosureCheck(
            "claims_source_linked",
            citation_ok,
            "citation_lint ok" if citation_ok else str(report.citation_lint),
        )
    )

    bundle = find_latest_green_gate_bundle(workspace, "pack17")
    checks.append(
        PackClosureCheck(
            "pack17_proof_bundle_green",
            bundle is not None,
            str(bundle.relative_to(workspace)).replace("\\", "/") if bundle else "no green pack17 bundle",
        )
    )

    inventory = workspace / "docs" / "reports" / "phases" / "CT_DEFERRED_ITEM_INVENTORY.md"
    inv_text = inventory.read_text(encoding="utf-8") if inventory.is_file() else ""
    doc_extras_deferred = "D-15" in inv_text and "POST_CT" in inv_text
    checks.append(
        PackClosureCheck(
            "doc_extras_honestly_deferred",
            doc_extras_deferred,
            "D-15..D-17 POST_CT backburner documented",
            critical=False,
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "pack": "doc_claim_chain",
        "packs": ("CT-17",),
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
        "claim_check_summary": {
            "ok": report.ok,
            "head": report.head,
            "docs_scanned": report.docs_scanned,
            "findings_count": len(report.findings),
            "citation_lint_ok": citation_ok,
        },
    }


__all__ = ["run_doc_claim_closure_checks"]
