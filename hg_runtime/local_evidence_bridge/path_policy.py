"""LEB-4 operator inbox path policy.

Local-only, path-bounded ingestion policy. The operator inbox is DISABLED by
default. Even when explicitly enabled (tests/gate only), it accepts only files
that live under an explicitly configured allowed root, are listed in an explicit
manifest, carry an allowed text extension, are not binary, are not oversized, and
do not escape the allowed root via traversal or symlink.

No directory crawling. No arbitrary path. No PDF/OCR. No binaries. No symlink
escape. No web. No providers. No belief promotion. No authority.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from hg_runtime.local_evidence_bridge.schemas import (
    EvidenceBridgeError,
    assert_neutral,
    neutral_flags,
    record_hash,
)

# The single allowed operator-inbox root used by tests and the gate.
DEFAULT_INBOX_ROOT = "tests/fixtures/operator_inbox"
INBOX_ENABLED_BY_DEFAULT = False
ALLOWED_EXTENSIONS = (".md", ".txt")
DENIED_EXTENSIONS = (".pdf", ".bin", ".exe", ".png", ".jpg", ".jpeg", ".gif", ".zip", ".gz", ".so", ".dll", ".ipynb")
MAX_BYTES = 16_384


def build_inbox_policy(
    *,
    enabled: bool = INBOX_ENABLED_BY_DEFAULT,
    allowed_root: str = DEFAULT_INBOX_ROOT,
    max_bytes: int = MAX_BYTES,
) -> dict:
    """Build an operator_inbox_policy_v1 record. Disabled unless explicitly enabled."""
    policy = {
        "schema_version": "1",
        "record_type": "operator_inbox_policy_v1",
        "policy_id": "leb4-operator-inbox-policy",
        "operator_inbox_enabled": bool(enabled),
        "operator_inbox_disabled_by_default": True,
        "explicit_enable_flag_required": True,
        "explicit_manifest_required": True,
        "allowed_root": allowed_root.replace("\\", "/"),
        "allowed_extensions": list(ALLOWED_EXTENSIONS),
        "denied_extensions": list(DENIED_EXTENSIONS),
        "max_bytes": int(max_bytes),
        "directory_crawling_enabled": False,
        "arbitrary_path_access_enabled": False,
        "pdf_ocr_enabled": False,
        "binary_ingestion_enabled": False,
        "symlink_following_enabled": False,
        "links_followed": False,
        "web_access_enabled": False,
        "provider_access_enabled": False,
        **neutral_flags(),
    }
    policy["record_hash"] = record_hash(policy)
    assert_neutral(policy)
    return policy


def path_within_root(base: Path, candidate: Path) -> bool:
    """Return True iff `candidate` is `base` or strictly contained under it."""
    return candidate == base or base in candidate.parents


def validate_inbox_relative_path(relative_path: str, allowed_root: str) -> None:
    """Lexical guard: reject absolute paths, traversal, and out-of-root paths."""
    normalized = PurePosixPath(relative_path.replace("\\", "/"))
    if normalized.is_absolute() or ".." in normalized.parts:
        raise EvidenceBridgeError("path_traversal_or_absolute_path_forbidden")
    root = PurePosixPath(allowed_root.replace("\\", "/"))
    if not (normalized == root or root in normalized.parents):
        raise EvidenceBridgeError("source_path_outside_allowed_root")


def resolve_inbox_path(root: Path, relative_path: str, allowed_root: str) -> Path:
    """Resolve and confirm the real path stays inside the allowed root (symlink-safe)."""
    validate_inbox_relative_path(relative_path, allowed_root)
    base = (root / allowed_root).resolve()
    resolved = (root / relative_path).resolve()
    if not path_within_root(base, resolved):
        raise EvidenceBridgeError("symlink_or_path_escape_forbidden")
    return resolved


def extension_allowed(relative_path: str) -> bool:
    suffix = PurePosixPath(relative_path.replace("\\", "/")).suffix.lower()
    return suffix in ALLOWED_EXTENSIONS and suffix not in DENIED_EXTENSIONS
