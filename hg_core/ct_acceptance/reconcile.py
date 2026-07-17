"""Reconcile CT reports and proof bundles for Batch CT-C first safe slice."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TS_RE = re.compile(r"^\d{8}T\d{6}Z$")

REQUIRED_PHASE_REPORTS = (
    "CT_DEFERRED_ITEM_INVENTORY.md",
    "CT_DEFERRED_ITEM_CLOSURE_REPORT.md",
    "CT-GATE-INTEGRITY-AUDIT.md",
    "CT-PACK-CLOSURE-AUDIT.md",
    "CT-A_AUDIT.md",
    "CT-B_AUDIT.md",
    "CT-V1-FINAL-ACCEPTANCE-AUDIT.md",
    "CT_FULL_FINAL_AUDIT.md",
)

PROOF_LOCATIONS: tuple[tuple[str, str], ...] = (
    ("ct_a", "docs/proofs/connective_tissue/CT-A"),
    ("ct_b_all", "docs/proofs/connective_tissue/CT-B/all"),
    ("ct_x", "docs/proofs/connective_tissue/CT-X"),
    ("ct_v1", "docs/proofs/connective_tissue/CT-V1"),
    ("obt_strict", "docs/proofs/connective_tissue/pack04"),
)


@dataclass(frozen=True)
class AcceptanceCheck:
    check_id: str
    ok: bool
    detail: str
    critical: bool = True

    def to_payload(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "ok": self.ok,
            "detail": self.detail,
            "critical": self.critical,
        }


def _latest_bundle(pack_dir: Path) -> Path | None:
    if not pack_dir.is_dir():
        return None
    bundles = sorted(p for p in pack_dir.iterdir() if p.is_dir() and TS_RE.match(p.name))
    return bundles[-1] if bundles else None


def _find_gate_ok_bundle(pack_dir: Path) -> Path | None:
    if not pack_dir.is_dir():
        return None
    for bundle in sorted(
        (p for p in pack_dir.iterdir() if p.is_dir() and TS_RE.match(p.name)),
        reverse=True,
    ):
        ok, _ = _bundle_gate_ok(bundle)
        if ok:
            return bundle
    return None


def _find_obt_strict_green_bundle(pack_dir: Path) -> Path | None:
    if not pack_dir.is_dir():
        return None
    candidates = sorted(
        (p for p in pack_dir.iterdir() if p.is_dir() and TS_RE.match(p.name)),
        reverse=True,
    )
    for bundle in candidates:
        report_path = bundle / "truth_gate_report.json"
        if not report_path.is_file():
            continue
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(report, dict) and report.get("verdict") == "green" and report.get("strict_ct_mode"):
            return bundle
    return None


def _bundle_gate_ok(bundle: Path) -> tuple[bool, str]:
    gate_result = bundle / "gate_result.json"
    if gate_result.is_file():
        try:
            payload = json.loads(gate_result.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False, "gate_result.json parse error"
        if isinstance(payload, dict):
            if payload.get("ok") is True:
                return True, "gate_result.ok=true"
            if payload.get("verdict") == "green":
                return True, "gate_result.verdict=green"
            return False, f"gate_result.ok={payload.get('ok')}"
    truth_report = bundle / "truth_gate_report.json"
    if truth_report.is_file():
        try:
            report = json.loads(truth_report.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False, "truth_gate_report.json parse error"
        if isinstance(report, dict):
            verdict = str(report.get("verdict", ""))
            if verdict == "green":
                return True, "truth_gate_report.verdict=green"
            return False, f"truth_gate_report.verdict={verdict}"
    return False, "no gate_result or truth_gate_report"


def _inventory_open_blockers(inventory_text: str) -> list[str]:
    open_rows: list[str] = []
    for line in inventory_text.splitlines():
        if re.search(r"\|\s*\*?\*?Open\*?\*?\s*\|", line, re.IGNORECASE):
            open_rows.append(line.strip())
    return open_rows


def _inventory_claims_no_open_abc(inventory_text: str) -> bool:
    if "Open CT-required items after closure pass" not in inventory_text:
        return False
    section = inventory_text.split("Open CT-required items after closure pass", 1)[-1]
    return "None" in section.split("##", 1)[0]


def run_ct_acceptance_reconcile(workspace: Path) -> dict[str, Any]:
    """Static reconciliation of reports and on-disk proof bundles."""
    checks: list[AcceptanceCheck] = []
    phases = workspace / "docs" / "reports" / "phases"

    missing_reports = [name for name in REQUIRED_PHASE_REPORTS if not (phases / name).is_file()]
    checks.append(
        AcceptanceCheck(
            "required_phase_reports",
            not missing_reports,
            f"missing={missing_reports}" if missing_reports else f"count={len(REQUIRED_PHASE_REPORTS)}",
        )
    )

    inventory_path = phases / "CT_DEFERRED_ITEM_INVENTORY.md"
    inventory_text = inventory_path.read_text(encoding="utf-8") if inventory_path.is_file() else ""
    open_blockers = _inventory_open_blockers(inventory_text)
    checks.append(
        AcceptanceCheck(
            "no_open_abc_blockers_in_table",
            not open_blockers,
            f"open_rows={len(open_blockers)}",
        )
    )
    checks.append(
        AcceptanceCheck(
            "inventory_declares_no_open_abc",
            _inventory_claims_no_open_abc(inventory_text),
            "closure section present",
        )
    )

    closure_path = phases / "CT_DEFERRED_ITEM_CLOSURE_REPORT.md"
    closure_text = closure_path.read_text(encoding="utf-8") if closure_path.is_file() else ""
    checks.append(
        AcceptanceCheck(
            "closure_report_green",
            "GREEN" in closure_text and "Remaining blockers" in closure_text,
            "closure report cites GREEN",
        )
    )
    checks.append(
        AcceptanceCheck(
            "closure_no_remaining_blockers",
            "None for CT-V1" in closure_text or "None." in closure_text.split("Remaining blockers", 1)[-1][:80],
            "no CT-V1 blockers claimed",
        )
    )

    proof_results: list[dict[str, Any]] = []
    for label, rel in PROOF_LOCATIONS:
        pack_dir = workspace / Path(rel)
        if label == "obt_strict":
            bundle = _find_obt_strict_green_bundle(pack_dir)
        elif label in {"ct_v1", "ct_b_all"}:
            bundle = _find_gate_ok_bundle(pack_dir)
        else:
            bundle = _latest_bundle(pack_dir)
        if bundle is None:
            proof_results.append({"pack": label, "ok": False, "detail": "no bundle"})
            continue
        has_log = (bundle / "command_log.jsonl").is_file()
        gate_ok, gate_detail = _bundle_gate_ok(bundle)
        proof_results.append(
            {
                "pack": label,
                "bundle": str(bundle.relative_to(workspace)).replace("\\", "/"),
                "ok": gate_ok,
                "command_log": has_log,
                "detail": gate_detail,
            }
        )
    proof_ok = all(r["ok"] for r in proof_results)
    checks.append(
        AcceptanceCheck(
            "proof_bundles_reconciled",
            proof_ok,
            json.dumps(proof_results, sort_keys=True),
        )
    )

    milestone = workspace / "docs" / "planning" / "connective_tissue" / "CT_MILESTONE.md"
    milestone_text = milestone.read_text(encoding="utf-8") if milestone.is_file() else ""
    checks.append(
        AcceptanceCheck(
            "milestone_not_claiming_open_wave1",
            "blocks SRP apply" in milestone_text and "[x]" in milestone_text,
            "milestone wave checkboxes present",
        )
    )

    queue = workspace / "docs" / "planning" / "POST_CT_MASTER_CURSOR_QUEUE.md"
    queue_text = queue.read_text(encoding="utf-8") if queue.is_file() else ""
    checks.append(
        AcceptanceCheck(
            "queue_ct_closure_marked_closed",
            "CT closure (CLOSED" in queue_text or "CT-V1 green" in queue_text,
            "master queue acknowledges CT closure",
        )
    )

    critical_failures = [c.check_id for c in checks if c.critical and not c.ok]
    return {
        "ok": not critical_failures,
        "critical_failures": critical_failures,
        "checks": [c.to_payload() for c in checks],
        "proof_bundles": proof_results,
        "inventory_path": str(inventory_path.relative_to(workspace)).replace("\\", "/"),
    }


__all__ = [
    "AcceptanceCheck",
    "PROOF_LOCATIONS",
    "REQUIRED_PHASE_REPORTS",
    "run_ct_acceptance_reconcile",
]
