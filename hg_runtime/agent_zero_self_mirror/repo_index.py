"""Shared repo indexing with secret/path exclusions."""

from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from hg_runtime.agent_zero_self_mirror.schema import FROZEN_FALSE, IndexEntry, IndexStatus, TaintClass
from hg_runtime.trust_boundary.secrets import SecretGuard

WORKSPACE = Path(__file__).resolve().parents[2]

EXCLUDE_DIR_NAMES = frozenset({
    ".git", "__pycache__", "node_modules", ".venv", "venv", ".hg-local",
    ".hg_demo", "dist", "build", ".eggs", "audio_models", "voice_models",
})

EXCLUDE_PATH_FRAGMENTS = (
    ".env", "credentials", "cookie", "session", "browser", "secret",
    ".onnx", ".wav", ".mp3", ".flac", ".pt", ".bin", ".pkl",
)

MAX_EXCERPT = 240
MAX_FILE_BYTES = 512_000


def _git_head(workspace: Path) -> tuple[str, str]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=workspace, capture_output=True, text=True, check=False)
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=workspace, capture_output=True, text=True, check=False)
    return (head.stdout.strip() if head.returncode == 0 else ""), (branch.stdout.strip() if branch.returncode == 0 else "")


def _should_exclude(rel: str) -> str | None:
    low = rel.replace("\\", "/").lower()
    parts = low.split("/")
    if any(p in EXCLUDE_DIR_NAMES for p in parts):
        return "excluded directory"
    if any(p.startswith(".env") for p in parts):
        return ".env* excluded"
    for frag in EXCLUDE_PATH_FRAGMENTS:
        if frag in low:
            return f"forbidden fragment: {frag}"
    return None


def _file_hash(path: Path) -> str | None:
    try:
        data = path.read_bytes()
        if len(data) > MAX_FILE_BYTES:
            data = data[:MAX_FILE_BYTES]
        return hashlib.sha256(data).hexdigest()
    except OSError:
        return None


def _safe_excerpt(path: Path) -> str | None:
    if path.suffix not in {".py", ".md", ".json", ".yaml", ".yml", ".txt"}:
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:MAX_EXCERPT]
        if SecretGuard.contains_secret(text):
            return "[REDACTED: secret-shaped content]"
        return text
    except OSError:
        return None


def _module_guess(rel: str) -> str | None:
    if rel.startswith("hg_runtime/") and rel.endswith(".py"):
        return rel.replace("/", ".").removesuffix(".py")
    return None


def index_paths(
    roots: Iterable[str],
    *,
    workspace: Path | None = None,
    taint_class: TaintClass = TaintClass.LOCAL_SOURCE,
    metadata_only: bool = False,
) -> tuple[IndexStatus, list[IndexEntry]]:
    ws = workspace or WORKSPACE
    entries: list[IndexEntry] = []
    partial = False
    for root_name in roots:
        root = ws / root_name
        if not root.is_dir():
            partial = True
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = str(path.relative_to(ws)).replace("\\", "/")
            reason = _should_exclude(rel)
            if reason:
                entries.append(
                    IndexEntry(
                        path=rel,
                        file_type=path.suffix or "none",
                        size_bytes=0,
                        excluded=True,
                        exclude_reason=reason,
                        taint_class=TaintClass.EXCLUDED.value,
                    )
                )
                continue
            try:
                size = path.stat().st_size
                mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
            except OSError:
                partial = True
                continue
            excerpt = None if metadata_only else _safe_excerpt(path)
            secret_status = "redacted" if excerpt and excerpt.startswith("[REDACTED") else "clean"
            if not metadata_only and path.suffix in {".py", ".md", ".json", ".yaml", ".yml"}:
                try:
                    raw = path.read_text(encoding="utf-8", errors="replace")[:2000]
                    if SecretGuard.contains_secret(raw):
                        secret_status = "refused"
                        excerpt = None
                except OSError:
                    pass
            entries.append(
                IndexEntry(
                    path=rel,
                    file_type=path.suffix or "none",
                    size_bytes=size,
                    content_hash=_file_hash(path),
                    modified_utc=mtime,
                    module_guess=_module_guess(rel),
                    taint_class=taint_class.value,
                    secret_scan_status=secret_status,
                    safe_excerpt=excerpt,
                )
            )
    status = IndexStatus.PARTIAL if partial else IndexStatus.READY
    return status, entries


def snapshot_hash(payload: dict) -> str:
    import json

    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


__all__ = ["EXCLUDE_DIR_NAMES", "WORKSPACE", "_git_head", "index_paths", "snapshot_hash"]
