"""Build the perspective matrix from normalized receipts.

Rows = prompt IDs. Columns = participant/model IDs. Each cell links to exactly
one source receipt and records what that model included/omitted/refused/framed.
A cell is a *description* of a model artifact, never a truth claim.
"""

from __future__ import annotations

from hg_runtime.cross_model_perspective.schemas import (
    PERSPECTIVE_MATRIX_CELL_SCHEMA,
    PERSPECTIVE_MATRIX_SCHEMA,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def _cell(receipt: dict) -> dict:
    cell = {
        "schema": PERSPECTIVE_MATRIX_CELL_SCHEMA,
        "prompt_id": receipt["prompt_id"],
        "participant_id": receipt["participant_id"],
        "model_id": receipt["model_id"],
        "receipt_id": receipt["receipt_id"],
        "receipt_hash": receipt["receipt_hash"],
        "links_to_receipt": True,
        "included_claim_tags": receipt["included_claim_tags"],
        "evidence_refs": receipt["evidence_refs"],
        "sourced": receipt["sourced"],
        "refusal_state": receipt["refusal_state"],
        "willingness_state": receipt["willingness_state"],
        "framing_tags": receipt["framing_tags"],
        "moral_principle_tags": receipt["moral_principle_tags"],
        "evidence_gap_tags": receipt["evidence_gap_tags"],
        "genericity_score": receipt["genericity_score"],
        "specificity_score": receipt["specificity_score"],
        "specificity_class": receipt["specificity_class"],
        # Cell-level boundary reminders.
        "refusal_is_authority": False,
        "willingness_is_permission": False,
        "moral_claim_is_authority": False,
        "cell_is_truth_claim": False,
        **neutral_flags(),
    }
    cell["cell_hash"] = canonical_hash(cell)
    return cell


def build_perspective_matrix(receipts: list[dict]) -> dict:
    rows = sorted({r["prompt_id"] for r in receipts})
    columns = sorted({r["participant_id"] for r in receipts})
    cells = [_cell(r) for r in sorted(receipts, key=lambda r: (r["prompt_id"], r["participant_id"]))]
    matrix = {
        "schema": PERSPECTIVE_MATRIX_SCHEMA,
        "version": "perspective_matrix_v1",
        "rows": rows,
        "columns": columns,
        "row_kind": "prompt_id_or_claim_cluster",
        "column_kind": "participant_model_id",
        "cells": cells,
        "cell_count": len(cells),
        "every_cell_links_to_receipt": all(c["links_to_receipt"] and c["receipt_id"] for c in cells),
        "consensus_is_truth": False,
        "disagreement_is_evidence": False,
        **neutral_flags(),
    }
    matrix["matrix_hash"] = canonical_hash(matrix)
    return matrix
