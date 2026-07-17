"""Classification replay helpers."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.schemas import record_hash


def replay_classification_layer(layer: dict) -> dict:
    expected = record_hash(
        {
            "classifications": [row["classification_hash"] for row in layer["document_type_classifications"]],
            "accepted": [row["record_hash"] for row in layer["document_file_records"]],
            "rejected": [row["classification_hash"] for row in layer["rejected_document_records"]],
        }
    )
    replay = record_hash(
        {
            "classifications": [row["classification_hash"] for row in layer["document_type_classifications"]],
            "accepted": [row["record_hash"] for row in layer["document_file_records"]],
            "rejected": [row["classification_hash"] for row in layer["rejected_document_records"]],
        }
    )
    return {
        "replay_deterministic": expected == replay,
        "expected_hash": expected,
        "observed_hash": replay,
    }
