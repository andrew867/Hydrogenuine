"""LEB-0 deterministic fixtures."""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.receipt import build_boundary_receipt, build_evidence_receipt, build_excerpt_receipt
from hg_runtime.local_evidence_bridge.schemas import record_hash
from hg_runtime.local_evidence_bridge.source_identity import build_operator_source
from hg_runtime.local_evidence_bridge.source_manifest import build_source_manifest


def build_leb0_fixture_layer() -> dict:
    sources = [
        build_operator_source(source_id="src-fixture-001", source_path="tests/fixtures/local_evidence/source_001.md"),
        build_operator_source(source_id="src-fixture-002", source_path="tests/fixtures/local_evidence/source_002.txt"),
    ]
    evidence = [
        build_evidence_receipt(receipt_id="ev-src-fixture-001", source_id=sources[0]["source_id"], source_hash=sources[0]["record_hash"]),
        build_evidence_receipt(receipt_id="ev-src-fixture-002", source_id=sources[1]["source_id"], source_hash=sources[1]["record_hash"]),
    ]
    excerpts = [
        build_excerpt_receipt(excerpt_id="ex-src-fixture-001", source_id=sources[0]["source_id"], excerpt_hash=record_hash({"excerpt": "fixture-only"})),
        build_excerpt_receipt(excerpt_id="ex-src-fixture-002", source_id=sources[1]["source_id"], excerpt_hash=record_hash({"excerpt": "boundary-only"})),
    ]
    boundary = build_boundary_receipt(boundary_id="leb0-boundary")
    manifest = build_source_manifest(sources, evidence, excerpts, boundary)
    redaction = {
        "schema_version": "1",
        "record_type": "evidence_redaction_record_v1",
        "redaction_id": "leb0-redaction",
        "secrets_in_receipts": False,
    }
    redaction["record_hash"] = record_hash(redaction)
    request = {
        "schema_version": "1",
        "record_type": "evidence_ingestion_request_v1",
        "request_id": "leb0-schema-only-request",
        "request_is_permission": False,
        "real_ingestion_enabled": False,
    }
    request["record_hash"] = record_hash(request)
    return {
        "sources": sources,
        "evidence_receipts": evidence,
        "excerpt_receipts": excerpts,
        "boundary_receipt": boundary,
        "manifest": manifest,
        "redaction_record": redaction,
        "ingestion_request": request,
    }
