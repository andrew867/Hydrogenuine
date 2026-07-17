#!/usr/bin/env python3
"""Fail public trees that contain Python bytecode or bytecode-only packages."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


def ignored(path: Path) -> bool:
    return bool(set(path.parts) & {".git", ".pytest_cache", "__pycache__", "node_modules"})


def scan(root: Path) -> list[str]:
    failures: list[str] = []
    for pyc in sorted(p for p in root.rglob("*.pyc") if p.is_file() and not ignored(p)):
        failures.append(f"{pyc.relative_to(root)}: bytecode file is not allowed")
    for directory in sorted(p for p in root.rglob("*") if p.is_dir() and not ignored(p)):
        if any(directory.glob("*.pyc")) and not any(directory.glob("*.py")):
            failures.append(f"{directory.relative_to(root)}: bytecode without adjacent source")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.exists():
        print(f"root does not exist: {root}", file=sys.stderr)
        return 2
    failures = scan(root)
    if failures:
        print("bytecode gate failed:")
        for item in failures:
            print(f"- {item}")
        return 1
    print(f"ok: no bytecode-only directories under {root.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
