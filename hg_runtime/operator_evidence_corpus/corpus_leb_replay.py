"""Replay OEC-2 corpus ingestion."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.operator_evidence_corpus.corpus_ingestion_harness import ingest_curated_corpus


def replay_corpus_ingestion(root: Path, *, expected_receipt_hashes: list[str]) -> dict:
    layer = ingest_curated_corpus(root)
    receipt_hashes = [row["receipt_hash"] for row in layer["corpus_evidence_receipts"]]
    return {
        "replay_preserves_receipt_hashes": receipt_hashes == expected_receipt_hashes,
        "receipt_hashes": receipt_hashes,
    }
