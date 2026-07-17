import json
from pathlib import Path
from typing import Any, Dict, List

from .run_index_db import get_run as _get


def load_tool_trace(run_id: str, limit: int = 200) -> Dict[str, Any]:
    r = _get(run_id)
    if not r:
        return {"ok": False, "error": {"code": "NOT_FOUND", "message": "run not found"}}
    run_dir = Path(r.get("run_dir") or "")
    path = run_dir / "recordings" / "attempts.jsonl"
    if not path.exists():
        return {"ok": True, "items": [], "count": 0, "note": "no recordings"}

    requests: Dict[str, Dict[str, Any]] = {}
    responses: Dict[str, Dict[str, Any]] = {}
    items: List[Dict[str, Any]] = []

    def key(rec: Dict[str, Any]) -> str:
        return f"{rec.get('node_id')}:{rec.get('attempt_no')}:{rec.get('loop_id')}:{rec.get('iteration')}"

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("kind") == "request":
                requests[key(rec)] = rec
            elif rec.get("kind") == "response":
                responses[key(rec)] = rec

    for k, req in requests.items():
        request_payload = req.get("request") or {}
        if request_payload.get("type") != "tool":
            continue
        resp = responses.get(k)
        item = {
            "node_id": req.get("node_id"),
            "attempt_no": req.get("attempt_no"),
            "loop_id": req.get("loop_id"),
            "iteration": req.get("iteration"),
            "ts": req.get("ts"),
            "assigned_entity": request_payload.get("assigned_entity"),
            "inputs": request_payload.get("resolved_inputs"),
            "policy": request_payload.get("policy"),
            "response": resp.get("response") if resp else None,
            "error": resp.get("error") if resp else None,
        }
        items.append(item)

    items.sort(key=lambda x: (x.get("ts") or 0.0), reverse=True)
    if limit and len(items) > limit:
        items = items[:limit]
    return {"ok": True, "items": items, "count": len(items)}
