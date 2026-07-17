"""Transient artifact scan."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

from hg_runtime.wake_refresh.boot_hygiene import WORKSPACE, is_allowed_transient, is_protected_path, normalize_rel
from hg_runtime.wake_refresh.schema import CleanupDecision, TransientArtifact, WasteClass, WakeHygieneState
from hg_runtime.wake_refresh.stale_locks import detect_stale_locks

SCAN_ROOTS = [
    ".hg-local/tmp",
    ".hg-local/runtime_locks",
    ".hg-local/provider_cache",
    ".hg-local/browser",
    ".hg-local/audio_runtime",
    ".hg-local/runtime",
]

STALE_AGE_S = 300


def _hash_file(path: Path) -> str | None:
    try:
        data = path.read_bytes()[:65536]
        return hashlib.sha256(data).hexdigest()
    except OSError:
        return None


def _classify_path(rel: str) -> WasteClass:
    low = rel.replace("\\", "/").lower()
    if "panic" in low:
        return WasteClass.STALE_PANIC
    if "lock" in low or rel.startswith(".hg-local/runtime_locks"):
        return WasteClass.STALE_LOCK
    if "/browser/" in low or low.startswith(".hg-local/browser/"):
        return WasteClass.PARTIAL_BROWSER_CAPTURE
    if "/audio_runtime/tts/" in low and low.endswith(".wav"):
        return WasteClass.PARTIAL_AUDIO_OUTPUT
    if low.endswith("_receipt.json") or low.endswith("download_receipt.json"):
        return WasteClass.UNKNOWN_REVIEW_REQUIRED
    if "provider" in low or "cache" in low:
        return WasteClass.PROVIDER_SESSION_CACHE
    if "orphan" in low or ".pid" in low:
        return WasteClass.ORPHAN_PROCESS_MARKER
    if "draft" in low:
        return WasteClass.EXPIRED_DRAFT
    if "queue" in low:
        return WasteClass.EXPIRED_QUEUE_ITEM
    if "/tmp/" in low or low.endswith(".tmp"):
        return WasteClass.TEMP_FILE
    return WasteClass.UNKNOWN_REVIEW_REQUIRED


def scan_transient(*, workspace: Path | None = None, stale_age_s: float = STALE_AGE_S) -> WakeHygieneState:
    ws = workspace or WORKSPACE
    now = time.time()
    hygiene = WakeHygieneState()
    hygiene.stale_locks = detect_stale_locks(workspace=ws)

    for root_name in SCAN_ROOTS:
        root = ws / root_name
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = normalize_rel(path, ws)
            protected, reason = is_protected_path(rel)
            if protected:
                hygiene.cleanup_decisions.append(
                    CleanupDecision(path=rel, waste_class=WasteClass.UNKNOWN_REVIEW_REQUIRED, allowed=False, reason=reason)
                )
                continue
            if not is_allowed_transient(rel):
                hygiene.cleanup_decisions.append(
                    CleanupDecision(path=rel, waste_class=WasteClass.UNKNOWN_REVIEW_REQUIRED, allowed=False, reason="outside allowed transient scope")
                )
                continue
            try:
                age = now - path.stat().st_mtime
                size = path.stat().st_size
            except OSError:
                continue
            wc = _classify_path(rel)
            stale = age >= stale_age_s or wc in {WasteClass.STALE_PANIC, WasteClass.STALE_LOCK}
            art = TransientArtifact(path=rel, waste_class=wc, size_bytes=size, content_hash=_hash_file(path), stale=stale)
            hygiene.transient_artifacts.append(art)
            if wc == WasteClass.STALE_PANIC:
                hygiene.stale_panic_files.append(rel)
            hygiene.cleanup_decisions.append(
                CleanupDecision(
                    path=rel,
                    waste_class=wc,
                    allowed=stale and not protected,
                    reason="stale transient" if stale else "not stale enough",
                    apply=False,
                )
            )
    return hygiene


__all__ = ["SCAN_ROOTS", "scan_transient"]
