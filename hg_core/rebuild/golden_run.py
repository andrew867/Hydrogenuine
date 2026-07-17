"""
OS Phase 1: Golden run generator — deterministic synthetic ledger for CI.
Emits a fixed set of events so rebuild produces stable hash manifest.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from hg_core.ledger import emit

SCOPE = {"type": "run", "id": "golden"}
ACTOR = {"agent_id": "golden-run", "pubkey": "0" * 64, "key_id": "golden"}


def generate_golden_run(workspace_root: Path) -> Dict[str, Any]:
    """
    Emit a deterministic minimal set of events (one decision, one work item, one observation) so that
    rebuild produces a stable manifest. Returns summary with event_count and scope.
    """
    workspace_root = Path(workspace_root)
    emit(
        "DECISION_COMMITTED",
        "decision",
        "golden_dec_1",
        {"title": "Golden decision", "based_on_claim_ids": []},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=workspace_root,
    )
    from hg_core.work_items import create_work_item
    create_work_item(
        wi_type="task",
        title="Golden task",
        scope=SCOPE,
        actor=ACTOR,
        priority="normal",
        workspace_root=workspace_root,
    )
    emit(
        "OBSERVATION_RECORDED",
        "observation",
        "golden_obs_1",
        {"observation_id": "golden_obs_1", "signal_id": "golden_sig", "pii_class": "none", "payload_ref": {}},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=workspace_root,
    )
    return {"ok": True, "scope": SCOPE, "event_count": 3}
