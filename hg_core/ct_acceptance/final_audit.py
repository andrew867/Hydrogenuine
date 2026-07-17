"""Full final CT audit aggregation (Batch CT-C)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_core.ct_acceptance.milestone import run_ct_v1_milestone_checks
from hg_core.ct_acceptance.reconcile import run_ct_acceptance_reconcile
from hg_core.ct_acceptance.reconcile import AcceptanceCheck
from hg_core.pack_closure.proof_bundles import find_latest_green_gate_bundle


def _full_audit_doc_green(workspace: Path) -> tuple[bool, str]:
    doc = workspace / "docs" / "reports" / "phases" / "CT_FULL_FINAL_AUDIT.md"
    if not doc.is_file():
        return False, "missing"
    text = doc.read_text(encoding="utf-8")
    if "## Final verdict" not in text:
        return False, "no final verdict section"
    section = text.split("## Final verdict", 1)[-1]
    if "# GREEN" not in section and "**GREEN**" not in section:
        return False, "final verdict not GREEN"
    if "CT_REQUIRED" in section and "unclosed" in section.lower():
        return False, "claims unclosed CT-required items"
    return True, "CT_FULL_FINAL_AUDIT cites GREEN"


def run_ct_full_final_audit_checks(
    workspace: Path,
    *,
    fresh_ct_v1_bundle: Path | None = None,
) -> dict[str, Any]:
    """Aggregate reconcile + milestone + full audit report checks."""
    checks: list[AcceptanceCheck] = []

    reconcile = run_ct_acceptance_reconcile(workspace)
    checks.append(
        AcceptanceCheck(
            "reconcile_green",
            reconcile["ok"],
            f"critical_failures={reconcile.get('critical_failures', [])}",
        )
    )

    milestone = run_ct_v1_milestone_checks(workspace, fresh_bundle=fresh_ct_v1_bundle)
    checks.append(
        AcceptanceCheck(
            "milestone_green",
            milestone["ok"],
            f"critical_failures={milestone.get('critical_failures', [])}",
        )
    )

    doc_ok, doc_detail = _full_audit_doc_green(workspace)
    checks.append(
        AcceptanceCheck(
            "full_final_audit_report_green",
            doc_ok,
            doc_detail,
        )
    )

    acceptance_report = workspace / "docs" / "reports" / "phases" / "CT-V1-FINAL-ACCEPTANCE-AUDIT.md"
    checks.append(
        AcceptanceCheck(
            "acceptance_implementation_report_present",
            acceptance_report.is_file(),
            str(acceptance_report.relative_to(workspace)).replace("\\", "/"),
        )
    )

    batch_bundles = {
        "CT-A": find_latest_green_gate_bundle(workspace, "CT-A"),
        "CT-B/all": find_latest_green_gate_bundle(workspace, "CT-B", "all"),
        "CT-X": find_latest_green_gate_bundle(workspace, "CT-X"),
    }
    missing = [label for label, path in batch_bundles.items() if path is None]
    checks.append(
        AcceptanceCheck(
            "batch_queue_proof_bundles_green",
            not missing,
            f"missing={missing}" if missing else json_paths(batch_bundles, workspace),
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "slice": "full",
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
        "reconcile": reconcile,
        "milestone": milestone,
    }


def json_paths(bundles: dict[str, Path | None], workspace: Path) -> str:
    parts: list[str] = []
    for label, path in bundles.items():
        if path:
            parts.append(f"{label}={path.relative_to(workspace)}".replace("\\", "/"))
    return "; ".join(parts)


__all__ = ["run_ct_full_final_audit_checks"]
