"""Replay curated corpus build for determinism checks."""

from __future__ import annotations

from hg_runtime.operator_evidence_corpus.curated_corpus_builder import build_curated_corpus
from hg_runtime.operator_evidence_corpus.schemas import record_hash


def replay_curated_corpus(*, expected_manifest_hash: str) -> dict:
    records = build_curated_corpus()
    manifest_hash = records["corpus_manifest"]["manifest_hash"]
    return {
        "replay_preserves_manifest_hash": manifest_hash == expected_manifest_hash,
        "manifest_hash": manifest_hash,
    }
