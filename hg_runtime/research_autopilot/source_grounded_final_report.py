"""Source-grounded final report builder -- aggregates soak results into
a structured report with proof artifacts.

Source is not truth.  Model output is not truth.  Model consensus is not
proof.  No promotion.  Operator review required.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

from hg_runtime.research_autopilot.source_grounded_run_manifest import (
    SCHEMA_VERSION as MANIFEST_SCHEMA,
    _INVARIANTS,
)

REPORT_SCHEMA = "source_grounded_final_report_v1"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_final_report(
    *,
    run_id: str,
    manifest: dict,
    plan: dict,
    cycles: list[dict],
    operator_digest: str = "",
) -> dict:
    """Build the final report for the soak.

    Returns dict with: schema, run_id, manifest_summary, total_cycles,
    source_receipts_count, route_decisions_count, quality_reviews_count,
    contradiction_count, evidence_graph_summary, quarantine_count,
    public_claim_issues, verdict, **_INVARIANTS
    """
    source_receipts_count = sum(
        1 for c in cycles if c.get("source_result") is not None
    )
    route_decisions_count = sum(
        1 for c in cycles if c.get("route_receipt") is not None
    )
    quality_reviews_count = sum(
        1 for c in cycles if c.get("quality_receipt") is not None
    )
    contradiction_count = sum(
        1 for c in cycles if c.get("contradiction_entry") is not None
    )
    quarantine_count = sum(
        1 for c in cycles if c.get("quarantine_receipt") is not None
    )
    public_claim_issues = sum(
        c.get("public_claim_check", {}).get("flagged_count", 0)
        for c in cycles
    )

    # Build evidence graph summary from last cycle's graph receipt
    evidence_graph_summary = {}
    if cycles:
        last_receipt = cycles[-1].get("evidence_graph_receipt", {})
        evidence_graph_summary = {
            "node_count": last_receipt.get("node_count", 0),
            "edge_count": last_receipt.get("edge_count", 0),
            "unsupported_claims": last_receipt.get("unsupported_claims", 0),
        }

    manifest_summary = {
        "run_id": manifest.get("run_id", ""),
        "mode": manifest.get("mode", ""),
        "duration_hours": manifest.get("duration_hours", 0),
        "run_label": manifest.get("run_label", ""),
    }

    live_http_fetches = sum(
        1 for c in cycles if c.get("http_fetch_receipt") is not None
    )
    live_http_successes = sum(
        1 for c in cycles
        if c.get("http_fetch_receipt", {}).get("success")
    )

    verdict = "COMPLETE" if plan.get("policy_verified") else "POLICY_VIOLATION"

    report = {
        "schema": REPORT_SCHEMA,
        "report_id": "",
        "run_id": run_id,
        "created_at": _utc_now_iso(),
        "manifest_summary": manifest_summary,
        "total_cycles": len(cycles),
        "source_receipts_count": source_receipts_count,
        "route_decisions_count": route_decisions_count,
        "quality_reviews_count": quality_reviews_count,
        "contradiction_count": contradiction_count,
        "evidence_graph_summary": evidence_graph_summary,
        "quarantine_count": quarantine_count,
        "public_claim_issues": public_claim_issues,
        "live_http_fetches": live_http_fetches,
        "live_http_successes": live_http_successes,
        "operator_digest": operator_digest,
        "verdict": verdict,
        **_INVARIANTS,
    }

    raw = json.dumps(report, sort_keys=True)
    report["report_id"] = hashlib.sha256(raw.encode()).hexdigest()[:24]
    return report


def write_proof_artifacts(
    report: dict,
    output_dir: str,
    *,
    cycles: list[dict] | None = None,
    plan: dict | None = None,
) -> dict:
    """Write all JSONL/JSON artifacts to output_dir. Returns paths dict."""
    os.makedirs(output_dir, exist_ok=True)
    cycles = cycles or []
    plan = plan or {}

    # Write final report
    report_path = os.path.join(output_dir, "final_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    # Write plan
    plan_path = os.path.join(output_dir, "plan.json")
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, sort_keys=True)

    # Write route receipts
    route_receipts_path = os.path.join(output_dir, "route_receipts.jsonl")
    with open(route_receipts_path, "w", encoding="utf-8") as f:
        for c in cycles:
            receipt = c.get("route_receipt")
            if receipt:
                f.write(json.dumps(receipt, sort_keys=True) + "\n")

    # Write source receipts
    source_receipts_path = os.path.join(output_dir, "source_receipts.jsonl")
    with open(source_receipts_path, "w", encoding="utf-8") as f:
        for c in cycles:
            result = c.get("source_result")
            if result:
                f.write(json.dumps(result, sort_keys=True) + "\n")

    # Write quality receipts
    quality_receipts_path = os.path.join(output_dir, "quality_receipts.jsonl")
    with open(quality_receipts_path, "w", encoding="utf-8") as f:
        for c in cycles:
            receipt = c.get("quality_receipt")
            if receipt:
                f.write(json.dumps(receipt, sort_keys=True) + "\n")

    # Write contradiction entries
    contradictions_path = os.path.join(output_dir, "contradictions.jsonl")
    with open(contradictions_path, "w", encoding="utf-8") as f:
        for c in cycles:
            entry = c.get("contradiction_entry")
            if entry:
                f.write(json.dumps(entry, sort_keys=True) + "\n")

    # Write evidence graph receipts
    graph_receipts_path = os.path.join(output_dir, "evidence_graph_receipts.jsonl")
    with open(graph_receipts_path, "w", encoding="utf-8") as f:
        for c in cycles:
            receipt = c.get("evidence_graph_receipt")
            if receipt:
                f.write(json.dumps(receipt, sort_keys=True) + "\n")

    # Write quarantine receipts
    quarantine_path = os.path.join(output_dir, "quarantine_receipts.jsonl")
    with open(quarantine_path, "w", encoding="utf-8") as f:
        for c in cycles:
            receipt = c.get("quarantine_receipt")
            if receipt:
                f.write(json.dumps(receipt, sort_keys=True) + "\n")

    # Write public claim checks
    public_claims_path = os.path.join(output_dir, "public_claim_checks.jsonl")
    with open(public_claims_path, "w", encoding="utf-8") as f:
        for c in cycles:
            check = c.get("public_claim_check")
            if check:
                f.write(json.dumps(check, sort_keys=True) + "\n")

    # Write HTTP fetch receipts (if any live HTTP cycles)
    http_fetch_path = os.path.join(output_dir, "http_fetch_receipts.jsonl")
    has_http = False
    with open(http_fetch_path, "w", encoding="utf-8") as f:
        for c in cycles:
            receipt = c.get("http_fetch_receipt")
            if receipt:
                has_http = True
                f.write(json.dumps(receipt, sort_keys=True) + "\n")

    # Write model inference receipts (if any)
    model_inference_path = os.path.join(output_dir, "model_inference_receipts.jsonl")
    has_model = False
    with open(model_inference_path, "w", encoding="utf-8") as f:
        for c in cycles:
            receipt = c.get("model_inference_receipt")
            if receipt:
                has_model = True
                f.write(json.dumps(receipt, sort_keys=True) + "\n")

    paths = {
        "final_report": report_path,
        "plan": plan_path,
        "route_receipts": route_receipts_path,
        "source_receipts": source_receipts_path,
        "quality_receipts": quality_receipts_path,
        "contradictions": contradictions_path,
        "evidence_graph_receipts": graph_receipts_path,
        "quarantine_receipts": quarantine_path,
        "public_claim_checks": public_claims_path,
    }
    if has_http:
        paths["http_fetch_receipts"] = http_fetch_path
    if has_model:
        paths["model_inference_receipts"] = model_inference_path
    return paths


def validate_final_report(report: dict) -> list[str]:
    """Validate a final report's invariants and structure.

    Returns list of error strings (empty = valid).
    """
    errors = []

    if report.get("schema") != REPORT_SCHEMA:
        errors.append(f"wrong schema: {report.get('schema')}")

    # Check all invariants
    for key, expected in _INVARIANTS.items():
        actual = report.get(key)
        if actual is not expected and actual != expected:
            errors.append(f"invariant violated: {key} is {actual}, expected {expected}")

    # Basic structure checks
    if not report.get("run_id"):
        errors.append("missing run_id")

    if not report.get("verdict"):
        errors.append("missing verdict")

    if report.get("total_cycles") is None:
        errors.append("missing total_cycles")

    return errors
