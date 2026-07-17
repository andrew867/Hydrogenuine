"""
Layer 9 Phase 4: Debate protocol — run two sides, collect turns, judge, store DebateOutcome.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from hg_core.alignment_science.schemas import (
    debate_outcome,
    debate_turn,
    DebateOutcome,
    DebateTurn,
    validate_debate_outcome,
)


def _artifacts_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "alignment_science" / "debate"


def _stub_turns(
    topic: str, max_turns: int, stance_a: Optional[str], stance_b: Optional[str]
) -> List[DebateTurn]:
    """Placeholder turn generation until LLM debate is wired; deterministic for tests and demos."""
    turns: List[DebateTurn] = []
    for i in range(max_turns):
        side = "a" if i % 2 == 0 else "b"
        content = f"[{side}] turn {i+1} on: {topic[:50]}"
        turns.append(debate_turn(side, content))
    return turns


def _stub_judge(turns: List[DebateTurn]) -> tuple[str, str]:
    """Placeholder judge until LLM judge is wired; deterministic for tests and demos."""
    if len(turns) >= 4:
        return "draw", "Both sides engaged."
    return "inconclusive", "Insufficient turns."


def run_debate(
    workspace_root: Path,
    topic: str,
    stance_a: Optional[str] = None,
    stance_b: Optional[str] = None,
    max_turns: int = 4,
    judge_type: str = "rule",
    emit_ledger: bool = True,
) -> DebateOutcome:
    workspace_root = Path(workspace_root)
    session_id = str(uuid.uuid4())
    turns = _stub_turns(topic, max_turns, stance_a, stance_b)
    judge_outcome, judge_rationale = _stub_judge(turns)
    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    root = _artifacts_root(workspace_root) / date_prefix
    root.mkdir(parents=True, exist_ok=True)
    artifact_path = root / f"{session_id}.json"
    result = debate_outcome(
        session_id=session_id,
        topic=topic,
        judge_outcome=judge_outcome,
        artifact_ref=str(artifact_path),
        stance_a=stance_a,
        stance_b=stance_b,
        turns=turns,
        judge_rationale=judge_rationale,
    )
    artifact_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    if emit_ledger:
        try:
            from hg_core.ledger import emit

            emit(
                "DEBATE_COMPLETED",
                "debate",
                session_id,
                {
                    "session_id": session_id,
                    "topic": topic,
                    "judge_outcome": judge_outcome,
                    "artifact_ref": str(artifact_path),
                },
                workspace_root=workspace_root,
                object_path=str(artifact_path),
            )
        except Exception:
            pass
    return result


def get_debate_outcome(workspace_root: Path, session_id: str) -> Optional[DebateOutcome]:
    workspace_root = Path(workspace_root)
    root = _artifacts_root(workspace_root)
    if not root.exists():
        return None
    for date_dir in sorted(root.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue
        path = date_dir / f"{session_id}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("session_id") == session_id and validate_debate_outcome(data):
                    return data
            except Exception:
                continue
    return None
