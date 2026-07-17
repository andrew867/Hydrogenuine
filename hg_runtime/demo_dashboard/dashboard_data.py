"""Build dashboard_data.json from a demo proof bundle.

Reads the bundle's index.json, receipts, model outputs, evidence graph,
quarantine, public claim checks, and reports. Produces a single JSON
structure for the dashboard HTML to render.

Does NOT mutate the source bundle. Source is not truth.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from hg_runtime.demo_bundle.redaction import redact_text, redact_json_values


def _read_jsonl(path: str) -> list[dict]:
    if not os.path.isfile(path):
        return []
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def _read_json(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _read_text(path: str) -> str:
    if not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _read_model_outputs(bundle_dir: str) -> list[dict]:
    model_dir = os.path.join(bundle_dir, "model_outputs")
    if not os.path.isdir(model_dir):
        return []
    outputs = []
    for fname in sorted(os.listdir(model_dir)):
        fpath = os.path.join(model_dir, fname)
        if os.path.isfile(fpath):
            text = _read_text(fpath)
            outputs.append({"filename": fname, "text": text[:5000]})
    return outputs


def _build_sources(http_receipts: list[dict], source_receipts: list[dict]) -> list[dict]:
    sources = []
    for r in http_receipts:
        sources.append({
            "url": r.get("canonical_url", r.get("url", "")),
            "status": "success" if r.get("success") else "failed",
            "http_status": r.get("http_status", 0),
            "content_hash": r.get("content_hash", "")[:16] + "..." if r.get("content_hash") else "",
            "content_length": r.get("content_length", 0),
            "source_is_truth": False,
            "receipt_id": r.get("receipt_id", ""),
            "source_candidate_id": r.get("source_candidate_id", ""),
            "failure_reason": r.get("failure_reason", ""),
        })
    return sources


def _build_model_witnesses(inference_receipts: list[dict], model_outputs: list[dict]) -> list[dict]:
    witnesses = []
    for r in inference_receipts:
        output_text = ""
        for mo in model_outputs:
            cid = r.get("source_candidate_id", "")
            if cid and cid in mo.get("filename", ""):
                output_text = mo["text"]
                break

        witnesses.append({
            "cycle_id": r.get("cycle_id", ""),
            "model_name": r.get("model_name", ""),
            "endpoint_kind": r.get("endpoint_kind", ""),
            "inference_status": r.get("inference_status", ""),
            "remote_fallback_used": r.get("remote_fallback_used", False),
            "output_hash": (r.get("output_hash", "")[:16] + "...") if r.get("output_hash") else "",
            "output_chars": r.get("output_chars", 0),
            "latency_ms": r.get("latency_ms", 0),
            "model_output_is_truth": False,
            "output_text_preview": output_text[:1000] if output_text else "",
        })
    return witnesses


def _build_evidence_traces(eg_receipts: list[dict]) -> list[dict]:
    traces = []
    seen = set()
    for r in eg_receipts:
        rid = r.get("receipt_id", "")
        if rid in seen:
            continue
        seen.add(rid)
        traces.append({
            "receipt_id": rid,
            "node_count": r.get("node_count", 0),
            "edge_count": r.get("edge_count", 0),
            "contradiction_count": r.get("contradiction_count", 0),
            "evidence_gap_count": r.get("evidence_gap_count", 0),
            "unsupported_claims": r.get("unsupported_claims", 0),
            "graph_edge_is_not_proof": True,
        })
    return traces


def _build_quarantine_items(q_receipts: list[dict]) -> list[dict]:
    items = []
    for r in q_receipts:
        items.append({
            "receipt_id": r.get("receipt_id", ""),
            "quarantined_count": r.get("quarantined_count", 0),
            "promoted_count": r.get("promoted_count", 0),
            "promotion_allowed": r.get("promotion_allowed", False),
            "candidate_knowledge_is_not_knowledge": r.get("candidate_knowledge_is_not_knowledge", True),
            "timestamp": r.get("timestamp", ""),
        })
    return items


def _build_public_claim_check(pc_receipts: list[dict]) -> dict:
    total = len(pc_receipts)
    flagged = sum(1 for r in pc_receipts if r.get("flagged_count", 0) > 0)
    clean = total - flagged
    return {
        "total_checked": total,
        "clean": clean,
        "flagged": flagged,
        "status": "clean" if flagged == 0 else "flagged",
        "items": [
            {
                "source_label": r.get("source_label", ""),
                "flagged_count": r.get("flagged_count", 0),
                "clean": r.get("clean", True),
                "findings": r.get("findings", []),
            }
            for r in pc_receipts
        ],
    }


def _build_why_not_promoted() -> list[dict]:
    from hg_runtime.post_run_review.why_not_promoted import explain_why_not_promoted
    example = explain_why_not_promoted(
        item_id="example_model_output",
        item_type="model_output",
        is_model_output=True,
        promotion_allowed=False,
        operator_reviewed=False,
    )
    return [{
        "item_id": example["item_id"],
        "promotion_allowed": example["promotion_allowed"],
        "blocking_reasons": [
            {"reason": r["reason"], "explanation": r.get("explanation", r["reason"])}
            for r in example["blocking_reasons"][:5]
        ],
        "next_action": example["next_possible_operator_action"],
    }]


def build_dashboard_data(bundle_dir: str) -> dict:
    """Build the complete dashboard data from a demo bundle directory."""
    index = _read_json(os.path.join(bundle_dir, "index.json"))
    manifest = _read_json(os.path.join(bundle_dir, "manifest.json"))
    gate = _read_json(os.path.join(bundle_dir, "gates", "gate_result.json"))
    redaction_report = _read_json(os.path.join(bundle_dir, "redaction_report.json"))

    stats = index.get("stats", {})

    http_receipts = _read_jsonl(os.path.join(bundle_dir, "receipts", "http_fetch_receipts.jsonl"))
    source_receipts = _read_jsonl(os.path.join(bundle_dir, "receipts", "source_receipts.jsonl"))
    inference_receipts = _read_jsonl(os.path.join(bundle_dir, "receipts", "model_inference_receipts.jsonl"))
    quality_receipts = _read_jsonl(os.path.join(bundle_dir, "receipts", "quality_receipts.jsonl"))
    eg_receipts = _read_jsonl(os.path.join(bundle_dir, "evidence_graph", "evidence_graph_receipts.jsonl"))
    q_receipts = _read_jsonl(os.path.join(bundle_dir, "quarantine", "quarantine_receipts.jsonl"))
    pc_receipts = _read_jsonl(os.path.join(bundle_dir, "public_claim_check", "public_claim_checks.jsonl"))

    model_outputs = _read_model_outputs(bundle_dir)

    reports_dir = os.path.join(bundle_dir, "reports")
    reports = {}
    if os.path.isdir(reports_dir):
        for fname in sorted(os.listdir(reports_dir)):
            if fname.endswith(".md"):
                reports[fname[:-3]] = _read_text(os.path.join(reports_dir, fname))

    screenshot_files = []
    ss_dir = os.path.join(bundle_dir, "screenshots")
    if os.path.isdir(ss_dir):
        for fname in sorted(os.listdir(ss_dir)):
            if fname.lower().endswith((".png", ".jpg", ".jpeg")):
                screenshot_files.append({"filename": fname, "path": f"screenshots/{fname}"})

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bundle_dir": redact_text(bundle_dir),
        "overview": {
            "final_verdict": stats.get("final_verdict", "UNKNOWN"),
            "gate_verdict": stats.get("gate_verdict", "UNKNOWN"),
            "gate_checks_passed": stats.get("gate_checks_passed", 0),
            "gate_checks_total": stats.get("gate_checks_total", 0),
            "run_id": stats.get("run_id", ""),
            "cycles": stats.get("cycles", 0),
            "sources_attempted": stats.get("sources_attempted", 0),
            "successful_fetches": stats.get("successful_fetches", 0),
            "failed_fetches": stats.get("failed_fetches", 0),
            "screenshots_captured": stats.get("screenshots_captured", 0),
            "model_successes": stats.get("model_successes", 0),
            "model_attempts": stats.get("model_attempts", 0),
            "model_name": stats.get("model_name", ""),
            "model_endpoint_kind": stats.get("model_endpoint_kind", ""),
            "contradictions": stats.get("contradictions", 0),
            "quarantine_entries": stats.get("quarantine_entries", 0),
            "quality_issues": stats.get("quality_issues", 0),
            "promotions_count": stats.get("promotions_count", 0),
            "external_effects_count": stats.get("external_effects_count", 0),
            "public_claim_flags": stats.get("public_claim_flags", 0),
            "domains": stats.get("domains", []),
        },
        "sources": _build_sources(http_receipts, source_receipts),
        "screenshots": screenshot_files,
        "model_witnesses": _build_model_witnesses(inference_receipts, model_outputs),
        "evidence_traces": _build_evidence_traces(eg_receipts),
        "contradictions": {
            "count": stats.get("contradictions", 0),
            "quality_issues": stats.get("quality_issues", 0),
        },
        "quarantine_items": _build_quarantine_items(q_receipts),
        "why_not_promoted": _build_why_not_promoted(),
        "public_claim_check": _build_public_claim_check(pc_receipts),
        "gates": gate,
        "reports": reports,
        "proof_inventory": {
            "http_fetch_receipts": len(http_receipts),
            "source_receipts": len(source_receipts),
            "model_inference_receipts": len(inference_receipts),
            "quality_receipts": len(quality_receipts),
            "evidence_graph_receipts": len(eg_receipts),
            "quarantine_receipts": len(q_receipts),
            "public_claim_checks": len(pc_receipts),
            "model_output_files": len(model_outputs),
            "screenshot_files": len(screenshot_files),
            "report_files": len(reports),
        },
        "redaction": redaction_report,
    }
