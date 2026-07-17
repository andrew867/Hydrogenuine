"""Shared storage substrate helpers.

The substrate keeps storage non-authoritative by construction. Every receipt
emitted here carries negative authority fields unless a future authority-chain
implementation explicitly wraps it elsewhere.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "storage_substrate_v2"
ADVISORY_AUTHORITY_FIELDS = {
    "permission_granted": False,
    "authority_created": False,
    "advisory_only": True,
}

SECRET_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
)


class StorageAuthorityError(ValueError):
    """Raised when storage data attempts to cross into authority semantics."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_hash(payload: Any) -> str:
    return "sha256:" + hashlib.sha256(stable_json(payload).encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(stable_json(payload) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"non-object JSONL record in {path}")
            records.append(value)
    return records


def authority_fields() -> dict[str, Any]:
    return dict(ADVISORY_AUTHORITY_FIELDS)


def require_non_authority(payload: dict[str, Any]) -> None:
    if payload.get("permission_granted") is True:
        raise StorageAuthorityError("storage record cannot grant permission")
    if payload.get("authority_created") is True:
        raise StorageAuthorityError("storage record cannot create authority")
    if payload.get("permit_minted") is True:
        raise StorageAuthorityError("storage record cannot mint permits")
    if payload.get("execution_admitted") is True:
        raise StorageAuthorityError("storage record cannot admit execution")


def looks_secret(value: str) -> bool:
    return any(pattern.search(value) for pattern in SECRET_PATTERNS)


def git_head(workspace: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def environment_info(workspace: Path) -> dict[str, Any]:
    return {
        "cwd": str(workspace),
        "head": git_head(workspace),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "canonical_runtime": os.environ.get("HG_CANONICAL_PROOF_RUNTIME", "unknown"),
        "schema_version": SCHEMA_VERSION,
    }


def safe_relative_path(root: Path, candidate: str) -> Path:
    target = (root / candidate).resolve()
    root_resolved = root.resolve()
    try:
        target.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"path traversal refused: {candidate}") from exc
    return target

