"""Proposal backlog writer with deterministic replay."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.autonomous_proposal_soak.schemas import PROPOSAL_BACKLOG_SCHEMA, neutral_flags


def _yaml_scalar(value: Any) -> str:
    text = str(value).replace('"', '\\"')
    return f'"{text}"'


def backlog_yaml(proposals: list[Mapping[str, Any]]) -> str:
    lines = ["schema: proposal_backlog_v1", "proposals:"]
    for proposal in proposals:
        lines.append(f"  - proposal_id: {_yaml_scalar(proposal['proposal_id'])}")
        lines.append(f"    title: {_yaml_scalar(proposal['title'])}")
        lines.append(f"    severity: {_yaml_scalar(proposal['severity'])}")
        lines.append(f"    authority_risk: {_yaml_scalar(proposal['authority_risk'])}")
        lines.append("    acceptance_criteria:")
        for item in proposal.get("acceptance_criteria", []):
            lines.append(f"      - {_yaml_scalar(item)}")
    return "\n".join(lines) + "\n"


def write_backlog(path: Path, proposals: list[Mapping[str, Any]]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = backlog_yaml(proposals)
    path.write_text(text, encoding="utf-8")
    record = {
        "schema": PROPOSAL_BACKLOG_SCHEMA,
        "path": str(path),
        "proposal_count": len(proposals),
        "backlog_hash": canonical_hash({"yaml": text}),
        **neutral_flags(),
    }
    return record


def replay_backlog(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return {"ok": text.startswith("schema: proposal_backlog_v1"), "backlog_hash": canonical_hash({"yaml": text})}


def write_jsonl(path: Path, rows: list[Mapping[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


__all__ = ["backlog_yaml", "replay_backlog", "write_backlog", "write_jsonl"]
