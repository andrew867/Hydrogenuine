"""Load evidence gaps from prior proof/audit bundles."""

from __future__ import annotations

import os
from hg_runtime.memory_rehydration.proof_loader import load_jsonl


def load_evidence_gaps(proof_path: str) -> list[dict]:
    return load_jsonl(os.path.join(proof_path, "evidence_gap_ledger.jsonl"))


def load_evidence_gap_backlog(audit_path: str) -> list[dict]:
    return load_jsonl(os.path.join(audit_path, "evidence_gap_backlog.jsonl"))
