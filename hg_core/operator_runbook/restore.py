"""Restore helpers from git bundle or proof artifacts (CT-15 RUN)."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.operator_runbook.replay import verify_proof_bundle


@dataclass(frozen=True)
class RestoreResult:
    ok: bool
    detail: str
    restored_paths: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "detail": self.detail,
            "restored_paths": list(self.restored_paths),
        }


def restore_from_git_bundle(bundle_path: Path, dest_dir: Path) -> RestoreResult:
    if not bundle_path.exists():
        return RestoreResult(False, "git_bundle_missing")
    dest_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "bundle", "verify", str(bundle_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return RestoreResult(False, f"git_bundle_verify_failed:{result.stderr.strip()}")
    clone_dir = dest_dir / "restored_repo"
    if clone_dir.exists():
        shutil.rmtree(clone_dir)
    clone = subprocess.run(
        ["git", "clone", str(bundle_path), str(clone_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    if clone.returncode != 0:
        return RestoreResult(False, f"git_clone_failed:{clone.stderr.strip()}")
    return RestoreResult(True, "git_bundle_restored", restored_paths=(str(clone_dir),))


def restore_from_proof_bundle(bundle_dir: Path, dest_dir: Path) -> RestoreResult:
    verify = verify_proof_bundle(bundle_dir)
    if not verify.ok:
        return RestoreResult(False, verify.detail, restored_paths=())
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / bundle_dir.name
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(bundle_dir, out)
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    marker = dest_dir / "restore_marker.json"
    marker.write_text(
        json.dumps(
            {
                "schema": "restore_marker_v1",
                "source_bundle": str(bundle_dir),
                "manifest_head": manifest.get("head"),
                "manifest_digest": f"sha256:{digest}",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return RestoreResult(
        True,
        "proof_bundle_restored",
        restored_paths=(str(out), str(marker)),
    )


__all__ = ["RestoreResult", "restore_from_git_bundle", "restore_from_proof_bundle"]
