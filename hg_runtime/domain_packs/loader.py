"""Domain pack loading and hash validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.memory_ledger.schemas import OperationControl
from hg_runtime.domain_packs.schemas import DomainPackError, validate_domain_pack


def _hash_body(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "pack_hash"}


def compute_pack_hash(payload: Mapping[str, Any]) -> str:
    return canonical_hash(_hash_body(payload))


def load_domain_pack(
    source: Mapping[str, Any] | Path,
    *,
    known_tool_refs: set[str] | None = None,
    known_skill_refs: set[str] | None = None,
    known_memory_refs: set[str] | None = None,
    control: OperationControl | None = None,
) -> dict[str, Any]:
    reason = (control or OperationControl()).refuse_reason(stop_blocks=True)
    if reason:
        raise DomainPackError(reason)
    if isinstance(source, Path):
        payload = json.loads(source.read_text(encoding="utf-8"))
    else:
        payload = dict(source)
    expected = compute_pack_hash(payload)
    if not payload.get("pack_hash"):
        raise DomainPackError("unhashed_pack_rejected")
    return validate_domain_pack(
        payload,
        expected_hash=expected,
        known_tool_refs=known_tool_refs,
        known_skill_refs=known_skill_refs,
        known_memory_refs=known_memory_refs,
    )


__all__ = ["compute_pack_hash", "load_domain_pack"]
