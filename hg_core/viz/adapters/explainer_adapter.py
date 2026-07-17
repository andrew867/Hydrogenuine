"""
Viz Phase 4: Explorable explainers — decision explainer, compare_decisions, proof-path (read-only).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from hg_core.ledger.facts_meaning import explain_decision, compare_decisions
from hg_core.metacognition.proof_path import get_proof_path


def adapt_decision_explainer(workspace_root: Path, decision_id: str) -> Dict[str, Any]:
    """
    Return structured data for explaining a decision: claims, value_weights, context_ref, artifacts, title, event_id.
    Read-only; uses ledger and materialized decisions.
    """
    root = Path(workspace_root)
    return explain_decision(decision_id, root)


def adapt_compare_decisions(
    workspace_root: Path,
    decision_id_a: str,
    decision_id_b: str,
) -> Dict[str, Any]:
    """
    Compare two decisions: overlapping_claim_ids, value_weight_diffs, same_facts_different_action.
    Read-only.
    """
    root = Path(workspace_root)
    return compare_decisions(decision_id_a, decision_id_b, root)


def adapt_proof_path(workspace_root: Path, decision_id: str) -> Dict[str, Any]:
    """
    Return full proof path for a decision: decision, predictions, evaluations, self_assessments.
    Read-only; does not export or emit.
    """
    root = Path(workspace_root)
    return get_proof_path(root, decision_id)
