"""Deterministic OEC-0 schema foundation fixtures."""

from __future__ import annotations

from hg_runtime.operator_evidence_corpus.corpus_claim import build_corpus_claim, build_corpus_expected_outcome
from hg_runtime.operator_evidence_corpus.corpus_manifest import build_corpus_manifest, build_operator_evidence_corpus
from hg_runtime.operator_evidence_corpus.corpus_packet import build_corpus_claim_packet
from hg_runtime.operator_evidence_corpus.corpus_policy import build_corpus_boundary_policy
from hg_runtime.operator_evidence_corpus.corpus_source import build_corpus_source
from hg_runtime.operator_evidence_corpus.schemas import CLAIM_FAMILY_IDS, EXPECTED_OUTCOME_TYPES


def build_oec0_fixture_records() -> dict:
    policy = build_corpus_boundary_policy()
    corpus = build_operator_evidence_corpus(corpus_id="oec0-corpus-fixture", manifest_id="oec0-manifest-fixture")
    manifest = build_corpus_manifest(
        manifest_id="oec0-manifest-fixture",
        source_paths=["tests/fixtures/operator_evidence_corpus/family_01/source_alpha.md"],
        claim_ids=["oec0-claim-fixture"],
        family_ids=["TWO_INDEPENDENT_SOURCES"],
    )
    sources = [
        build_corpus_source(
            source_id="oec0-source-fixture",
            path_ref="tests/fixtures/operator_evidence_corpus/family_01/source_alpha.md",
            logical_key="oec.fixture.alpha",
            family_id="TWO_INDEPENDENT_SOURCES",
        )
    ]
    claims = [
        build_corpus_claim(
            claim_id="oec0-claim-fixture",
            family_id="TWO_INDEPENDENT_SOURCES",
            claim_text="Fixture claim for OEC schema foundation.",
            source_ids=["oec0-source-fixture"],
        )
    ]
    outcomes = [
        build_corpus_expected_outcome(
            outcome_id="oec0-outcome-fixture",
            claim_id="oec0-claim-fixture",
            family_id="TWO_INDEPENDENT_SOURCES",
            outcome_type="TWO_INDEPENDENT_SOURCES_PRESENT",
        )
    ]
    packets = [
        build_corpus_claim_packet(
            packet_id="oec0-packet-fixture",
            claim_id="oec0-claim-fixture",
            family_id="TWO_INDEPENDENT_SOURCES",
            source_ids=["oec0-source-fixture"],
            expected_outcome_id="oec0-outcome-fixture",
        )
    ]
    return {
        "operator_evidence_corpus": corpus,
        "corpus_boundary_policy": policy,
        "corpus_manifest": manifest,
        "corpus_sources": sources,
        "corpus_claims": claims,
        "corpus_expected_outcomes": outcomes,
        "corpus_claim_packets": packets,
        "claim_family_ids": sorted(CLAIM_FAMILY_IDS),
        "expected_outcome_types": sorted(EXPECTED_OUTCOME_TYPES),
    }
