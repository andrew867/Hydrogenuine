"""SQP-3 deterministic provenance graph builder.

Builds a metadata-only provenance graph linking local-evidence sources,
fingerprints, quality scores, excerpts, evidence receipts, claim links,
operator review decisions, promotion requests, gated revision inputs, and
reviewed belief states.

Doctrine:

* Provenance is not authority.
* A provenance graph is not proof.
* Lineage is not truth.
* Duplicate copies are not independent corroboration; many copies are not many
  sources.
* The graph cannot authorize action, authorize tools, or promote belief.
* Missing lineage blocks GREEN (an incomplete graph is reported, never faked).
* Old records are preserved; the builder is append-only and side-effect free.
"""

from __future__ import annotations

from hg_runtime.source_quality_provenance.hashing import record_hash
from hg_runtime.source_quality_provenance.provenance_edge_builder import build_provenance_edge
from hg_runtime.source_quality_provenance.provenance_node_builder import build_provenance_node
from hg_runtime.source_quality_provenance.schemas import (
    PROVENANCE_EDGE_TYPES,
    PROVENANCE_NODE_TYPES,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.source_quality_provenance.source_identity import FIXED_TIME


def build_sqp3_provenance_inputs() -> dict:
    """Deterministic fixture inputs mimicking upstream LEB/ORP/SQP artifacts.

    These are local fixtures only — no files are read, no providers are called.
    They stand in for: LEB local source manifests, LEB evidence receipts, LEB
    evidence claim links, ORP reviewed evidence links, ORP promotion requests,
    ORP promotion-gated belief revision artifacts, SQP-1 fingerprints, and SQP-2
    quality scores.
    """
    sources = [
        {
            "source_id": "sqp3-source-001",
            "logical_source_key": "leb.fixture.source.001",
            "manifest_ref": "docs/proofs/autonomous_agent_zero/LEB-1-TEXT-EVIDENCE-INGESTION",
        },
        {
            "source_id": "sqp3-source-002",
            "logical_source_key": "leb.fixture.source.002",
            "manifest_ref": "docs/proofs/autonomous_agent_zero/LEB-1-TEXT-EVIDENCE-INGESTION",
        },
        {
            # A duplicate copy of source-001 — not an independent source.
            "source_id": "sqp3-source-001-copy",
            "logical_source_key": "leb.fixture.source.001",
            "manifest_ref": "docs/proofs/autonomous_agent_zero/LEB-1-TEXT-EVIDENCE-INGESTION",
            "duplicate_of": "sqp3-source-001",
        },
    ]
    fingerprints = [
        {"source_id": "sqp3-source-001", "fingerprint_ref": "sha256:fixture-fp-001"},
        {"source_id": "sqp3-source-002", "fingerprint_ref": "sha256:fixture-fp-002"},
    ]
    quality_scores = [
        {"source_id": "sqp3-source-001", "quality_band": "REVIEWED_USABLE"},
        {"source_id": "sqp3-source-002", "quality_band": "STRUCTURALLY_USABLE"},
    ]
    excerpts = [
        {"excerpt_id": "sqp3-excerpt-001", "source_id": "sqp3-source-001"},
        {"excerpt_id": "sqp3-excerpt-002", "source_id": "sqp3-source-002"},
    ]
    evidence_receipts = [
        {"receipt_id": "sqp3-receipt-001", "excerpt_id": "sqp3-excerpt-001"},
        {"receipt_id": "sqp3-receipt-002", "excerpt_id": "sqp3-excerpt-002"},
    ]
    claim_links = [
        {"claim_link_id": "sqp3-claim-001", "receipt_id": "sqp3-receipt-001"},
        {"claim_link_id": "sqp3-claim-002", "receipt_id": "sqp3-receipt-002"},
    ]
    reviewed_links = [
        {"review_decision_id": "sqp3-review-001", "claim_link_id": "sqp3-claim-001"},
        {"review_decision_id": "sqp3-review-002", "claim_link_id": "sqp3-claim-002"},
    ]
    promotion_requests = [
        {"promotion_request_id": "sqp3-promo-001", "review_decision_id": "sqp3-review-001"},
    ]
    revision_inputs = [
        {"revision_input_id": "sqp3-revinput-001", "promotion_request_id": "sqp3-promo-001"},
    ]
    belief_states = [
        {"belief_state_id": "sqp3-belief-001", "revision_input_id": "sqp3-revinput-001"},
    ]
    return {
        "sources": sources,
        "fingerprints": fingerprints,
        "quality_scores": quality_scores,
        "excerpts": excerpts,
        "evidence_receipts": evidence_receipts,
        "claim_links": claim_links,
        "reviewed_links": reviewed_links,
        "promotion_requests": promotion_requests,
        "revision_inputs": revision_inputs,
        "belief_states": belief_states,
    }


def build_provenance_graph_layer(inputs: dict) -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []

    def node(node_id: str, node_type: str, ref: str, source_id: str | None = None, metadata: dict | None = None) -> None:
        nodes.append(
            build_provenance_node(
                node_id=node_id, node_type=node_type, ref=ref, source_id=source_id, metadata=metadata
            )
        )

    def edge(edge_id: str, frm: str, to: str, edge_type: str, evidence_ref: str) -> None:
        edges.append(
            build_provenance_edge(
                edge_id=edge_id, from_node_id=frm, to_node_id=to, edge_type=edge_type, evidence_ref=evidence_ref
            )
        )

    # SOURCE nodes (+ DUPLICATE_OF edges for copies).
    for src in inputs["sources"]:
        node(f"node-source-{src['source_id']}", "SOURCE", src["manifest_ref"], source_id=src["source_id"])
    for src in inputs["sources"]:
        if src.get("duplicate_of"):
            edge(
                f"edge-dup-{src['source_id']}",
                f"node-source-{src['source_id']}",
                f"node-source-{src['duplicate_of']}",
                "DUPLICATE_OF",
                src["manifest_ref"],
            )

    # FINGERPRINT + QUALITY_SCORE nodes hung off their source.
    for fp in inputs["fingerprints"]:
        nid = f"node-fingerprint-{fp['source_id']}"
        node(nid, "FINGERPRINT", fp["fingerprint_ref"], source_id=fp["source_id"])
        edge(f"edge-hasfp-{fp['source_id']}", f"node-source-{fp['source_id']}", nid, "HAS_FINGERPRINT", fp["fingerprint_ref"])
    for qs in inputs["quality_scores"]:
        nid = f"node-quality-{qs['source_id']}"
        node(nid, "QUALITY_SCORE", qs["quality_band"], source_id=qs["source_id"])
        edge(f"edge-hasquality-{qs['source_id']}", f"node-source-{qs['source_id']}", nid, "HAS_QUALITY_SCORE", qs["quality_band"])

    # EXCERPT EXCERPTED_FROM SOURCE.
    for ex in inputs["excerpts"]:
        nid = f"node-excerpt-{ex['excerpt_id']}"
        node(nid, "EXCERPT", ex["excerpt_id"], source_id=ex["source_id"])
        edge(f"edge-excerpt-{ex['excerpt_id']}", nid, f"node-source-{ex['source_id']}", "EXCERPTED_FROM", ex["excerpt_id"])

    # EVIDENCE_RECEIPT DERIVED_FROM EXCERPT.
    for rc in inputs["evidence_receipts"]:
        nid = f"node-receipt-{rc['receipt_id']}"
        node(nid, "EVIDENCE_RECEIPT", rc["receipt_id"])
        edge(f"edge-derived-{rc['receipt_id']}", nid, f"node-excerpt-{rc['excerpt_id']}", "DERIVED_FROM", rc["receipt_id"])

    # CLAIM_LINK; EVIDENCE_RECEIPT LINKS_TO_CLAIM CLAIM_LINK.
    for cl in inputs["claim_links"]:
        nid = f"node-claim-{cl['claim_link_id']}"
        node(nid, "CLAIM_LINK", cl["claim_link_id"])
        edge(f"edge-linkclaim-{cl['claim_link_id']}", f"node-receipt-{cl['receipt_id']}", nid, "LINKS_TO_CLAIM", cl["claim_link_id"])

    # REVIEW_DECISION; CLAIM_LINK REVIEWED_BY REVIEW_DECISION.
    for rv in inputs["reviewed_links"]:
        nid = f"node-review-{rv['review_decision_id']}"
        node(nid, "REVIEW_DECISION", rv["review_decision_id"])
        edge(f"edge-reviewed-{rv['review_decision_id']}", f"node-claim-{rv['claim_link_id']}", nid, "REVIEWED_BY", rv["review_decision_id"])

    # PROMOTION_REQUEST REQUESTED_PROMOTION_FROM REVIEW_DECISION.
    for pr in inputs["promotion_requests"]:
        nid = f"node-promo-{pr['promotion_request_id']}"
        node(nid, "PROMOTION_REQUEST", pr["promotion_request_id"])
        edge(f"edge-promofrom-{pr['promotion_request_id']}", nid, f"node-review-{pr['review_decision_id']}", "REQUESTED_PROMOTION_FROM", pr["promotion_request_id"])

    # REVISION_INPUT; PROMOTION_REQUEST GATED_INTO REVISION_INPUT.
    for ri in inputs["revision_inputs"]:
        nid = f"node-revinput-{ri['revision_input_id']}"
        node(nid, "REVISION_INPUT", ri["revision_input_id"])
        edge(f"edge-gated-{ri['revision_input_id']}", f"node-promo-{ri['promotion_request_id']}", nid, "GATED_INTO", ri["revision_input_id"])

    # REVIEWED_BELIEF_STATE; REVISION_INPUT PRODUCED_BELIEF_STATE REVIEWED_BELIEF_STATE.
    for bs in inputs["belief_states"]:
        nid = f"node-belief-{bs['belief_state_id']}"
        node(nid, "REVIEWED_BELIEF_STATE", bs["belief_state_id"])
        edge(f"edge-produced-{bs['belief_state_id']}", f"node-revinput-{bs['revision_input_id']}", nid, "PRODUCED_BELIEF_STATE", bs["belief_state_id"])

    graph = build_graph_record(nodes, edges)
    manifest = build_graph_manifest(nodes, edges, graph)
    return {"nodes": nodes, "edges": edges, "graph": graph, "manifest": manifest}


def build_graph_record(nodes: list[dict], edges: list[dict]) -> dict:
    source_ids = sorted({n["source_id"] for n in nodes if n["node_type"] == "SOURCE" and n["source_id"]})
    logical_keys: set[str] = set()  # distinct logical sources (copies collapse).
    for n in nodes:
        if n["node_type"] == "SOURCE" and n["source_id"]:
            logical_keys.add(n["source_id"].replace("-copy", ""))
    record = {
        "schema_version": "1",
        "record_type": "provenance_graph_v1",
        "graph_id": "sqp3-provenance-graph",
        "source_ids": source_ids,
        "source_node_count": len(source_ids),
        "distinct_logical_source_count": len(logical_keys),
        "node_hashes": [n["record_hash"] for n in nodes],
        "edge_hashes": [e["record_hash"] for e in edges],
        "built_at": FIXED_TIME,
        "doctrine_note": "A provenance graph is not proof. Lineage is not truth.",
        "provenance_treated_as_authority": False,
        "lineage_treated_as_truth": False,
        "graph_is_proof": False,
        "graph_path_is_proof": False,
        "graph_authorizes_action": False,
        "graph_authorizes_tools": False,
        "graph_promotes_belief": False,
        "duplicate_treated_as_corroboration": False,
        "many_copies_treated_as_many_sources": False,
        **neutral_flags(),
    }
    record["graph_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def lineage_completeness(nodes: list[dict], edges: list[dict]) -> dict:
    node_ids = {n["node_id"] for n in nodes}
    present_node_types = {n["node_type"] for n in nodes}
    present_edge_types = {e["edge_type"] for e in edges}
    dangling = sorted(
        {e["edge_id"] for e in edges if e["from_node_id"] not in node_ids or e["to_node_id"] not in node_ids}
    )
    missing_node_types = sorted(PROVENANCE_NODE_TYPES - present_node_types)
    missing_edge_types = sorted(PROVENANCE_EDGE_TYPES - present_edge_types)
    # Every non-SOURCE node must have at least one incident edge (be reachable).
    incident = {e["from_node_id"] for e in edges} | {e["to_node_id"] for e in edges}
    orphan_nodes = sorted({n["node_id"] for n in nodes if n["node_type"] != "SOURCE" and n["node_id"] not in incident})
    complete = not dangling and not missing_node_types and not missing_edge_types and not orphan_nodes
    return {
        "lineage_complete": complete,
        "dangling_edges": dangling,
        "missing_node_types": missing_node_types,
        "missing_edge_types": missing_edge_types,
        "orphan_nodes": orphan_nodes,
    }


def build_graph_manifest(nodes: list[dict], edges: list[dict], graph: dict) -> dict:
    lineage = lineage_completeness(nodes, edges)
    manifest = {
        "schema_version": "1",
        "record_type": "provenance_graph_manifest_v1",
        "phase": "SQP-3",
        "node_count": len(nodes),
        "edge_count": len(edges),
        "node_types_present": sorted({n["node_type"] for n in nodes}),
        "edge_types_present": sorted({e["edge_type"] for e in edges}),
        "graph_hash": graph["graph_hash"],
        "distinct_logical_source_count": graph["distinct_logical_source_count"],
        "source_node_count": graph["source_node_count"],
        **lineage,
        "doctrine_note": "Missing lineage blocks GREEN. Provenance is not authority.",
        "provenance_treated_as_authority": False,
        "lineage_treated_as_truth": False,
        "graph_path_is_proof": False,
        "duplicate_treated_as_corroboration": False,
        "many_copies_treated_as_many_sources": False,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return manifest
