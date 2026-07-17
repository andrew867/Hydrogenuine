"""Proof bundle tamper-evidence hashing.

Computes SHA-256 hashes for all files in a proof directory and writes
a proof integrity manifest. This is tamper-evidence foundation, not
identity signing. No keys required.

Read-only on source files. Only writes new integrity files.
No mutation of existing proof artifacts.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

VOLATILE_FILES = frozenset({
    ".write_test",
    "proof_integrity_manifest.json",
    "proof_integrity_manifest.sha256",
})

VOLATILE_EXTENSIONS = frozenset({
    ".pyc", ".pyo", ".tmp", ".swp",
})


def _should_hash(filename: str) -> bool:
    if filename in VOLATILE_FILES:
        return False
    _, ext = os.path.splitext(filename)
    if ext in VOLATILE_EXTENSIONS:
        return False
    return True


def hash_file(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def hash_proof_directory(proof_dir: str) -> dict:
    file_hashes: dict[str, str] = {}
    for root, dirs, files in os.walk(proof_dir):
        dirs.sort()
        for fname in sorted(files):
            if not _should_hash(fname):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, proof_dir).replace("\\", "/")
            file_hashes[rel] = hash_file(fpath)
    return file_hashes


def build_integrity_manifest(proof_dir: str) -> dict:
    file_hashes = hash_proof_directory(proof_dir)

    combined = hashlib.sha256()
    for rel in sorted(file_hashes.keys()):
        combined.update(f"{rel}:{file_hashes[rel]}\n".encode("utf-8"))

    manifest = {
        "proof_dir": os.path.basename(proof_dir),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "file_count": len(file_hashes),
        "combined_hash": combined.hexdigest(),
        "files": file_hashes,
        "hash_algorithm": "sha256",
        "is_tamper_evidence_only": True,
        "is_identity_signing": False,
        "operator_review_required": True,
        "promotion_allowed": False,
    }
    return manifest


def write_integrity_manifest(proof_dir: str,
                             out_dir: str | None = None) -> str:
    manifest = build_integrity_manifest(proof_dir)
    target_dir = out_dir or proof_dir
    os.makedirs(target_dir, exist_ok=True)

    manifest_path = os.path.join(target_dir, "proof_integrity_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    sha_path = os.path.join(target_dir, "proof_integrity_manifest.sha256")
    with open(sha_path, "w", encoding="utf-8") as f:
        f.write(f"{manifest['combined_hash']}  proof_integrity_manifest.json\n")

    return manifest_path


def verify_integrity(proof_dir: str, manifest_path: str) -> dict:
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    current = hash_proof_directory(proof_dir)
    expected = manifest.get("files", {})

    added = sorted(set(current.keys()) - set(expected.keys()))
    removed = sorted(set(expected.keys()) - set(current.keys()))
    changed = sorted(
        k for k in set(current.keys()) & set(expected.keys())
        if current[k] != expected[k]
    )

    ok = not added and not removed and not changed

    return {
        "verified": ok,
        "added_files": added,
        "removed_files": removed,
        "changed_files": changed,
        "files_checked": len(current),
        "expected_files": len(expected),
    }
