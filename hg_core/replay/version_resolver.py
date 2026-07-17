"""
Versioned materializers: register versions, record runs, replay-compat profile, resolve versions for as-of date.
MATERIALIZER_VERSION_REGISTERED, MATERIALIZER_RUN_RECORDED, REPLAY_COMPAT_PROFILE_PUBLISHED.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _registry_path(workspace_root: Path) -> Path:
    return workspace_root / "artifacts" / "replay" / "materializer_versions.json"


def load_materializer_registry(workspace_root: Path) -> Dict[str, Any]:
    """Load materializer version registry from artifacts/replay/materializer_versions.json."""
    p = _registry_path(Path(workspace_root))
    if not p.exists():
        return {"versions": {}, "profiles": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"versions": {}, "profiles": []}


def _write_registry(workspace_root: Path, data: Dict[str, Any]) -> None:
    p = _registry_path(workspace_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def register_materializer_version(
    *,
    name: str,
    version: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    code_hash: str = "",
    event_taxonomy_version: str = "",
    policy_schema_version: str = "",
    workspace_root: Optional[Path] = None,
) -> str:
    """Register materializer version in registry artifact, emit MATERIALIZER_VERSION_REGISTERED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    reg = load_materializer_registry(workspace_root)
    versions = reg.setdefault("versions", {})
    key = f"{name}@{version}"
    versions[key] = {
        "name": name,
        "version": version,
        "code_hash": code_hash,
        "event_taxonomy_version": event_taxonomy_version,
        "policy_schema_version": policy_schema_version,
        "registered_ts": ts,
    }
    _write_registry(workspace_root, reg)
    root = workspace_root / "artifacts" / "replay" / "versions"
    root.mkdir(parents=True, exist_ok=True)
    artifact_path = root / f"{name}_{version.replace('.', '_')}.json"
    artifact_path.write_text(
        json.dumps(versions[key], indent=2),
        encoding="utf-8",
    )
    return emit(
        "MATERIALIZER_VERSION_REGISTERED",
        "materializer_version",
        key,
        {
            "name": name,
            "version": version,
            "artifact_id": str(artifact_path),
            "ts": ts,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def record_materializer_run(
    *,
    materializer_name: str,
    materializer_version: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    ledger_anchor_range: Optional[Dict[str, str]] = None,
    policy_artifact_ids: Optional[List[str]] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Write run summary artifact, emit MATERIALIZER_RUN_RECORDED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    run_id = "mrun_" + hashlib.sha256(f"{materializer_name}:{materializer_version}:{ts}".encode()).hexdigest()[:16]
    root = workspace_root / "artifacts" / "replay" / "runs"
    root.mkdir(parents=True, exist_ok=True)
    summary_path = root / f"{run_id}.json"
    summary = {
        "run_id": run_id,
        "materializer_name": materializer_name,
        "materializer_version": materializer_version,
        "ledger_anchor_range": ledger_anchor_range or {},
        "policy_artifact_ids": policy_artifact_ids or [],
        "ts": ts,
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return emit(
        "MATERIALIZER_RUN_RECORDED",
        "materializer_run",
        run_id,
        {"run_id": run_id, "summary_artifact_id": str(summary_path), "materializer_name": materializer_name, "materializer_version": materializer_version, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def publish_replay_compat_profile(
    *,
    profile_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    materializer_versions: List[Dict[str, str]],
    event_taxonomy_version: str = "",
    workspace_root: Optional[Path] = None,
) -> str:
    """Write replay compat profile artifact, emit REPLAY_COMPAT_PROFILE_PUBLISHED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    root = workspace_root / "artifacts" / "replay" / "profiles"
    root.mkdir(parents=True, exist_ok=True)
    artifact_path = root / f"{profile_id}.json"
    profile = {
        "profile_id": profile_id,
        "materializer_versions": materializer_versions,
        "event_taxonomy_version": event_taxonomy_version,
        "ts": ts,
    }
    artifact_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    reg = load_materializer_registry(workspace_root)
    reg.setdefault("profiles", []).append({"profile_id": profile_id, "ts": ts})
    _write_registry(workspace_root, reg)
    return emit(
        "REPLAY_COMPAT_PROFILE_PUBLISHED",
        "replay_profile",
        profile_id,
        {"profile_id": profile_id, "artifact_id": str(artifact_path), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def resolve_versions_for_replay(
    workspace_root: Path,
    as_of_date: Optional[str] = None,
    tenant_id: str = "default",
    environment: str = "prod",
) -> Dict[str, Any]:
    """
    Resolve which materializer versions to use for replay. Returns replay plan with profile_id and version list.
    Uses latest profile if as_of_date not provided; else selects profile with ts <= as_of_date.
    """
    reg = load_materializer_registry(Path(workspace_root))
    profiles_list = reg.get("profiles") or []
    if not profiles_list:
        return {"plan_id": "none", "materializer_versions": [], "tenant_id": tenant_id, "environment": environment}
    profiles_dir = workspace_root / "artifacts" / "replay" / "profiles"
    candidate = None
    for entry in sorted(profiles_list, key=lambda x: x.get("ts", ""), reverse=True):
        pid = entry.get("profile_id")
        ts = entry.get("ts", "")
        if as_of_date and ts > as_of_date:
            continue
        path = profiles_dir / f"{pid}.json"
        if path.exists():
            candidate = (pid, path)
            break
    if not candidate:
        return {"plan_id": "none", "materializer_versions": [], "tenant_id": tenant_id, "environment": environment}
    pid, path = candidate
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "plan_id": pid,
        "profile_id": pid,
        "materializer_versions": data.get("materializer_versions", []),
        "tenant_id": tenant_id,
        "environment": environment,
        "as_of_date": as_of_date,
    }
