"""Deterministic SQP schema foundation fixtures."""

from __future__ import annotations

from hg_runtime.source_quality_provenance.conflict import build_conflict_record
from hg_runtime.source_quality_provenance.duplicate_detector import detect_duplicates
from hg_runtime.source_quality_provenance.fingerprint_builder import build_fingerprint_bundle
from hg_runtime.source_quality_provenance.provenance import build_provenance_edge, build_provenance_graph, build_provenance_node
from hg_runtime.source_quality_provenance.quality_scorer import score_sources
from hg_runtime.source_quality_provenance.review_hint import build_quarantine_history, build_redaction_status, build_review_policy_hint
from hg_runtime.source_quality_provenance.source_fingerprint import build_duplicate_source_record, build_source_fingerprint
from hg_runtime.source_quality_provenance.source_identity import build_source_identity
from hg_runtime.source_quality_provenance.source_quality import build_source_quality_score
from hg_runtime.source_quality_provenance.staleness import build_staleness_record


def build_sqp0_fixture_records() -> dict:
    identities = [
        build_source_identity(
            source_id="sqp-source-001",
            logical_source_key="leb.fixture.source.001",
            path_ref="tests/fixtures/local_evidence/source_001.md",
            envelope_ref="LEB-1-TEXT-EVIDENCE-INGESTION",
        ),
        build_source_identity(
            source_id="sqp-source-phase19",
            logical_source_key="phase19.debug.dispatch.incident",
            path_ref="docs/proofs/autonomous_agent_zero/PHASE-40-LEDGER-REPAIR",
            envelope_ref="PHASE-40-LEDGER-REPAIR",
        ),
    ]
    fingerprints = [
        build_source_fingerprint(source_id="sqp-source-001", content_hash="sha256:fixture-content", envelope_hash="sha256:fixture-envelope"),
        build_source_fingerprint(source_id="sqp-source-phase19", content_hash="sha256:phase19-content", envelope_hash="sha256:phase19-envelope"),
    ]
    duplicates = [
        build_duplicate_source_record(
            record_id="sqp-duplicate-schema-fixture",
            primary_source_id="sqp-source-001",
            duplicate_source_id="sqp-source-001-copy",
            relation="DUPLICATE_OF",
            composite_hash=fingerprints[0]["composite_hash"],
        )
    ]
    quality_scores = [build_source_quality_score(source_id=identity["source_id"]) for identity in identities]
    nodes = [
        build_provenance_node(node_id="sqp-node-source-001", node_type="SOURCE", ref=identities[0]["identity_hash"], source_id="sqp-source-001"),
        build_provenance_node(node_id="sqp-node-review-001", node_type="REVIEW_RECEIPT", ref="ORP-4-PROMOTION-GATED-BELIEF-REVISION"),
        build_provenance_node(node_id="sqp-node-phase19", node_type="SOURCE", ref=identities[1]["identity_hash"], source_id="sqp-source-phase19"),
    ]
    edges = [build_provenance_edge(edge_id="sqp-edge-reviewed-by", from_node_id="sqp-node-source-001", to_node_id="sqp-node-review-001", edge_type="REVIEWED_BY")]
    graph = build_provenance_graph(graph_id="sqp0-schema-foundation-graph", source_ids=[row["source_id"] for row in identities], nodes=nodes, edges=edges)
    return {
        "source_identities": identities,
        "source_fingerprints": fingerprints,
        "duplicate_source_records": duplicates,
        "source_quality_scores": quality_scores,
        "provenance_nodes": nodes,
        "provenance_edges": edges,
        "provenance_graph": graph,
        "source_staleness_records": [build_staleness_record(source_id=identity["source_id"]) for identity in identities],
        "source_conflict_records": [build_conflict_record(conflict_id="sqp-conflict-schema-fixture", participant_source_ids=[row["source_id"] for row in identities])],
        "source_redaction_status": [build_redaction_status(source_id=identity["source_id"]) for identity in identities],
        "source_quarantine_history": [build_quarantine_history(source_id=identity["source_id"]) for identity in identities],
        "source_review_policy_hints": [build_review_policy_hint(source_id=identity["source_id"]) for identity in identities],
    }


def build_sqp1_source_fixtures() -> list[dict]:
    return [
        {
            "source_id": "sqp1-source-exact-a",
            "logical_source_key": "leb.fixture.exact.a",
            "path_ref": "tests/fixtures/local_evidence/sqp1_exact.md",
            "excerpt_id": "excerpt-a",
            "text": "Duplicate evidence sentence.",
        },
        {
            "source_id": "sqp1-source-exact-b",
            "logical_source_key": "leb.fixture.exact.a",
            "path_ref": "tests/fixtures/local_evidence/sqp1_exact.md",
            "excerpt_id": "excerpt-a",
            "text": "Duplicate evidence sentence.",
        },
        {
            "source_id": "sqp1-source-same-source-excerpt",
            "logical_source_key": "leb.fixture.exact.a",
            "path_ref": "tests/fixtures/local_evidence/sqp1_exact.md",
            "excerpt_id": "excerpt-b",
            "text": "Duplicate evidence sentence.",
        },
        {
            "source_id": "sqp1-source-normalized",
            "logical_source_key": "leb.fixture.normalized",
            "path_ref": "tests/fixtures/local_evidence/sqp1_normalized.md",
            "excerpt_id": "excerpt-normalized",
            "text": "   duplicate   EVIDENCE sentence.   ",
        },
        {
            "source_id": "sqp1-source-copy-path",
            "logical_source_key": "leb.fixture.copy",
            "path_ref": "tests/fixtures/local_evidence/copy/sqp1_exact_copy.md",
            "excerpt_id": "excerpt-copy",
            "text": "Duplicate evidence sentence.",
        },
        {
            "source_id": "sqp1-source-suspect-copy",
            "logical_source_key": "leb.fixture.exact.a",
            "path_ref": "tests/fixtures/local_evidence/suspect/sqp1_summary.md",
            "excerpt_id": "excerpt-suspect",
            "text": "Related but not identical summary.",
        },
        {
            "source_id": "sqp1-source-distinct",
            "logical_source_key": "leb.fixture.distinct",
            "path_ref": "tests/fixtures/local_evidence/sqp1_distinct.md",
            "excerpt_id": "excerpt-distinct",
            "text": "Independent fixture sentence.",
        },
    ]


def build_sqp1_duplicate_fixture_records() -> dict:
    sources = build_sqp1_source_fixtures()
    bundles = [build_fingerprint_bundle(source) for source in sources]
    identities = [bundle["identity"] for bundle in bundles]
    fingerprints = [bundle["fingerprint"] for bundle in bundles]
    duplicate_records = detect_duplicates(fingerprints)
    return {
        "sources": sources,
        "source_identity_records": identities,
        "source_fingerprints": fingerprints,
        "duplicate_source_records": duplicate_records,
    }


def build_sqp2_quality_feature_sets() -> dict[str, dict[str, bool]]:
    return {
        "sqp2-source-unrated": {},
        "sqp2-source-low-information": {
            "HAS_SOURCE_IDENTITY": True,
        },
        "sqp2-source-structural": {
            "HAS_SOURCE_IDENTITY": True,
            "HAS_STABLE_FINGERPRINT": True,
            "HAS_EXCERPT_BOUNDARY": True,
            "HAS_REDACTION_STATUS": True,
        },
        "sqp2-source-reviewed": {
            "HAS_SOURCE_IDENTITY": True,
            "HAS_STABLE_FINGERPRINT": True,
            "HAS_EXCERPT_BOUNDARY": True,
            "HAS_REDACTION_STATUS": True,
            "HAS_REVIEW_DECISION": True,
            "HAS_PROVENANCE_LINK": True,
            "DUPLICATE_COLLAPSED": True,
        },
        "sqp2-source-conflicted": {
            "HAS_SOURCE_IDENTITY": True,
            "HAS_STABLE_FINGERPRINT": True,
            "CONFLICT_SIGNAL_PRESENT": True,
            "STALE_SIGNAL_PRESENT": True,
            "QUARANTINE_HISTORY_PRESENT": True,
        },
        "sqp2-source-blocked": {
            "HAS_SOURCE_IDENTITY": True,
            "HAS_STABLE_FINGERPRINT": True,
            "SECURITY_FINDING_PRESENT": True,
        },
    }


def build_sqp2_quality_fixture_records() -> dict:
    feature_sets = build_sqp2_quality_feature_sets()
    scored = score_sources(feature_sets)
    return {
        "feature_sets": feature_sets,
        **scored,
    }
