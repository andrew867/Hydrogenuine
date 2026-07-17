"""Doc registry loader (CT-17 DOC)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CLAIM_CATEGORIES = ("implemented", "scaffold", "gated", "stub", "future", "unknown")


@dataclass(frozen=True)
class DocRegistry:
    schema: str
    claim_bearing_globs: tuple[str, ...]
    head_binding_paths: tuple[str, ...]
    master_timeline: str
    sotu_skeleton: str
    ct_phase_reports: dict[str, str]
    free_doc_globs: tuple[str, ...]


@dataclass(frozen=True)
class ClaimRules:
    schema: str
    claim_categories: tuple[str, ...]
    status_word_map: dict[str, str]
    hedge_patterns: tuple[str, ...]
    complete_qualifiers: tuple[str, ...]
    forbidden_complete: tuple[dict[str, Any], ...]
    proof_topics: dict[str, dict[str, Any]]


def default_registry_path(workspace: Path | None = None) -> Path:
    root = workspace or Path(__file__).resolve().parents[2]
    return root / "config" / "doc_registry_v1.yaml"


def default_rules_path(workspace: Path | None = None) -> Path:
    root = workspace or Path(__file__).resolve().parents[2]
    return root / "config" / "doc_claim_rules_v1.yaml"


def load_registry(path: Path | None = None, *, workspace: Path | None = None) -> DocRegistry:
    registry_path = path or default_registry_path(workspace)
    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    if payload.get("schema") != "doc_registry_v1":
        raise ValueError(f"unsupported doc registry schema: {payload.get('schema')}")
    return DocRegistry(
        schema="doc_registry_v1",
        claim_bearing_globs=tuple(str(x) for x in payload.get("claim_bearing_globs", ())),
        head_binding_paths=tuple(str(x) for x in payload.get("head_binding_paths", ())),
        master_timeline=str(payload.get("master_timeline", "")),
        sotu_skeleton=str(payload.get("sotu_skeleton", "")),
        ct_phase_reports={str(k): str(v) for k, v in payload.get("ct_phase_reports", {}).items()},
        free_doc_globs=tuple(str(x) for x in payload.get("free_doc_globs", ())),
    )


def load_claim_rules(path: Path | None = None, *, workspace: Path | None = None) -> ClaimRules:
    rules_path = path or default_rules_path(workspace)
    payload = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    if payload.get("schema") != "doc_claim_rules_v1":
        raise ValueError(f"unsupported claim rules schema: {payload.get('schema')}")
    return ClaimRules(
        schema="doc_claim_rules_v1",
        claim_categories=tuple(str(x) for x in payload.get("claim_categories", CLAIM_CATEGORIES)),
        status_word_map={str(k): str(v) for k, v in payload.get("status_word_map", {}).items()},
        hedge_patterns=tuple(str(x) for x in payload.get("hedge_patterns", ())),
        complete_qualifiers=tuple(str(x).lower() for x in payload.get("complete_qualifiers", ())),
        forbidden_complete=tuple(dict(x) for x in payload.get("forbidden_complete_without_proof", ())),
        proof_topics={str(k): dict(v) for k, v in payload.get("proof_topics", {}).items()},
    )


def enumerate_claim_bearing_docs(workspace: Path, registry: DocRegistry) -> list[Path]:
    seen: set[Path] = set()
    docs: list[Path] = []
    for pattern in registry.claim_bearing_globs:
        for path in sorted(workspace.glob(pattern)):
            if not path.is_file():
                continue
            if path in seen:
                continue
            if _is_free_doc(path, workspace, registry):
                continue
            seen.add(path)
            docs.append(path)
    return docs


def _is_free_doc(path: Path, workspace: Path, registry: DocRegistry) -> bool:
    rel = str(path.relative_to(workspace)).replace("\\", "/")
    for pattern in registry.free_doc_globs:
        if path.match(pattern) or Path(rel).match(pattern):
            return True
    return False


__all__ = [
    "CLAIM_CATEGORIES",
    "ClaimRules",
    "DocRegistry",
    "default_registry_path",
    "default_rules_path",
    "enumerate_claim_bearing_docs",
    "load_claim_rules",
    "load_registry",
]
