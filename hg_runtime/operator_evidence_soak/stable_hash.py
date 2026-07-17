"""Stable hash computation excluding timestamp/noise fields."""

from __future__ import annotations

from typing import Any

from hg_runtime.operator_evidence_soak.schemas import STABLE_HASH_EXCLUDE, record_hash


def _strip_noise(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _strip_noise(v) for k, v in value.items() if k not in STABLE_HASH_EXCLUDE}
    if isinstance(value, list):
        return [_strip_noise(item) for item in value]
    return value


def stable_hash(payload: Any) -> str:
    return record_hash(_strip_noise(payload))


def stable_pipeline_hash(ingestion: dict, evaluation: dict) -> str:
    return stable_hash(
        {
            "receipts": ingestion["corpus_evidence_receipts"],
            "excerpts": ingestion["corpus_source_excerpt_receipts"],
            "claim_packets": evaluation["corpus_claim_packets"],
            "second_source_results": evaluation["corpus_second_source_results"],
            "contradiction_packets": evaluation["corpus_contradiction_packets"],
            "dashboard": evaluation["corpus_operator_dashboard"],
        }
    )
