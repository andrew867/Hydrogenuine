"""Local scratch store — transient posture only; receipts are forbidden."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from hg_core.ledger.canonical_json import canonical_dumps
from hg_runtime.yawn.types import ScratchSnapshot

ALLOWED_SCRATCH_KEYS = frozenset(
    {
        "transient_prompt_buffer",
        "uncommitted_proposal_drafts",
        "temporary_local_summaries",
        "cached_context_windows",
        "local_debounce_flags",
        "scratch_notes",
        "stale_token_stream_buffers",
    }
)

FORBIDDEN_SCRATCH_KEYS = frozenset(
    {
        "event_log",
        "mel_ledger",
        "ter_receipts",
        "oea_receipts",
        "srp_bundles",
        "approvals",
        "final_confirmations",
        "memory_records",
        "checkpoints",
        "trusted_snapshots",
        "committed_decisions",
        "authority_refs",
        "pending_protected_actions",
    }
)


def _scratch_dir(runtime_dir: Path) -> Path:
    return Path(runtime_dir) / "yawn_scratch"


def _agent_path(runtime_dir: Path, agent_id: str) -> Path:
    safe = agent_id.replace("/", "_").replace("\\", "_")
    return _scratch_dir(runtime_dir) / f"{safe}.json"


def scratch_hash(data: dict[str, Any]) -> str:
    digest = hashlib.sha256(canonical_dumps(data)).hexdigest()
    return f"sha256:{digest}"


def load_scratch(runtime_dir: Path, agent_id: str) -> dict[str, Any]:
    path = _agent_path(runtime_dir, agent_id)
    if not path.exists():
        return {
            "agent_id": agent_id,
            "event_head_seq": 0,
            "updated_at": 0,
            "transient": {},
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {
        "agent_id": agent_id,
        "event_head_seq": 0,
        "updated_at": 0,
        "transient": {},
    }


def save_scratch(runtime_dir: Path, agent_id: str, data: dict[str, Any]) -> None:
    path = _agent_path(runtime_dir, agent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(canonical_dumps(data))
    tmp.replace(path)


def snapshot_scratch(runtime_dir: Path, agent_id: str) -> ScratchSnapshot:
    data = load_scratch(runtime_dir, agent_id)
    transient = data.get("transient", {})
    if not isinstance(transient, dict):
        transient = {}
    keys = tuple(sorted(k for k in transient if k in ALLOWED_SCRATCH_KEYS))
    return ScratchSnapshot(
        agent_id=agent_id,
        scratch_hash=scratch_hash(data),
        event_head_seq=int(data.get("event_head_seq", 0) or 0),
        keys_present=keys,
    )


def clear_allowed_scratch(
    runtime_dir: Path,
    agent_id: str,
    *,
    clear_transient: bool = True,
) -> tuple[list[str], str]:
    """Clear only allowed transient keys; return cleared key names and hash before."""
    data = load_scratch(runtime_dir, agent_id)
    before_hash = scratch_hash(data)
    cleared: list[str] = []
    if not clear_transient:
        return cleared, before_hash
    transient = data.get("transient", {})
    if not isinstance(transient, dict):
        transient = {}
    drafts = transient.get("uncommitted_proposal_drafts")
    if isinstance(drafts, list):
        for item in drafts:
            if isinstance(item, dict):
                item["stale"] = True
                item["authority_freshened"] = False
    for key in list(transient.keys()):
        if key in FORBIDDEN_SCRATCH_KEYS:
            continue
        if key in ALLOWED_SCRATCH_KEYS:
            del transient[key]
            cleared.append(key)
        elif key.startswith("_stale_"):
            del transient[key]
            cleared.append(key)
    data["transient"] = transient
    data["updated_at"] = int(time.time())
    save_scratch(runtime_dir, agent_id, data)
    return cleared, before_hash


def update_scratch_head(runtime_dir: Path, agent_id: str, event_head_seq: int) -> None:
    data = load_scratch(runtime_dir, agent_id)
    data["event_head_seq"] = event_head_seq
    data["updated_at"] = int(time.time())
    save_scratch(runtime_dir, agent_id, data)


def scratch_age_seconds(data: dict[str, Any], *, now: int | None = None) -> int:
    updated = int(data.get("updated_at", 0) or 0)
    if updated <= 0:
        return 0
    current = now if now is not None else int(time.time())
    return max(0, current - updated)


def seed_transient_scratch(
    runtime_dir: Path,
    agent_id: str,
    *,
    event_head_seq: int,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Test/helper: create scratch with stale head and transient buffers."""
    transient: dict[str, Any] = {
        "transient_prompt_buffer": "old context",
        "uncommitted_proposal_drafts": [{"proposal_id": "p1", "stale": False}],
        "cached_context_windows": ["w1"],
    }
    if extra:
        for key, value in extra.items():
            if key in ALLOWED_SCRATCH_KEYS:
                transient[key] = value
    data = {
        "agent_id": agent_id,
        "event_head_seq": event_head_seq,
        "updated_at": int(time.time()) - 600,
        "transient": transient,
    }
    save_scratch(runtime_dir, agent_id, data)
    return data


__all__ = [
    "ALLOWED_SCRATCH_KEYS",
    "FORBIDDEN_SCRATCH_KEYS",
    "clear_allowed_scratch",
    "load_scratch",
    "save_scratch",
    "scratch_age_seconds",
    "scratch_hash",
    "seed_transient_scratch",
    "snapshot_scratch",
    "update_scratch_head",
]
