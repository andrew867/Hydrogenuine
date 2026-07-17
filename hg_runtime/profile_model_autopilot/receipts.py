"""Receipt writers for the autopilot. Every proposal/decision is recorded."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path


def write_jsonl(records: list, path: str) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(asdict(r) if hasattr(r, "__dataclass_fields__") else r, default=str) + "\n")
    return str(p)


def write_json(obj, path: str) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(obj) if hasattr(obj, "__dataclass_fields__") else obj
    p.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return str(p)


def operator_review_queue(proposals: list, decisions: list) -> list[dict]:
    """Build a morning operator review queue from proposals + decisions."""
    queue = []
    dec_by_id = {d.proposal_id: d for d in decisions}
    for p in proposals:
        d = dec_by_id.get(p.proposal_id)
        queue.append({
            "proposal_id": p.proposal_id,
            "proposal_kind": p.proposal_kind,
            "decision": d.decision if d else "pending",
            "reason": d.reason if d else "",
            "operator_review_required": True,
            "authority_granted": False,
            "speculative_promotion_allowed": False,
        })
    return queue
