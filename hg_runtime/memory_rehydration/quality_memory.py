"""Load quality/weak-output data from prior audit."""

from __future__ import annotations

import os
from hg_runtime.memory_rehydration.proof_loader import load_json, load_jsonl


def load_quality_summary(audit_path: str) -> dict | None:
    return load_json(os.path.join(audit_path, "quality_issue_taxonomy.json"))


def load_weak_output_candidates(audit_path: str) -> list[dict]:
    return load_jsonl(os.path.join(audit_path, "weak_output_candidates.jsonl"))
