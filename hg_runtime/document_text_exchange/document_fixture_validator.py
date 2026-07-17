"""Validate DTX document corpus fixtures and explicit manifest paths."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from hg_runtime.document_text_exchange.schemas import ALLOWED_EXTENSIONS, DOCUMENT_FIXTURE_FAMILIES, DTX_APPROVED_ROOT, DTXBoundaryError, EXPECTED_OUTCOME_TYPES


def validate_fixture_paths(root: Path, fixture_paths: list[str]) -> dict:
    failures: list[str] = []
    for path in fixture_paths:
        normalized = PurePosixPath(path.replace("\\", "/"))
        if normalized.is_absolute() or ".." in normalized.parts:
            failures.append(f"path_traversal:{path}")
            continue
        if not str(normalized).startswith(DTX_APPROVED_ROOT):
            failures.append(f"outside_approved_root:{path}")
            continue
        suffix = normalized.suffix.lower()
        if suffix == ".json":
            continue
        if suffix not in ALLOWED_EXTENSIONS:
            failures.append(f"extension_not_allowed:{path}")
            continue
        resolved = (root / str(normalized)).resolve()
        base = (root / DTX_APPROVED_ROOT).resolve()
        if base not in resolved.parents and resolved != base:
            failures.append(f"symlink_escape:{path}")
            continue
        if not resolved.is_file():
            failures.append(f"missing_fixture:{path}")
    return {"ok": not failures, "failures": failures, "validated_path_count": len(fixture_paths)}


def validate_corpus_records(records: dict) -> dict:
    failures: list[str] = []
    families = {row["family_id"] for row in records["dtx_expected_outcomes"]}
    if families != DOCUMENT_FIXTURE_FAMILIES:
        failures.append("family_coverage_incomplete")
    outcomes = {row["outcome_type"] for row in records["dtx_expected_outcomes"]}
    if outcomes != EXPECTED_OUTCOME_TYPES:
        failures.append("outcome_coverage_incomplete")
    if not records["dtx_manifest"]["only_explicit_paths"]:
        failures.append("explicit_paths_not_enforced")
    if records["dtx_boundary_policy"]["directory_crawling_enabled"]:
        failures.append("directory_crawling_enabled")
    if records["dtx_boundary_policy"]["arbitrary_file_ingestion_enabled"]:
        failures.append("arbitrary_ingestion_enabled")
    rows = [records["safe_text_document_exchange"], records["dtx_manifest"], records["dtx_boundary_policy"]] + records["dtx_document_fixtures"] + records["dtx_expected_outcomes"]
    if any(row.get("document_corpus_treated_as_world") for row in rows):
        failures.append("document_corpus_treated_as_world")
    if any(row.get("expected_outcome_treated_as_proof") for row in rows):
        failures.append("expected_outcome_treated_as_proof")
    return {"ok": not failures, "failures": failures}


def validate_document_corpus(root: Path, records: dict) -> dict:
    path_result = validate_fixture_paths(root, records["dtx_manifest"]["explicit_fixture_paths"])
    record_result = validate_corpus_records(records)
    failures = path_result["failures"] + record_result["failures"]
    if failures:
        raise DTXBoundaryError(f"corpus_validation_failed:{failures}")
    return {
        "ok": True,
        "failures": [],
        "validated_path_count": path_result["validated_path_count"],
        "family_count": len(records["dtx_expected_outcomes"]),
        "fixture_count": len(records["dtx_document_fixtures"]),
    }
