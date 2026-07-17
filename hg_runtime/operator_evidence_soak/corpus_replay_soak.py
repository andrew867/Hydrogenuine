"""Run OEC corpus pipeline for soak replay."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.operator_evidence_corpus.corpus_ingestion_harness import ingest_curated_corpus
from hg_runtime.operator_evidence_corpus.corpus_packet_evaluation import evaluate_corpus_packets
from hg_runtime.operator_evidence_soak.stable_hash import stable_pipeline_hash


def run_corpus_pipeline(root: Path) -> dict:
    ingestion = ingest_curated_corpus(root)
    evaluation = evaluate_corpus_packets(ingestion)
    return {
        "ingestion": ingestion,
        "evaluation": evaluation,
        "stable_hash": stable_pipeline_hash(ingestion, evaluation),
        "corpus_manifest_ref": ingestion["corpus_records"]["corpus_manifest"]["manifest_id"],
    }
