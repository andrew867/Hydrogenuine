"""Load seed progress from a prior proof bundle."""

from __future__ import annotations

import os
from hg_runtime.memory_rehydration.proof_loader import load_json, load_jsonl


def load_seed_progress(proof_path: str) -> list[dict]:
    return load_jsonl(os.path.join(proof_path, "research_seed_progress.jsonl"))


def load_seed_progress_summary(audit_path: str) -> dict | None:
    return load_json(os.path.join(audit_path, "seed_progress_summary.json"))
