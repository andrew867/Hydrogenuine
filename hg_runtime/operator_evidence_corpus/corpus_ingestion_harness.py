"""OEC-2 corpus ingestion harness."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.operator_evidence_corpus.corpus_to_leb import (
    build_corpus_local_source_manifest,
    ingest_corpus_text_source,
)
from hg_runtime.operator_evidence_corpus.curated_corpus_builder import build_curated_corpus
from hg_runtime.operator_evidence_corpus.schemas import assert_neutral, neutral_flags, record_hash


def ingest_curated_corpus(root: Path) -> dict:
    corpus = build_curated_corpus()
    paths = corpus["corpus_manifest"]["explicit_source_paths"]
    source_by_path = {row["path_ref"]: row for row in corpus["corpus_sources"]}
    rows = []
    for path in paths:
        source = source_by_path[path]
        rows.append(ingest_corpus_text_source(root, path, source_id=source["source_id"]))
    receipts = [row["evidence_receipt"] for row in rows]
    excerpts = [row["excerpt_receipt"] for row in rows]
    local_manifest = build_corpus_local_source_manifest(corpus["corpus_sources"], paths)
    ingestion_manifest = {
        "schema_version": "1",
        "record_type": "corpus_leb_ingestion_manifest_v1",
        "manifest_id": "oec-corpus-leb-ingestion",
        "explicit_source_paths": paths,
        "source_count": len(paths),
        "evidence_receipt_count": len(receipts),
        "excerpt_receipt_count": len(excerpts),
        "only_explicit_paths": True,
        "directory_crawling_enabled": False,
        "arbitrary_file_ingestion_enabled": False,
        **neutral_flags(),
    }
    ingestion_manifest["manifest_hash"] = record_hash(ingestion_manifest)
    assert_neutral(ingestion_manifest)
    return {
        "corpus_leb_ingestion_manifest": ingestion_manifest,
        "corpus_local_source_manifest": local_manifest,
        "corpus_evidence_receipts": receipts,
        "corpus_source_excerpt_receipts": excerpts,
        "corpus_records": corpus,
    }
