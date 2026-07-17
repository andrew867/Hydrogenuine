"""Proof bundle index for claim validation (CT-17 DOC)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ProofIndex:
    packs: dict[str, dict[str, Any]] = field(default_factory=dict)
    topics: dict[str, bool] = field(default_factory=dict)

    def topic_proven(self, topic_id: str) -> bool:
        return bool(self.topics.get(topic_id))


def _latest_bundle_dir(pack_dir: Path) -> Path | None:
    if not pack_dir.exists():
        return None
    bundles = sorted(p for p in pack_dir.iterdir() if p.is_dir())
    return bundles[-1] if bundles else None


def _load_gate_result(bundle_dir: Path) -> dict[str, Any] | None:
    gate_path = bundle_dir / "gate_result.json"
    if not gate_path.exists():
        return None
    try:
        return json.loads(gate_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _gate_has_not_proven(gate: dict[str, Any], check_names: list[str]) -> bool:
    verdicts = gate.get("verdicts") or gate.get("checks") or []
    if isinstance(verdicts, list):
        for item in verdicts:
            if not isinstance(item, dict):
                continue
            name = str(item.get("check", ""))
            verdict = str(item.get("verdict", ""))
            if name in check_names and verdict.startswith("not_proven"):
                return True
    not_proven = gate.get("not_proven") or []
    for entry in not_proven:
        entry_s = str(entry)
        if any(name in entry_s for name in check_names):
            return True
    return False


def build_proof_index(workspace: Path, rules_topics: dict[str, dict[str, Any]]) -> ProofIndex:
    proofs_root = workspace / "docs" / "proofs" / "connective_tissue"
    index = ProofIndex()

    for pack_dir in sorted(proofs_root.glob("pack*")):
        latest = _latest_bundle_dir(pack_dir)
        if latest is None:
            continue
        gate = _load_gate_result(latest)
        if gate is None:
            continue
        index.packs[pack_dir.name] = {
            "bundle": str(latest.relative_to(workspace)).replace("\\", "/"),
            "ok": bool(gate.get("ok")),
            "gate": gate.get("gate"),
            "not_proven": gate.get("not_proven", []),
        }

    for topic_id, spec in rules_topics.items():
        packs = [str(p) for p in spec.get("packs", [])]
        require_ok = bool(spec.get("require_ok", True))
        disallow_np = [str(x) for x in spec.get("disallow_not_proven", [])]
        proven = False
        if packs:
            for pack in packs:
                pack_info = index.packs.get(pack)
                if not pack_info:
                    continue
                if require_ok and not pack_info.get("ok"):
                    continue
                bundle_dir = workspace / pack_info["bundle"]
                gate = _load_gate_result(bundle_dir) if bundle_dir.exists() else None
                if gate and disallow_np and _gate_has_not_proven(gate, disallow_np):
                    continue
                proven = True
                break
        index.topics[topic_id] = proven

    return index


def extract_head_from_doc(text: str) -> str | None:
    match = re.search(r"\*\*HEAD:\*\*\s*`([0-9a-f]{7,40})`", text, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"\*\*HEAD:\*\*\s*([0-9a-f]{7,40})", text, re.IGNORECASE)
    return match.group(1) if match else None


def has_stale_banner(text: str) -> bool:
    return bool(re.search(r"STALE\s+as\s+of\s+`?([0-9a-f]{7,40})`?", text, re.IGNORECASE))


__all__ = ["ProofIndex", "build_proof_index", "extract_head_from_doc", "has_stale_banner"]
