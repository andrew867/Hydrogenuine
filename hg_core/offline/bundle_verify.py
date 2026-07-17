"""Pack 6: Offline bundle verification."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from hg_core.ledger.ledger_verify import verify_chain
from hg_core.contracts.reality_contracts import load_reality_contract


def verify_bundle(workspace_root: Path, conformance: bool = False) -> Dict[str, Any]:
    """Run offline checks. If conformance=True, run public conformance v0.1 checks. Returns report dict."""
    workspace_root = Path(workspace_root)
    report: Dict[str, Any] = {"ok": True, "checks": {}, "errors": [], "warnings": []}
    chain = verify_chain(workspace_root)
    report["checks"]["ledger_chain"] = chain
    if not chain.get("ok", True):
        report["ok"] = False
        report["errors"].extend(chain.get("errors", []))
    contract = load_reality_contract(workspace_root)
    report["checks"]["reality_contract"] = {"loaded": contract is not None}
    if contract is None:
        report["warnings"].append("no_reality_contract")
    ledger_root = workspace_root / "memory" / "ledger" / "scopes"
    report["checks"]["ledger_exists"] = ledger_root.exists()
    if not ledger_root.exists():
        report["warnings"].append("ledger_scopes_missing")
    if conformance:
        try:
            from hg_core.conformance import run_conformance_checks
            cr = run_conformance_checks(workspace_root)
            report["checks"]["conformance_v01"] = cr
            if not cr.get("ok", True):
                report["ok"] = False
                report["errors"].extend(cr.get("errors", []))
        except Exception as e:
            report["checks"]["conformance_v01"] = {"ok": False, "error": str(e)}
            report["warnings"].append("conformance_check_failed: " + str(e))
    return report


def format_report_txt(report: Dict[str, Any]) -> str:
    """Human-readable report."""
    lines = ["Bundle verification report", "=" * 40, "Overall: " + ("PASS" if report.get("ok") else "FAIL")]
    for k, v in report.get("checks", {}).items():
        lines.append("  %s: %s" % (k, v))
    for e in report.get("errors", []):
        lines.append("  ERROR: %s" % e)
    for w in report.get("warnings", []):
        lines.append("  WARN: %s" % w)
    return "\n".join(lines)
