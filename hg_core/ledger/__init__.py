"""
Sticky Reality ledger: canonical append-only event stream, hash-chained, signed.
Pack 5: In non-dev, explicit signing key required (no default stub).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from .event_envelope import build_envelope
from .ledger_writer import (
    append_event,
    get_last_hash,
    get_ledger_root,
    get_scope_ledger_path,
    iterate_events,
)
from .ledger_verify import get_event, verify_chain
from . import facts_meaning

# Default actor when none provided (stub key for local/dev).
# Real per-agent identity: OS Phase 5 (IAM/RBAC) or Interop Pack 2 (DID/VC).
# Optional: set _actor_provider(scope, action) -> actor dict to plug in custom identity.
DEFAULT_ACTOR = {
    "agent_id": "hg-ledger",
    "pubkey": "0" * 64,
    "key_id": "default",
}

_actor_provider: Optional[Any] = None


def emit(
    action: str,
    object_type: str,
    object_id: str,
    payload: Dict[str, Any],
    scope: Optional[Dict[str, str]] = None,
    actor: Optional[Dict[str, str]] = None,
    workspace_root: Optional[Path] = None,
    object_path: Optional[str] = None,
    secret_key_hex: Optional[str] = None,
) -> str:
    """
    Emit one ledger event. Uses current scope from scope_context if scope not provided.
    Returns event_id.
    """
    if workspace_root is None:
        try:
            from hg_lib.config import get_workspace_root
            workspace_root = get_workspace_root()
        except ImportError:
            workspace_root = Path(".")
    if scope is None:
        try:
            from hg_core.scope_context import get_scope
            s = get_scope()
            scope = {"type": s.get("scope_type") or "global", "id": s.get("scope_id") or "default"}
        except ImportError:
            scope = {"type": "global", "id": "default"}
    actor_provider = globals().get("_actor_provider")
    if actor is None and actor_provider is not None:
        try:
            actor = actor_provider(scope, action)
        except Exception:
            actor = None
    actor = actor or DEFAULT_ACTOR
    # Pack 5: non-dev requires explicit signing key (no default stub in prod)
    if os.environ.get("HG_ENV", "").strip().lower() == "prod" and secret_key_hex is None:
        raise RuntimeError(
            "Production ledger requires explicit signing key (secret_key_hex or HG_LEDGER_SECRET_KEY). "
            "Use hg-ledger keygen in dev only and set key via env/keystore for prod."
        )
    prev_hash = get_last_hash(
        workspace_root,
        scope["type"],
        scope["id"],
        tenant_id=scope.get("tenant_id"),
        environment=scope.get("environment"),
    )
    envelope = build_envelope(
        action=action,
        object_type=object_type,
        object_id=object_id,
        payload=payload,
        scope=scope,
        actor=actor,
        prev_hash=prev_hash,
        object_path=object_path,
        secret_key_hex=secret_key_hex,
    )
    return append_event(envelope, workspace_root)


def emit_retrieval_set(
    top_k_ids: list,
    agent_id: Optional[str] = None,
    selected_ids: Optional[list] = None,
    scope: Optional[Dict[str, str]] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Emit RETRIEVAL_SET for co-access materializer. Call when a retrieval set or identity
    snapshot is produced (e.g. after context load or access aggregation). Uses scope_context if scope None.
    """
    if workspace_root is None:
        try:
            from hg_lib.config import get_workspace_root
            workspace_root = get_workspace_root()
        except ImportError:
            workspace_root = Path(".")
    if scope is None:
        try:
            from hg_core.scope_context import get_scope
            s = get_scope()
            scope = {"type": s.get("scope_type") or "global", "id": s.get("scope_id") or "default"}
            _sid = s.get("session_id") or ""
            agent_id = agent_id or str(_sid).replace("automation-", "") or DEFAULT_ACTOR["agent_id"]
        except ImportError:
            scope = {"type": "global", "id": "default"}
            agent_id = agent_id or DEFAULT_ACTOR["agent_id"]
    else:
        agent_id = agent_id or DEFAULT_ACTOR["agent_id"]
    import hashlib
    import time
    obj_id = "ret_" + hashlib.sha256(f"{scope}{top_k_ids}{time.time()}".encode()).hexdigest()[:12]
    payload = {"top_k_ids": list(top_k_ids)[:100], "agent_id": agent_id}
    if selected_ids is not None:
        payload["selected_ids"] = list(selected_ids)[:50]
    return emit(
        "RETRIEVAL_SET",
        "retrieval_set",
        obj_id,
        payload,
        scope=scope,
        workspace_root=workspace_root,
    )


def emit_artifact_published(
    path: str,
    artifact_type: str = "artifact",
    checksum: Optional[str] = None,
    version: Optional[str] = None,
    scope: Optional[Dict[str, str]] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Emit ARTIFACT_PUBLISH when an artifact is written. Uses scope_context if scope None.
    """
    if workspace_root is None:
        try:
            from hg_lib.config import get_workspace_root
            workspace_root = get_workspace_root()
        except ImportError:
            workspace_root = Path(".")
    if scope is None:
        try:
            from hg_core.scope_context import get_scope
            s = get_scope()
            scope = {"type": s.get("scope_type") or "global", "id": s.get("scope_id") or "default"}
        except ImportError:
            scope = {"type": "global", "id": "default"}
    import hashlib
    obj_id = "art_" + hashlib.sha256(path.encode()).hexdigest()[:12]
    payload = {"path": path, "artifact_type": artifact_type}
    if checksum:
        payload["checksum"] = checksum
    if version:
        payload["version"] = version
    return emit(
        "ARTIFACT_PUBLISH",
        "artifact",
        obj_id,
        payload,
        scope=scope,
        object_path=path,
        workspace_root=workspace_root,
    )


__all__ = [
    "append_event",
    "build_envelope",
    "emit",
    "emit_retrieval_set",
    "emit_artifact_published",
    "get_event",
    "get_last_hash",
    "get_ledger_root",
    "get_scope_ledger_path",
    "iterate_events",
    "verify_chain",
    "explain_decision",
    "compare_decisions",
    "explain_message_provenance",
    "DEFAULT_ACTOR",
]


def explain_decision(decision_id: str, workspace_root: Path) -> Dict[str, Any]:
    return facts_meaning.explain_decision(decision_id, workspace_root)


def compare_decisions(decision_id_a: str, decision_id_b: str, workspace_root: Path) -> Dict[str, Any]:
    return facts_meaning.compare_decisions(decision_id_a, decision_id_b, workspace_root)


def explain_message_provenance(**kwargs: Any) -> Dict[str, Any]:
    return facts_meaning.explain_message_provenance(**kwargs)
