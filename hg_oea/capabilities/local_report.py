"""Harmless local report file write capability."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Tuple

from hg_oea.config import OEAConfig
from hg_oea.validation import ValidationError, canonical_hash, resolve_proof_path


def execute_local_report_write(
    arguments: Mapping[str, object],
    *,
    config: OEAConfig,
) -> Tuple[str, Tuple[str, ...]]:
    filename = str(arguments.get("filename", ""))
    content = str(arguments.get("content", ""))
    overwrite = bool(arguments.get("overwrite", False))
    target = resolve_proof_path(config.proof_dir, filename)
    config.proof_dir.mkdir(parents=True, exist_ok=True)
    if target.exists() and not overwrite:
        raise ValidationError("file_exists_without_overwrite")
    target.write_text(content, encoding="utf-8")
    output_hash = canonical_hash({"path": str(target), "bytes": len(content.encode("utf-8"))})
    return output_hash, (str(target),)


__all__ = ["execute_local_report_write"]
