"""Learning loop operator panels: labels, relabel queue, track records."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_learning.evolution.track_record import TrackRecordLedger
from hg_learning.flywheel.corpus_store import default_corpus_store
from hg_learning.flywheel.label_store import default_label_store
from hg_learning.flywheel.outcome_labeler import OutcomeLabeler
from hg_learning.flywheel.proof_miner import ProofMiner
from hg_learning.evolution.lineage import default_lineage_store
from hg_learning.feedback.activation import path_status
from hg_learning.feedback.control_group import default_control_group_store
from hg_learning.feedback.incidents import default_incident_store
from hg_learning.feedback.live_priors import default_live_priors_store
from hg_learning.feedback.runner import run_all_shadow_feedback
from hg_learning.feedback.shadow_ledger import default_shadow_ledger
from hg_learning.telemetry import collect_learning_telemetry
from hg_learning.contracts import OutcomeVerdict


def _workspace_root() -> Path:
    try:
        from hg_lib.config import get_workspace_root

        return Path(get_workspace_root())
    except Exception:
        return Path(".")


def _stores():
    root = _workspace_root()
    corpus = default_corpus_store(root)
    labels = default_label_store(root)
    labeler = OutcomeLabeler(corpus, labels)
    ledger = TrackRecordLedger(corpus, labeler)
    return root, corpus, labels, labeler, ledger


def _feedback_stores(root: Path):
    shadow = default_shadow_ledger(root)
    live = default_live_priors_store(root)
    incidents = default_incident_store(root)
    control = default_control_group_store(root)
    return shadow, live, incidents, control


def _full_telemetry(root: Path, corpus, labels, labeler):
    shadow, live, incidents, control = _feedback_stores(root)
    return collect_learning_telemetry(
        corpus, labels, labeler, shadow, live, incidents, control
    )


def sync_learning_corpus() -> Dict[str, Any]:
    """Mine proofs + sync automated labels (idempotent)."""
    root, corpus, labels, labeler, _ledger = _stores()
    miner = ProofMiner(corpus, root)
    mining = miner.backfill()
    label_stats = labeler.sync_corpus_labels()
    telemetry = collect_learning_telemetry(corpus, labels, labeler)
    return {
        "ok": True,
        "mining": mining.to_dict(),
        "labeling": label_stats,
        "telemetry": telemetry,
    }


def get_learning_telemetry() -> Dict[str, Any]:
    _, corpus, labels, labeler, _ = _stores()
    return {"ok": True, **collect_learning_telemetry(corpus, labels, labeler)}


def get_relabel_queue() -> Dict[str, Any]:
    _, corpus, labels, labeler, _ = _stores()
    labeler.sync_corpus_labels()
    items = []
    for row in labels.open_queue():
        signal = corpus.get_signal(row["signal_id"])
        effective = labeler.effective_label(row["signal_id"])
        history = [h.to_dict() for h in labeler.label_history(row["signal_id"])]
        items.append(
            {
                **row,
                "signal_type": signal.signal_type.value if signal else None,
                "payload_preview": (signal.payload if signal else {}),
                "effective_label": effective.to_dict() if effective else None,
                "label_history": history,
            }
        )
    return {"ok": True, "items": items, "count": len(items)}


def post_operator_relabel(
    signal_id: str,
    *,
    verdict: str,
    actor_id: str = "operator",
    rationale: str = "",
) -> Dict[str, Any]:
    _, _corpus, labels, labeler, _ = _stores()
    try:
        v = OutcomeVerdict(verdict.lower())
    except ValueError:
        return {"ok": False, "error": "invalid_verdict"}
    record = labeler.label_operator(
        signal_id,
        v,
        actor_id=actor_id,
        details={"rationale": rationale} if rationale else {},
    )
    return {
        "ok": True,
        "label": record.to_dict(),
        "queue_depth": labels.queue_count(),
    }


def get_track_records(entity_id: Optional[str] = None) -> Dict[str, Any]:
    _, corpus, labels, labeler, ledger = _stores()
    labeler.sync_corpus_labels()
    if entity_id:
        windows = ledger.compute(entity_id)
        return {
            "ok": True,
            "entity_id": entity_id,
            "windows": {k: v.to_dict() for k, v in windows.items()},
        }
    all_records = ledger.compute_all()
    entities = [
        {
            "entity_id": eid,
            "windows": {k: v.to_dict() for k, v in windows.items()},
        }
        for eid, windows in all_records.items()
    ]
    return {"ok": True, "entities": entities, "count": len(entities)}


def run_shadow_feedback() -> Dict[str, Any]:
    root = _workspace_root()
    report = run_all_shadow_feedback(root)
    _, corpus, labels, labeler, _ = _stores()
    ledger = default_shadow_ledger(root)
    return {
        "ok": True,
        "shadow_run": report.to_dict(),
        "ledger_count": ledger.count(),
        "live_applied": report.live_applied,
        "telemetry": _full_telemetry(root, corpus, labels, labeler),
    }


def get_shadow_ledger(*, path_name: str | None = None, limit: int = 100) -> Dict[str, Any]:
    root = _workspace_root()
    ledger = default_shadow_ledger(root)
    return {
        "ok": True,
        "adjustments": ledger.list_recent(path_name=path_name, limit=limit),
        "freezes": ledger.list_freezes(),
        "count": ledger.count(),
    }


def get_learning_activity() -> Dict[str, Any]:
    root = _workspace_root()
    _, corpus, labels, labeler, _ = _stores()
    shadow, live, incidents, control = _feedback_stores(root)
    activation = path_status()
    activity = []
    for path, status in activation.items():
        recent = shadow.list_recent(path_name=path, limit=5)
        mode = str(status.get("mode") or "shadow")
        activity.append(
            {
                "path_name": path,
                "mode": mode,
                "live_enabled": mode == "live",
                "deferred_reason": status.get("reason"),
                "frozen": shadow.is_path_frozen(path),
                "recent_adjustments": recent,
            }
        )
    lineage = default_lineage_store(root)
    pending_evolution = lineage.list_pending_proposals(limit=20)
    return {
        "ok": True,
        "paths": activity,
        "path_activation": activation,
        "live_priors": live.all_priors(),
        "bounded_violations": live.verify_bounded(),
        "open_incidents": incidents.list_open(limit=20),
        "pending_evolution_proposals": pending_evolution,
        "control_group": control.stats(),
        "telemetry": _full_telemetry(root, corpus, labels, labeler),
        "ledger_count": shadow.count(),
    }


def get_live_priors() -> Dict[str, Any]:
    root = _workspace_root()
    live = default_live_priors_store(root)
    return {
        "ok": True,
        "priors": live.all_priors(),
        "bounded_violations": live.verify_bounded(),
        "path_activation": path_status(),
    }


def unfreeze_learning_path(path_name: str) -> Dict[str, Any]:
    root = _workspace_root()
    shadow = default_shadow_ledger(root)
    ok = shadow.unfreeze_path(path_name)
    return {"ok": ok, "path_name": path_name, "unfrozen": ok}


def unfreeze_learning_parameter(parameter: str) -> Dict[str, Any]:
    root = _workspace_root()
    shadow = default_shadow_ledger(root)
    ok = shadow.unfreeze_parameter(parameter)
    return {"ok": ok, "parameter": parameter, "unfrozen": ok}


def resolve_learning_incident(incident_id: str) -> Dict[str, Any]:
    root = _workspace_root()
    incidents = default_incident_store(root)
    ok = incidents.resolve(incident_id)
    return {"ok": ok, "incident_id": incident_id, "resolved": ok}


def get_control_group_stats() -> Dict[str, Any]:
    root = _workspace_root()
    control = default_control_group_store(root)
    return {"ok": True, **control.stats(), "path_activation": path_status()}


def list_capability_escrow() -> Dict[str, Any]:
    from hg_learning.capability_escrow import default_escrow_store

    store = default_escrow_store(_workspace_root())
    return {"ok": True, "deposits": store.list_deposits()}


def deposit_capability_escrow(body: Dict[str, Any]) -> Dict[str, Any]:
    from hg_learning.capability_escrow import default_escrow_store

    store = default_escrow_store(_workspace_root())
    try:
        deposit = store.deposit(
            source_entity=str(body["source_entity"]),
            profile=dict(body["profile"]),
            steering=dict(body.get("steering") or {}),
            artifact_refs=list(body.get("artifact_refs") or []),
        )
    except (KeyError, TypeError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "deposit": deposit.to_dict()}


def replay_capability_escrow(escrow_id: str, *, target_entity: str) -> Dict[str, Any]:
    from hg_learning.capability_escrow import default_escrow_store

    store = default_escrow_store(_workspace_root())
    try:
        replay = store.replay(escrow_id, target_entity=target_entity)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "replay": replay.to_dict()}
