"""LEB-0 evidence boundary validation."""

from __future__ import annotations

from pathlib import PurePosixPath

from hg_runtime.local_evidence_bridge.schemas import EvidenceBridgeError, assert_neutral


def validate_source_path(path: str, *, approved_roots: tuple[str, ...] = ("tests/fixtures/local_evidence",)) -> None:
    normalized = PurePosixPath(path.replace("\\", "/"))
    if normalized.is_absolute() or ".." in normalized.parts:
        raise EvidenceBridgeError("path_traversal_or_absolute_path_forbidden")
    if not any(str(normalized).startswith(root) for root in approved_roots):
        raise EvidenceBridgeError("source_path_not_approved_fixture_root")


def validate_boundary_record(record: dict) -> None:
    assert_neutral(record)
    if record.get("operator_provided_source_is_truth"):
        raise EvidenceBridgeError("operator_source_is_not_truth")
    if record.get("local_file_trusted_by_default"):
        raise EvidenceBridgeError("local_file_not_trusted_by_default")
    if record.get("source_excerpt_is_belief"):
        raise EvidenceBridgeError("source_excerpt_is_not_belief")
    if record.get("evidence_receipt_is_truth"):
        raise EvidenceBridgeError("evidence_receipt_is_not_truth")
    if record.get("evidence_receipt_is_authority"):
        raise EvidenceBridgeError("evidence_receipt_is_not_authority")
    if record.get("request_is_permission"):
        raise EvidenceBridgeError("ingestion_request_is_not_permission")
