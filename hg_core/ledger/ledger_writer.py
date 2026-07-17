"""
Append-only ledger writer: per-scope chain files, file lock (portalocker), optional global anchors.
Pack 5: Cross-platform locking via portalocker for reliable Windows append.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Generator, Optional, Tuple

import portalocker

from .event_envelope import build_envelope, verify_envelope


def get_ledger_root(workspace_root: Path) -> Path:
    """Root directory for ledger (memory/ledger)."""
    return workspace_root / "memory" / "ledger"


def get_scope_ledger_path(
    workspace_root: Path,
    scope_type: str,
    scope_id: str,
    tenant_id: Optional[str] = None,
    environment: Optional[str] = None,
) -> Path:
    """
    Path to per-scope JSONL file.
    With tenant_id and environment: memory/ledger/scopes/<tenant_id>/<environment>/<scope_type>/<scope_id>.jsonl.
    Without (legacy): memory/ledger/scopes/<scope_type>/<scope_id>.jsonl.
    """
    root = get_ledger_root(workspace_root)
    if tenant_id and environment:
        return root / "scopes" / tenant_id / environment / scope_type / f"{scope_id}.jsonl"
    return root / "scopes" / scope_type / f"{scope_id}.jsonl"


def _get_scope_lock_path(scope_path: Path) -> Path:
    """Path to lock file for a scope ledger (used by portalocker when locking ledger file)."""
    return scope_path


def _append_line(path: Path, line: str) -> None:
    """Append one line with cross-platform exclusive lock (portalocker on ledger file)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with portalocker.Lock(str(path), "a", timeout=10) as f:
        f.write(line.rstrip("\n") + "\n")
        f.flush()
        if hasattr(f, "fileno"):
            try:
                os.fsync(f.fileno())
            except OSError:
                pass


def append_event(
    event: Dict[str, Any],
    workspace_root: Path,
    verify_before_append: bool = True,
) -> str:
    """
    Append a full event envelope to the ledger. Uses per-scope chain file.
    Returns event_id. Creates directories as needed. Locks for append.
    """
    if verify_before_append and not verify_envelope(event):
        raise ValueError("Event failed verification (event_id or signature)")
    scope = event.get("scope") or {}
    scope_type = (scope.get("type") or "global").strip() or "global"
    scope_id = (scope.get("id") or "default").strip() or "default"
    tenant_id = scope.get("tenant_id") or None
    environment = scope.get("environment") or None
    path = get_scope_ledger_path(workspace_root, scope_type, scope_id, tenant_id=tenant_id, environment=environment)
    line = json.dumps(event, ensure_ascii=False) + "\n"
    _append_line(path, line)
    return event["event_id"]


def _iter_scope_paths(workspace_root: Path) -> Generator[Tuple[str, str, Path], None, None]:
    """Yield (scope_type, scope_id, path) for every scope ledger file (legacy and tenancy layouts)."""
    root = get_ledger_root(workspace_root)
    scopes_dir = root / "scopes"
    if not scopes_dir.exists():
        return
    envs = {"dev", "staging", "prod"}
    for top in sorted(scopes_dir.iterdir()):
        if not top.is_dir():
            continue
        subdirs = [d.name for d in top.iterdir() if d.is_dir()]
        if subdirs and set(subdirs) <= envs:
            for env_name in sorted(subdirs):
                env_dir = top / env_name
                for type_dir in sorted(env_dir.iterdir()):
                    if not type_dir.is_dir():
                        continue
                    for f in sorted(type_dir.glob("*.jsonl")):
                        if f.suffix != ".jsonl" or ".lock" in f.name:
                            continue
                        yield type_dir.name, f.stem, f
        else:
            for f in sorted(top.glob("*.jsonl")):
                if f.suffix != ".jsonl" or ".lock" in f.name:
                    continue
                yield top.name, f.stem, f


def iterate_events(
    workspace_root: Path,
    scope_type: Optional[str] = None,
    scope_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    environment: Optional[str] = None,
    action: Optional[str] = None,
    actor_id: Optional[str] = None,
) -> Generator[Dict[str, Any], None, None]:
    """
    Iterate ledger events. If scope_type/scope_id given, read that scope file (optionally with tenant_id/environment);
    else read all scope files under memory/ledger/scopes/ (legacy and tenancy layouts).
    Optional filter by action or actor.agent_id.
    """
    root = get_ledger_root(workspace_root)
    scopes_dir = root / "scopes"
    if not scopes_dir.exists():
        return
    if scope_type is not None and scope_id is not None:
        path = get_scope_ledger_path(workspace_root, scope_type, scope_id, tenant_id=tenant_id, environment=environment)
        if path.exists():
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    ev = json.loads(line)
                    if action is not None and ev.get("action") != action:
                        continue
                    if actor_id is not None and (ev.get("actor") or {}).get("agent_id") != actor_id:
                        continue
                    yield ev
        return
    for st, sid, path in _iter_scope_paths(workspace_root):
        with open(path, encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                ev = json.loads(line)
                if scope_type is not None and ev.get("scope", {}).get("type") != scope_type:
                    continue
                if scope_id is not None and ev.get("scope", {}).get("id") != scope_id:
                    continue
                if action is not None and ev.get("action") != action:
                    continue
                if actor_id is not None and (ev.get("actor") or {}).get("agent_id") != actor_id:
                    continue
                yield ev


def iter_events_by_scope(
    workspace_root: Path,
) -> Generator[Tuple[str, str, Dict[str, Any]], None, None]:
    """
    Yield (scope_type, scope_id, event) for every event in deterministic order (by scope path, then by line).
    Walks both legacy (scopes/type/id.jsonl) and tenancy (scopes/tenant/env/type/id.jsonl) layouts.
    Used by materializers for incremental checkpointing.
    """
    for scope_type, scope_id, path in _iter_scope_paths(workspace_root):
        with open(path, encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                ev = json.loads(line)
                yield scope_type, scope_id, ev


def get_last_hash(
    workspace_root: Path,
    scope_type: str,
    scope_id: str,
    tenant_id: Optional[str] = None,
    environment: Optional[str] = None,
) -> Optional[str]:
    """Return event_id of last event in scope chain, or None if empty."""
    path = get_scope_ledger_path(workspace_root, scope_type, scope_id, tenant_id=tenant_id, environment=environment)
    if not path.exists():
        return None
    last_id = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ev = json.loads(line)
            last_id = ev.get("event_id")
    return last_id
