"""Reliability Tranche integration -- wires together all 6 reliability
modules into unified check functions.

No model calls. No web calls. No file mutations. No authority granted.
Promotion is NEVER allowed. Operator review is ALWAYS required.
"""

from __future__ import annotations

import os

# Output quality
from hg_runtime.output_quality.quality_receipts import create_quality_receipt
from hg_runtime.output_quality.slop_detectors import detect_all_issues
from hg_runtime.output_quality.routing_policy import recommend_action

# Contradictions
from hg_runtime.contradictions.contradiction_ledger import (
    create_ledger,
    add_entry,
    get_unresolved,
    ledger_summary,
)
from hg_runtime.contradictions.contradiction_receipts import (
    create_contradiction_receipt,
)

# Evidence graph
from hg_runtime.evidence_graph.graph_builder import (
    create_graph,
    build_seed_claim_chain,
)
from hg_runtime.evidence_graph.graph_queries import graph_summary
from hg_runtime.evidence_graph.graph_receipts import create_graph_receipt

# Operator console
from hg_runtime.operator_console.read_model import (
    build_full_read_model,
)

# Public claims
from hg_runtime.public_claims.public_claim_checker_v2 import (
    check_text,
    check_report_file,
)

# Memory quarantine
from hg_runtime.memory_quarantine.quarantine_store import (
    create_store,
    create_candidate,
    add_candidate,
    store_summary,
)
from hg_runtime.memory_quarantine.quarantine_receipts import (
    create_quarantine_receipt,
)


def check_stop_panic(*, stop_file: str = "", panic_file: str = "") -> dict:
    """Check whether STOP or PANIC sentinel files exist on disk.

    Returns {"active": bool, "stop": bool, "panic": bool, "reason": str}.
    Does NOT create sentinel files.
    """
    stop = bool(stop_file and os.path.isfile(stop_file))
    panic = bool(panic_file and os.path.isfile(panic_file))
    active = stop or panic

    reasons = []
    if stop:
        reasons.append(f"STOP file exists: {stop_file}")
    if panic:
        reasons.append(f"PANIC file exists: {panic_file}")

    return {
        "active": active,
        "stop": stop,
        "panic": panic,
        "reason": "; ".join(reasons) if reasons else "",
    }


def run_quality_check(
    content: str = "",
    *,
    model_id: str = "test",
    stop_panic: bool = False,
) -> dict:
    """Run output quality check on content.

    Creates a quality receipt, runs all slop/quality detectors, and
    recommends an action based on detected issues.

    Returns {"status": "pass"|"weak"|"blocked", "issues": list,
             "action": str, "receipt": dict}.
    """
    if stop_panic:
        receipt = create_quality_receipt(content, model_id=model_id)
        return {
            "status": "blocked",
            "issues": [],
            "action": "blocked_stop_panic",
            "receipt": receipt,
        }

    receipt = create_quality_receipt(content, model_id=model_id)
    issues = detect_all_issues(content, model_id=model_id)
    action_result = recommend_action(issues, model_id=model_id)

    action = action_result["action"]

    # Determine status
    if not issues:
        status = "pass"
    elif action in (
        "reject_for_boundary_violation",
        "quarantine_candidate",
        "route_to_safety_auditor",
    ):
        status = "blocked"
    else:
        status = "weak"

    # Update receipt with results
    receipt["detected_issues"] = issues
    receipt["recommended_action"] = action
    receipt["actual_action"] = action

    return {
        "status": status,
        "issues": issues,
        "action": action,
        "receipt": receipt,
    }


def run_contradiction_check(
    *,
    claims: list[dict] | None = None,
    stop_panic: bool = False,
) -> dict:
    """Run contradiction check on a list of claim pairs.

    claims is a list of {"type": str, "summary": str, "model_ids": list}.

    Returns {"status": "clean"|"unresolved"|"blocked",
             "unresolved_count": int, "ledger_summary": dict}.
    """
    if stop_panic:
        return {
            "status": "blocked",
            "unresolved_count": 0,
            "ledger_summary": {},
        }

    ledger = create_ledger()
    claims = claims or []

    for claim in claims:
        receipt = create_contradiction_receipt(
            contradiction_type=claim.get("type", "model_vs_model"),
            summary=claim.get("summary", ""),
            model_ids=claim.get("model_ids", []),
        )
        ledger = add_entry(ledger, receipt)

    unresolved = get_unresolved(ledger)
    summary = ledger_summary(ledger)

    if not claims:
        status = "clean"
    elif len(unresolved) > 0:
        status = "unresolved"
    else:
        status = "clean"

    return {
        "status": status,
        "unresolved_count": len(unresolved),
        "ledger_summary": summary,
    }


def run_evidence_graph_check(
    *,
    seeds: list[dict] | None = None,
    stop_panic: bool = False,
) -> dict:
    """Build evidence graph from seeds.

    Each seed: {"seed_id": str, "claim_id": str, "seed_label": str,
                "claim_label": str}.

    Returns {"status": "built"|"blocked", "graph_summary": dict,
             "receipt": dict}.
    """
    if stop_panic:
        return {
            "status": "blocked",
            "graph_summary": {},
            "receipt": {},
        }

    graph = create_graph()
    seeds = seeds or []

    for seed in seeds:
        graph = build_seed_claim_chain(
            graph,
            seed_id=seed.get("seed_id", "seed_0"),
            seed_label=seed.get("seed_label", ""),
            claim_id=seed.get("claim_id", "claim_0"),
            claim_label=seed.get("claim_label", ""),
        )

    summary = graph_summary(graph)
    receipt = create_graph_receipt(graph)

    return {
        "status": "built",
        "graph_summary": summary,
        "receipt": receipt,
    }


def run_public_claim_check(
    *,
    text: str = "",
    file_path: str = "",
    stop_panic: bool = False,
) -> dict:
    """Run public claim checker on text or a file.

    Returns {"status": "clean"|"flagged"|"blocked",
             "flagged_count": int, "receipt": dict}.
    """
    if stop_panic:
        receipt = check_text("", stop_panic=True)
        return {
            "status": "blocked",
            "flagged_count": 0,
            "receipt": receipt,
        }

    if file_path and os.path.isfile(file_path):
        receipt = check_report_file(file_path)
    else:
        receipt = check_text(text)

    flagged_count = receipt.get("flagged_count", 0)
    status = "flagged" if flagged_count > 0 else "clean"

    return {
        "status": status,
        "flagged_count": flagged_count,
        "receipt": receipt,
    }


def run_memory_quarantine_check(
    *,
    candidates: list[dict] | None = None,
    stop_panic: bool = False,
) -> dict:
    """Create quarantine store and add candidates.

    Returns {"status": "quarantined"|"blocked",
             "candidate_count": int, "promotion_allowed": False,
             "store_summary": dict}.
    """
    if stop_panic:
        return {
            "status": "blocked",
            "candidate_count": 0,
            "promotion_allowed": False,
            "store_summary": {},
        }

    store = create_store()
    candidates = candidates or []

    for cand in candidates:
        entry = create_candidate(
            candidate_id=cand.get("candidate_id", "cand_0"),
            content_summary=cand.get("content_summary", ""),
            source=cand.get("source", "model_output"),
            model_id=cand.get("model_id", ""),
        )
        store = add_candidate(store, entry)

    summary = store_summary(store)

    return {
        "status": "quarantined",
        "candidate_count": len(candidates),
        "promotion_allowed": False,
        "store_summary": summary,
    }


def run_operator_read_model(
    *,
    run_id: str = "",
    quality_result: dict | None = None,
    contradiction_result: dict | None = None,
    quarantine_result: dict | None = None,
    stop_panic: bool = False,
) -> dict:
    """Build operator console read model from sub-check results.

    Returns {"status": "built"|"blocked", "model": dict}.
    """
    if stop_panic:
        return {
            "status": "blocked",
            "model": {},
        }

    quality_result = quality_result or {}
    contradiction_result = contradiction_result or {}
    quarantine_result = quarantine_result or {}

    weak_outputs = 1 if quality_result.get("status") == "weak" else 0
    unresolved = contradiction_result.get("unresolved_count", 0)
    quarantined = quarantine_result.get("candidate_count", 0)

    alerts = []
    if quality_result.get("status") == "blocked":
        alerts.append({"level": "critical", "message": "Quality check blocked."})
    if contradiction_result.get("status") == "unresolved":
        alerts.append({"level": "warning", "message": f"{unresolved} unresolved contradictions."})

    model = build_full_read_model(
        run_id=run_id,
        active_run_id=run_id,
        weak_outputs=weak_outputs,
        unresolved_contradictions=unresolved,
        quarantined_candidates=quarantined,
        alerts=alerts,
    )

    return {
        "status": "built",
        "model": model,
    }
