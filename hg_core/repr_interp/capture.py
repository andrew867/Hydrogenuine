"""
Layer 8 Phase 2: Opt-in capture for representation interpretability.
When enabled, capture context at executor/Ch3 hooks for later inspection (Phase 3).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional



def is_repr_interp_capture_enabled(
    workspace_root: Optional[Path] = None,
    run_config: Optional[Dict[str, Any]] = None,
) -> bool:
    """Return True if repr_interp capture is enabled via env or run_config."""
    if run_config is not None and run_config.get("repr_interp_capture") is True:
        return True
    return os.environ.get("REPR_INTERP_CAPTURE", "").strip() in ("1", "true", "yes")


def _guard_human_target(context_ref: Optional[Dict[str, Any]], workspace_root: Path) -> None:
    """Fail-closed consent check for user-targeted recognition (G15 / CS-1)."""
    ref = context_ref or {}
    if str(ref.get("target") or "").lower() != "human":
        return
    subject_id = str(ref.get("subject_id") or ref.get("user_id") or "unknown")
    from hg_core.consent import assert_recognition_consent

    min_class = str(ref.get("min_consent_class") or "session")
    assert_recognition_consent(subject_id, min_class=min_class, workspace_root=workspace_root, source="repr_interp_capture")


def capture_context(
    workspace_root: Path,
    run_id: str,
    run_dir: Path,
    node_id: str,
    node_type: str,
    context_ref: Optional[Dict[str, Any]] = None,
    event_id: Optional[str] = None,
) -> None:
    """
    When capture is enabled, append a capture record to run_dir/repr_interp_capture.jsonl.
    Call from executor or Ch3 at key points (e.g. after agent node). No-op if disabled.
    """
    if not is_repr_interp_capture_enabled(Path(workspace_root)):
        return
    _guard_human_target(context_ref, Path(workspace_root))
    path = Path(run_dir) / "repr_interp_capture.jsonl"
    record: Dict[str, Any] = {
        "run_id": run_id,
        "node_id": node_id,
        "node_type": node_type,
        "context_ref": context_ref or {},
        "event_id": event_id,
    }
    ref = context_ref or {}
    if str(ref.get("target") or "").lower() == "human":
        interaction = ref.get("interaction")
        if interaction and isinstance(interaction, dict):
            try:
                from .user_recognition import is_user_recognition_enabled, recognize_user

                if is_user_recognition_enabled():
                    subject_id = str(ref.get("subject_id") or ref.get("user_id") or "unknown")
                    rec = recognize_user(
                        subject_id=subject_id,
                        interaction=interaction,
                        workspace_root=Path(workspace_root),
                        purpose=str(ref.get("purpose") or "repr_interp_capture"),
                    )
                    if rec.get("ok"):
                        record["recognition"] = {
                            "recognition_id": rec.get("recognition_id"),
                            "kinship_detected": rec.get("kinship_detected"),
                            "top_match": rec.get("top_match"),
                        }
            except Exception:
                pass
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def read_captured_contexts(run_dir: Path) -> List[Dict[str, Any]]:
    """Read capture records from run_dir/repr_interp_capture.jsonl (for tests and Phase 3)."""
    path = Path(run_dir) / "repr_interp_capture.jsonl"
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out
