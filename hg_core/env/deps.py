"""Dependency and lockfile verification (CT-16 ENV)."""

from __future__ import annotations

import hashlib
import importlib
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DepCheckResult:
    ok: bool
    detail: str
    versions: dict[str, str]

    def to_payload(self) -> dict[str, Any]:
        return {"ok": self.ok, "detail": self.detail, "versions": self.versions}


def _parse_version(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in version.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        if digits:
            parts.append(int(digits))
    return tuple(parts) if parts else (0,)


def check_python_version(*, min_version: str, max_version: str) -> DepCheckResult:
    current = _parse_version(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    low = _parse_version(min_version)
    high = _parse_version(max_version)
    ok = low <= current[: max(len(low), 2)] <= high[: max(len(high), 2)]
    detail = "python_in_range" if ok else f"python_out_of_range:{sys.version.split()[0]}"
    return DepCheckResult(
        ok=ok,
        detail=detail,
        versions={"python": sys.version.split()[0], "implementation": platform.python_implementation()},
    )


def lockfile_hash(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def verify_lockfile(workspace: Path, *, relative_path: str, expected_hash: str) -> DepCheckResult:
    lock_path = workspace / relative_path
    if not lock_path.exists():
        return DepCheckResult(False, f"lockfile_missing:{relative_path}", {})
    actual = lockfile_hash(lock_path)
    ok = actual == expected_hash
    return DepCheckResult(
        ok=ok,
        detail="lockfile_verified" if ok else f"lockfile_hash_mismatch:{actual}",
        versions={"lockfile": relative_path, "hash": actual},
    )


def check_required_modules(modules: tuple[str, ...]) -> DepCheckResult:
    versions: dict[str, str] = {}
    missing: list[str] = []
    for name in modules:
        try:
            mod = importlib.import_module(name)
        except ImportError:
            missing.append(name)
            continue
        version = getattr(mod, "__version__", "present")
        versions[name] = str(version)
    if missing:
        return DepCheckResult(False, f"required_module_missing:{','.join(missing)}", versions)
    return DepCheckResult(True, "required_modules_present", versions)


__all__ = [
    "DepCheckResult",
    "check_python_version",
    "check_required_modules",
    "lockfile_hash",
    "verify_lockfile",
]
