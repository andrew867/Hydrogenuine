"""Disposable drill harness — setup/teardown with zero residue (CT-07 RBK)."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from hg_srp.apply_types import content_hash


@dataclass
class DrillHarness:
    root: Path
    clock: Callable[[], str] = field(default_factory=lambda: (lambda: "2026-06-12T15:00:00.000000Z"))
    artifacts: list[dict[str, Any]] = field(default_factory=list)

    @property
    def repo_root(self) -> Path:
        return self.root

    def snapshot_dir(self) -> Path:
        return self.root / ".rbk_snapshot"

    def write_snapshot_manifest(self, files: dict[str, str]) -> dict[str, Any]:
        manifest = {
            "schema": "rbk_snapshot_v1",
            "timestamp": self.clock(),
            "files": files,
            "manifest_hash": content_hash({"files": files}),
        }
        snap = self.snapshot_dir()
        snap.mkdir(parents=True, exist_ok=True)
        (snap / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        for rel, content in files.items():
            path = snap / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return manifest

    def restore_snapshot(self) -> tuple[bool, str]:
        manifest_path = self.snapshot_dir() / "manifest.json"
        if not manifest_path.exists():
            return False, "missing_snapshot"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for rel in manifest.get("files", {}):
            src = self.snapshot_dir() / rel
            dst = self.root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        restored_hash = content_hash({"files": manifest.get("files", {})})
        return restored_hash == manifest.get("manifest_hash"), restored_hash

    def teardown(self) -> bool:
        """Return True if no owned drill residue remains."""
        residue = [
            p
            for p in self.root.rglob("*")
            if p.is_file() and (".tmp_srp_apply" in p.as_posix() or ".rbk_drill" in p.as_posix())
        ]
        for path in list(self.root.glob(".tmp_srp_apply")) + list(self.root.glob(".rbk_drill")):
            shutil.rmtree(path, ignore_errors=True)
        return not residue or all(not p.exists() for p in residue)


def file_hash(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


__all__ = ["DrillHarness", "file_hash"]
