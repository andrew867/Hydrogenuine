"""Replay dispatcher (MVP).

Replaces live tool/agent dispatch with recorded responses.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from .recording import build_canonical_request
from .schema import Node


def _canon(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _canon(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [_canon(x) for x in obj]
    return obj


def _digest(obj: Any) -> str:
    b = json.dumps(_canon(obj), separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(b).hexdigest()


@dataclass
class ReplayConfig:
    strict_requests: bool = True


class ReplayDispatcher:
    def __init__(self, run_dir: str, cfg: Optional[ReplayConfig] = None):
        self.run_dir = Path(run_dir)
        self.cfg = cfg or ReplayConfig()
        self._load()

    def _load(self) -> None:
        path = self.run_dir / "recordings" / "attempts.jsonl"
        self.records: list = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                self.records.append(json.loads(line))
        self.req: Dict[tuple, Dict[str, Any]] = {}
        self.resp: Dict[tuple, Dict[str, Any]] = {}
        for r in self.records:
            key = (r.get("node_id"), r.get("attempt_no"), r.get("loop_id"), r.get("iteration"))
            if r["kind"] == "request":
                self.req[key] = r
            else:
                self.resp[key] = r

    def dispatch(
        self,
        *,
        node_id: str,
        attempt_no: int,
        request: Dict[str, Any],
        loop_id: Optional[str] = None,
        iteration: Optional[int] = None,
    ) -> Dict[str, Any]:
        key = (node_id, attempt_no, loop_id, iteration)
        if key not in self.resp:
            raise KeyError(f"Missing replay record for {key}")
        if self.cfg.strict_requests:
            if key not in self.req:
                raise KeyError(f"Missing request record for {key}")
            dig = _digest(request)
            if dig != self.req[key]["request_digest"]:
                raise ValueError(f"Request digest mismatch for {key}")
        return self.resp[key]["response"]


def make_replay_adapter(
    run_dir: str,
    cfg: Optional[ReplayConfig] = None,
) -> Callable[..., Dict[str, Any]]:
    """Return a callable with the same signature as dispatch_node for use as executor.dispatcher."""

    replay = ReplayDispatcher(run_dir, cfg)

    def adapter(
        node: Node,
        resolved_inputs: Dict[str, Any],
        run_state: Optional[Any] = None,
        graph_inputs: Optional[Dict[str, Any]] = None,
        expression_strict: bool = False,
    ) -> Dict[str, Any]:
        body_to_loop = getattr(run_state, "body_to_loop", None) or {}
        loop_id = body_to_loop.get(node.id) if body_to_loop else None
        iteration = None
        if loop_id and run_state and getattr(run_state, "loop_state", None):
            iteration = (run_state.loop_state.get(loop_id) or {}).get("iteration")
        request = build_canonical_request(node, resolved_inputs)
        return replay.dispatch(
            node_id=node.id,
            attempt_no=node.attempt_count,
            request=request,
            loop_id=loop_id,
            iteration=iteration,
        )

    return adapter
