"""Deterministic curated operator evidence corpus family definitions."""

from __future__ import annotations

CORPUS_ROOT = "tests/fixtures/operator_evidence_corpus"

FAMILY_SPECS: list[dict] = [
    {
        "family_id": "TWO_INDEPENDENT_SOURCES",
        "claim_id": "oec-claim-01-two-independent",
        "claim_text": "Module latency increased after deploy window.",
        "outcome_type": "TWO_INDEPENDENT_SOURCES_PRESENT",
        "sources": [
            {"source_id": "oec-src-01a", "path": f"{CORPUS_ROOT}/family_01/source_alpha.md", "logical_key": "oec.family01.alpha", "quality_band": "REVIEWED_USABLE"},
            {"source_id": "oec-src-01b", "path": f"{CORPUS_ROOT}/family_01/source_beta.txt", "logical_key": "oec.family01.beta", "quality_band": "REVIEWED_USABLE"},
        ],
    },
    {
        "family_id": "DUPLICATE_DISGUISED_AS_SECOND",
        "claim_id": "oec-claim-02-duplicate-disguised",
        "claim_text": "Cache invalidation caused the latency spike.",
        "outcome_type": "DUPLICATE_NOT_CORROBORATION",
        "sources": [
            {"source_id": "oec-src-02-primary", "path": f"{CORPUS_ROOT}/family_02/source_primary.md", "logical_key": "oec.family02.primary", "duplicate_of": None},
            {"source_id": "oec-src-02-copy", "path": f"{CORPUS_ROOT}/family_02/source_copy.txt", "logical_key": "oec.family02.primary", "duplicate_of": "oec-src-02-primary"},
        ],
    },
    {
        "family_id": "CONTRADICTED_BY_SECOND",
        "claim_id": "oec-claim-03-contradicted",
        "claim_text": "The latency spike was caused by cache invalidation.",
        "outcome_type": "CONTRADICTION_VISIBLE",
        "sources": [
            {"source_id": "oec-src-03-support", "path": f"{CORPUS_ROOT}/family_03/source_support.md", "logical_key": "oec.family03.support"},
            {"source_id": "oec-src-03-contra", "path": f"{CORPUS_ROOT}/family_03/source_contra.txt", "logical_key": "oec.family03.contra"},
        ],
    },
    {
        "family_id": "STALE_VS_CURRENT",
        "claim_id": "oec-claim-04-stale-current",
        "claim_text": "Service tier remains on legacy hardware.",
        "outcome_type": "STALE_NOT_FALSE",
        "sources": [
            {"source_id": "oec-src-04-stale", "path": f"{CORPUS_ROOT}/family_04/source_stale.md", "logical_key": "oec.family04.stale", "stale": True},
            {"source_id": "oec-src-04-current", "path": f"{CORPUS_ROOT}/family_04/source_current.txt", "logical_key": "oec.family04.current"},
        ],
    },
    {
        "family_id": "QUARANTINE_RECOMMENDED",
        "claim_id": "oec-claim-05-quarantine",
        "claim_text": "Imported summary may contain unsafe operator notes.",
        "outcome_type": "QUARANTINE_RECOMMENDED",
        "sources": [
            {"source_id": "oec-src-05-quarantine", "path": f"{CORPUS_ROOT}/family_05/source_quarantine.md", "logical_key": "oec.family05.quarantine", "quarantine": True},
        ],
    },
    {
        "family_id": "INSUFFICIENT_EVIDENCE",
        "claim_id": "oec-claim-06-insufficient",
        "claim_text": "Only one local note mentions the incident.",
        "outcome_type": "INSUFFICIENT_EVIDENCE",
        "second_source_required": True,
        "sources": [
            {"source_id": "oec-src-06-only", "path": f"{CORPUS_ROOT}/family_06/source_only.md", "logical_key": "oec.family06.only", "quality_band": "LOW_INFORMATION"},
        ],
    },
    {
        "family_id": "REDACTION_SENSITIVE",
        "claim_id": "oec-claim-07-redaction",
        "claim_text": "Operator note references credential-like token material.",
        "outcome_type": "REDACTION_REQUIRED",
        "sources": [
            {"source_id": "oec-src-07-redaction", "path": f"{CORPUS_ROOT}/family_07/source_redaction.md", "logical_key": "oec.family07.redaction"},
        ],
    },
    {
        "family_id": "LOW_QUALITY_PRESERVED",
        "claim_id": "oec-claim-08-low-quality",
        "claim_text": "Thin note mentions possible slowdown.",
        "outcome_type": "LOW_QUALITY_PRESERVED",
        "sources": [
            {"source_id": "oec-src-08-thin", "path": f"{CORPUS_ROOT}/family_08/source_thin.txt", "logical_key": "oec.family08.thin", "quality_band": "LOW_INFORMATION"},
        ],
    },
    {
        "family_id": "HIGH_QUALITY_NOT_TRUTH",
        "claim_id": "oec-claim-09-high-quality",
        "claim_text": "Reviewed excerpt cites stable deploy receipts.",
        "outcome_type": "HIGH_QUALITY_NOT_CERTAINTY",
        "sources": [
            {"source_id": "oec-src-09-reviewed", "path": f"{CORPUS_ROOT}/family_09/source_reviewed.md", "logical_key": "oec.family09.reviewed", "quality_band": "REVIEWED_USABLE"},
        ],
    },
    {
        "family_id": "OPERATOR_REVIEW_REQUIRED",
        "claim_id": "oec-claim-10-operator-review",
        "claim_text": "Conflicting operator summaries require explicit review.",
        "outcome_type": "OPERATOR_REVIEW_REQUIRED",
        "sources": [
            {"source_id": "oec-src-10-review", "path": f"{CORPUS_ROOT}/family_10/source_review.md", "logical_key": "oec.family10.review"},
            {"source_id": "oec-src-10-review-b", "path": f"{CORPUS_ROOT}/family_10/source_review_b.txt", "logical_key": "oec.family10.review.b"},
        ],
    },
]


def build_curated_corpus() -> dict:
    from hg_runtime.operator_evidence_corpus.corpus_claim import build_corpus_claim, build_corpus_expected_outcome
    from hg_runtime.operator_evidence_corpus.corpus_manifest import build_corpus_manifest, build_operator_evidence_corpus
    from hg_runtime.operator_evidence_corpus.corpus_packet import build_corpus_claim_packet
    from hg_runtime.operator_evidence_corpus.corpus_policy import build_corpus_boundary_policy
    from hg_runtime.operator_evidence_corpus.corpus_source import build_corpus_source

    policy = build_corpus_boundary_policy()
    corpus = build_operator_evidence_corpus(corpus_id="oec-curated-corpus-v1", manifest_id="oec-curated-manifest-v1")
    sources: list[dict] = []
    claims: list[dict] = []
    outcomes: list[dict] = []
    packets: list[dict] = []
    source_paths: list[str] = []
    claim_ids: list[str] = []
    family_ids: list[str] = []

    for spec in FAMILY_SPECS:
        family_ids.append(spec["family_id"])
        claim_ids.append(spec["claim_id"])
        source_ids = [row["source_id"] for row in spec["sources"]]
        for src in spec["sources"]:
            source_paths.append(src["path"])
            sources.append(
                build_corpus_source(
                    source_id=src["source_id"],
                    path_ref=src["path"],
                    logical_key=src["logical_key"],
                    family_id=spec["family_id"],
                    quality_band=src.get("quality_band", "STRUCTURALLY_USABLE"),
                )
            )
        claims.append(
            build_corpus_claim(
                claim_id=spec["claim_id"],
                family_id=spec["family_id"],
                claim_text=spec["claim_text"],
                source_ids=source_ids,
                second_source_required=spec.get("second_source_required", len(source_ids) >= 2),
            )
        )
        outcome_id = f"{spec['claim_id']}-outcome"
        outcomes.append(
            build_corpus_expected_outcome(
                outcome_id=outcome_id,
                claim_id=spec["claim_id"],
                family_id=spec["family_id"],
                outcome_type=spec["outcome_type"],
            )
        )
        packets.append(
            build_corpus_claim_packet(
                packet_id=f"{spec['claim_id']}-packet",
                claim_id=spec["claim_id"],
                family_id=spec["family_id"],
                source_ids=source_ids,
                expected_outcome_id=outcome_id,
            )
        )

    manifest = build_corpus_manifest(
        manifest_id="oec-curated-manifest-v1",
        source_paths=sorted(set(source_paths)),
        claim_ids=claim_ids,
        family_ids=family_ids,
    )
    return {
        "operator_evidence_corpus": corpus,
        "corpus_boundary_policy": policy,
        "corpus_manifest": manifest,
        "corpus_sources": sources,
        "corpus_claims": claims,
        "corpus_expected_outcomes": outcomes,
        "corpus_claim_packets": packets,
        "family_specs": FAMILY_SPECS,
    }
