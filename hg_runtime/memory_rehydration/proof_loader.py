"""Load proof bundles as context without importing authority."""

from __future__ import annotations

import json
import os


def load_json(path: str) -> dict | list | None:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def load_proof_summary(proof_path: str) -> dict | None:
    """Load a proof bundle's final report or audit manifest as context."""
    for name in ("final_report.json", "audit_manifest.json", "report_snapshot.md"):
        p = os.path.join(proof_path, name)
        if os.path.exists(p):
            if name.endswith(".json"):
                return load_json(p)
            with open(p, "r", encoding="utf-8") as f:
                return {"report_text": f.read(), "source_file": name}
    return None
