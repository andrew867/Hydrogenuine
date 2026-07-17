"""Run DTX corpus through DIB safe text extraction."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.document_intake_boundary.safe_text_extractor import extract_safe_text_manifest
from hg_runtime.document_text_exchange.document_corpus import build_dtx_extraction_exchange_record
from hg_runtime.document_text_exchange.document_corpus_builder import build_document_corpus
from hg_runtime.document_text_exchange.dtx_leb_bridge import build_bridge_records
from hg_runtime.document_text_exchange.schemas import assert_neutral, neutral_flags, record_hash


def run_dtx_dib_extraction(root: Path) -> dict:
    corpus = build_document_corpus()
    manifest = corpus["dtx_extraction_manifest"]
    layer = extract_safe_text_manifest(root=root, manifest=manifest)
    exchange_records: list[dict] = []
    for idx, receipt in enumerate(layer["extraction_receipts"]):
        exchange_records.append(
            build_dtx_extraction_exchange_record(
                exchange_record_id=f"dtx-exchange-{idx:03d}",
                fixture_id=receipt["file_id"],
                extraction_receipt_id=receipt["receipt_id"],
                content_hash=receipt["content_hash"],
            )
        )
    bridge_records = build_bridge_records(
        extraction_receipts=layer["extraction_receipts"],
        dib_adapters=layer["dib_to_leb_adapter_records"],
    )
    bridge_manifest = {
        "manifest_id": "dtx-bridge-manifest-v1",
        "corpus_manifest_id": corpus["dtx_manifest"]["manifest_id"],
        "extraction_manifest_id": manifest["manifest_id"],
        "receipt_count": len(layer["extraction_receipts"]),
        "failure_count": len(layer["extraction_failure_records"]),
        "bridge_count": len(bridge_records),
        "explicit_manifest_only": True,
        **neutral_flags(),
    }
    bridge_manifest["manifest_hash"] = record_hash(bridge_manifest)
    assert_neutral(bridge_manifest)
    return {
        "corpus_records": corpus,
        "extraction_layer": layer,
        "dtx_extraction_receipts": layer["extraction_receipts"],
        "dtx_extraction_failures": layer["extraction_failure_records"],
        "dtx_document_source_identities": layer["document_source_identity_records"],
        "dtx_document_provenance_adapter_records": layer["document_provenance_adapter_records"],
        "dtx_dib_to_leb_adapter_records": layer["dib_to_leb_adapter_records"],
        "dtx_extraction_exchange_records": exchange_records,
        "dtx_leb_bridge_records": bridge_records,
        "dtx_bridge_manifest": bridge_manifest,
    }
