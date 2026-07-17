"""Download quarantine — metadata fixtures, no auto-open."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from hg_runtime.web_action_queue.sanitization import WebActionSanitizer
from hg_runtime.web_action_queue.schema import WebDownloadQuarantineRef

WORKSPACE = Path(__file__).resolve().parents[2]
DEFAULT_QUARANTINE_ROOT = WORKSPACE / ".hg-local" / "web_quarantine"


def new_quarantine_id() -> str:
    return f"wq-{uuid.uuid4().hex[:12]}"


def quarantine_root(workspace: Path | None = None) -> Path:
    return (workspace or WORKSPACE) / ".hg-local" / "web_quarantine"


def create_quarantine_metadata(
    *,
    original_url: str,
    filename: str,
    source_action_ref: str,
    workspace: Path | None = None,
    sha256: str | None = None,
    mime_type: str | None = None,
    size_bytes: int | None = None,
) -> WebDownloadQuarantineRef:
    root = quarantine_root(workspace)
    root.mkdir(parents=True, exist_ok=True)
    qid = new_quarantine_id()
    safe_name = Path(filename).name[:120] or "download.bin"
    stored = root / qid / safe_name
    stored.parent.mkdir(parents=True, exist_ok=True)
    # Metadata-only fixture: placeholder file, never auto-opened
    if not stored.exists():
        stored.write_bytes(b"")

    ref = WebDownloadQuarantineRef(
        quarantine_id=qid,
        original_url_redacted=WebActionSanitizer.redact_url(original_url) or "",
        filename=safe_name,
        stored_path=f".hg-local/web_quarantine/{qid}/{safe_name}",
        sha256=sha256,
        mime_type=mime_type,
        size_bytes=size_bytes,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_action_ref=source_action_ref,
        status="quarantined",
        notes="metadata-only fixture; operator must approve before use",
    )
    meta_path = root / qid / "metadata.json"
    meta_path.write_text(json.dumps(ref.to_payload(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return ref


__all__ = [
    "DEFAULT_QUARANTINE_ROOT",
    "create_quarantine_metadata",
    "new_quarantine_id",
    "quarantine_root",
]
