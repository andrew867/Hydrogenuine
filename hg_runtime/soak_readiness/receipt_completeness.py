"""Receipt completeness audit for overnight research proof directories.

Verifies that all expected receipts, artifacts, and doctrine markers exist.
Read-only except writing audit report. No promotion. No self-authorization.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass


@dataclass
class ReceiptCheck:
    name: str
    passed: bool
    severity: str  # "required" | "recommended"
    detail: str = ""


def _file_exists(proof_dir: str, filename: str) -> bool:
    return os.path.isfile(os.path.join(proof_dir, filename))


def _file_nonempty(proof_dir: str, filename: str) -> bool:
    path = os.path.join(proof_dir, filename)
    return os.path.isfile(path) and os.path.getsize(path) > 2


def _read_json(proof_dir: str, filename: str) -> dict | list | None:
    path = os.path.join(proof_dir, filename)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def audit_proof_dir(proof_dir: str) -> list[ReceiptCheck]:
    checks: list[ReceiptCheck] = []

    manifest = _read_json(proof_dir, "run_manifest.json")
    checks.append(ReceiptCheck(
        "run_manifest", manifest is not None, "required",
        "present" if manifest else "missing run_manifest.json"))

    checks.append(ReceiptCheck(
        "question_json", _file_exists(proof_dir, "question.json"), "required",
        "present" if _file_exists(proof_dir, "question.json") else "missing"))

    checks.append(ReceiptCheck(
        "source_plan", _file_exists(proof_dir, "source_plan.json"), "required",
        "present" if _file_exists(proof_dir, "source_plan.json") else "missing"))

    checks.append(ReceiptCheck(
        "model_inference_receipts",
        _file_exists(proof_dir, "model_inference_receipts.jsonl"),
        "required",
        "present" if _file_exists(proof_dir, "model_inference_receipts.jsonl") else "missing"))

    checks.append(ReceiptCheck(
        "claim_stack", _file_exists(proof_dir, "claim_stack.json"), "required",
        "present" if _file_exists(proof_dir, "claim_stack.json") else "missing"))

    checks.append(ReceiptCheck(
        "term_glossary", _file_exists(proof_dir, "term_glossary.json"), "recommended",
        "present" if _file_exists(proof_dir, "term_glossary.json") else "missing"))

    checks.append(ReceiptCheck(
        "mainstream_comparison",
        _file_exists(proof_dir, "mainstream_comparison.json"), "recommended",
        "present" if _file_exists(proof_dir, "mainstream_comparison.json") else "missing"))

    checks.append(ReceiptCheck(
        "unsupported_leap_audit",
        _file_exists(proof_dir, "unsupported_leap_audit.json"), "recommended",
        "present" if _file_exists(proof_dir, "unsupported_leap_audit.json") else "missing"))

    checks.append(ReceiptCheck(
        "evidence_gap_ledger",
        _file_exists(proof_dir, "evidence_gap_ledger.jsonl"), "recommended",
        "present" if _file_exists(proof_dir, "evidence_gap_ledger.jsonl") else "missing"))

    checks.append(ReceiptCheck(
        "why_not_promoted",
        _file_exists(proof_dir, "why_not_promoted.json"), "required",
        "present" if _file_exists(proof_dir, "why_not_promoted.json") else "missing"))

    checks.append(ReceiptCheck(
        "morning_packet",
        _file_exists(proof_dir, "morning_operator_packet.md"), "required",
        "present" if _file_exists(proof_dir, "morning_operator_packet.md") else "missing"))

    checks.append(ReceiptCheck(
        "public_safe_summary",
        _file_exists(proof_dir, "public_safe_summary.md"), "required",
        "present" if _file_exists(proof_dir, "public_safe_summary.md") else "missing"))

    if manifest and isinstance(manifest, dict):
        checks.append(ReceiptCheck(
            "no_promotion",
            manifest.get("promotion_allowed") is False and manifest.get("promotions", -1) == 0,
            "required",
            "promotion_allowed=False, promotions=0" if manifest.get("promotion_allowed") is False else "VIOLATION"))

        checks.append(ReceiptCheck(
            "no_remote_fallback",
            manifest.get("no_remote_model_fallback") is True
            or manifest.get("remote_fallback_used") is False,
            "required",
            "no remote fallback"))

        checks.append(ReceiptCheck(
            "operator_review_required",
            manifest.get("operator_review_required") is True,
            "required",
            "operator review required"))

        checks.append(ReceiptCheck(
            "model_output_not_truth",
            manifest.get("model_output_is_truth") is False,
            "required",
            "model output is not truth"))

        ts = manifest.get("throughput_summary")
        if ts:
            checks.append(ReceiptCheck(
                "throughput_summary_present", True, "recommended",
                f"calls_planned={ts.get('model_calls_planned', '?')}"))
        else:
            checks.append(ReceiptCheck(
                "throughput_summary_present", False, "recommended",
                "throughput_summary missing from manifest"))

    checks.append(ReceiptCheck(
        "compression_receipts",
        _file_exists(proof_dir, "compression_receipts.jsonl"),
        "recommended",
        "present" if _file_exists(proof_dir, "compression_receipts.jsonl") else "not found"))

    scheduler_found = (
        _file_exists(proof_dir, "model_call_scheduler_receipts.jsonl")
        or _file_exists(proof_dir, "model_scheduler_receipts.jsonl")
    )
    checks.append(ReceiptCheck(
        "scheduler_receipts",
        scheduler_found,
        "recommended",
        "present" if scheduler_found else "not found"))

    model_selection_found = _file_exists(proof_dir, "model_selection_receipts.jsonl")
    checks.append(ReceiptCheck(
        "model_selection_receipts",
        model_selection_found,
        "optional",
        "present" if model_selection_found else "not found (optional — dynamic selection)"))

    return checks


def compute_receipt_verdict(checks: list[ReceiptCheck]) -> str:
    required_failed = [c for c in checks if not c.passed and c.severity == "required"]
    if required_failed:
        return "RED_RECEIPTS_INCOMPLETE"
    recommended_failed = [c for c in checks if not c.passed and c.severity == "recommended"]
    if recommended_failed:
        return "YELLOW_RECEIPTS_PARTIAL"
    return "GREEN_RECEIPTS_COMPLETE"


def write_receipt_audit(proof_dir: str, checks: list[ReceiptCheck],
                        out_path: str | None = None) -> dict:
    verdict = compute_receipt_verdict(checks)
    passed = sum(1 for c in checks if c.passed)
    total = len(checks)

    result = {
        "receipt_audit_verdict": verdict,
        "passed": passed,
        "total": total,
        "proof_dir": proof_dir,
        "checks": [
            {"name": c.name, "passed": c.passed, "severity": c.severity, "detail": c.detail}
            for c in checks
        ],
        "failed": [c.name for c in checks if not c.passed],
        "operator_review_required": True,
        "promotion_allowed": False,
    }

    target = out_path or os.path.join(proof_dir, "receipt_completeness_report.json")
    with open(target, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    md_path = target.replace(".json", ".md")
    lines = [
        "# Receipt Completeness Audit",
        "",
        f"Verdict: {verdict}",
        f"Passed: {passed}/{total}",
        f"Proof dir: {proof_dir}",
        "",
    ]
    for c in checks:
        status = "PASS" if c.passed else "FAIL"
        lines.append(f"- [{status}] {c.name} ({c.severity}): {c.detail}")
    lines.extend(["", "---", "Operator review required. No promotion."])
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return result
