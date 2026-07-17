"""Phase 25 advisory input reader.

Reads local, structured proof summaries (gate_result.json) and references
planning docs by path only. This is read-only: no arbitrary file ingestion, no
PDF/OCR/HTML, no provider/web. Reading our own structured proof JSON is not
document ingestion and is never treated as truth.
"""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.advisory_self_improvement.schemas import assert_neutral, neutral_flags, record_hash

PLANNING_DOCS = (
    "docs/planning/active/HG_ACTIVE_MASTER_PLAN_RECONCILED_2026-06-20.md",
    "docs/planning/active/HG_NEXT_WORK_ORDER_2026-06-20.md",
)


def _latest_gate(root: Path, proof_root_name: str) -> dict:
    proof_root = root / "docs/proofs/autonomous_agent_zero" / proof_root_name
    gates = sorted(proof_root.glob("*/gate_result.json"))
    if not gates:
        return {"verdict": "UNKNOWN", "proof_bundle": "", "present": False}
    data = json.loads(gates[-1].read_text(encoding="utf-8"))
    return {
        "verdict": data.get("verdict", "UNKNOWN"),
        "proof_bundle": str(gates[-1].parent.relative_to(root)),
        "present": True,
    }


def build_phase25_inputs(root: Path) -> dict:
    rc = _latest_gate(root, "SLE-SAFE-LOCAL-EVIDENCE-RELEASE-CANDIDATE")
    extended = _latest_gate(root, "SLE-RC-EXTENDED-REGRESSION-SOAK")
    phase40 = _latest_gate(root, "PHASE-40-LEDGER-REPAIR")
    planning_refs = [
        {"path": p, "present": (root / p).exists()} for p in PLANNING_DOCS
    ]
    inputs = {
        "schema_version": "1",
        "record_type": "phase25_input_summary_v1",
        "sle_rc_status": rc,
        "sle_rc_extended_soak_status": extended,
        "phase40_ledger_repair_status": phase40,
        "phase19_status": "YELLOW",
        "phase24_status": "infrastructure_only",
        "planning_doc_refs": planning_refs,
        "read_only": True,
        "arbitrary_file_ingestion_enabled": False,
        "pdf_ocr_enabled": False,
        "html_parsing_enabled": False,
        **neutral_flags(),
    }
    inputs["input_hash"] = record_hash(inputs)
    assert_neutral(inputs)
    return inputs
