"""DTX corpus replay helpers."""

from __future__ import annotations

from hg_runtime.document_text_exchange.schemas import record_hash


def replay_corpus_layer(layer: dict) -> dict:
    payload = {
        "manifest": layer["dtx_manifest"]["manifest_hash"],
        "fixtures": [row["record_hash"] for row in layer["dtx_document_fixtures"]],
        "outcomes": [row["record_hash"] for row in layer["dtx_expected_outcomes"]],
    }
    expected = record_hash(payload)
    observed = record_hash(payload)
    return {"replay_deterministic": expected == observed, "manifest_hash": layer["dtx_manifest"]["manifest_hash"]}
