"""Operator Console Read Model — read-only projection of system state
for the operator.

The console does NOT control anything. It only reads. It aggregates data
from other modules into a unified view for operator inspection.

The console grants NO authority. It is a display surface, not a decision
mechanism. Promotion is NEVER allowed. Operator review is ALWAYS required
— the console exists FOR operator review.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone

SCHEMA_VERSION = "operator_console_read_model_v1"

SECTION_TYPES = {"info", "warning", "critical", "summary"}

_INVARIANTS = {
    "console_is_read_only": True,
    "console_grants_no_authority": True,
    "promotion_allowed": False,
    "operator_review_required": True,
    "model_output_treated_as_truth": False,
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_console_snapshot(*, run_id: str = "", timestamp: str = "") -> dict:
    """Create an empty console snapshot.

    The snapshot is a read-only projection — it never changes system state.
    """
    return {
        "schema": SCHEMA_VERSION,
        "run_id": run_id,
        "timestamp": timestamp or _utc_now_iso(),
        "sections": {},
        **copy.deepcopy(_INVARIANTS),
    }


def add_section(
    snapshot: dict,
    *,
    section_id: str,
    title: str,
    data: dict,
    section_type: str = "info",
) -> dict:
    """Add a section to the snapshot. Returns new snapshot.

    section_type must be one of: info, warning, critical, summary.
    The console only reads — adding a section does not change system state.
    """
    if section_type not in SECTION_TYPES:
        raise ValueError(
            f"Invalid section_type '{section_type}'. "
            f"Must be one of: {sorted(SECTION_TYPES)}"
        )

    section = {
        "section_id": section_id,
        "title": title,
        "section_type": section_type,
        "data": data,
        "added_at": _utc_now_iso(),
    }

    snapshot = dict(snapshot)
    snapshot["sections"] = dict(snapshot.get("sections", {}))
    snapshot["sections"][section_id] = section

    # Re-enforce invariants
    snapshot.update(copy.deepcopy(_INVARIANTS))

    return snapshot


def add_quality_summary(
    snapshot: dict,
    *,
    adjudication_receipts: list | None = None,
    batch_summary: dict | None = None,
) -> dict:
    """Aggregate quality stats from adjudication receipts into a
    'quality_overview' section.

    Reads from receipts or batch summary — never modifies them.
    """
    receipts = adjudication_receipts or []

    total = len(receipts)
    reject_count = 0
    review_count = 0
    high_value_count = 0
    quality_classes = {}

    for r in receipts:
        qc = r.get("quality_class", "")
        quality_classes[qc] = quality_classes.get(qc, 0) + 1
        if qc in ("REJECT_UNSUPPORTED", "REJECT_UNSAFE_OVERCLAIM"):
            reject_count += 1
        if qc in ("HIGH_VALUE", "USABLE_WITH_CAVEATS"):
            high_value_count += 1
        if r.get("operator_review_required"):
            review_count += 1

    # If batch summary provided, overlay its stats
    if batch_summary:
        total = batch_summary.get("total", total)
        reject_count = batch_summary.get("reject_count", reject_count)
        high_value_count = batch_summary.get("high_value_count", high_value_count)
        review_count = batch_summary.get("operator_review_count", review_count)

    data = {
        "total_receipts": total,
        "reject_count": reject_count,
        "high_value_count": high_value_count,
        "operator_review_count": review_count,
        "quality_classes": quality_classes,
    }

    section_type = "critical" if reject_count > 0 else "info"

    return add_section(
        snapshot,
        section_id="quality_overview",
        title="Quality Overview",
        data=data,
        section_type=section_type,
    )


def add_contradiction_summary(
    snapshot: dict,
    *,
    ledger: dict | None = None,
) -> dict:
    """Aggregate contradiction/agreement stats from a ledger into a
    'contradiction_overview' section.

    Reads from ledger — never modifies it.
    """
    ledger = ledger or {}

    contradictions = ledger.get("contradictions", [])
    agreements = ledger.get("agreements", [])

    unresolved = sum(
        1 for c in contradictions if not c.get("resolved_to_truth", False)
    )

    data = {
        "total_contradictions": len(contradictions),
        "total_agreements": len(agreements),
        "unresolved_contradictions": unresolved,
        "contradiction_resolved_to_truth": False,
        "model_consensus_is_not_proof": True,
    }

    section_type = "warning" if len(contradictions) > 0 else "info"

    return add_section(
        snapshot,
        section_id="contradiction_overview",
        title="Contradiction Overview",
        data=data,
        section_type=section_type,
    )


def add_quarantine_summary(
    snapshot: dict,
    *,
    quarantine: dict | None = None,
) -> dict:
    """Aggregate quarantine stats into a 'quarantine_overview' section.

    Reads from quarantine — never modifies it.
    """
    quarantine = quarantine or {}
    entries = quarantine.get("entries", [])

    counts = {}
    for e in entries:
        state = e.get("state", "unknown")
        counts[state] = counts.get(state, 0) + 1

    data = {
        "total_entries": len(entries),
        "counts_by_state": counts,
        "quarantined": counts.get("quarantined", 0),
        "promoted": counts.get("promoted", 0),
        "rejected": counts.get("rejected", 0),
        "candidate_knowledge_is_not_knowledge": True,
    }

    section_type = "warning" if counts.get("quarantined", 0) > 0 else "info"

    return add_section(
        snapshot,
        section_id="quarantine_overview",
        title="Quarantine Overview",
        data=data,
        section_type=section_type,
    )


def add_graph_summary(
    snapshot: dict,
    *,
    graph: dict | None = None,
) -> dict:
    """Aggregate citation graph stats into a 'graph_overview' section.

    Reads from graph — never modifies it.
    """
    graph = graph or {}
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    node_counts = {}
    for n in nodes:
        nt = n.get("node_type", "unknown")
        node_counts[nt] = node_counts.get(nt, 0) + 1

    edge_counts = {}
    for e in edges:
        et = e.get("edge_type", "unknown")
        edge_counts[et] = edge_counts.get(et, 0) + 1

    # Count unsupported claims (claims with no inbound supports/cites)
    claim_node_ids = {
        n.get("node_id") for n in nodes if n.get("node_type") == "claim"
    }
    supported_ids = set()
    for e in edges:
        if e.get("edge_type") in ("supports", "cites"):
            supported_ids.add(e.get("target_node_id"))
    unsupported_count = len(claim_node_ids - supported_ids)

    contradiction_count = sum(
        1 for e in edges if e.get("edge_type") == "contradicts"
    )

    data = {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "node_counts_by_type": node_counts,
        "edge_counts_by_type": edge_counts,
        "unsupported_claims_count": unsupported_count,
        "contradiction_count": contradiction_count,
        "citation_existence_is_not_truth": True,
    }

    section_type = "warning" if contradiction_count > 0 else "info"

    return add_section(
        snapshot,
        section_id="graph_overview",
        title="Graph Overview",
        data=data,
        section_type=section_type,
    )


def get_critical_sections(snapshot: dict) -> list:
    """Return sections with type 'critical'."""
    return [
        dict(s)
        for s in snapshot.get("sections", {}).values()
        if s.get("section_type") == "critical"
    ]


def get_warnings(snapshot: dict) -> list:
    """Return sections with type 'warning'."""
    return [
        dict(s)
        for s in snapshot.get("sections", {}).values()
        if s.get("section_type") == "warning"
    ]


def console_summary(snapshot: dict) -> dict:
    """Section count by type, has_critical, has_warnings."""
    sections = snapshot.get("sections", {})

    counts = {}
    for s in sections.values():
        st = s.get("section_type", "unknown")
        counts[st] = counts.get(st, 0) + 1

    return {
        "total_sections": len(sections),
        "counts_by_type": counts,
        "has_critical": counts.get("critical", 0) > 0,
        "has_warnings": counts.get("warning", 0) > 0,
        "console_is_read_only": True,
        "console_grants_no_authority": True,
        "promotion_allowed": False,
    }


def validate_console(snapshot: dict) -> list[str]:
    """Validate console snapshot invariants.
    Returns list of errors (empty = valid)."""
    errors = []

    if snapshot.get("schema") != SCHEMA_VERSION:
        errors.append(
            f"wrong schema: expected {SCHEMA_VERSION}, "
            f"got {snapshot.get('schema')}"
        )

    # Core invariants — must ALWAYS hold
    if snapshot.get("console_is_read_only") is not True:
        errors.append("console_is_read_only must be True")

    if snapshot.get("console_grants_no_authority") is not True:
        errors.append("console_grants_no_authority must be True")

    if snapshot.get("promotion_allowed") is not False:
        errors.append("promotion_allowed must be False")

    if snapshot.get("operator_review_required") is not True:
        errors.append("operator_review_required must be True")

    if snapshot.get("model_output_treated_as_truth") is not False:
        errors.append("model_output_treated_as_truth must be False")

    # Validate section types
    for sid, section in snapshot.get("sections", {}).items():
        st = section.get("section_type")
        if st not in SECTION_TYPES:
            errors.append(
                f"section[{sid}] has invalid section_type: {st}"
            )

    return errors
