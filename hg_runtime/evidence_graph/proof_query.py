"""Evidence graph proof query — read-only queries over proof artifacts.

No mutation. No network. No model calls. No promotion.
Evidence graph edge is not proof.
"""

from __future__ import annotations

import json
import os

from hg_runtime.post_run_review.artifact_loader import load_proof_dir
from hg_runtime.post_run_review.why_not_promoted import explain_why_not_promoted


def query_summary(proof_dir: str) -> dict:
    """Summary statistics for a proof directory."""
    a = load_proof_dir(proof_dir)
    report = a.get("final_report", {})
    model = a.get("model_inference_receipts", [])
    http = a.get("http_fetch_receipts", [])
    screenshots = [f for f in a.get("screenshot_files", []) if f["is_png"]]

    return {
        "proof_dir": proof_dir,
        "run_id": report.get("run_id", ""),
        "final_verdict": report.get("final_verdict", "UNKNOWN"),
        "total_cycles": report.get("total_cycles", 0),
        "sources": len(a.get("source_receipts", [])),
        "http_fetches": len(http),
        "http_successes": sum(1 for r in http if r.get("success")),
        "model_inferences": len(model),
        "model_successes": sum(
            1 for r in model if r.get("inference_status") == "success"
        ),
        "screenshots": len(screenshots),
        "quality_receipts": len(a.get("quality_receipts", [])),
        "contradictions": len(a.get("contradictions", [])),
        "quarantine_entries": len(a.get("quarantine_receipts", [])),
        "evidence_graph_entries": len(a.get("evidence_graph_receipts", [])),
        "model_output_files": len(a.get("model_output_files", [])),
        "promotions": 0,
    }


def list_sources(proof_dir: str) -> list[dict]:
    """List all source receipts."""
    a = load_proof_dir(proof_dir)
    return [
        {
            "pipeline_id": r.get("pipeline_id", ""),
            "url": r.get("url", ""),
            "title": r.get("title", ""),
            "retrieval_method": r.get("retrieval_method", ""),
        }
        for r in a.get("source_receipts", [])
    ]


def list_claims(proof_dir: str) -> list[dict]:
    """List claims from quality receipts."""
    a = load_proof_dir(proof_dir)
    claims = []
    for q in a.get("quality_receipts", []):
        issues = q.get("detected_issues", [])
        claims.append({
            "quality_review_id": q.get("quality_review_id", ""),
            "seed_id": q.get("seed_id", ""),
            "issue_count": len(issues),
            "issues": issues,
        })
    return claims


def list_model_outputs(proof_dir: str) -> list[dict]:
    """List model inference receipts and output files."""
    a = load_proof_dir(proof_dir)
    results = []
    for r in a.get("model_inference_receipts", []):
        results.append({
            "receipt_id": r.get("receipt_id", ""),
            "cycle_id": r.get("cycle_id", ""),
            "inference_status": r.get("inference_status", ""),
            "model_name": r.get("model_name", ""),
            "output_chars": r.get("output_chars", 0),
            "latency_ms": r.get("latency_ms", 0),
            "model_output_is_truth": False,
        })
    return results


def list_gaps(proof_dir: str) -> list[dict]:
    """List evidence gaps from the evidence graph."""
    a = load_proof_dir(proof_dir)
    gaps = []
    for g in a.get("evidence_graph_receipts", []):
        graph = g.get("graph", {})
        for node_id, node in graph.get("nodes", {}).items():
            if "gap" in node_id.lower():
                gaps.append({
                    "node_id": node_id,
                    "label": node.get("label", ""),
                    "node_type": node.get("type", ""),
                })
    return gaps


def list_contradictions(proof_dir: str) -> list[dict]:
    """List contradictions."""
    a = load_proof_dir(proof_dir)
    return [
        {
            "contradiction_id": c.get("contradiction_id", ""),
            "contradiction_type": c.get("contradiction_type", ""),
            "summary": c.get("summary", ""),
            "resolved": c.get("resolved", False),
        }
        for c in a.get("contradictions", [])
    ]


def list_quarantine(proof_dir: str) -> list[dict]:
    """List quarantine entries."""
    a = load_proof_dir(proof_dir)
    results = []
    for q in a.get("quarantine_receipts", []):
        store = q.get("store", {})
        for cand in store.get("candidates", []):
            results.append({
                "candidate_id": cand.get("candidate_id", ""),
                "source": cand.get("source", ""),
                "content_summary": cand.get("content_summary", ""),
                "promoted": cand.get("promoted", False),
            })
    return results


def trace_claim(proof_dir: str, claim_id: str) -> dict:
    """Trace a claim through the evidence graph."""
    a = load_proof_dir(proof_dir)
    found_nodes = []
    found_edges = []
    for g in a.get("evidence_graph_receipts", []):
        graph = g.get("graph", {})
        for node_id, node in graph.get("nodes", {}).items():
            if claim_id in node_id:
                found_nodes.append({"node_id": node_id, **node})
        for edge in graph.get("edges", []):
            if claim_id in edge.get("from", "") or claim_id in edge.get("to", ""):
                found_edges.append(edge)

    return {
        "claim_id": claim_id,
        "nodes_found": found_nodes,
        "edges_found": found_edges,
        "evidence_graph_edge_is_not_proof": True,
    }


def why_not_promoted_item(proof_dir: str, item_id: str) -> dict:
    """Explain why a specific item was not promoted."""
    a = load_proof_dir(proof_dir)

    is_source = any(
        item_id in str(r) for r in a.get("source_receipts", [])
    )
    is_model = any(
        item_id in str(r) for r in a.get("model_inference_receipts", [])
    )

    contras = [
        c for c in a.get("contradictions", [])
        if item_id in str(c)
    ]
    quality = [
        q for q in a.get("quality_receipts", [])
        if item_id in str(q)
    ]
    total_issues = sum(len(q.get("detected_issues", [])) for q in quality)

    return explain_why_not_promoted(
        item_id=item_id,
        item_type="source" if is_source else "model_output" if is_model else "unknown",
        promotion_allowed=False,
        operator_reviewed=False,
        gate_receipt_present=bool(a.get("gate_result")),
        contradictions_unresolved=len(contras),
        evidence_gaps=1,
        unsupported_leaps=0,
        quality_issues=total_issues,
        is_source=is_source,
        is_model_output=is_model,
    )


def export_subgraph(proof_dir: str) -> dict:
    """Export evidence graph as a single combined structure."""
    a = load_proof_dir(proof_dir)
    all_nodes = {}
    all_edges = []
    for g in a.get("evidence_graph_receipts", []):
        graph = g.get("graph", {})
        all_nodes.update(graph.get("nodes", {}))
        all_edges.extend(graph.get("edges", []))
    return {
        "nodes": all_nodes,
        "edges": all_edges,
        "total_nodes": len(all_nodes),
        "total_edges": len(all_edges),
        "evidence_graph_edge_is_not_proof": True,
    }
