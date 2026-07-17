"""Bounded local artifact store for Workbench uploads.

Writes uploaded file *bytes* to a per-run, sealed directory
`<run_dir>/artifacts/<artifact_id>_<sanitized_filename>` and returns only
metadata (server-computed sha256, size, stored path reference relative to the
run dir). No external storage; no cloud SDK; nothing executes the bytes.

Doctrine locks enforced here:
  * The untrusted filename is sanitized to a safe basename (no ``..``, no path
    separators, no null/control bytes, no leading dots), then the *resolved*
    target path is asserted to stay inside ``<run_dir>/artifacts/`` — the
    containment assertion (not the string scrub) is the real traversal boundary.
  * The write is chunked with a hard size cap (``HG_WORKBENCH_MAX_UPLOAD_BYTES``,
    default 25 MiB); Content-Length is never trusted — overflow raises
    ``ArtifactTooLargeError`` and the partial file is removed.
  * Raw bytes are returned to the caller only as a path reference + sha256; the
    receipt layer records the hash/size/ref, never the content.
"""
from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

# 25 MiB conservative default; override via env for tests / policy.
DEFAULT_MAX_UPLOAD_BYTES = 25 * 1024 * 1024
_CHUNK = 1024 * 1024

# Whitelist basename: alnum start, then alnum/dot/dash/underscore, bounded length.
_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]")
_ARTIFACTS_SUBDIR = "artifacts"


class ArtifactStoreError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ArtifactTooLargeError(ArtifactStoreError):
    """Raised when the streamed bytes exceed the configured cap."""


def max_upload_bytes() -> int:
    """Configured upload cap; conservative default, env-overridable."""
    raw = os.environ.get("HG_WORKBENCH_MAX_UPLOAD_BYTES")
    if raw is None:
        return DEFAULT_MAX_UPLOAD_BYTES
    try:
        val = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_MAX_UPLOAD_BYTES
    return val if val > 0 else DEFAULT_MAX_UPLOAD_BYTES


def sanitize_filename(filename: str) -> str:
    """Reduce an untrusted client filename to a safe stored basename.

    Strips directory components, ``..``, null/control bytes and leading dots;
    collapses anything outside ``[A-Za-z0-9._-]`` to ``_``; bounds the length.
    Returns ``"upload.bin"`` when nothing usable remains.
    """
    # Drop any path structure the client tried to smuggle (both separators).
    base = str(filename or "").replace("\\", "/").split("/")[-1]
    base = base.replace("\x00", "")
    base = _SAFE_FILENAME.sub("_", base)
    base = base.lstrip(".")               # no leading dots -> no hidden/relative
    base = base[:128]
    return base or "upload.bin"


@dataclass(frozen=True)
class StoredArtifact:
    """Result of a bounded write — metadata only, never the bytes."""
    stored_path_ref: str      # relative to the run dir, e.g. "artifacts/<id>_<name>"
    absolute_path: str
    size_bytes: int
    content_hash: str         # "sha256:<hex>" computed server-side over the bytes
    sanitized_filename: str


def _resolve_within(base: Path, target: Path) -> Path:
    """Assert ``target`` resolves inside ``base`` (the real traversal boundary)."""
    base_r = base.resolve()
    target_r = target.resolve()
    if base_r != target_r and base_r not in target_r.parents:
        raise ArtifactStoreError("path_traversal")
    return target_r


def store_upload(
    *,
    run_dir: Path,
    artifact_id: str,
    filename: str,
    chunks: Iterable[bytes],
    max_bytes: Optional[int] = None,
) -> StoredArtifact:
    """Stream ``chunks`` into the run's artifact dir under a bounded cap.

    ``run_dir`` is the caller-owned sealed per-run directory. The stored file is
    ``<run_dir>/artifacts/<artifact_id>_<sanitized>``. Returns metadata only.
    Raises :class:`ArtifactTooLargeError` on overflow (partial file removed) and
    :class:`ArtifactStoreError` on a traversal / bad-id violation.
    """
    if not re.fullmatch(r"wba-[0-9a-f]{8,}", artifact_id):
        raise ArtifactStoreError("bad_artifact_id")
    cap = max_bytes if (max_bytes and max_bytes > 0) else max_upload_bytes()

    run_dir = Path(run_dir)
    artifacts_dir = _resolve_within(run_dir, run_dir / _ARTIFACTS_SUBDIR)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    sanitized = sanitize_filename(filename)
    stored_name = f"{artifact_id}_{sanitized}"
    target = _resolve_within(artifacts_dir, artifacts_dir / stored_name)

    hasher = hashlib.sha256()
    total = 0
    try:
        with open(target, "wb") as fh:
            for chunk in chunks:
                if not chunk:
                    continue
                total += len(chunk)
                if total > cap:
                    raise ArtifactTooLargeError("upload_too_large")
                hasher.update(chunk)
                fh.write(chunk)
    except ArtifactTooLargeError:
        target.unlink(missing_ok=True)
        raise
    except Exception:
        target.unlink(missing_ok=True)
        raise

    ref = f"{_ARTIFACTS_SUBDIR}/{stored_name}"
    return StoredArtifact(
        stored_path_ref=ref, absolute_path=str(target), size_bytes=total,
        content_hash="sha256:" + hasher.hexdigest(), sanitized_filename=sanitized)


def read_in_chunks(data: bytes, size: int = _CHUNK) -> Iterable[bytes]:
    """Adapt an in-memory ``bytes`` payload to the chunked writer (tests/clients)."""
    for i in range(0, len(data), size):
        yield data[i:i + size]


__all__ = [
    "ArtifactStoreError", "ArtifactTooLargeError", "DEFAULT_MAX_UPLOAD_BYTES",
    "StoredArtifact", "max_upload_bytes", "read_in_chunks", "sanitize_filename",
    "store_upload",
]
