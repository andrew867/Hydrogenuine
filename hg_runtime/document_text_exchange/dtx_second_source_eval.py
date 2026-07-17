"""DTX second-source evaluation helpers."""

from __future__ import annotations

from hg_runtime.document_text_exchange.document_corpus_builder import FAMILY_SPECS


def duplicate_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for spec in FAMILY_SPECS:
        for doc in spec["documents"]:
            if doc.get("duplicate_of"):
                mapping[doc["doc_id"]] = doc["duplicate_of"]
    return mapping


def family_signals(spec: dict) -> dict:
    doc_ids = [doc["doc_id"] for doc in spec["documents"]]
    return {
        "source_ids": doc_ids,
        "duplicate_primary": duplicate_map(),
        "conflict_source_ids": set(doc_ids) if spec["family_id"] == "CONTRADICTORY_TEXT" else set(),
        "quarantine_source_ids": set(),
        "fever_source_ids": set(),
        "redaction_blocked_source_ids": set(doc_ids) if spec["family_id"] == "REDACTION_SENSITIVE" else set(),
        "second_source_required": len(doc_ids) >= 2 and spec["family_id"] not in {"EXTRACTION_FAILURE_CANDIDATE"},
    }


def outcome_to_second_source(spec: dict, outcome: str) -> str:
    if spec["family_id"] == "DUPLICATE_MARKDOWN_COPY":
        return "SECOND_SOURCE_PRESENT_BUT_DUPLICATE"
    if spec["family_id"] in {"CONTRADICTORY_TEXT", "STALE_TEXT"}:
        return "BLOCKED_BY_CONFLICT"
    if spec["family_id"] == "REDACTION_SENSITIVE":
        return "BLOCKED_BY_REDACTION"
    if len(spec["documents"]) >= 2 and spec["family_id"] not in {"DUPLICATE_MARKDOWN_COPY"}:
        return "SECOND_SOURCE_PRESENT_REVIEW_READY"
    return outcome
