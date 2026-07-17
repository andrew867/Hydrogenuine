"""Recording helpers (MVP).

Writes append-only attempts.jsonl records. Keep this module side-effect free except file I/O.

Expected usage:
- recorder = AttemptRecorder(run_dir, run_id, graph_id)
- token = recorder.record_request(...)
- recorder.record_response(token, ...)
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .schema import Node


def _canon(obj: Any) -> Any:
    # minimal canonicalization: sort dict keys recursively
    if isinstance(obj, dict):
        return {k: _canon(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [_canon(x) for x in obj]
    return obj


def _digest(obj: Any) -> str:
    b = json.dumps(_canon(obj), separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(b).hexdigest()


def build_canonical_request(node: Node, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Build a canonical dispatch request for recording/replay (deterministic, key-sorted)."""
    policy_subset: Dict[str, Any] = {}
    if getattr(node.policy, "timeout_s", None) is not None:
        policy_subset["timeout_s"] = node.policy.timeout_s
    if getattr(node.policy, "memory_profile", None) is not None:
        policy_subset["memory_profile"] = node.policy.memory_profile
    return {
        "type": node.type,
        "assigned_entity": node.assigned_entity,
        "resolved_inputs": inputs,
        "policy": policy_subset,
    }


@dataclass
class AttemptToken:
    node_id: str
    attempt_no: int
    loop_id: Optional[str] = None
    iteration: Optional[int] = None


class AttemptRecorder:
    def __init__(self, run_dir: str, run_id: str, graph_id: str):
        self.run_dir = Path(run_dir)
        self.run_id = run_id
        self.graph_id = graph_id
        self.rec_dir = self.run_dir / "recordings"
        self.rec_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.rec_dir / "attempts.jsonl"

    def record_request(
        self,
        *,
        node_id: str,
        attempt_no: int,
        request: Dict[str, Any],
        loop_id: Optional[str] = None,
        iteration: Optional[int] = None,
        gate_parent: Optional[str] = None,
        gate_taken: Optional[Any] = None,
    ) -> AttemptToken:
        rec = {
            "kind": "request",
            "run_id": self.run_id,
            "graph_id": self.graph_id,
            "node_id": node_id,
            "attempt_no": attempt_no,
            "loop_id": loop_id,
            "iteration": iteration,
            "gate_parent": gate_parent,
            "gate_taken": gate_taken,
            "ts": time.time(),
            "request": request,
            "request_digest": _digest(request),
        }
        self._append(rec)
        return AttemptToken(node_id=node_id, attempt_no=attempt_no, loop_id=loop_id, iteration=iteration)

    def record_response(
        self,
        token: AttemptToken,
        response: Dict[str, Any],
        error: Optional[Dict[str, Any]] = None,
    ) -> None:
        rec = {
            "kind": "response",
            "run_id": self.run_id,
            "graph_id": self.graph_id,
            "node_id": token.node_id,
            "attempt_no": token.attempt_no,
            "loop_id": token.loop_id,
            "iteration": token.iteration,
            "ts": time.time(),
            "response": response,
            "error": error,
            "response_digest": _digest({"response": response, "error": error}),
        }
        self._append(rec)

    def _append(self, rec: Dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
