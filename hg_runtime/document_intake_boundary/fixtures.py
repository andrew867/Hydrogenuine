"""Deterministic DIB-0 schema foundation fixtures."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.boundary_policy import build_boundary_policy
from hg_runtime.document_intake_boundary.classification import build_document_type_classification
from hg_runtime.document_intake_boundary.document_file_record import build_document_file_record
from hg_runtime.document_intake_boundary.document_manifest import build_document_intake_manifest
from hg_runtime.document_intake_boundary.intake_records import (
    build_document_provenance_adapter_record,
    build_document_source_identity,
    build_extraction_failure_record,
    build_extraction_receipt,
)
from hg_runtime.document_intake_boundary.parser_policy import build_parser_sandbox_policy
from hg_runtime.document_intake_boundary.quarantine import build_parser_quarantine_record
from hg_runtime.document_intake_boundary.redaction import build_document_redaction_record


def build_dib0_fixture_records() -> dict:
    policy = build_boundary_policy()
    manifest = build_document_intake_manifest(
        manifest_id="dib0-manifest-fixture",
        allowed_paths=["text/sample.txt", "markdown/sample.md", "json/manifest.json"],
    )
    file_record = build_document_file_record(
        file_id="dib-file-001",
        manifest_path="text/sample.txt",
        filename_label="sample.txt",
    )
    classification = build_document_type_classification(
        classification_id="dib-class-001",
        file_id=file_record["file_id"],
        classification_class="TEXT_PLAIN_ALLOWED",
        manifest_path=file_record["manifest_path"],
        extension_label=".txt",
        accepted=True,
    )
    parser_policy = build_parser_sandbox_policy()
    extraction = build_extraction_receipt(receipt_id="dib-extract-001", file_id=file_record["file_id"])
    failure = build_extraction_failure_record(failure_id="dib-fail-001", file_id=file_record["file_id"])
    quarantine = build_parser_quarantine_record(quarantine_id="dib-q-001", file_id=file_record["file_id"], reason="fixture")
    redaction = build_document_redaction_record(redaction_id="dib-redact-001", file_id=file_record["file_id"])
    source_identity = build_document_source_identity(
        source_id="dib-src-001",
        manifest_id=manifest["manifest_id"],
        file_id=file_record["file_id"],
        content_fingerprint=file_record["content_fingerprint"],
    )
    provenance = build_document_provenance_adapter_record(adapter_id="dib-prov-001", source_id=source_identity["source_id"])
    return {
        "boundary_policy": policy,
        "document_intake_manifest": manifest,
        "document_file_record": file_record,
        "document_type_classification": classification,
        "parser_sandbox_policy": parser_policy,
        "extraction_receipt": extraction,
        "extraction_failure_record": failure,
        "parser_quarantine_record": quarantine,
        "document_redaction_record": redaction,
        "document_source_identity": source_identity,
        "document_provenance_adapter_record": provenance,
    }


def build_dib1_fixture_entries() -> list[dict]:
    return [
        {"file_id": "dib-txt-001", "manifest_path": "text/sample.txt", "filename_label": "sample.txt"},
        {"file_id": "dib-md-001", "manifest_path": "markdown/sample.md", "filename_label": "sample.md"},
        {"file_id": "dib-json-001", "manifest_path": "json/manifest.json", "filename_label": "manifest.json"},
        {"file_id": "dib-pdf-001", "manifest_path": "pdf/sample.pdf", "filename_label": "sample.pdf", "declared_media_type": "application/pdf"},
        {"file_id": "dib-ocr-001", "manifest_path": "text/scan.txt", "filename_label": "scan.txt", "ocr_requested": True},
        {"file_id": "dib-html-001", "manifest_path": "html/page.html", "filename_label": "page.html", "declared_media_type": "text/html"},
        {"file_id": "dib-bin-001", "manifest_path": "binary/sample.bin", "filename_label": "sample.bin"},
        {"file_id": "dib-unknown-001", "manifest_path": "unknown/sample.xyz", "filename_label": "sample.xyz"},
        {"file_id": "dib-traversal-001", "manifest_path": "../escape.txt", "filename_label": "escape.txt"},
        {"file_id": "dib-symlink-001", "manifest_path": "text/__symlink__/sample.txt", "filename_label": "sample.txt", "symlink_marker": True},
        {"file_id": "dib-crawl-001", "manifest_path": "text/crawl.txt", "filename_label": "crawl.txt", "directory_crawl_marker": True},
    ]


def build_dib1_manifest() -> dict:
    entries = build_dib1_fixture_entries()
    return build_document_intake_manifest(
        manifest_id="dib1-classifier-manifest-v1",
        allowed_paths=[entry["manifest_path"] for entry in entries if ".." not in entry["manifest_path"]],
    )


def build_dib1_classification_layer() -> dict:
    from hg_runtime.document_intake_boundary.boundary_policy import build_boundary_policy
    from hg_runtime.document_intake_boundary.classification_replay import replay_classification_layer
    from hg_runtime.document_intake_boundary.file_type_classifier import classify_manifest_entries

    manifest = build_dib1_manifest()
    policy = build_boundary_policy()
    entries = build_dib1_fixture_entries()
    layer = classify_manifest_entries(manifest=manifest, entries=entries, policy=policy)
    layer["file_type_classifier_manifest"] = {
        "manifest_id": manifest["manifest_id"],
        "entry_count": len(entries),
        "accepted_count": layer["accepted_count"],
        "rejected_count": layer["rejected_count"],
        "metadata_only": True,
        "parser_execution_enabled": False,
        "content_extraction_enabled": False,
    }
    layer["replay"] = replay_classification_layer(layer)
    return layer


def build_dib2_parser_sandbox_layer() -> dict:
    from hg_runtime.document_intake_boundary.boundary_policy import build_boundary_policy
    from hg_runtime.document_intake_boundary.file_type_classifier import classify_manifest_entries
    from hg_runtime.document_intake_boundary.parser_registry import build_parser_registry
    from hg_runtime.document_intake_boundary.parser_sandbox import build_dib2_parser_sandbox_policy, evaluate_parser_sandbox_layer
    from hg_runtime.document_intake_boundary.parser_sandbox_replay import replay_parser_sandbox_layer

    manifest = build_dib1_manifest()
    policy = build_boundary_policy()
    sandbox_policy = build_dib2_parser_sandbox_policy()
    registry = build_parser_registry()
    entries = build_dib1_fixture_entries()
    dib1 = classify_manifest_entries(manifest=manifest, entries=entries, policy=policy)
    classifications = {}
    for row in dib1["document_type_classifications"]:
        classifications[row["file_id"]] = row["classification_class"]
    for row in dib1["rejected_document_records"]:
        classifications[row["file_id"]] = row["classification_class"]
    layer = evaluate_parser_sandbox_layer(
        entries=entries,
        manifest=manifest,
        policy=sandbox_policy,
        classifications=classifications,
    )
    layer["parser_sandbox_policy"] = sandbox_policy
    layer["parser_registry"] = registry
    layer["parser_sandbox_manifest"] = {
        "manifest_id": manifest["manifest_id"],
        "entry_count": len(entries),
        "evaluation_count": len(layer["parser_evaluations"]),
        "failure_count": layer["failure_count"],
        "quarantine_count": layer["quarantine_count"],
        "parser_execution_enabled": False,
        "content_extraction_enabled": False,
        "no_content_extraction": True,
    }
    layer["replay"] = replay_parser_sandbox_layer(layer)
    return layer


def build_dib3_extraction_layer(*, root=None) -> dict:
    from pathlib import Path

    from hg_runtime.document_intake_boundary.extraction_replay import replay_extraction_layer
    from hg_runtime.document_intake_boundary.safe_text_extractor import extract_safe_text_manifest, load_extraction_manifest

    workspace_root = Path(root) if root else Path(__file__).resolve().parents[2]
    manifest = load_extraction_manifest(workspace_root)
    layer = extract_safe_text_manifest(root=workspace_root, manifest=manifest)
    layer["replay"] = replay_extraction_layer(layer)
    return layer
