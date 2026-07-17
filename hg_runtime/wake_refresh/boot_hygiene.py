"""Protected path policy for WRR cleanup."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.wake_refresh.schema import PROTECTED_FRAGMENTS, PROTECTED_PREFIXES

WORKSPACE = Path(__file__).resolve().parents[2]

ALLOWED_TRANSIENT_ROOTS = (
    ".hg-local/tmp",
    ".hg-local/runtime_locks",
    ".hg-local/provider_cache",
    ".hg-local/browser",
    ".hg-local/audio_runtime",
    ".hg-local/runtime",
)

PRESERVE_UNDER_HG_LOCAL = (
    "wake_refresh/last_sleep_state.json",
    "wake_refresh/wake_readiness_context.json",
    "external_start_anchor/",
    "external_witness_journal/",
    "audio_runtime/venv/",
    "audio_runtime/stt/",
    "audio_models/",
)


def normalize_rel(path: Path, workspace: Path | None = None) -> str:
    ws = workspace or WORKSPACE
    # Fast path: scan paths already live under the workspace, so avoid the per-file
    # realpath() (slow on Windows over large transient trees). Fall back to resolve()
    # only when the plain relative_to fails (e.g. a symlinked scan root).
    try:
        return str(path.relative_to(ws)).replace("\\", "/")
    except ValueError:
        try:
            return str(path.resolve().relative_to(ws.resolve())).replace("\\", "/")
        except ValueError:
            return str(path).replace("\\", "/")


def is_protected_path(rel: str) -> tuple[bool, str]:
    low = rel.replace("\\", "/").lower()
    if not low.startswith(".hg-local/") and not low.startswith(".hg-local\\"):
        for prefix in PROTECTED_PREFIXES:
            if low.startswith(prefix.lower()):
                return True, f"protected prefix: {prefix}"
    for frag in PROTECTED_FRAGMENTS:
        if frag in low:
            return True, f"protected fragment: {frag}"
    for preserve in PRESERVE_UNDER_HG_LOCAL:
        if preserve in low:
            return True, f"preserved state: {preserve}"
    if low.startswith("docs/proofs"):
        return True, "proof bundles never cleaned"
    return False, ""


def is_allowed_transient(rel: str) -> bool:
    low = rel.replace("\\", "/")
    if not low.startswith(".hg-local/"):
        return False
    for preserve in PRESERVE_UNDER_HG_LOCAL:
        if preserve.rstrip("/") in low:
            return False
    for root in ALLOWED_TRANSIENT_ROOTS:
        if low.startswith(root + "/") or low == root:
            return True
    # Allow explicit temp patterns under allowed roots
    if "/tmp/" in low or low.endswith("/tmp") or "/temp/" in low:
        return True
    return False


__all__ = ["ALLOWED_TRANSIENT_ROOTS", "WORKSPACE", "is_allowed_transient", "is_protected_path", "normalize_rel"]
