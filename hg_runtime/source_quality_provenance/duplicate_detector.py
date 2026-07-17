"""Deterministic SQP-1 duplicate detector."""

from __future__ import annotations

from itertools import combinations

from hg_runtime.source_quality_provenance.hashing import record_hash
from hg_runtime.source_quality_provenance.schemas import DUPLICATE_CLASSES, assert_neutral, neutral_flags


def classify_duplicate(left: dict, right: dict) -> str:
    if left["content_hash"] == right["content_hash"] and left["source_path_ref"] == right["source_path_ref"]:
        return "SAME_SOURCE_DIFFERENT_EXCERPT" if left.get("excerpt_id") != right.get("excerpt_id") else "EXACT_CONTENT_DUPLICATE"
    if left["content_hash"] == right["content_hash"] and left["source_path_ref"] != right["source_path_ref"]:
        return "SAME_TEXT_DIFFERENT_PATH"
    if left.get("normalized_text_hash") == right.get("normalized_text_hash"):
        return "NORMALIZED_TEXT_DUPLICATE"
    if left["logical_source_key"] == right["logical_source_key"] and left["source_path_ref"] != right["source_path_ref"]:
        return "SUSPECT_COPY_WITHOUT_INDEPENDENCE"
    return "NOT_DUPLICATE"


def build_duplicate_record(left: dict, right: dict) -> dict:
    duplicate_class = classify_duplicate(left, right)
    if duplicate_class not in DUPLICATE_CLASSES:
        raise ValueError(f"unknown_duplicate_class:{duplicate_class}")
    independent = 2 if duplicate_class == "NOT_DUPLICATE" else 1
    record = {
        "schema_version": "1",
        "record_type": "duplicate_source_record_v1",
        "record_id": f"sqp1-duplicate-{left['source_id']}-{right['source_id']}",
        "primary_source_id": left["source_id"],
        "duplicate_source_id": right["source_id"],
        "duplicate_class": duplicate_class,
        "relation": "NOT_DUPLICATE" if duplicate_class == "NOT_DUPLICATE" else "DUPLICATE_OR_COPY_SIGNAL",
        "composite_hash": record_hash(
            {
                "left": left["fingerprint_hash"],
                "right": right["fingerprint_hash"],
                "duplicate_class": duplicate_class,
            }
        ),
        "copy_path_refs": sorted({left["source_path_ref"], right["source_path_ref"]}),
        "independent_corroboration_count": independent,
        "auto_merge_performed": False,
        "old_proof_mutated": False,
        "doctrine_note": "Duplicate detection is not corroboration, truth, authority, deletion, or merge permission.",
        "duplicate_treated_as_corroboration": False,
        "many_copies_treated_as_many_sources": False,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def detect_duplicates(fingerprints: list[dict]) -> list[dict]:
    return [build_duplicate_record(left, right) for left, right in combinations(fingerprints, 2)]
