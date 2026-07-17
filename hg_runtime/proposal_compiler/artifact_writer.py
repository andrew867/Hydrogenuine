"""Phase 37 work-package artifact writer.

Writes a compiled package to ``docs/planning/generated_work_packages/<id>/`` and
maintains the ``WORK_PACKAGE_INDEX.md`` summary. Never silently overwrites a
package whose content differs: a differing package is written to a
hash-suffixed sibling directory; identical content is idempotently rewritten.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

WORK_PACKAGE_ROOT_NAME = "docs/planning/generated_work_packages"
INDEX_NAME = "WORK_PACKAGE_INDEX.md"


def _package_dir(root: Path, result: Mapping[str, Any]) -> Path:
    base = root / result["proposal_id"]
    suffix = result["package_hash"].removeprefix("sha256:")[:8]
    if not base.exists():
        return base
    existing_receipt = base / "compiler_receipt.json"
    if existing_receipt.is_file():
        try:
            prior = json.loads(existing_receipt.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prior = {}
        if prior.get("package_hash") == result["package_hash"]:
            return base  # identical content: idempotent rewrite
    return root / f"{result['proposal_id']}__{suffix}"


def write_work_package(root: Path, result: Mapping[str, Any]) -> dict[str, Any]:
    root = Path(root)
    target = _package_dir(root, result)
    target.mkdir(parents=True, exist_ok=True)
    for name, content in result["docs"].items():
        (target / name).write_text(content, encoding="utf-8")
    (target / "compiler_receipt.json").write_text(
        json.dumps(result["receipt"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "proposal_id": result["proposal_id"],
        "status": result["status"],
        "path": str(target),
        "package_hash": result["package_hash"],
        "receipt_hash": result["receipt"]["receipt_hash"],
        "doc_names": result["doc_names"],
    }


def write_index(root: Path, written: list[Mapping[str, Any]]) -> str:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Generated Work Package Index",
        "",
        "> PLANNING_DOCS_ONLY_NOT_IMPLEMENTATION. Compiled by Phase 37; not implementations.",
        "",
        "| proposal_id | status | path | package_hash |",
        "| --- | --- | --- | --- |",
    ]
    for row in sorted(written, key=lambda item: item["proposal_id"]):
        rel = Path(row["path"]).name
        lines.append(f"| {row['proposal_id']} | {row['status']} | {rel} | {row['package_hash'][:18]} |")
    text = "\n".join(lines) + "\n"
    (root / INDEX_NAME).write_text(text, encoding="utf-8")
    return text


__all__ = ["INDEX_NAME", "WORK_PACKAGE_ROOT_NAME", "write_index", "write_work_package"]
