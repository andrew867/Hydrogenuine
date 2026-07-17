"""Validate curated corpus records and explicit manifest paths."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from hg_runtime.operator_evidence_corpus.schemas import (
    ALLOWED_EXTENSIONS,
    CLAIM_FAMILY_IDS,
    CORPUS_APPROVED_ROOT,
    EXPECTED_OUTCOME_TYPES,
    OECBoundaryError,
)


def validate_corpus_paths(root: Path, source_paths: list[str]) -> dict:
    failures: list[str] = []
    for path in source_paths:
        normalized = PurePosixPath(path.replace("\\", "/"))
        if normalized.is_absolute() or ".." in normalized.parts:
            failures.append(f"path_traversal:{path}")
            continue
        if not str(normalized).startswith(CORPUS_APPROVED_ROOT):
            failures.append(f"outside_approved_root:{path}")
            continue
        if normalized.suffix.lower() not in ALLOWED_EXTENSIONS:
            failures.append(f"extension_not_allowed:{path}")
            continue
        resolved = (root / str(normalized)).resolve()
        base = (root / CORPUS_APPROVED_ROOT).resolve()
        if base not in resolved.parents and resolved != base:
            failures.append(f"symlink_escape:{path}")
            continue
        if not resolved.is_file():
            failures.append(f"missing_fixture:{path}")
    return {"ok": not failures, "failures": failures, "validated_path_count": len(source_paths)}


def validate_corpus_records(records: dict) -> dict:
    failures: list[str] = []
    families = {row["family_id"] for row in records["corpus_claims"]}
    if families != CLAIM_FAMILY_IDS:
        failures.append("family_coverage_incomplete")
    outcomes = {row["outcome_type"] for row in records["corpus_expected_outcomes"]}
    if outcomes != EXPECTED_OUTCOME_TYPES:
        failures.append("outcome_coverage_incomplete")
    if not records["corpus_manifest"]["only_explicit_paths"]:
        failures.append("explicit_paths_not_enforced")
    if records["corpus_boundary_policy"]["directory_crawling_enabled"]:
        failures.append("directory_crawling_enabled")
    if records["corpus_boundary_policy"]["arbitrary_file_ingestion_enabled"]:
        failures.append("arbitrary_ingestion_enabled")
    rows = (
        [records["operator_evidence_corpus"], records["corpus_manifest"], records["corpus_boundary_policy"]]
        + records["corpus_sources"]
        + records["corpus_claims"]
        + records["corpus_expected_outcomes"]
        + records["corpus_claim_packets"]
    )
    if any(row.get("corpus_treated_as_truth") for row in rows):
        failures.append("corpus_treated_as_truth")
    if any(row.get("expected_outcome_treated_as_proof") for row in rows):
        failures.append("expected_outcome_treated_as_proof")
    return {"ok": not failures, "failures": failures}


def validate_curated_corpus(root: Path, records: dict) -> dict:
    path_result = validate_corpus_paths(root, records["corpus_manifest"]["explicit_source_paths"])
    record_result = validate_corpus_records(records)
    failures = path_result["failures"] + record_result["failures"]
    if not path_result["ok"] or not record_result["ok"]:
        raise OECBoundaryError(f"corpus_validation_failed:{failures}")
    return {
        "ok": True,
        "failures": [],
        "validated_path_count": path_result["validated_path_count"],
        "family_count": len(records["corpus_claims"]),
        "source_count": len(records["corpus_sources"]),
    }
