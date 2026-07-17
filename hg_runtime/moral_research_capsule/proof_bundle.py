"""Proof bundle builder for moral research capsule."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .schemas import (
    DOCTRINE, ConflictRecord, EvidenceGapTask, MatrixCell,
    ResponseReceipt, ResearchDocument, SourceRecord,
    UncertaintyRecord, MoralFrameResult,
)


def write_proof_bundle(
    bundle_dir: Path,
    gate_result: dict,
    scenarios: list,
    cohort: list,
    receipts: list[ResponseReceipt],
    frame_results: list[MoralFrameResult],
    matrix_cells: list[MatrixCell],
    conflicts: list[ConflictRecord],
    evidence_gaps: list[EvidenceGapTask],
    uncertainty_records: list[UncertaintyRecord],
    source_records: list[SourceRecord],
    research_doc: ResearchDocument,
    research_doc_md: str,
    test_results: dict,
) -> dict[str, str]:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}

    def _write_json(name: str, data):
        p = bundle_dir / name
        p.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        written[name] = str(p)

    def _write_jsonl(name: str, items):
        p = bundle_dir / name
        lines = [json.dumps(asdict(i) if hasattr(i, "__dataclass_fields__") else i, default=str) for i in items]
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written[name] = str(p)

    def _write_text(name: str, text: str):
        p = bundle_dir / name
        p.write_text(text, encoding="utf-8")
        written[name] = str(p)

    _write_json("gate_result.json", gate_result)
    _write_json("scenario_suite.json", [asdict(s) for s in scenarios])
    _write_json("model_cohort_registry.json", [asdict(m) for m in cohort])
    _write_jsonl("fixture_model_response_receipts.jsonl", receipts)
    _write_jsonl("response_classification_records.jsonl", receipts)
    _write_jsonl("moral_frame_classification_records.jsonl", frame_results)
    _write_json("moral_perspective_matrix.json", [asdict(c) for c in matrix_cells])
    _write_json("moral_conflict_map.json", [asdict(c) for c in conflicts])
    _write_jsonl("evidence_gap_ledger.jsonl", evidence_gaps)
    _write_jsonl("uncertainty_ledger.jsonl", uncertainty_records)
    _write_jsonl("source_ledger.jsonl", source_records)
    _write_json("research_document.json", asdict(research_doc))
    _write_text("research_document.md", research_doc_md)

    _write_json("boundary_assertions.json", {
        "doctrine": DOCTRINE,
        "phase_19": "YELLOW",
        "phase_24": "infrastructure_only",
        "zero_is_not_agi": True,
        "zero_is_not_conscious": True,
        "zero_is_not_sovereign": True,
        "zero_cannot_self_authorize": True,
        "live_providers_called": False,
        "external_calls_made": False,
        "internet_research_performed": False,
        "tools_authorized": False,
        "live_effects_created": False,
    })

    _write_json("redaction_audit.json", {
        "secrets_found": False,
        "pii_found": False,
        "redaction_performed": False,
        "notes": "Fixture data only, no real user data.",
    })

    _write_json("test_results.json", test_results)
    _write_text("report_snapshot.md", research_doc_md)

    return written
