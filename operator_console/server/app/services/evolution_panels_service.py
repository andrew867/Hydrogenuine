"""Fingerprint evolution operator panels (L4)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from hg_learning.evolution.fingerprint_evolver import FingerprintEvolver
from hg_learning.evolution.lineage import default_lineage_store
from hg_learning.evolution.track_record import TrackRecordLedger
from hg_learning.flywheel.corpus_store import default_corpus_store
from hg_learning.flywheel.label_store import default_label_store
from hg_learning.flywheel.outcome_labeler import OutcomeLabeler


def _workspace_root() -> Path:
    try:
        from hg_lib.config import get_workspace_root

        return Path(get_workspace_root())
    except Exception:
        return Path(".")


def _evolver(root: Path) -> FingerprintEvolver:
    corpus = default_corpus_store(root)
    labels = default_label_store(root)
    labeler = OutcomeLabeler(corpus, labels)
    ledger = TrackRecordLedger(corpus, labeler)
    lineage = default_lineage_store(root)
    return FingerprintEvolver(corpus, labeler, ledger, lineage)


def get_lineage_tree(entity_id: str) -> Dict[str, Any]:
    root = _workspace_root()
    lineage = default_lineage_store(root)
    return {"ok": True, **lineage.lineage_tree(entity_id)}


def list_evolution_proposals(*, entity_id: Optional[str] = None) -> Dict[str, Any]:
    root = _workspace_root()
    lineage = default_lineage_store(root)
    pending = lineage.list_pending_proposals(entity_id=entity_id)
    return {"ok": True, "proposals": pending, "count": len(pending)}


def propose_evolution(entity_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    root = _workspace_root()
    evolver = _evolver(root)
    proposal, reason = evolver.propose(entity_id, profile)
    if proposal is None:
        return {"ok": True, "proposal": None, "skipped_reason": reason}
    stored = default_lineage_store(root).get_proposal(proposal.proposal_id)
    return {"ok": True, "proposal": stored, "skipped_reason": None}


def approve_evolution_proposal(
    proposal_id: str,
    *,
    operator_id: str = "operator",
    written_justification: str = "",
) -> Dict[str, Any]:
    root = _workspace_root()
    evolver = _evolver(root)
    try:
        result = evolver.approve_proposal(
            proposal_id,
            operator_id=operator_id,
            written_justification=written_justification,
            workspace_root=root,
        )
        return result
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


def rollback_evolution(entity_id: str, *, operator_id: str = "operator") -> Dict[str, Any]:
    root = _workspace_root()
    return _evolver(root).rollback(entity_id, operator_id=operator_id)
