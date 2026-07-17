"""Load proof bundles and proof directories for CLI/TUI consumption.

Read-only. No mutation. No network. Source is not truth.
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


def _sanitize_terminal(text: str) -> str:
    """Strip ANSI/terminal control characters from untrusted text."""
    import re
    text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text


def detect_proof_type(path: str) -> str:
    """Detect whether a path is a demo bundle or raw proof dir."""
    if os.path.isfile(os.path.join(path, "manifest.json")):
        return "bundle"
    if os.path.isfile(os.path.join(path, "run_manifest.json")):
        return "overnight_proof_dir"
    if os.path.isfile(os.path.join(path, "soak_manifest.json")):
        return "proof_dir"
    for fname in os.listdir(path) if os.path.isdir(path) else []:
        if fname.endswith("_receipts.jsonl"):
            return "proof_dir"
    return "unknown"


def load_bundle(bundle_dir: str, *, redact: bool = True) -> dict:
    """Load a demo bundle into the standard data model."""
    from hg_runtime.demo_dashboard.dashboard_data import build_dashboard_data
    data = build_dashboard_data(bundle_dir)
    if redact:
        data = redact_json_values(data)
    return data


def load_proof_dir(proof_dir: str, *, redact: bool = True) -> dict:
    """Load a raw proof directory into the standard data model."""
    index = _read_json(os.path.join(proof_dir, "index.json"))
    manifest = _read_json(os.path.join(proof_dir, "soak_manifest.json"))

    http_receipts = _read_jsonl(os.path.join(proof_dir, "http_fetch_receipts.jsonl"))
    source_receipts = _read_jsonl(os.path.join(proof_dir, "source_receipts.jsonl"))
    inference_receipts = _read_jsonl(os.path.join(proof_dir, "model_inference_receipts.jsonl"))
    quality_receipts = _read_jsonl(os.path.join(proof_dir, "quality_receipts.jsonl"))
    eg_receipts = _read_jsonl(os.path.join(proof_dir, "evidence_graph_receipts.jsonl"))
    q_receipts = _read_jsonl(os.path.join(proof_dir, "quarantine_receipts.jsonl"))
    pc_receipts = _read_jsonl(os.path.join(proof_dir, "public_claim_checks.jsonl"))

    model_outputs = []
    mo_dir = os.path.join(proof_dir, "model_outputs")
    if os.path.isdir(mo_dir):
        for fname in sorted(os.listdir(mo_dir)):
            fpath = os.path.join(mo_dir, fname)
            if os.path.isfile(fpath):
                model_outputs.append({
                    "filename": fname,
                    "text": _sanitize_terminal(_read_text(fpath)[:5000]),
                })

    sources = []
    for r in http_receipts:
        sources.append({
            "url": r.get("canonical_url", r.get("url", "")),
            "status": "success" if r.get("success") else "failed",
            "http_status": r.get("http_status", 0),
            "content_hash": (r.get("content_hash", "")[:16] + "...") if r.get("content_hash") else "",
            "source_is_truth": False,
            "receipt_id": r.get("receipt_id", ""),
            "source_candidate_id": r.get("source_candidate_id", ""),
        })

    witnesses = []
    for r in inference_receipts:
        output_text = ""
        cid = r.get("source_candidate_id", "")
        for mo in model_outputs:
            if cid and cid in mo.get("filename", ""):
                output_text = mo["text"]
                break
        witnesses.append({
            "cycle_id": r.get("cycle_id", ""),
            "model_name": r.get("model_name", ""),
            "endpoint_kind": r.get("endpoint_kind", ""),
            "inference_status": r.get("inference_status", ""),
            "remote_fallback_used": r.get("remote_fallback_used", False),
            "output_chars": r.get("output_chars", 0),
            "latency_ms": r.get("latency_ms", 0),
            "model_output_is_truth": False,
            "output_text_preview": output_text[:1000],
        })

    overview = {
        "run_id": manifest.get("run_id", ""),
        "cycles": len(http_receipts),
        "sources_attempted": len(http_receipts),
        "successful_fetches": sum(1 for r in http_receipts if r.get("success")),
        "failed_fetches": sum(1 for r in http_receipts if not r.get("success")),
        "model_successes": sum(1 for r in inference_receipts if r.get("inference_status") == "success"),
        "model_attempts": len(inference_receipts),
        "contradictions": len([r for r in eg_receipts if r.get("contradiction_count", 0) > 0]),
        "quarantine_entries": len(q_receipts),
        "promotions_count": 0,
        "external_effects_count": 0,
        "public_claim_flags": sum(r.get("flagged_count", 0) for r in pc_receipts),
        "screenshots_captured": 0,
        "gate_verdict": "UNKNOWN",
        "gate_checks_passed": 0,
        "gate_checks_total": 0,
        "final_verdict": "UNKNOWN",
        "model_endpoint_kind": "",
        "model_name": "",
        "domains": [],
    }

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_type": "proof_dir",
        "overview": overview,
        "sources": sources,
        "model_witnesses": witnesses,
        "evidence_traces": [],
        "contradictions": {"count": 0, "quality_issues": 0},
        "quarantine_items": [],
        "why_not_promoted": [],
        "public_claim_check": {"total_checked": len(pc_receipts), "clean": len(pc_receipts), "flagged": 0, "status": "clean", "items": []},
        "gates": {},
        "reports": {},
        "screenshots": [],
        "proof_inventory": {
            "http_fetch_receipts": len(http_receipts),
            "source_receipts": len(source_receipts),
            "model_inference_receipts": len(inference_receipts),
            "quality_receipts": len(quality_receipts),
            "evidence_graph_receipts": len(eg_receipts),
            "quarantine_receipts": len(q_receipts),
            "public_claim_checks": len(pc_receipts),
            "model_output_files": len(model_outputs),
            "screenshot_files": 0,
            "report_files": 0,
        },
        "redaction": {},
    }

    if redact:
        data = redact_json_values(data)

    return data


def load_overnight_proof_dir(proof_dir: str, *, redact: bool = True) -> dict:
    """Load an overnight research proof directory."""
    manifest = _read_json(os.path.join(proof_dir, "run_manifest.json"))
    question = _read_json(os.path.join(proof_dir, "question.json"))
    inference_receipts = _read_jsonl(os.path.join(proof_dir, "model_inference_receipts.jsonl"))
    compression_receipts = _read_jsonl(os.path.join(proof_dir, "compression_receipts.jsonl"))
    scheduler_receipts = _read_jsonl(os.path.join(proof_dir, "model_scheduler_receipts.jsonl"))

    ts = manifest.get("throughput_summary", {}) if manifest else {}
    backlog_dir = os.path.join(proof_dir, "backlog")
    backlog_topics = []
    if os.path.isdir(os.path.join(backlog_dir, "topics")):
        for topic_id in sorted(os.listdir(os.path.join(backlog_dir, "topics"))):
            topic_dir = os.path.join(backlog_dir, "topics", topic_id)
            mini = _read_text(os.path.join(topic_dir, "mini_operator_packet.md"))
            backlog_topics.append({"topic_id": topic_id, "mini_packet_preview": mini[:500]})

    overview = {
        "run_id": manifest.get("run_id", "") if manifest else "",
        "question": (question.get("question", "") if question else "")[:200],
        "verdict": manifest.get("verdict", "UNKNOWN") if manifest else "UNKNOWN",
        "model_profile": ts.get("model_profile_used", "unknown"),
        "sources_fetched": manifest.get("sources_fetched", 0) if manifest else 0,
        "model_calls": manifest.get("model_calls", 0) if manifest else 0,
        "model_calls_succeeded": ts.get("model_calls_succeeded", 0),
        "model_calls_timed_out": ts.get("model_calls_timed_out", 0),
        "model_calls_skipped": ts.get("model_calls_skipped", 0),
        "compression_count": len(compression_receipts),
        "claims_extracted": manifest.get("claims_extracted", 0) if manifest else 0,
        "promotions": 0,
        "operator_review_required": True,
        "model_output_is_truth": False,
        "backlog_topics": len(backlog_topics),
    }

    telemetry = _read_json(os.path.join(proof_dir, "telemetry_summary.json"))
    ensemble_receipts = _read_jsonl(os.path.join(proof_dir, "ensemble_receipts.jsonl"))
    checkpoint_receipts = _read_jsonl(os.path.join(proof_dir, "checkpoint_receipts.jsonl"))
    integrity_manifest = _read_json(os.path.join(proof_dir, "proof_integrity_manifest.json"))
    receipt_audit = _read_json(os.path.join(proof_dir, "receipt_completeness_report.json"))

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_type": "overnight_proof_dir",
        "overview": overview,
        "throughput_summary": ts,
        "backlog_topics": backlog_topics,
        "telemetry_summary": telemetry or {},
        "ensemble_receipts_count": len(ensemble_receipts),
        "checkpoint_receipts_count": len(checkpoint_receipts),
        "integrity_manifest": {
            "present": bool(integrity_manifest),
            "file_count": integrity_manifest.get("file_count", 0) if integrity_manifest else 0,
            "combined_hash": (integrity_manifest.get("combined_hash", "")[:16] + "...")
                             if integrity_manifest else "",
            "tamper_evidence_only": integrity_manifest.get("is_tamper_evidence_only", True)
                                   if integrity_manifest else True,
        },
        "receipt_completeness": {
            "present": bool(receipt_audit),
            "verdict": receipt_audit.get("receipt_audit_verdict", "UNKNOWN")
                       if receipt_audit else "NOT_RUN",
            "passed": receipt_audit.get("passed", 0) if receipt_audit else 0,
            "total": receipt_audit.get("total", 0) if receipt_audit else 0,
        },
        "proof_inventory": {
            "model_inference_receipts": len(inference_receipts),
            "compression_receipts": len(compression_receipts),
            "scheduler_receipts": len(scheduler_receipts),
            "ensemble_receipts": len(ensemble_receipts),
            "checkpoint_receipts": len(checkpoint_receipts),
            "telemetry_summary": 1 if telemetry else 0,
            "integrity_manifest": 1 if integrity_manifest else 0,
            "receipt_completeness_report": 1 if receipt_audit else 0,
        },
    }

    if redact:
        data = redact_json_values(data)
    return data


def load_any(path: str, *, redact: bool = True) -> dict:
    """Auto-detect and load a proof bundle or proof dir."""
    ptype = detect_proof_type(path)
    if ptype == "bundle":
        return load_bundle(path, redact=redact)
    elif ptype == "overnight_proof_dir":
        return load_overnight_proof_dir(path, redact=redact)
    elif ptype == "proof_dir":
        return load_proof_dir(path, redact=redact)
    else:
        return load_bundle(path, redact=redact)
